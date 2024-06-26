import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, logout_user, login_user
import pytz
from dotenv import load_dotenv
from flask_migrate import Migrate
from sqlalchemy import extract, and_

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

selected_email = None

class Employee(UserMixin, db.Model):  # Use Employee for UserMixin to integrate with Flask-Login
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    card_id = db.Column(db.String(120), unique=True, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    in_time = db.Column(db.DateTime, nullable=False)
    out_time = db.Column(db.DateTime, nullable=True)
    working_hours = db.Column(db.Time, nullable=True)
    subject = db.Column(db.String(120), nullable=False, default="")  # Provide a default value
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
    return Employee.query.get(int(user_id))

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

        employee = Employee.query.filter_by(email=email).first()

        if employee and check_password_hash(employee.password, password):
            login_user(employee)
            session['logged_in'] = True
            session['is_admin'] = employee.is_admin
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
            employee = Employee(name=name, email=email, password=hashed_password, is_admin=False)
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
    print("Session values:", session)
    employee = Employee.query.filter_by(email=session['email']).first()
    if employee and employee.is_admin:
        show_tabs = True
        attendance_records = db.session.query(Employee.name, Attendance.in_time, Attendance.out_time, Attendance.working_hours, Attendance.subject).join(Attendance).all()
    else:
        show_tabs = False
        attendance_records = db.session.query(Employee.name, Attendance.in_time, Attendance.out_time, Attendance.working_hours, Attendance.subject).join(Attendance).filter(Employee.email == session['email']).all()

    employees = Employee.query.with_entities(Employee.name, Employee.email, Employee.card_id).all()
    timetable = Timetable.query.order_by(Timetable.start_time).all()

    return render_template('dashboard.html', attendance_records=attendance_records, employees=employees, timetable=timetable, show_tabs=show_tabs)

@app.route('/register_card', methods=['POST'])
@login_required
def register_card():
    email = request.form.get('email')
    card_id = request.form.get('card_id')
    
    if not email or not card_id:
        return jsonify({'error': 'Email and card ID are required'}), 400
    
    try:
        employee = Employee.query.filter_by(email=email).first()
        if employee:
            employee.card_id = card_id
            db.session.commit()
            return redirect(url_for('dashboard'))
        return jsonify({'error': 'Employee not found'}), 404
    except Exception as e:
        return jsonify({'error': 'Database update failed', 'message': str(e)}), 500

@app.route('/register_subject', methods=['POST'])
@login_required
def register_subject():
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    subject = request.form.get('subject')
    
    if not start_time or not end_time or not subject:
        return jsonify({'error': 'Start time, end time, and subject are required'}), 400
    
    try:
        timetable_entry = Timetable(start_time=start_time, end_time=end_time, subject=subject)
        db.session.add(timetable_entry)
        db.session.commit()
        return redirect(url_for('dashboard'))
    except Exception as e:
        return jsonify({'error': 'Database insert failed', 'message': str(e)}), 500

@app.route('/reset_timetable', methods=['POST'])
@login_required
def reset_timetable():
    try:
        db.session.query(Timetable).delete()
        db.session.commit()
        return redirect(url_for('dashboard'))
    except Exception as e:
        return jsonify({'error': 'Database reset failed', 'message': str(e)}), 500

@app.route('/record_attendance', methods=['GET'])
def record_attendance():  # Temporarily remove @login_required for testing
    card_id = request.args.get('id')
    
    if not card_id:
        return jsonify({'error': 'Card ID is required'}), 400
    
    try:
        employee = Employee.query.filter_by(card_id=card_id).first()
        if employee:
            current_time = datetime.now(malaysia_tz)

            # Retrieve the current subject based on the current time
            timetable_entry = Timetable.query.filter(
                and_(
                    Timetable.start_time <= current_time.time(),
                    Timetable.end_time >= current_time.time()
                )
            ).first()
            
            subject = timetable_entry.subject if timetable_entry else ""

            # Check if the employee has an open attendance record (in_time is set but out_time is null)
            attendance = Attendance.query.filter(and_(Attendance.employee_id == employee.id, 
                                                     Attendance.out_time == None)).order_by(Attendance.in_time.desc()).first()
            if attendance:
                # Ensure in_time is timezone-aware
                if attendance.in_time.tzinfo is None:
                    attendance.in_time = malaysia_tz.localize(attendance.in_time)
                # Update the out_time and working_hours
                attendance.out_time = current_time
                duration = attendance.out_time - attendance.in_time
                attendance.working_hours = (datetime.min + duration).time()
            else:
                # Create a new attendance record with the current in_time and subject
                attendance = Attendance(employee_id=employee.id, in_time=current_time, subject=subject)
                db.session.add(attendance)
                
            db.session.commit()
            return jsonify({'message': 'Attendance recorded successfully'}), 200
        return jsonify({'error': 'Employee not found'}), 404
    except Exception as e:
        return jsonify({'error': 'Database operation failed', 'message': str(e)}), 500

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
