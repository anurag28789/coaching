from app import app, db, User, bcrypt
import sys

def create_user(username, password, role):
    """
    Creates a new user in the database.
    """
    with app.app_context():
        # Check if the user already exists
        if User.query.filter_by(username=username).first():
            print(f"User '{username}' already exists.")
            return

        # Hash the password for security
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Create a new User object
        new_user = User(username=username, password_hash=hashed_password, role=role)
        
        # Add the new user to the database session and commit
        db.session.add(new_user)
        db.session.commit()
        print(f"User '{username}' with role '{role}' created successfully.")

if __name__ == '__main__':
    # You can change these values to create your own admin user.
    # Replace 'your_new_admin_username' and 'your_strong_password'
    new_username = 'admin'
    new_password = '123456'
    new_role = 'admin'

    create_user(new_username, new_password, new_role)