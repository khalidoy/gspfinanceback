# config.py

import os

class Config:
    # MongoDB URI for MongoDB Atlas
    MONGO_URI = os.getenv("MONGO_URI")
    
    # Flask Secret Key (used for session management and security)
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
    
    # Logging configuration (if you want to set custom log levels or formats)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Other configurations can be added here as needed
