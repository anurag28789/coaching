import site
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, bcrypt, User, Student, Staff, Enquiry, Receptionist, Course, Subject, Appointment

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

# --- User Loader for Flask-Login ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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
        if user and user.check_password(password):
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_portal'))
            elif user.role == 'staff':
                return redirect(url_for('staff_portal'))
            elif user.role == 'receptionist':
                return redirect(url_for('receptionist_portal'))
        
        return "Login failed. Please try again."

    return render_template('login.html')

@app.route('/admin_portal')
@login_required
def admin_portal():
    if current_user.role == 'admin':
        total_students = Student.query.count()
        total_staff = Staff.query.count()
        fees_collected = 75000
        pending_fees = 15000

        return render_template(
            'admin_portal.html',
            total_students=total_students,
            total_staff=total_staff,
            fees_collected=fees_collected,
            pending_fees=pending_fees,
            current_user=current_user
        )
    return redirect(url_for('login'))

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
        new_user = User(username=username, password_hash=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        if role == 'staff':
            new_staff = Staff(name=name, user_id=new_user.id)
            db.session.add(new_staff)
        elif role == 'receptionist':
            new_receptionist = Receptionist(name=name, user_id=new_user.id)
            db.session.add(new_receptionist)

        db.session.commit()
        flash(f"User '{username}' with role '{role}' created successfully.", 'success')
        return redirect(url_for('admin_portal'))

    return render_template('add_user.html')


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
            flash(f"Course '{course_name}' added successfully.", 'success')
        
        return redirect(url_for('view_courses'))
    
    return render_template('add_course.html')


@app.route('/admin_portal/add_subject/<int:course_id>', methods=['GET', 'POST'])
@login_required
def add_subject(course_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        subject_name = request.form.get('subject_name')
        new_subject = Subject(name=subject_name, course_id=course.id)
        db.session.add(new_subject)
        db.session.commit()
        flash(f"Subject '{subject_name}' added to {course.name} successfully.", 'success')
        return redirect(url_for('view_courses'))
        
    return render_template('add_subject.html', course=course)


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
        flash(f"Enquiry for {name} submitted successfully!", 'success')
        return redirect(url_for('receptionist_portal'))

    return render_template('add_enquiry.html', courses=courses)

@app.route('/receptionist_portal/cancel_enquiry/<int:enquiry_id>')
@login_required
def cancel_enquiry(enquiry_id):
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))
    
    enquiry = Enquiry.query.get_or_404(enquiry_id)
    enquiry.status = 'Cancelled'
    db.session.commit()
    flash(f"Enquiry for {enquiry.name} has been cancelled.", 'success')
    return redirect(url_for('receptionist_portal'))


@app.route('/receptionist_portal/admit_student/<int:enquiry_id>', methods=['GET', 'POST'])
@login_required
def admit_student(enquiry_id):
    if current_user.role != 'receptionist':
        return redirect(url_for('login'))
    
    enquiry = Enquiry.query.get_or_404(enquiry_id)
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
        
        # Check if the enquiry has already been admitted
        if enquiry.status == 'Admitted':
            flash("This enquiry has already been processed for admission.", 'warning')
            return redirect(url_for('receptionist_portal'))
        
        # Create a new student record
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
        
        # Update the enquiry status
        enquiry.status = 'Admitted'
        
        db.session.commit()
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

        # Create a new Enquiry record with 'Admitted' status
        new_enquiry = Enquiry(
            name=name,
            contact=contact,
            course_interest=course,
            status='Admitted',
            joining_date=date_of_admission
        )
        db.session.add(new_enquiry)
        db.session.commit()

        # Create a new Student record, linked to the new Enquiry
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
        
        flash(f"Appointment for {visitor_name} scheduled successfully!", 'success')
        return redirect(url_for('receptionist_portal'))
        
    return render_template('schedule_appointment.html', staff_members=staff_members)


@app.route('/logout')
@login_required
def logout():
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