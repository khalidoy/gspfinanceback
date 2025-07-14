import os
import sys
import pandas as pd
from dotenv import load_dotenv
from mongoengine import connect, DoesNotExist
from models import (
    Classe, Student, SchoolYearPeriod, User,
    Save, ChangeDetail, Payment, PaymentInfo,
    AgreedPayments, RealPayments
)
from datetime import datetime

# Load .env and point at development DB
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/gspFinance")

def connect_dev():
    connect(host=MONGO_URI)
    print(f"Connected to dev MongoDB @ {MONGO_URI}")

def get_or_create_default_user(username='admin', password='admin_password'):
    try:
        return User.objects.get(username=username)
    except DoesNotExist:
        u = User(username=username)
        u.set_password(password)
        u.save()
        return u

def get_or_create_school_year():
    # Try to get the latest SchoolYearPeriod, or create a dummy one if none exists
    sy = SchoolYearPeriod.objects.order_by('-start_date').first()
    if sy:
        return sy
    now = datetime.utcnow()
    sy = SchoolYearPeriod(
        name=f"DevYear {now.year}",
        start_date=datetime(now.year, 9, 1),
        end_date=datetime(now.year+1, 7, 31)
    )
    sy.save()
    return sy

def process_csv(path):
    df = pd.read_csv(path, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()
    school_year = get_or_create_school_year()
    user = get_or_create_default_user()

    for idx, row in df.iterrows():
        # --- Classe ---
        cls_name = str(row['classe']).strip()
        classe = Classe.objects(name=cls_name).first()
        if not classe:
            classe = Classe(name=cls_name)
            classe.save()

        # --- Student ---
        student_name = str(row['name']).strip()
        joined_month = 9
        observations = ""
        transport_fee = float(row['transport']) if not pd.isna(row['transport']) else 0
        insurance_fee = float(row['assurance']) if not pd.isna(row['assurance']) else 0

        # Monthly fees
        m_fields = ['m9','m10','m11','m12','m1','m2','m3','m4','m5','m6']
        months = [9,10,11,12,1,2,3,4,5,6]
        monthly_fees = []
        for mf in m_fields:
            val = float(row[mf]) if not pd.isna(row[mf]) else 0
            monthly_fees.append(val)

        # Create Student
        student = Student(
            name=student_name,
            school_year=school_year,
            isNew=False,
            isLeft=False,
            joined_month=joined_month,
            observations=observations,
            payments=None,
            left_date=None,
            classe=classe
        )
        student.save()

        # Save record for creation
        # changes = [
        #     ChangeDetail(field_name='name', old_value=None, new_value=student.name),
        #     ChangeDetail(field_name='joined_month', old_value=None, new_value=str(student.joined_month)),
        #     ChangeDetail(field_name='observations', old_value=None, new_value=student.observations)
        # ]
        # Save(
        #     student=student,
        #     user=user,
        #     types=['other'],
        #     changes=changes,
        #     date=datetime.utcnow()
        # ).save()

        # --- PaymentInfo ---
        agreed_payments = AgreedPayments(
            m9_agreed=monthly_fees[0],
            m10_agreed=monthly_fees[1],
            m11_agreed=monthly_fees[2],
            m12_agreed=monthly_fees[3],
            m1_agreed=monthly_fees[4],
            m2_agreed=monthly_fees[5],
            m3_agreed=monthly_fees[6],
            m4_agreed=monthly_fees[7],
            m5_agreed=monthly_fees[8],
            m6_agreed=monthly_fees[9],
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
            insurance_agreed=1100
        )
        real_payments = RealPayments(
            m9_real=monthly_fees[0],
            m10_real=monthly_fees[1],
            m11_real=monthly_fees[2],
            m12_real=monthly_fees[3],
            m1_real=monthly_fees[4],
            m2_real=monthly_fees[5],
            m3_real=monthly_fees[6],
            m4_real=monthly_fees[7],
            m5_real=monthly_fees[8],
            m6_real=monthly_fees[9],
            m9_transport_real=transport_fee,
            m10_transport_real=transport_fee if monthly_fees[1] > 0 else 0,
            m11_transport_real=transport_fee if monthly_fees[2] > 0 else 0,
            m12_transport_real=transport_fee if monthly_fees[3] > 0 else 0,
            m1_transport_real=transport_fee if monthly_fees[4] > 0 else 0,
            m2_transport_real=transport_fee if monthly_fees[5] > 0 else 0,
            m3_transport_real=transport_fee if monthly_fees[6] > 0 else 0,
            m4_transport_real=transport_fee if monthly_fees[7] > 0 else 0,
            m5_transport_real=transport_fee if monthly_fees[8] > 0 else 0,
            m6_transport_real=transport_fee if monthly_fees[9] > 0 else 0,
            insurance_real=insurance_fee
        )
        payment_info = PaymentInfo(
            agreed_payments=agreed_payments,
            real_payments=real_payments
        )
        student.payments = payment_info
        student.save()

        # --- Payments and Save records ---
        for i, month in enumerate(months):
            # Monthly payment
            amt = monthly_fees[i]
            if amt > 0:
                p = Payment(
                    student=student,
                    user=user,
                    amount=amt,
                    payment_type='monthly',
                    month=month,
                    date=datetime.utcnow()
                )
                p.save()
                Save(
                    student=student,
                    user=user,
                    types=['payment'],
                    changes=[ChangeDetail(field_name=f'm{month}_real', old_value=None, new_value=str(amt))],
                    date=p.date
                ).save()
            # Transport payment
            t_amt = transport_fee if amt > 0 else 0
            if t_amt > 0:
                p = Payment(
                    student=student,
                    user=user,
                    amount=t_amt,
                    payment_type='transport',
                    month=month,
                    date=datetime.utcnow()
                )
                p.save()
                Save(
                    student=student,
                    user=user,
                    types=['payment'],
                    changes=[ChangeDetail(field_name=f'm{month}_transport_real', old_value=None, new_value=str(t_amt))],
                    date=p.date
                ).save()
        # Insurance payment
        if insurance_fee > 0:
            p = Payment(
                student=student,
                user=user,
                amount=insurance_fee,
                payment_type='insurance',
                month=None,
                date=datetime.utcnow()
            )
            p.save()
            Save(
                student=student,
                user=user,
                types=['payment'],
                changes=[ChangeDetail(field_name='insurance_real', old_value=None, new_value=str(insurance_fee))],
                date=p.date
            ).save()

        print(f"[{idx+1}] Inserted Student: {student.name} (Classe: {cls_name})")

if __name__ == "__main__":
    # Hardcoded CSV file path
    csv_path = r"c:\Users\desktop\Downloads\csvFile.csv"
    connect_dev()
    process_csv(csv_path)
    print("All done.")