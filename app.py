from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, bcrypt, User, Student, Staff  # import db & models together

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

# --- Routes (same as before) ---
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
        return render_template('receptionist_portal.html', current_user=current_user)
    return redirect(url_for('login'))

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
    create_initial_data()
    app.run(debug=True)
