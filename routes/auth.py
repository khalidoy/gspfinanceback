# routes/auth.py

from flask import Blueprint, jsonify

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    # Placeholder login route
    return jsonify({"message": "Login route (authentication is disabled)"}), 200
