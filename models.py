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
    fees = db.relationship('Fee', backref='student', lazy=True, cascade='all, delete-orphan')


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

# --- Fee Model ---
class Fee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    payment_plan = db.Column(db.String(50), nullable=False)
    num_installments = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending')
    payments = db.relationship('Payment', backref='fee', lazy=True, cascade='all, delete-orphan')

    # This property calculates the total paid amount on the fly
    @property
    def amount_paid(self):
        return sum(payment.amount for payment in self.payments)

    # This property calculates the pending amount on the fly
    @property
    def pending_amount(self):
        return self.total_amount - self.amount_paid
    
# --- Payment Model for Transaction History ---
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fee_id = db.Column(db.Integer, db.ForeignKey('fee.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.String(200), nullable=True)