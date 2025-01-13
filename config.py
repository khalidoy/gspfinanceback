# config.py

import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your_secret_key_here")
    MONGODB_SETTINGS = {
<<<<<<< HEAD
        'db': 'gspFinance',
        'host': "mongodb+srv://khalid:Khayamowa6@cluster0.8urff.mongodb.net/gspFinance?retryWrites=true&w=majority"
=======
        'host': os.getenv("MONGO_URI")
>>>>>>> dd2373cbfc987ecea76ade053ff99627bd25067e
    }
