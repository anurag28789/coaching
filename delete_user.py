from app import app, db, User
import sys

def delete_user(username):
    """
    Deletes a user from the database by their username.
    """
    with app.app_context():
        # Find the user in the database
        user = User.query.filter_by(username=username).first()

        if user:
            # Delete the user from the database session
            db.session.delete(user)
            # Commit the changes to the database
            db.session.commit()
            print(f"User '{username}' deleted successfully.")
        else:
            print(f"User '{username}' not found.")

if __name__ == '__main__':
    # Enter the username of the admin you want to delete
    username_to_delete = 'your_new_admin_username' 
    delete_user(username_to_delete)
    