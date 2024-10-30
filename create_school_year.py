# create_school_year.py

from models import db, SchoolYearPeriod
from mongoengine import connect
from datetime import datetime

# Connect to MongoDB
def connect_db():
    connect(
        db='gspFinance',
        host='localhost',
        port=27017
        # Add 'username', 'password', 'authentication_source' if required
    )
    print("Connected to MongoDB.")

def create_school_year(name, start_date, end_date):
    try:
        # Check if the school year already exists
        school_year = SchoolYearPeriod.objects.get(name=name)
        print(f"SchoolYearPeriod '{name}' already exists with ID: {school_year.id}")
    except SchoolYearPeriod.DoesNotExist:
        # Create a new SchoolYearPeriod
        school_year = SchoolYearPeriod(
            name=name,
            start_date=start_date,
            end_date=end_date
        )
        school_year.save()
        print(f"Created SchoolYearPeriod '{name}' with ID: {school_year.id}")
    return school_year

if __name__ == '__main__':
    connect_db()
    # Define your school year details
    school_year_name = "2023/2024"
    school_year_start = datetime(2023, 9, 1)  # September 1, 2023
    school_year_end = datetime(2024, 6, 30)   # June 30, 2024

    create_school_year(school_year_name, school_year_start, school_year_end)
