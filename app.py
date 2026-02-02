import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message
import random
import string
from datetime import datetime, timedelta
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from functools import wraps
from tensorflow.keras.models import load_model
import numpy as np
from tensorflow.keras.applications.vgg16 import preprocess_input
from tensorflow.keras.preprocessing import image
from tensorflow.keras.utils import load_img, img_to_array
from models import db, Patient, Diagnosis, Appointment, User
from datetime import datetime, date, time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eye_disease.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'  # Needed for flash messages

# Flask-Mail Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'skrkollam2013@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'Madhavam439') # Note: Verify if this is App Password or Login Password
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin():
    with app.app_context():
        if not User.query.filter_by(role='it_expert').first():
            admin = User(username='admin', role='it_expert')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created.")

# Load Model
model = load_model('models/final_model.h5')

# Ensure database tables exist
with app.app_context():
    db.create_all()
    create_admin()

# Allow files with extension png, jpg and jpeg
ALLOWED_EXT = set(['jpg', 'jpeg', 'png'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT



def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    # Landing page - redirect to login if not authenticated, otherwise to dashboard
    if current_user.is_authenticated:
        if current_user.role == 'it_expert':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect if already logged in
    if current_user.is_authenticated:
        if current_user.role == 'it_expert':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # Check if account is active
            if user.account_status != 'Active':
                flash('Your account has been deactivated. Please contact the administrator.', 'danger')
                return render_template('login.html')
            
            login_user(user)
            # Track last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash('Login Successful!', 'success')
            # Redirect to appropriate dashboard based on role
            if user.role == 'it_expert':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Redirect admin to admin dashboard
    if current_user.role == 'it_expert':
        return redirect(url_for('admin_dashboard'))
    
    # Get stats for doctor/staff
    patient_count = Patient.query.count()
    appointment_count = Appointment.query.count()
    diagnosis_count = Diagnosis.query.count() if current_user.role == 'doctor' else 0
    staff_count = User.query.filter_by(role='staff').count() if current_user.role == 'doctor' else 0
    
    return render_template('unified_dashboard.html',
                           patient_count=patient_count,
                           appointment_count=appointment_count,
                           diagnosis_count=diagnosis_count,
                           staff_count=staff_count)

@app.route('/patient/search', methods=['POST'])
@login_required
def patient_search():
    # Patient search functionality
    if current_user.role not in ['doctor', 'staff']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    patient_id = request.form.get('patient_id')
    if patient_id:
        patient = Patient.query.get(patient_id)
        if patient:
            return redirect(url_for('patient_dashboard', patient_id=patient.id))
        else:
            flash('Patient ID not found!', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/admin/dashboard')
@login_required
@role_required('it_expert')
def admin_dashboard():
    users = User.query.all()
    doctor_count = User.query.filter_by(role='doctor').count()
    staff_count = User.query.filter_by(role='staff').count()
    patient_count = Patient.query.count()
    appointment_count = Appointment.query.count()
    
    return render_template('unified_dashboard.html', 
                           users=users,
                           doctor_count=doctor_count,
                           staff_count=staff_count,
                           patient_count=patient_count,
                           appointment_count=appointment_count)

@app.route('/doctors')
@login_required
@role_required('it_expert')
def doctors_list():
    doctors = User.query.filter_by(role='doctor').order_by(User.id.desc()).all()
    return render_template('list_view.html', 
                           items=doctors,
                           list_type='doctors',
                           page_title='Doctors List')

@app.route('/staff')
@login_required
def staff_list():
    # Accessible to IT Expert and Doctor
    if current_user.role not in ['it_expert', 'doctor']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    staff = User.query.filter_by(role='staff').order_by(User.id.desc()).all()
    return render_template('list_view.html', 
                           items=staff,
                           list_type='staff',
                           page_title='Staff Members List')

@app.route('/patients')
@login_required
def patients_list():
    # Accessible to all authenticated users
    if current_user.role not in ['it_expert', 'doctor', 'staff']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    patients = Patient.query.order_by(Patient.id.desc()).all()
    return render_template('list_view.html', 
                           items=patients,
                           list_type='patients',
                           page_title='Patients List')


@app.route('/admin/create_user', methods=['POST'])
@login_required
@role_required('it_expert')
def create_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    email = request.form.get('email')
    phone_number = request.form.get('phone_number', '')
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists', 'danger')
    elif email and User.query.filter_by(email=email).first(): # Check email uniqueness
        flash('Email already registered', 'danger')
    else:
        new_user = User(username=username, role=role, email=email, phone_number=phone_number)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash(f'User {username} created successfully', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/view_user/<int:user_id>')
@login_required
@role_required('it_expert')
def view_user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('view_user_profile.html', user=user)

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('it_expert')
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        new_username = request.form.get('username')
        new_email = request.form.get('email')
        new_phone = request.form.get('phone_number')
        new_role = request.form.get('role')
        
        # Check username uniqueness
        if new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                flash('Username already exists', 'danger')
                return redirect(url_for('admin_edit_user', user_id=user_id))
        
        # Check email uniqueness
        if new_email != user.email:
            if User.query.filter_by(email=new_email).first():
                flash('Email already registered', 'danger')
                return redirect(url_for('admin_edit_user', user_id=user_id))
        
        # Update user
        user.username = new_username
        user.email = new_email
        user.phone_number = new_phone
        user.role = new_role
        db.session.commit()
        
        flash(f'User {user.username} updated successfully', 'success')
        return redirect(url_for('view_user', user_id=user_id))
    
    return render_template('edit_user.html', user=user)

@app.route('/admin/toggle_status/<int:user_id>', methods=['POST'])
@login_required
@role_required('it_expert')
def admin_toggle_status(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deactivating themselves
    if user.id == current_user.id:
        flash('You cannot deactivate your own account', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Toggle status
    if user.account_status == 'Active':
        user.account_status = 'Deactivated'
        flash(f'User {user.username} has been deactivated', 'warning')
    else:
        user.account_status = 'Active'
        flash(f'User {user.username} has been activated', 'success')
    
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('it_expert')
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # Check if user has diagnoses (safety check)
    if user.diagnoses:
        flash(f'Cannot delete user {user.username}: User has {len(user.diagnoses)} diagnosis records. Deactivate instead.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {username} has been deleted', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if current_user.role not in ['staff', 'doctor', 'it_expert']: # Staff primarily, but doctors might need to?
         # "The system allows staff users to perform patient registration"
         # Usually doctors can too in small clinics, but let's stick to strict or permissive?
         # "Staff users are limited to administrative operations... patient registration"
         if current_user.role != 'staff' and current_user.role != 'doctor': # Assuming doctor is super-set effectively or just different?
             # Doctors have "full access to clinical...". Doesn't explicitly say they can register, but usually implied. 
             # Let's allow Staff and Doctor.
             flash('Permission denied', 'danger')
             return redirect(url_for('index'))
             
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        place = request.form['place']
        phone = request.form['phone']
        
        new_patient = Patient(name=name, age=age, gender=gender, blood_group=blood_group, place=place, phone=phone)
        db.session.add(new_patient)
        db.session.commit()
        
        flash(f'Patient Registered Successfully! ID: {new_patient.id}', 'success')
        return redirect(url_for('patient_dashboard', patient_id=new_patient.id))
    return render_template('register.html')

@app.route('/diagnosis/patients')
@login_required
@role_required('doctor')
def diagnosis_patients():
    # Show list of all patients for diagnosis
    patients = Patient.query.order_by(Patient.id.desc()).all()
    return render_template('diagnosis_patients.html', patients=patients)

@app.route('/patient/<int:patient_id>', methods=['GET'])
@login_required
def patient_dashboard(patient_id):
    # Staff and Doctor can view dashboard, but content is filtered in template
    if current_user.role not in ['staff', 'doctor']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    patient = Patient.query.get_or_404(patient_id)
    return render_template('patient_dashboard.html', patient=patient)

@app.route('/predict/<int:patient_id>', methods=['POST'])
@login_required
@role_required('doctor')
def predict(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    
    file = request.files.get('filename')
    if file and allowed_file(file.filename):
        filename = f"{patient_id}_{int(datetime.now().timestamp())}_{file.filename}"
        file_path = os.path.join('static/images', filename)
        file.save(file_path)

        # Prediction Logic
        image_obj = load_img(file_path, target_size=(224, 224))
        input_arr = img_to_array(image_obj)
        input_arr = np.array([input_arr])
        prediction = model(input_arr)
        classes_x = np.argmax(prediction, axis=1)
        pred_prob = np.max(prediction)
        
        labs = ['Cataract', 'Glaucoma', 'Diabetic Retinopathy', 'Normal']
        diseases = labs[classes_x[0]] if classes_x[0] < len(labs) else "Unknown"

        # Save Diagnosis to DB
        new_diagnosis = Diagnosis(
            patient_id=patient.id,
            doctor_id=current_user.id,
            disease=diseases,
            probability=float(pred_prob),
            image_path=file_path
        )
        db.session.add(new_diagnosis)
        db.session.commit()
        
        flash('Diagnosis added successfully!', 'success')
        return redirect(url_for('patient_dashboard', patient_id=patient_id))
    else:
        flash('Invalid file or upload failed.', 'danger')
        return redirect(url_for('patient_dashboard', patient_id=patient_id))

@app.route('/appointments', methods=['GET'])
@login_required
def appointments():
    if current_user.role not in ['staff', 'doctor']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    filter_date = request.args.get('date')
    if filter_date:
        try:
            search_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
            appointments = Appointment.query.filter_by(date=search_date).order_by(Appointment.time).all()
        except ValueError:
            flash('Invalid date format', 'danger')
            appointments = []
    else:
        # Default to all appointments or just today/upcoming? Let's show all for now or upcoming
        # For simplicity in this step, let's just show all ordered by date/time
        appointments = Appointment.query.order_by(Appointment.date, Appointment.time).all()
    
    return render_template('appointments.html', 
                           appointments=appointments, 
                           filter_date=filter_date,
                           today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/appointments/today', methods=['GET'])
@login_required
def today_appointments():
    today = date.today()
    return redirect(url_for('appointments', date=today.isoformat()))

@app.route('/book_appointment', methods=['GET', 'POST'])
@login_required
def book_appointment():
    if current_user.role not in ['staff', 'doctor']: # Doctors might also want to book?
         flash('Unauthorized', 'danger')
         return redirect(url_for('index'))
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        appt_date_str = request.form.get('appointment_date')
        appt_time_str = request.form.get('appointment_time')
        
        if not patient_id or not appt_date_str:
            flash('Patient and Date are required', 'danger')
            return redirect(url_for('book_appointment'))
            
        try:
            appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
            if appt_time_str:
                appt_time = datetime.strptime(appt_time_str, '%H:%M').time()
            else:
                appt_time = time(9, 0) # Default 9 AM
                
            new_appt = Appointment(
                patient_id=patient_id,
                date=appt_date,
                time=appt_time
            )
            db.session.add(new_appt)
            db.session.commit()
            flash('Appointment booked successfully!', 'success')
            return redirect(url_for('appointments', date=appt_date_str))
            
        except ValueError:
            flash('Invalid date/time format', 'danger')
            
    patients = Patient.query.all()
    # Pre-select patient if patient_id is passed in args
    selected_patient_id = request.args.get('patient_id')
    return render_template('book_appointment.html', patients=patients, selected_patient_id=selected_patient_id)

# OTP Helper
def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(user, purpose):
    otp = generate_otp()
    user.otp_secret = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    db.session.commit()
    
    msg = Message(f'Your OTP for {purpose}', recipients=[user.email])
    msg.body = f'Your OTP is: {otp}. It expires in 5 minutes.'
    try:
        mail.send(msg)
        print(f"DEBUG: Sent OTP {otp} to {user.email}") # For local testing if mail fails
    except Exception as e:
        print(f"Error sending email: {e}")
        flash('Error sending email. Check console for debug OTP.', 'warning')
        print(f"DEBUG: OTP (Fallback) for {user.email}: {otp}")

# Forgot Password Routes
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            send_otp_email(user, 'Password Reset')
            session['reset_email'] = email
            session['otp_purpose'] = 'reset_password'
            flash('OTP sent to your email', 'info')
            return redirect(url_for('verify_otp'))
        else:
            flash('Email not found', 'danger')
    return render_template('forgot_password.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        otp_input = request.form['otp']
        purpose = session.get('otp_purpose')
        
        if purpose == 'reset_password':
            email = session.get('reset_email')
            user = User.query.filter_by(email=email).first()
        elif purpose in ['change_username', 'change_password']:
            user = current_user
        else:
            flash('Invalid session', 'danger')
            return redirect(url_for('login'))

        if user and user.otp_secret == otp_input and user.otp_expiry > datetime.utcnow():
            user.otp_secret = None # Clear OTP
            user.otp_expiry = None
            db.session.commit()
            session['otp_verified'] = True
            
            if purpose == 'reset_password':
                return redirect(url_for('reset_password'))
            elif purpose == 'change_username':
                 # Apply change immediately or redirect? Let's apply valid pending change
                 new_username = session.get('pending_username')
                 if new_username:
                     user.username = new_username
                     db.session.commit()
                     flash('Username updated successfully!', 'success')
                     return redirect(url_for('profile'))
            elif purpose == 'change_password':
                 new_password = session.get('pending_password')
                 if new_password:
                     user.set_password(new_password)
                     db.session.commit()
                     flash('Password updated successfully!', 'success')
                     return redirect(url_for('profile'))
        else:
            flash('Invalid or Expired OTP', 'danger')
    return render_template('verify_otp.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('otp_verified') or session.get('otp_purpose') != 'reset_password':
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        password = request.form['password']
        confirm = request.form['confirm_password']
        if password != confirm:
            flash('Passwords do not match', 'danger')
        else:
            email = session.get('reset_email')
            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(password)
                db.session.commit()
                flash('Password reset successful. Please Login.', 'success')
                session.clear()
                return redirect(url_for('login'))
    return render_template('reset_password.html')

# Profile Routes
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/profile/change_username', methods=['POST'])
@login_required
def change_username():
    new_username = request.form['new_username']
    if User.query.filter_by(username=new_username).first():
        flash('Username already exists', 'danger')
        return redirect(url_for('profile'))
    
    session['pending_username'] = new_username
    session['otp_purpose'] = 'change_username'
    if not current_user.email:
         flash('No email registered for this account. Cannot verify.', 'danger')
         return redirect(url_for('profile'))
         
    send_otp_email(current_user, 'Username Change')
    flash('OTP sent to your email to confirm username change', 'info')
    return redirect(url_for('verify_otp'))

@app.route('/profile/change_password', methods=['POST'])
@login_required
def change_password():
    new_password = request.form['new_password']
    session['pending_password'] = new_password
    session['otp_purpose'] = 'change_password'
    
    if not current_user.email:
         flash('No email registered for this account. Cannot verify.', 'danger')
         return redirect(url_for('profile'))

    send_otp_email(current_user, 'Password Change')
    flash('OTP sent to your email to confirm password change', 'info')
    return redirect(url_for('verify_otp'))

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True, port=8000)