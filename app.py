import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, logout_user, login_user
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
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

malaysia_tz = pytz.timezone('Asia/Kuala_Lumpur')
malaysia_time = datetime.now(malaysia_tz)

selected_email = None

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    card_id = db.Column(db.String(120), unique=True, nullable=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    in_time = db.Column(db.DateTime, nullable=False)
    out_time = db.Column(db.DateTime, nullable=True)
    working_hours = db.Column(db.Float, nullable=True)
    subject = db.Column(db.String(120), nullable=True)
    employee = db.relationship('Employee', backref=db.backref('attendances', lazy=True))

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    subject = db.Column(db.String(120), nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/capture_card')
def capture_card():
    global selected_email
    card_id = request.args.get('id')
    if not card_id or not selected_email:
        return jsonify({'error': 'No card ID or email provided'}), 400

    try:
        employee = Employee.query.filter_by(email=selected_email).first()
        if employee:
            employee.card_id = card_id
            db.session.commit()
            return redirect('/dashboard')
        return jsonify({'error': 'Employee not found'}), 404
    except Exception as e:
        return jsonify({'error': 'Database update failed', 'message': str(e)}), 500

@app.route('/select_user', methods=['GET', 'POST'])
def select_user():
    if request.method == 'POST':
        email = request.form.get('email')
        card_id = request.form.get('card_id')

        try:
            employee = Employee.query.filter_by(email=email).first()
            if employee:
                employee.card_id = card_id
                db.session.commit()
                return redirect(url_for('dashboard'))
            return jsonify({'error': 'Employee not found'}), 404
        except Exception as e:
            return jsonify({'error': 'Database update failed', 'message': str(e)}), 500
    else:
        employees = Employee.query.with_entities(Employee.email).all()
        emails = [employee.email for employee in employees]
        return render_template('select_user.html', emails=emails)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            session['logged_in'] = True
            session['is_admin'] = user.is_admin
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            return "Invalid email or password"
    else:
        return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password)

        try:
            user = User(email=email, password=hashed_password)
            db.session.add(user)
            db.session.commit()

            employee = Employee(name=name, email=email)
            db.session.add(employee)
            db.session.commit()

            return redirect(url_for('login'))
        except Exception as e:
            return jsonify({'error': 'Database insert failed', 'message': str(e)}), 500
    else:
        return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('is_admin'):
        attendance_records = db.session.query(Employee.name, Attendance.in_time, Attendance.out_time, Attendance.working_hours, Attendance.subject).join(Attendance).all()
    else:
        attendance_records = db.session.query(Employee.name, Attendance.in_time, Attendance.out_time, Attendance.working_hours, Attendance.subject).join(Attendance).filter(Employee.email == session['email']).all()

    employees = Employee.query.with_entities(Employee.name, Employee.email, Employee.card_id).all()
    timetable = Timetable.query.order_by(Timetable.start_time).all()

    timetable_data = Timetable.query.all()

    show_tabs = session.get('is_admin', False)

    return render_template('dashboard.html', attendance_records=attendance_records, employees=employees, timetable=timetable, show_tabs=show_tabs, timetable_data=timetable_data)

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
