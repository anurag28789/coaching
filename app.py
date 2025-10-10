import site
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, bcrypt, User, Student, Staff, Enquiry, Receptionist, Course, Subject, Appointment, Fee, Payment, AuditLog
from datetime import datetime, timedelta
import math

# Initialize the Flask application
app = Flask(__name__)

# --- Configuration ---
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions with the app
db.init_app(app)
bcrypt.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Global settings dictionary (simulated)
settings = {
    'global_discount_percentage': 0.0
}

# --- User Loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    # Fix for LegacyAPIWarning
    return db.session.get(User, int(user_id))

# --- Auditing Function ---
def log_action(user, action, details):
    new_log = AuditLog(
        user_id=user.id,
        action=action,
        details=details,
        timestamp=datetime.now()
    )
    db.session.add(new_log)
    db.session.commit()
    print(f"AUDIT: User '{user.username}' ({user.role}) performed '{action}' - {details}")

# --- Routes ---
@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.is_active and user.check_password(password):
            login_user(user)
            log_action(user, 'login', f"Successful login.")
            if user.role == 'admin':
                return redirect(url_for('admin_portal'))
            elif user.role == 'staff':
                return redirect(url_for('staff_portal'))
            elif user.role == 'receptionist':
                return redirect(url_for('receptionist_portal'))
        
        flash("Login failed. Please try again.", 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/admin_portal')
@login_required
def admin_portal():
    if current_user.role == 'admin':
        total_students = Student.query.count()
        total_staff = Staff.query.count()
        
        # Fix for SAWarning (Cartesian Product)
        fees_collected = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
        
        pending_fees_subquery = db.session.query(db.func.sum(Fee.total_amount) - db.func.sum(Payment.amount)).join(Payment).filter(Fee.status != 'paid').subquery()
        pending_fees = db.session.query(pending_fees_subquery).scalar() or 0

        return render_template(
            'admin_portal.html',
            total_students=total_students,
            total_staff=total_staff,
            fees_collected=fees_collected,
            pending_fees=pending_fees,
            current_user=current_user
        )
    return redirect(url_for('login'))

@app.route('/admin_portal/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    query = User.query.join(Staff, isouter=True).join(Receptionist, isouter=True)
    search_query = request.form.get('search_query')
    role_filter = request.form.get('role_filter')

    if request.method == 'POST':
        if search_query:
            query = query.filter(db.or_(
                User.username.like(f'%{search_query}%'),
                Staff.name.like(f'%{search_query}%'),
                Receptionist.name.like(f'%{search_query}%')
            ))
        if role_filter and role_filter != 'All':
            query = query.filter(User.role == role_filter)

    users = query.all()
    return render_template('manage_users.html', users=users, search_query=search_query, role_filter=role_filter)

@app.route('/admin_portal/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')
        name = request.form.get('name')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f"User '{username}' already exists. Please choose a different username.", 'danger')
            return redirect(url_for('add_user'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, password_hash=hashed_password, role=role, is_active=True)
        db.session.add(new_user)
        db.session.commit()

        if role == 'staff':
            new_staff = Staff(name=name, user_id=new_user.id)
            db.session.add(new_staff)
        elif role == 'receptionist':
            new_receptionist = Receptionist(name=name, user_id=new_user.id)
            db.session.add(new_receptionist)

        db.session.commit()
        log_action(current_user, 'add_user', f"Created user '{username}' with role '{role}'.")
        flash(f"User '{username}' with role '{role}' created successfully.", 'success')
        return redirect(url_for('admin_portal'))

    return render_template('add_user.html')

@app.route('/admin_portal/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    user_to_edit = db.session.get(User, user_id)
    if user_to_edit is None:
        flash("User not found.", 'danger')
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        new_username = request.form.get('username')
        new_password = request.form.get('password')
        new_role = request.form.get('role')
        name = request.form.get('name')

        # Check if the new username already exists with another user
        existing_user = User.query.filter(User.username == new_username, User.id != user_id).first()
        if existing_user:
            flash(f"Username '{new_username}' already in use.", 'danger')
            return redirect(url_for('edit_user', user_id=user_id))

        user_to_edit.username = new_username
        user_to_edit.role = new_role
        
        # Update associated profile name
        if user_to_edit.staff_profile:
            user_to_edit.staff_profile.name = name
        elif user_to_edit.receptionist_profile:
            user_to_edit.receptionist_profile.name = name
        
        if new_password:
            user_to_edit.set_password(new_password)
        
        db.session.commit()
        log_action(current_user, 'edit_user', f"Edited user '{user_to_edit.username}'.")
        flash(f"User '{user_to_edit.username}' updated successfully.", 'success')
        return redirect(url_for('manage_users'))

    return render_template('edit_user.html', user=user_to_edit)


@app.route('/admin_portal/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
        
    user_to_delete = db.session.get(User, user_id)
    if user_to_delete is None:
        flash("User not found.", 'danger')
        return redirect(url_for('manage_users'))

    if user_to_delete.role == 'admin':
        flash("Cannot delete an admin account.", 'danger')
        return redirect(url_for('manage_users'))

    if user_to_delete.role == 'staff' and user_to_delete.staff_profile:
        db.session.delete(user_to_delete.staff_profile)
    elif user_to_delete.role == 'receptionist' and user_to_delete.receptionist_profile:
        db.session.delete(user_to_delete.receptionist_profile)

    log_action(current_user, 'delete_user', f"Deleted user '{user_to_delete.username}'.")
    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f"User '{user_to_delete.username}' and associated profile deleted successfully.", 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin_portal/toggle_active/<int:user_id>', methods=['POST'])
@login_required
def toggle_active(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    user_to_toggle = db.session.get(User, user_id)
    if user_to_toggle is None:
        flash("User not found.", 'danger')
    elif user_to_toggle.role == 'admin':
        flash("Cannot deactivate an admin account.", 'danger')
    else:
        user_to_toggle.is_active = not user_to_toggle.is_active
        db.session.commit()
        status = 'deactivated' if not user_to_toggle.is_active else 'activated'
        log_action(current_user, 'toggle_active', f"{user_to_toggle.username} {status}.")
        flash(f"User '{user_to_toggle.username}' has been {status}.", 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin_portal/manage_students', methods=['GET', 'POST'])
@login_required
def manage_students():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    query = Student.query.join(Enquiry)
    search_query = request.form.get('search_query')
    course_filter = request.form.get('course_filter')
    
    if request.method == 'POST':
        if search_query:
            query = query.filter(Student.name.like(f'%{search_query}%'))
        if course_filter and course_filter != 'All':
            query = query.filter(Enquiry.course_interest == course_filter)
            
    students = query.all()
    courses = Course.query.all()
    return render_template('manage_students.html', students=students, courses=courses)

@app.route('/admin_portal/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    student = db.session.get(Student, student_id)
    if student is None:
        flash("Student not found.", 'danger')
        return redirect(url_for('manage_students'))

    if request.method == 'POST':
        student.name = request.form.get('student_name')
        student.father_name = request.form.get('father_name')
        student.contact_no = request.form.get('contact_no')
        student.father_contact_no = request.form.get('father_contact_no')
        student.dob = request.form.get('dob')
        student.full_address = request.form.get('full_address')
        student.qualification = request.form.get('qualification')
        student.exam_type = request.form.get('exam_type')
        student.target_exam = request.form.get('target_exam')
        
        db.session.commit()
        log_action(current_user, 'edit_student', f"Edited student '{student.name}'.")
        flash(f"Student '{student.name}' profile updated successfully.", 'success')
        return redirect(url_for('manage_students'))

    return render_template('edit_student.html', student=student)

@app.route('/admin_portal/financial_reports')
@login_required
def financial_reports():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    # Example: Total revenue per course
    revenue_by_course = db.session.query(
        Enquiry.course_interest,
        db.func.sum(Fee.total_amount).label('total_fees'),
        db.func.sum(Payment.amount).label('amount_paid')
    ).join(Student, Enquiry.id == Student.enquiry_id).join(Fee).join(Payment).group_by(Enquiry.course_interest).all()

    return render_template('financial_reports.html', revenue_by_course=revenue_by_course)

@app.route('/admin_portal/institutional_settings', methods=['GET', 'POST'])
@login_required
def institutional_settings():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        settings['global_discount_percentage'] = float(request.form.get('global_discount_percentage'))
        log_action(current_user, 'update_settings', f"Updated global discount to {settings['global_discount_percentage']}%.")
        flash("Settings updated successfully.", 'success')
        return redirect(url_for('institutional_settings'))

    return render_template('institutional_settings.html', settings=settings)


@app.route('/admin_portal/courses')
@login_required
def view_courses():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    courses = Course.query.all()
    return render_template('view_courses.html', courses=courses)


@app.route('/admin_portal/add_course', methods=['GET', 'POST'])
@login_required
def add_course():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        existing_course = Course.query.filter_by(name=course_name).first()

        if existing_course:
            flash("Course already exists.", 'danger')
        else:
            new_course = Course(name=course_name)
            db.session.add(new_course)
            db.session.commit()
            log_action(current_user, 'add_course', f"Added new course '{course_name}'.")
            flash(f"Course '{course_name}' added successfully.", 'success')
        
        return redirect(url_for('view_courses'))
    
    return render_template('add_course.html')

@app.route('/admin_portal/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    course = db.session.get(Course, course_id)
    if course is None:
        flash("Course not found.", 'danger')
        return redirect(url_for('view_courses'))
    
    if request.method == 'POST':
        new_name = request.form.get('course_name')
        if new_name:
            course.name = new_name
            db.session.commit()
            log_action(current_user, 'edit_course', f"Edited course ID {course_id} to '{new_name}'.")
            flash("Course updated successfully.", 'success')
            return redirect(url_for('view_courses'))
        else:
            flash("Course name cannot be empty.", 'danger')

    return render_template('edit_course.html', course=course)

@app.route('/admin_portal/delete_course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    course_to_delete = db.session.get(Course, course_id)
    if course_to_delete:
        log_action(current_user, 'delete_course', f"Deleted course '{course_to_delete.name}'.")
        db.session.delete(course_to_delete)
        db.session.commit()
        flash("Course and all associated subjects deleted successfully.", 'success')
    else:
        flash("Course not found.", 'danger')

    return redirect(url_for('view_courses'))


@app.route('/admin_portal/add_subject/<int:course_id>', methods=['GET', 'POST'])
@login_required
def add_subject(course_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    course = db.session.get(Course, course_id)
    if course is None:
        flash("Course not found.", 'danger')
        return redirect(url_for('view_courses'))
    
    if request.method == 'POST':
        subject_name = request.form.get('subject_name')
        new_subject = Subject(name=subject_name, course_id=course.id)
        db.session.add(new_subject)
        db.session.commit()
        log_action(current_user, 'add_subject', f"Added subject '{subject_name}' to course '{course.name}'.")
        flash(f"Subject '{subject_name}' added to {course.name} successfully.", 'success')
        return redirect(url_for('view_courses'))
        
    return render_template('add_subject.html', course=course)

@app.route('/admin_portal/edit_subject/<int:subject_id>', methods=['GET', 'POST'])
@login_required
def edit_subject(subject_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    subject = db.session.get(Subject, subject_id)
    if subject is None:
        flash("Subject not found.", 'danger')
        return redirect(url_for('view_courses'))
    
    if request.method == 'POST':
        new_name = request.form.get('subject_name')
        if new_name:
            subject.name = new_name
            db.session.commit()
            log_action(current_user, 'edit_subject', f"Edited subject ID {subject_id} to '{new_name}'.")
            flash("Subject updated successfully.", 'success')
            return redirect(url_for('view_courses'))
        else:
            flash("Subject name cannot be empty.", 'danger')

    return render_template('edit_subject.html', subject=subject)

@app.route('/admin_portal/delete_subject/<int:subject_id>', methods=['POST'])
@login_required
def delete_subject(subject_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    subject_to_delete = db.session.get(Subject, subject_id)
    if subject_to_delete:
        log_action(current_user, 'delete_subject', f"Deleted subject '{subject_to_delete.name}'.")
        db.session.delete(subject_to_delete)
        db.session.commit()
        flash("Subject deleted successfully.", 'success')
    else:
        flash("Subject not found.", 'danger')
        
    return redirect(url_for('view_courses'))


@app.route('/admin_portal/audit_logs')
@login_required
def audit_logs():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('audit_logs.html', logs=logs)

@app.route('/admin_portal/manage_appointments')
@login_required
def manage_appointments():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    appointments = Appointment.query.join(Staff).options(db.joinedload(Appointment.staff)).order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('manage_appointments.html', appointments=appointments)

@app.route('/staff_portal')
@login_required
def staff_portal():
    if current_user.role == 'staff':
        return render_template('staff_portal.html', current_user=current_user)
    return redirect(url_for('login'))


@app.route('/receptionist_portal')
@login_required
def receptionist_portal():
    if current_user.role == 'receptionist':
        enquiries = Enquiry.query.all()
        return render_template('receptionist_portal.html', current_user=current_user, enquiries=enquiries)
    return redirect(url_for('login'))


@app.route('/receptionist_portal/add_enquiry', methods=['GET', 'POST'])
@login_required
def add_enquiry():
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))
    
    courses = Course.query.all()

    if request.method == 'POST':
        name = request.form.get('name')
        contact = request.form.get('contact')
        course = request.form.get('course_interest')
        joining_date = request.form.get('joining_date')
        
        new_enquiry = Enquiry(
            name=name,
            contact=contact,
            course_interest=course,
            joining_date=joining_date
        )
        db.session.add(new_enquiry)
        db.session.commit()
        log_action(current_user, 'add_enquiry', f"Enquiry for {name} submitted.")
        flash(f"Enquiry for {name} submitted successfully!", 'success')
        return redirect(url_for('receptionist_portal'))

    return render_template('add_enquiry.html', courses=courses)

@app.route('/receptionist_portal/cancel_enquiry/<int:enquiry_id>')
@login_required
def cancel_enquiry(enquiry_id):
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))
    
    enquiry = db.session.get(Enquiry, enquiry_id)
    if enquiry is None:
        flash("Enquiry not found.", 'danger')
        return redirect(url_for('receptionist_portal'))
        
    enquiry.status = 'Cancelled'
    db.session.commit()
    log_action(current_user, 'cancel_enquiry', f"Enquiry for {enquiry.name} has been cancelled.")
    flash(f"Enquiry for {enquiry.name} has been cancelled.", 'success')
    return redirect(url_for('receptionist_portal'))


@app.route('/receptionist_portal/admit_student/<int:enquiry_id>', methods=['GET', 'POST'])
@login_required
def admit_student(enquiry_id):
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))
    
    enquiry = db.session.get(Enquiry, enquiry_id)
    if enquiry is None:
        flash("Enquiry not found.", 'danger')
        return redirect(url_for('receptionist_portal'))
        
    courses = Course.query.all()

    if request.method == 'POST':
        student_name = request.form.get('student_name')
        father_name = request.form.get('father_name')
        qualification = request.form.get('qualification')
        contact_no = request.form.get('contact_no')
        father_contact_no = request.form.get('father_contact_no')
        dob = request.form.get('dob')
        full_address = request.form.get('full_address')
        exam_type = request.form.get('exam_type')
        target_exam = request.form.get('target_exam')
        course_name = request.form.get('course_name')
        date_of_admission = request.form.get('date_of_admission')
        total_fees = request.form.get('total_fees')
        payment_plan = request.form.get('payment_plan')
        num_installments = request.form.get('num_installments')
        first_payment_amount = request.form.get('first_payment_amount')
        
        if enquiry.status == 'Admitted':
            flash("This enquiry has already been processed for admission.", 'warning')
            return redirect(url_for('receptionist_portal'))
        
        new_student = Student(
            name=student_name,
            father_name=father_name,
            qualification=qualification,
            contact_no=contact_no,
            father_contact_no=father_contact_no,
            dob=dob,
            full_address=full_address,
            exam_type=exam_type,
            target_exam=target_exam,
            date_of_admission=date_of_admission,
            enquiry_id=enquiry.id
        )
        db.session.add(new_student)
        
        enquiry.status = 'Admitted'
        
        db.session.commit()

        new_fee = Fee(
            student_id=new_student.id,
            total_amount=float(total_fees),
            payment_plan=payment_plan,
            num_installments=int(num_installments) if num_installments else None,
            status='pending'
        )
        db.session.add(new_fee)
        db.session.commit()

        if float(first_payment_amount) > 0:
            first_payment = Payment(
                fee_id=new_fee.id,
                amount=float(first_payment_amount),
                payment_date=datetime.now().strftime('%Y-%m-%d')
            )
            db.session.add(first_payment)

        if new_fee.amount_paid >= new_fee.total_amount:
            new_fee.status = 'paid'
        elif new_fee.amount_paid > 0:
            new_fee.status = 'partially_paid'
        else:
            new_fee.status = 'pending'

        db.session.commit()
        log_action(current_user, 'admit_student', f"Admitted student '{student_name}' from enquiry ID {enquiry_id}.")
        flash(f"Student '{student_name}' admitted successfully!", 'success')
        return redirect(url_for('receptionist_portal'))

    return render_template('admit_student.html', enquiry=enquiry, courses=courses)


@app.route('/receptionist_portal/direct_admission', methods=['GET', 'POST'])
@login_required
def direct_admission():
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))
    
    courses = Course.query.all()

    if request.method == 'POST':
        name = request.form.get('student_name')
        father_name = request.form.get('father_name')
        qualification = request.form.get('qualification')
        contact = request.form.get('contact_no')
        father_contact_no = request.form.get('father_contact_no')
        dob = request.form.get('dob')
        full_address = request.form.get('full_address')
        exam_type = request.form.get('exam_type')
        target_exam = request.form.get('target_exam')
        course = request.form.get('course_name')
        date_of_admission = request.form.get('date_of_admission')
        total_fees = request.form.get('total_fees')
        payment_plan = request.form.get('payment_plan')
        num_installments = request.form.get('num_installments')
        first_payment_amount = request.form.get('first_payment_amount')

        new_enquiry = Enquiry(
            name=name,
            contact=contact,
            course_interest=course,
            status='Admitted',
            joining_date=date_of_admission
        )
        db.session.add(new_enquiry)
        db.session.commit()

        new_student = Student(
            name=name,
            father_name=father_name,
            qualification=qualification,
            contact_no=contact,
            father_contact_no=father_contact_no,
            dob=dob,
            full_address=full_address,
            exam_type=exam_type,
            target_exam=target_exam,
            date_of_admission=date_of_admission,
            enquiry_id=new_enquiry.id
        )
        db.session.add(new_student)
        db.session.commit()

        new_fee = Fee(
            student_id=new_student.id,
            total_amount=float(total_fees),
            payment_plan=payment_plan,
            num_installments=int(num_installments) if num_installments else None,
            status='pending'
        )
        db.session.add(new_fee)
        db.session.commit()

        if float(first_payment_amount) > 0:
            first_payment = Payment(
                fee_id=new_fee.id,
                amount=float(first_payment_amount),
                payment_date=datetime.now().strftime('%Y-%m-%d')
            )
            db.session.add(first_payment)

        if new_fee.amount_paid >= new_fee.total_amount:
            new_fee.status = 'paid'
        elif new_fee.amount_paid > 0:
            new_fee.status = 'partially_paid'
        else:
            new_fee.status = 'pending'

        db.session.commit()
        log_action(current_user, 'direct_admission', f"Directly admitted student '{name}'.")
        flash(f"Direct admission for {name} was successful!", 'success')
        return redirect(url_for('receptionist_portal'))

    return render_template('direct_admission.html', courses=courses)


@app.route('/receptionist_portal/schedule_appointment', methods=['GET', 'POST'])
@login_required
def schedule_appointment():
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))
    
    staff_members = Staff.query.all()
    
    if request.method == 'POST':
        visitor_name = request.form.get('visitor_name')
        visitor_contact = request.form.get('visitor_contact')
        purpose = request.form.get('purpose')
        date = request.form.get('date')
        time = request.form.get('time')
        staff_id = request.form.get('staff_id')
        
        new_appointment = Appointment(
            visitor_name=visitor_name,
            visitor_contact=visitor_contact,
            purpose=purpose,
            date=date,
            time=time,
            staff_id=staff_id
        )
        db.session.add(new_appointment)
        db.session.commit()
        log_action(current_user, 'schedule_appointment', f"Scheduled an appointment for {visitor_name}.")
        flash(f"Appointment for {visitor_name} scheduled successfully!", 'success')
        return redirect(url_for('receptionist_portal'))
        
    return render_template('schedule_appointment.html', staff_members=staff_members)


@app.route('/receptionist_portal/fees_management')
@login_required
def fees_management():
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))
    
    students = Student.query.options(db.joinedload(Student.fees)).all()
    
    return render_template('fees_management.html', students=students)


