# config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB settings
    MONGODB_SETTINGS = {
        'host': os.getenv('MONGO_URI', 'mongodb://localhost:27017/gspFinance'),
        'db': 'gspFinance'  # Explicitly set database name
    }
    
    # Secret key for session and JWT
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key-change-in-production')
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds
    
    # CORS settings
    CORS_HEADERS = 'Content-Type'
