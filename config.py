# config.py

import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
    MONGODB_SETTINGS = {
        'db': 'gspFinance',
        'host': os.getenv("MONGO_URI", "mongodb+srv://khalid:Khayamowa6@cluster0.8urff.mongodb.net/gspFinance?retryWrites=true&w=majority")
    }
