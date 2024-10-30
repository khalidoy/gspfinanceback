# config.py

import os

class Config:
    # MongoDB URI (for MongoDB Atlas)
    # Use the MONGO_URI environment variable set on Render or your local environment
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/gspFinance')

    # Flask Secret Key (used for session management and security)
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key_here')

    # Additional MongoDB settings (if needed)
    MONGODB_DB = os.environ.get('MONGODB_DB', 'gspFinance')
    MONGODB_HOST = os.environ.get('MONGODB_HOST', 'localhost')
    MONGODB_PORT = int(os.environ.get('MONGODB_PORT', 27017))
    MONGODB_USERNAME = os.environ.get('MONGODB_USERNAME')
    MONGODB_PASSWORD = os.environ.get('MONGODB_PASSWORD')

    # Logging configuration (if you want to set custom log levels or formats)
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Other configurations can be added here as needed, for example:
    # Example: ENABLE_FEATURE_X = os.environ.get('ENABLE_FEATURE_X', 'False')
