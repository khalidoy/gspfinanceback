# migrate.py

import sys
import io
import pandas as pd
import json
from mongoengine import connect, DoesNotExist, ValidationError
from datetime import datetime
from dotenv import load_dotenv  # Import dotenv to load .env file
import os

# Load environment variables from .env file
load_dotenv()

from config import Config  # Import Config after loading environment variables

# Ensure utf-8 encoding is used for output (important for non-Latin characters)
if sys.version_info >= (3, 7):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
else:
    import sys
    from importlib import reload
    reload(sys)
    sys.setdefaultencoding('utf-8')

# Connect to MongoDB using configuration from config.py
def connect_db():
<<<<<<< HEAD
    # Use MONGODB_SETTINGS from Config
    connect(
        db=Config.MONGODB_SETTINGS['db'],
        host=Config.MONGODB_SETTINGS['host']
    )
    db=Config.MONGODB_SETTINGS['db']
    host=Config.MONGODB_SETTINGS['host']
    print("Connected to MongoDB")
    print("host :"+str(host))
    print("db :"+str(db))
=======
    try:
        connect(
            host=Config.MONGODB_SETTINGS['host']
            # db=Config.MONGODB_SETTINGS['db']  # Not needed if DB is included in the URI
        )
        print(f"Connected to MongoDB at: {Config.MONGODB_SETTINGS['host']}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

# Establish the connection before importing models
connect_db()

# Now import models after the connection is established
from models import (
    AgreedPayments, PaymentInfo, RealPayments, Student, SchoolYearPeriod,
    Payment, Save, ChangeDetail, User, Depence, DailyAccounting
)
>>>>>>> dd2373cbfc987ecea76ade053ff99627bd25067e

# Create or get default User
def get_or_create_default_user(username='admin', password='admin_password'):
    try:
        user = User.objects.get(username=username)
        print(f"User '{username}' already exists.")
    except DoesNotExist:
        user = User(username=username)
        user.set_password(password)
        user.save()
        print(f"Created default user '{username}'.")
    return user

# Create or get SchoolYearPeriod
def get_or_create_school_year(name, start_date, end_date):
    try:
        school_year = SchoolYearPeriod.objects.get(name=name)
        print(f"SchoolYearPeriod '{name}' already exists.")
    except DoesNotExist:
        school_year = SchoolYearPeriod(
            name=name,
            start_date=start_date,
            end_date=end_date
        )
        school_year.save()
        print(f"Created SchoolYearPeriod '{name}'.")
    return school_year

# Transform payment fields into Payment documents
def create_payment_records(student, user, payment_type, month, amount, payment_date):
    if amount <= 0:
        return None  # Skip zero or negative payments

    payment = Payment(
        student=student,
        user=user,
        amount=amount,
        payment_type=payment_type,
        month=month,
        date=payment_date
    )
    payment.save()
    print(f"Created Payment: {payment_type} for Student '{student.name}', Month: {month}, Amount: {amount}")
    return payment

# Create Save record
def create_save_record(student, user, types, changes, save_date):
    save = Save(
        student=student,
        user=user,
        types=types,
        changes=changes,
        date=save_date
    )
    save.save()
    print(f"Created Save record for Student '{student.name}' on {save_date.isoformat()}")
    return save

# Process a single student row
def process_student_row(row, school_year, user):
    student_name = row['الإسم الكامل']
    joined_month = 9  # As per your existing data; adjust if necessary
    observations = ""  # Set observations to empty string

    # Extract transport and insurance fees with defaulting to 0 if NaN
    transport_fee = row['النقل'] if pd.notna(row['النقل']) else 0
    insurance_fee = row['التأمين'] if pd.notna(row['التأمين']) else 0

    # Extract the monthly fees with defaulting to 0 if NaN
    m9 = row['شهر 09'] if pd.notna(row['شهر 09']) else 0
    m10 = row['شهر 10'] if pd.notna(row['شهر 10']) else 0
    m11 = row['شهر 11'] if pd.notna(row['شهر 11']) else 0
    m12 = row['شهر 12'] if pd.notna(row['شهر 12']) else 0
    m1 = row['شهر 01'] if pd.notna(row['شهر 01']) else 0
    m2 = row['شهر 02'] if pd.notna(row['شهر 02']) else 0
    m3 = row['شهر 03'] if pd.notna(row['شهر 03']) else 0
    m4 = row['شهر 04'] if pd.notna(row['شهر 04']) else 0
    m5 = row['شهر 05'] if pd.notna(row['شهر 05']) else 0
    m6 = row['شهر 06'] if pd.notna(row['شهر 06']) else 0

    # Create Student document
    student = Student(
        name=student_name,
        school_year=school_year,
        isNew=False,  # Existing students are not new
        isLeft=False, # Existing students are active
        joined_month=joined_month,
        observations=observations,
        payments=None,  # Initialize as None; will set PaymentInfo later
        left_date=None
    )
    student.save()
    print(f"Created Student: {student_name} (ID: {student.id})")

    # Create initial Save record for student creation
    changes = [
        ChangeDetail(field_name='name', old_value=None, new_value=student.name),
        ChangeDetail(field_name='joined_month', old_value=None, new_value=str(student.joined_month)),
        ChangeDetail(field_name='observations', old_value=None, new_value=student.observations)
    ]
    save = Save(
        student=student,
        user=user,
        types=['other'],
        changes=changes,
        date=datetime.utcnow()
    )
    save.save()
    print(f"Created Save record for Student '{student.name}' creation.")

    # Calculate real payments by ensuring no NaN values
    real_payments = {
        'm9_real': m9,
        'm10_real': m10 - transport_fee if m10 != 0 else 0,
        'm11_real': m11 - transport_fee if m11 != 0 else 0,
        'm12_real': m12 - transport_fee if m12 != 0 else 0,
        'm1_real': m1 - transport_fee if m1 != 0 else 0,
        'm2_real': m2 - transport_fee if m2 != 0 else 0,
        'm3_real': m3 - transport_fee if m3 != 0 else 0,
        'm4_real': m4 - transport_fee if m4 != 0 else 0,
        'm5_real': m5 - transport_fee if m5 != 0 else 0,
        'm6_real': m6 - transport_fee if m6 != 0 else 0,
    }

    # Ensure no negative real payments
    for key, value in real_payments.items():
        if value < 0:
            print(f"Warning: {key} for Student '{student.name}' is negative. Setting to 0.")
            real_payments[key] = 0

    # Construct PaymentInfo with agreed and real payments
    payment_info = PaymentInfo(
        agreed_payments=AgreedPayments(
            m9_agreed=m9,
            m10_agreed=m9,  # Adjust as per actual agreed logic
            m11_agreed=m9,
            m12_agreed=m9,
            m1_agreed=m9,
            m2_agreed=m9,
            m3_agreed=m9,
            m4_agreed=m9,
            m5_agreed=m9,
            m6_agreed=m9,

            m9_transport_agreed=transport_fee,
            m10_transport_agreed=transport_fee,
            m11_transport_agreed=transport_fee,
            m12_transport_agreed=transport_fee,
            m1_transport_agreed=transport_fee,
            m2_transport_agreed=transport_fee,
            m3_transport_agreed=transport_fee,
            m4_transport_agreed=transport_fee,
            m5_transport_agreed=transport_fee,
            m6_transport_agreed=transport_fee,

            insurance_agreed=1100  # Default agreed insurance
        ),
        real_payments=RealPayments(
            m9_real=real_payments['m9_real'],
            m10_real=real_payments['m10_real'],
            m11_real=real_payments['m11_real'],
            m12_real=real_payments['m12_real'],
            m1_real=real_payments['m1_real'],
            m2_real=real_payments['m2_real'],
            m3_real=real_payments['m3_real'],
            m4_real=real_payments['m4_real'],
            m5_real=real_payments['m5_real'],
            m6_real=real_payments['m6_real'],

            m9_transport_real=transport_fee,
            m10_transport_real=transport_fee if real_payments['m10_real'] > 0 else 0,
            m11_transport_real=transport_fee if real_payments['m11_real'] > 0 else 0,
            m12_transport_real=transport_fee if real_payments['m12_real'] > 0 else 0,
            m1_transport_real=transport_fee if real_payments['m1_real'] > 0 else 0,
            m2_transport_real=transport_fee if real_payments['m2_real'] > 0 else 0,
            m3_transport_real=transport_fee if real_payments['m3_real'] > 0 else 0,
            m4_transport_real=transport_fee if real_payments['m4_real'] > 0 else 0,
            m5_transport_real=transport_fee if real_payments['m5_real'] > 0 else 0,
            m6_transport_real=transport_fee if real_payments['m6_real'] > 0 else 0,

            insurance_real=insurance_fee
        )
    )

    student.payments = payment_info
    student.save()
    print(f"Updated PaymentInfo for Student '{student.name}'.")

    # Create Payment documents and Save records
    payment_fields = [
        ('m9_agreed', 'monthly'),
        ('m10_agreed', 'monthly'),
        ('m11_agreed', 'monthly'),
        ('m12_agreed', 'monthly'),
        ('m1_agreed', 'monthly'),
        ('m2_agreed', 'monthly'),
        ('m3_agreed', 'monthly'),
        ('m4_agreed', 'monthly'),
        ('m5_agreed', 'monthly'),
        ('m6_agreed', 'monthly'),

        ('m9_real', 'monthly'),
        ('m10_real', 'monthly'),
        ('m11_real', 'monthly'),
        ('m12_real', 'monthly'),
        ('m1_real', 'monthly'),
        ('m2_real', 'monthly'),
        ('m3_real', 'monthly'),
        ('m4_real', 'monthly'),
        ('m5_real', 'monthly'),
        ('m6_real', 'monthly'),

        ('m9_transport_agreed', 'transport'),
        ('m10_transport_agreed', 'transport'),
        ('m11_transport_agreed', 'transport'),
        ('m12_transport_agreed', 'transport'),
        ('m1_transport_agreed', 'transport'),
        ('m2_transport_agreed', 'transport'),
        ('m3_transport_agreed', 'transport'),
        ('m4_transport_agreed', 'transport'),
        ('m5_transport_agreed', 'transport'),
        ('m6_transport_agreed', 'transport'),

        ('m9_transport_real', 'transport'),
        ('m10_transport_real', 'transport'),
        ('m11_transport_real', 'transport'),
        ('m12_transport_real', 'transport'),
        ('m1_transport_real', 'transport'),
        ('m2_transport_real', 'transport'),
        ('m3_transport_real', 'transport'),
        ('m4_transport_real', 'transport'),
        ('m5_transport_real', 'transport'),
        ('m6_transport_real', 'transport'),

        # Insurance Fields
        ('insurance_agreed', 'insurance'),
        ('insurance_real', 'insurance'),
    ]

    for field, p_type in payment_fields:
        if 'agreed' in field:
            # Agreed payments are handled separately; skip creating Payment documents for them
            continue  # Alternatively, if you still want Payment documents for agreed payments, adjust accordingly

        # Real payments
        amount = getattr(payment_info.real_payments, field, 0)
        if p_type == 'insurance':
            payment_type = 'insurance'
            month = None  # Insurance payments do not have a month
        else:
            # Extract month number from field name, e.g., 'm9_real' -> 9
            month_str = field.split('_')[0][1:]  # 'm9_real' -> '9'
            try:
                month = int(month_str)
            except ValueError:
                print(f"Invalid month value extracted from field '{field}'. Skipping.")
                continue
            payment_type = p_type  # 'monthly' or 'transport'

        if amount > 0:
            payment_date = datetime.utcnow()  # Adjust as needed

            payment = create_payment_records(
                student=student,
                user=user,
                payment_type=payment_type,
                month=month,
                amount=amount,
                payment_date=payment_date
            )
            if payment:
                # Create Save record for this payment
                changes = [
                    ChangeDetail(
                        field_name=field,
                        old_value=None,
                        new_value=str(amount)
                    )
                ]
                save = Save(
                    student=student,
                    user=user,
                    types=['payment'],
                    changes=changes,
                    date=payment_date
                )
                save.save()
                print(f"Created Save record for Payment '{field}'.")

def process_student_data(file_path, school_year_id):
    # Load the Excel data into a pandas DataFrame
    try:
        df = pd.read_excel(file_path)
        print(f"Loaded Excel file: {file_path}")
    except Exception as e:
        print(f"Failed to load Excel file '{file_path}': {e}")
        return

    # Strip any leading/trailing spaces from column names
    df.columns = df.columns.str.strip()

    # Ensure necessary columns exist
    required_columns = ['شهر 09', 'شهر 10', 'شهر 11', 'شهر 12',
                        'شهر 01', 'شهر 02', 'شهر 03', 'شهر 04',
                        'شهر 05', 'شهر 06', 'النقل', 'التأمين', 'الإسم الكامل']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Missing columns in Excel file: {missing_columns}")
        return

    # Fetch SchoolYearPeriod
    try:
        school_year = SchoolYearPeriod.objects.get(id=school_year_id)
        print(f"Using SchoolYearPeriod: {school_year.name}")
    except DoesNotExist:
        print(f"SchoolYearPeriod with ID '{school_year_id}' does not exist.")
        return

    # Fetch default User
    user = get_or_create_default_user()

    # Iterate through each row (student) in the DataFrame
    for index, row in df.iterrows():
        print(f"Processing row {index + 1}/{len(df)}")
        process_student_row(row, school_year, user)

    print("Migration completed successfully.")

if __name__ == '__main__':
    print("Starting migration script...")
    # No need to call connect_db() here as it's already called above
    school_year_id = "67120eb278180a8e328b2d38"  # Provided SchoolYearPeriod ObjectId
    file_path = 'data/cleaned_students.xlsx'  # Replace with your actual file path
    process_student_data(file_path, school_year_id)
