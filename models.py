from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()

# --- ASSOCIATION TABLE (Must be defined BEFORE Staff class) ---
staff_subjects = db.Table('staff_subjects',
    db.Column('staff_id', db.Integer, db.ForeignKey('staff.id'), primary_key=True),
    db.Column('subject_id', db.Integer, db.ForeignKey('subject.id'), primary_key=True)
)

# --- User Model ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Relationships
    staff_profile = db.relationship('Staff', backref='user', uselist=False)
    receptionist_profile = db.relationship('Receptionist', backref='user', uselist=False)
    # If you added Student Portal earlier, ensure this line exists:
    student_profile = db.relationship('Student', backref='user', uselist=False)

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
    
    # User Link (For Student Portal)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=True)
    
    # Personal Details
    father_name = db.Column(db.String(100), nullable=True)
    qualification = db.Column(db.String(100), nullable=True)
    contact_no = db.Column(db.String(20), nullable=True)
    father_contact_no = db.Column(db.String(20), nullable=True)
    dob = db.Column(db.String(20), nullable=True)
    full_address = db.Column(db.String(200), nullable=True)
    exam_type = db.Column(db.String(100), nullable=True)
    target_exam = db.Column(db.String(100), nullable=True)
    
    fees = db.relationship('Fee', backref='student', lazy=True, cascade='all, delete-orphan')

# --- Staff Model ---
class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    # Relationship to Subject using the table defined above
    subjects = db.relationship('Subject', secondary=staff_subjects, lazy='subquery',
        backref=db.backref('teachers', lazy=True))

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
    subjects = db.relationship('Subject', backref='course', lazy=True, cascade='all, delete-orphan')

# --- Subject Model ---
class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

# --- Appointment Model ---
class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_name = db.Column(db.String(100), nullable=False)
    visitor_contact = db.Column(db.String(100), nullable=True)
    purpose = db.Column(db.String(200), nullable=True)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    staff = db.relationship('Staff', backref='appointments')

# --- Fee Model ---
class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_plan = db.Column(db.String(50), nullable=False)
    num_installments = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending')
    payments = db.relationship('Payment', backref='fee', lazy=True, cascade='all, delete-orphan')
    last_paid_date = db.Column(db.String(20), nullable=True)

    @property
    def amount_paid(self):
        return sum(payment.amount for payment in self.payments)

    @property
    def pending_amount(self):
        return self.total_amount - self.amount_paid
    
# --- Payment Model ---
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fee_id = db.Column(db.Integer, db.ForeignKey('fee.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.String(200), nullable=True)

# --- Audit Log Model ---
class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.String(500), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user = db.relationship('User', backref='audit_logs')

# --- Attendance Model ---
class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    course_name = db.Column(db.String(100), nullable=True)

    student_ref = db.relationship('Student', backref='attendance_records')
    staff_ref = db.relationship('Staff', backref='marked_attendance')

# --- Settings Model ---
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"Setting('{self.key}', '{self.value}')"