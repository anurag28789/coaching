from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

# --- User Model ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    staff_profile = db.relationship('Staff', backref='user', uselist=False)
    receptionist_profile = db.relationship('Receptionist', backref='user', uselist=False)

    def __repr__(self):
        return f"User('{self.username}', '{self.role}')"
    
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

# --- Student Model ---
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_of_admission = db.Column(db.String(20), nullable=True)
    enquiry_id = db.Column(db.Integer, db.ForeignKey('enquiry.id'), unique=True, nullable=True)
    enquiry = db.relationship('Enquiry', backref='student', uselist=False)
    
    # New fields from the admission form
    father_name = db.Column(db.String(100), nullable=True)
    qualification = db.Column(db.String(100), nullable=True)
    contact_no = db.Column(db.String(20), nullable=True)
    father_contact_no = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.String(20), nullable=True)
    full_address = db.Column(db.String(200), nullable=True)
    exam_type = db.Column(db.String(100), nullable=True)
    target_exam = db.Column(db.String(100), nullable=True)


# --- Staff Model ---
class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)

# --- Receptionist Model ---
class Receptionist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)

# --- Enquiry Model ---
class Enquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100), nullable=False)
    course_interest = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='New')
    joining_date = db.Column(db.String(20), nullable=True)

# --- Course Model ---
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    subjects = db.relationship('Subject', backref='course', lazy=True)

# --- Subject Model ---
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_name = db.Column(db.String(100), nullable=False)
    visitor_contact = db.Column(db.String(100), nullable=True)
    purpose = db.Column(db.String(200), nullable=True)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)