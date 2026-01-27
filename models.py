from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='staff') # it_expert, doctor, staff
    email = db.Column(db.String(120), unique=True)
    phone_number = db.Column(db.String(20))
    account_status = db.Column(db.String(20), default='Active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    otp_secret = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    place = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    diagnoses = db.relationship('Diagnosis', backref='patient', lazy=True)

class Diagnosis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    disease = db.Column(db.String(50), nullable=False)
    probability = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(200), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    doctor = db.relationship('User', backref=db.backref('diagnoses', lazy=True))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    patient_ref = db.relationship('Patient', backref=db.backref('appointments', lazy=True))