@app.route('/receptionist_portal/record_payment/<int:student_id>', methods=['GET', 'POST'])
@login_required
def record_payment(student_id):
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))

    fee_record = Fee.query.filter_by(student_id=student_id).first()
    if fee_record is None:
        flash("Fee record not found for this student.", 'danger')
        return redirect(url_for('fees_management'))
        
    student = db.session.get(Student, student_id)
    if student is None:
        flash("Student not found.", 'danger')
        return redirect(url_for('fees_management'))

    if request.method == 'POST':
        payment_amount = float(request.form.get('payment_amount'))
        
        new_payment = Payment(
            fee_id=fee_record.id,
            amount=payment_amount,
            payment_date=datetime.now().strftime('%Y-%m-%d')
        )
        db.session.add(new_payment)
        db.session.commit()

        if fee_record.amount_paid >= fee_record.total_amount:
            fee_record.status = 'paid'
        elif fee_record.amount_paid > 0:
            fee_record.status = 'partially_paid'
        
        db.session.commit()
        log_action(current_user, 'record_payment', f"Recorded a payment of ₹{payment_amount} for student '{student.name}'.")
        flash(f"Payment of ₹{payment_amount} recorded for {student.name}.", 'success')
        return redirect(url_for('fees_management'))

    return render_template('record_payment.html', fee_record=fee_record, student=student)


