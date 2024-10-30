# config.py

import os

class Config:
    # MongoDB settings
    MONGODB_SETTINGS = {
        'db': os.environ.get('MONGODB_DB', 'gspFinance'),
        'host': os.environ.get('MONGODB_HOST', 'localhost'),
        'port': int(os.environ.get('MONGODB_PORT', 27017)),
        # 'username': os.environ.get('MONGODB_USERNAME'),
        # 'password': os.environ.get('MONGODB_PASSWORD'),
        # 'authentication_source': os.environ.get('MONGODB_AUTH_SOURCE', 'admin')
    }

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key_here')

    # Other configurations can be added here
