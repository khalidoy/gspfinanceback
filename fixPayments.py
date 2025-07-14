from models import Student, SchoolYearPeriod
from flask_mongoengine import MongoEngine
from mongoengine import connect
import datetime
import sys
from dotenv import load_dotenv
import os

# Connect directly to production MongoDB
MONGO_URI = "mongodb+srv://khalid:Khayamowa6@cluster0.8urff.mongodb.net/gspFinance"

def connect_db():
    try:
        connect(host=MONGO_URI)
        print("Connected to production MongoDB")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

# Establish the connection before proceeding
connect_db()

def compare_payments():
    discrepancy_students = []
    
    # Get all students
    students = Student.objects()
    
    for student in students:
        if not student.payments:
            continue
            
        has_discrepancy = False
        discrepancies = []
        
        # Get real and agreed payments
        real = student.payments.real_payments
        agreed = student.payments.agreed_payments
        
        # Compare monthly payments
        for month in range(1, 13):
            if month < 7:
                month_str = f'm{month}'
            else:
                month_str = f'm{month}'
            
            # Regular monthly payments
            real_amount = getattr(real, f'{month_str}_real', 0) or 0
            agreed_amount = getattr(agreed, f'{month_str}_agreed', 0) or 0
            
            if real_amount > agreed_amount:
                discrepancies.append(f"Month {month}: Real (${real_amount}) > Agreed (${agreed_amount})")
                has_discrepancy = True
            
            # Transport payments
            real_transport = getattr(real, f'{month_str}_transport_real', 0) or 0
            agreed_transport = getattr(agreed, f'{month_str}_transport_agreed', 0) or 0
            
            if real_transport > agreed_transport:
                discrepancies.append(f"Month {month} Transport: Real (${real_transport}) > Agreed (${agreed_transport})")
                has_discrepancy = True
        
        # Compare insurance payments
        if (real.insurance_real or 0) > (agreed.insurance_agreed or 0):
            discrepancies.append(f"Insurance: Real (${real.insurance_real}) > Agreed (${agreed.insurance_agreed})")
            has_discrepancy = True
        
        if has_discrepancy:
            discrepancy_students.append({
                'student_name': student.name,
                'discrepancies': discrepancies
            })
    
    # Print results
    print(f"\nFound {len(discrepancy_students)} students with payment discrepancies:")
    print("=" * 50)
    
    for student in discrepancy_students:
        print(f"\nStudent: {student['student_name']}")
        for discrepancy in student['discrepancies']:
            print(f"  - {discrepancy}")
        print("-" * 30)

def fix_payments():
    fixed_count = 0
    
    # Get all students
    students = Student.objects()
    
    for student in students:
        if not student.payments:
            continue
            
        needs_update = False
        real = student.payments.real_payments
        agreed = student.payments.agreed_payments
        
        # Compare and fix monthly payments
        for month in range(1, 13):
            month_str = f'm{month}'
            
            # Regular monthly payments
            real_amount = getattr(real, f'{month_str}_real', 0) or 0
            agreed_amount = getattr(agreed, f'{month_str}_agreed', 0) or 0
            
            if real_amount > agreed_amount:
                setattr(agreed, f'{month_str}_agreed', real_amount)
                needs_update = True
                print(f"Fixing {student.name}'s {month_str} payment: {agreed_amount} -> {real_amount}")
            
            # Transport payments
            real_transport = getattr(real, f'{month_str}_transport_real', 0) or 0
            agreed_transport = getattr(agreed, f'{month_str}_transport_agreed', 0) or 0
            
            if real_transport > agreed_transport:
                setattr(agreed, f'{month_str}_transport_agreed', real_transport)
                needs_update = True
                print(f"Fixing {student.name}'s {month_str} transport: {agreed_transport} -> {real_transport}")
        
        # Fix insurance payments
        if (real.insurance_real or 0) > (agreed.insurance_agreed or 0):
            agreed.insurance_agreed = real.insurance_real
            needs_update = True
            print(f"Fixing {student.name}'s insurance: {agreed.insurance_agreed} -> {real.insurance_real}")
        
        # Save changes if needed
        if needs_update:
            student.save()
            fixed_count += 1
    
    print(f"\nFixed payments for {fixed_count} students")

if __name__ == "__main__":
    print("Starting payment fixes on production database...")
    fix_payments()
    print("Finished fixing payments")