@app.route('/receptionist_portal/student_profile')
@app.route('/receptionist_portal/student_profile/<int:student_id>')
@login_required
def student_profile(student_id=None):
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))

    courses = Course.query.all()
    
    if student_id:
        student = db.session.get(Student, student_id)
        if student is None:
            flash("Student not found.", 'danger')
            return redirect(url_for('student_profile'))
            
        fee_record = Fee.query.filter_by(student_id=student_id).first()
        
        next_payment_date = None
        if fee_record and fee_record.payment_plan == 'installments' and fee_record.payments:
            last_payment_date = max(p.payment_date for p in fee_record.payments)
            last_paid_date_obj = datetime.strptime(last_payment_date, '%Y-%m-%d')
            months_per_installment = math.ceil(12 / fee_record.num_installments)
            
            next_payment_date = (last_paid_date_obj + timedelta(days=months_per_installment * 30)).strftime('%Y-%m-%d')

        return render_template(
            'student_profile.html',
            student=student,
            fee_record=fee_record,
            show_profile=True,
            courses=courses,
            next_payment_date=next_payment_date
        )
    else:
        students = []
        if request.method == 'POST':
            search_query = request.form.get('search_query')
            course_filter = request.form.get('course_filter')
            
            base_query = Student.query.join(Enquiry).options(db.joinedload(Student.enquiry))

            if search_query:
                base_query = base_query.filter(Student.name.like(f'%{search_query}%'))
            
            if course_filter:
                base_query = base_query.filter(Enquiry.course_interest == course_filter)
                
            students = base_query.all()
        else:
            students = Student.query.join(Enquiry).options(db.joinedload(Student.enquiry)).all()

        return render_template('student_profile.html', students=students, courses=courses, show_profile=False)


@app.route('/logout')
@login_required
def logout():
    log_action(current_user, 'logout', 'Successful logout.')
    logout_user()
    return redirect(url_for('login'))


def create_initial_data():
    with app.app_context():
        db.create_all()

        if not User.query.first():
            hashed_password = bcrypt.generate_password_hash('admin_password').decode('utf-8')
            admin = User(username='admin_user', password_hash=hashed_password, role='admin')
            db.session.add(admin)

            hashed_password = bcrypt.generate_password_hash('staff_password').decode('utf-8')
            staff = User(username='staff_user', password_hash=hashed_password, role='staff')
            db.session.add(staff)

            hashed_password = bcrypt.generate_password_hash('receptionist_password').decode('utf-8')
            receptionist = User(username='receptionist_user', password_hash=hashed_password, role='receptionist')
            db.session.add(receptionist)

            db.session.commit()
            print("Initial users created.")

if __name__ == '__main__':
    with app.app_context():       
        db.create_all()
        create_initial_data()
    app.run(debug=True)