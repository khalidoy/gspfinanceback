import pandas as pd
from mongoengine import connect
from dotenv import load_dotenv
import os
from config import Config
from models import (
    Student, SchoolYearPeriod, User, PaymentInfo,
    AgreedPayments, RealPayments
)

# Load environment variables
load_dotenv()

def connect_to_db():
    try:
        connect(host=Config.MONGODB_SETTINGS['host'])
        print(f"Connected to MongoDB at: {Config.MONGODB_SETTINGS['host']}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

def get_or_create_default_user():
    try:
        user = User.objects.get(username='admin')
    except:
        user = User(username='admin')
        user.set_password('admin_password')
        user.save()
    return user

def detect_joined_month(row):
    months = ['m9', 'm10', 'm11', 'm12', 'm1', 'm2', 'm3', 'm4', 'm5', 'm6']
    
    # New simpler logic that preserves actual month numbers
    for month in months:
        if pd.notna(row[month]) and float(row[month]) > 0:
            month_num = int(month[1:])
            return month_num
    return 9  # Default to month 9 if no payments found

def process_student(row, school_year, user):
    name = row['name']
    transport_fee = float(row['transport']) if pd.notna(row['transport']) else 0
    insurance_fee = float(row['assurance']) if pd.notna(row['assurance']) else 0
    
    # Detect when student joined
    joined_month = detect_joined_month(row)
    
    # Create payment objects
    agreed_payments = AgreedPayments()
    real_payments = RealPayments()
    
    # Process monthly payments
    months = ['m9', 'm10', 'm11', 'm12', 'm1', 'm2', 'm3', 'm4', 'm5', 'm6']
    for month in months:
        amount = float(row[month]) if pd.notna(row[month]) else 0
        month_num = int(month[1:])
        
        # Set real payments
        real_amount = amount - transport_fee if amount > 0 and transport_fee > 0 else amount
        setattr(real_payments, f'{month}_real', max(0, real_amount))
        
        # Set transport payments
        if amount > 0 and transport_fee > 0:
            setattr(real_payments, f'{month}_transport_real', transport_fee)
        
        # Set agreed payments (same as real for this case)
        setattr(agreed_payments, f'{month}_agreed', real_amount)
        setattr(agreed_payments, f'{month}_transport_agreed', transport_fee)
    
    # Set insurance
    agreed_payments.insurance_agreed = insurance_fee
    real_payments.insurance_real = insurance_fee
    
    # Create payment info
    payment_info = PaymentInfo(
        agreed_payments=agreed_payments,
        real_payments=real_payments
    )
    
    # Create student
    student = Student(
        name=name,
        school_year=school_year,
        isNew=False,
        isLeft=True,  # These are from gone.csv so they left
        joined_month=joined_month,
        observations="Added from gone.csv",
        payments=payment_info
    )
    
    try:
        student.save()
        print(f"Successfully added student: {name} (joined in month {joined_month})")
    except Exception as e:
        print(f"Error adding student {name}: {e}")

def main():
    connect_to_db()
    
    # Get necessary objects
    try:
        school_year = SchoolYearPeriod.objects.get(name="2024/2025")
        user = get_or_create_default_user()
    except Exception as e:
        print(f"Error getting school year or user: {e}")
        return
    
    # Read CSV file
    try:
        df = pd.read_csv('c:/Users/desktop/Downloads/gone.csv')
        print(f"Found {len(df)} students in CSV")
        
        # Process each student
        for _, row in df.iterrows():
            process_student(row, school_year, user)
            
    except Exception as e:
        print(f"Error processing CSV: {e}")

if __name__ == "__main__":
    main()
