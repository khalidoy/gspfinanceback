# routes/auth.py

from flask import Blueprint, jsonify, request, session, make_response, current_app
from models import User
from mongoengine import DoesNotExist
import bcrypt
import jwt
import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"status": "error", "message": "Username and password are required"}), 400

        # Check if user already exists
        if User.objects(username=username).first():
            return jsonify({"status": "error", "message": "Username already exists"}), 400

        # Create new user
        new_user = User(username=username)
        new_user.set_password(password)  # This method is defined in your User model
        new_user.save()

        return jsonify({
            "status": "success",
            "message": "User created successfully"
        }), 201

    except Exception as e:
        logging.error(f"Error in register: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"status": "error", "message": "Username and password are required"}), 400

        # Find user by username
        try:
            user = User.objects.get(username=username)
        except DoesNotExist:
            return jsonify({"status": "error", "message": "Invalid username or password"}), 401

        # Check password
        if not user.check_password(password):
            return jsonify({"status": "error", "message": "Invalid username or password"}), 401

        # Generate JWT token
        secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')
        token = jwt.encode({
            'user_id': str(user.id),
            'username': user.username,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }, secret_key, algorithm='HS256')

        # Store user in session
        session['user'] = {
            'id': str(user.id),
            'username': user.username
        }

        # Create response
        resp = make_response(jsonify({
            "status": "success",
            "message": "Login successful",
            "user": {
                "id": str(user.id),
                "username": user.username
            },
            "token": token
        }), 200)

        # Set token as cookie
        resp.set_cookie('token', token, httponly=True, secure=False, samesite='Lax', max_age=86400)

        return resp

    except Exception as e:
        logging.error(f"Error in login: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    try:
        # Clear session
        session.pop('user', None)

        # Create response
        resp = make_response(jsonify({
            "status": "success",
            "message": "Logout successful"
        }), 200)

        # Clear token cookie
        resp.set_cookie('token', '', httponly=True, expires=0)

        return resp

    except Exception as e:
        logging.error(f"Error in logout: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@auth_bp.route('/current-user', methods=['GET'])
def get_current_user():
    try:
        # First check if user in session
        user_session = session.get('user')
        if user_session:
            return jsonify({"status": "success", "user": user_session}), 200

        # Then check for token in cookies or Authorization header
        token = request.cookies.get('token')
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({"status": "error", "message": "Not authenticated"}), 401

        # Verify token
        try:
            secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            user_id = payload['user_id']
            
            # Get user from database
            user = User.objects.get(id=user_id)
            
            # Update session
            session['user'] = {
                'id': str(user.id),
                'username': user.username
            }
            
            return jsonify({
                "status": "success", 
                "user": {
                    "id": str(user.id),
                    "username": user.username
                }
            }), 200
            
        except jwt.ExpiredSignatureError:
            return jsonify({"status": "error", "message": "Token expired"}), 401
        except (jwt.InvalidTokenError, DoesNotExist):
            return jsonify({"status": "error", "message": "Invalid token"}), 401
        
    except Exception as e:
        logging.error(f"Error in get_current_user: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Middleware function to verify JWT token
def token_required(f):
    from functools import wraps
    
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check for token in cookies or Authorization header
        token = request.cookies.get('token')
        if not token:
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'status': 'error', 'message': 'Token is missing'}), 401
        
        try:
            secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            current_user = User.objects.get(id=payload['user_id'])
        except jwt.ExpiredSignatureError:
            return jsonify({'status': 'error', 'message': 'Token expired'}), 401
        except (jwt.InvalidTokenError, DoesNotExist):
            return jsonify({'status': 'error', 'message': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated
