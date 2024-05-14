# import os

# from flask import (Flask, redirect, render_template, request,
#                    send_from_directory, url_for)

# app = Flask(__name__)


# @app.route('/')
# def index():
#    print('Request for index page received')
#    return render_template('index.html')

# @app.route('/favicon.ico')
# def favicon():
#     return send_from_directory(os.path.join(app.root_path, 'static'),
#                                'favicon.ico', mimetype='image/vnd.microsoft.icon')

# @app.route('/hello', methods=['POST'])
# def hello():
#    name = request.form.get('name')

#    if name:
#        print('Request for hello page received with name=%s' % name)
#        return render_template('hello.html', name = name)
#    else:
#        print('Request for hello page received with no name or blank name -- redirecting')
#        return redirect(url_for('index'))


# if __name__ == '__main__':
#    app.run()

import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, logout_user
import pytz
from dotenv import load_dotenv
from flask_migrate import Migrate

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

malaysia_tz = pytz.timezone('Asia/Kuala_Lumpur')
malaysia_time = datetime.now(malaysia_tz)

selected_email = None

# Define your models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/capture_card')
def capture_card():
    global selected_email
    card_id = request.args.get('id')
    if not card_id or not selected_email:
        return jsonify({'error': 'No card ID or email provided'}), 400

    try:
        db.engine.execute("UPDATE employees SET card_id = %s WHERE email = %s", card_id, selected_email)
        return redirect('/dashboard')
    except Exception as e:
        return jsonify({'error': 'Database update failed', 'message': str(e)}), 500

@app.route('/select_user', methods=['GET', 'POST'])
def select_user():
    if request.method == 'POST':
        email = request.form.get('email')
        card_id = request.form.get('card_id')

        try:
            db.engine.execute("UPDATE employees SET card_id = %s WHERE email = %s", card_id, email)
            return redirect(url_for('dashboard'))
        except Exception as e:
            return jsonify({'error': 'Database update failed', 'message': str(e)}), 500
    else:
        cursor = db.engine.execute("SELECT email FROM employees")
        emails = [row['email'] for row in cursor.fetchall()]
        return render_template('select_user.html', emails=emails)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cursor = db.engine.execute("SELECT * FROM employees WHERE email = %s", email)
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['logged_in'] = True
            session['is_admin'] = user['is_admin']
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            return "Invalid email or password"
    else:
        return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    cursor = db.engine.execute("SELECT employees.name, attendance.in_time, attendance.out_time, attendance.working_hours, attendance.subject FROM employees JOIN attendance ON employees.id = attendance.employee_id")
    attendance_records = cursor.fetchall()
    cursor = db.engine.execute("SELECT employees.name, employees.email, employees.card_id FROM employees")
    employees = cursor.fetchall()
    cursor = db.engine.execute("SELECT start_time, end_time, subject FROM timetable ORDER BY start_time")
    timetable = [{"start_time": str(row['start_time']), "end_time": str(row['end_time']), "subject": row['subject']} for row in cursor.fetchall()]
    show_tabs = session.get('is_admin', False)

    return render_template('dashboard.html', attendance_records=attendance_records, employees=employees, timetable=timetable, show_tabs=show_tabs)

@app.route('/test_db_connection')
def test_db_connection():
    try:
        cursor = db.engine.execute("SELECT DB_NAME() AS [Current Database]")
        db_name = cursor.fetchone()
        return f"Connected to database: {db_name['Current Database']}"
    except Exception as e:
        return f"Failed to connect to database: {e}"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
