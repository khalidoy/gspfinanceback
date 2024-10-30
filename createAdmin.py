# create_admin_user.py

from models import db, User
from mongoengine import connect, DoesNotExist
import sys

def connect_db():
    connect(
        db='gspFinance',
        host='localhost',
        port=27017
    )
    print("Connected to MongoDB.")

def create_admin_user(username='admin', password='lolo'):
    try:
        # Check if the admin user already exists
        user = User.objects.get(username=username)
        print(f"User '{username}' already exists with ID: {user.id}")
    except DoesNotExist:
        # Create a new admin user
        user = User(
            username=username
        )
        user.set_password(password)
        user.save()
        print(f"Created admin user '{username}' with ID: {user.id}")
    return user

if __name__ == '__main__':
    connect_db()
    
    # Optionally, allow setting username and password via command-line arguments
    if len(sys.argv) == 3:
        admin_username = sys.argv[1]
        admin_password = sys.argv[2]
    else:
        admin_username = 'admin'
        admin_password = 'lolo'  # **Important:** Change this to a secure password!

    create_admin_user(username=admin_username, password=admin_password)
