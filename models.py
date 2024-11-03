# models.py

from flask_mongoengine import MongoEngine
from datetime import datetime
import bcrypt
from mongoengine import (
    CASCADE, NULLIFY, PULL, StringField, DateTimeField, IntField, FloatField,
    BooleanField, ListField, ReferenceField, EmbeddedDocumentField, EmbeddedDocument
)

db = MongoEngine()

# ----------------------------------------
# Embedded Documents
# ----------------------------------------

class ChangeDetail(EmbeddedDocument):
    field_name = StringField(required=True)
    old_value = StringField()
    new_value = StringField()

class AgreedPayments(EmbeddedDocument):
    m9_agreed = FloatField(default=0)
    m10_agreed = FloatField(default=0)
    m11_agreed = FloatField(default=0)
    m12_agreed = FloatField(default=0)
    m1_agreed = FloatField(default=0)
    m2_agreed = FloatField(default=0)
    m3_agreed = FloatField(default=0)
    m4_agreed = FloatField(default=0)
    m5_agreed = FloatField(default=0)
    m6_agreed = FloatField(default=0)
    
    m9_transport_agreed = FloatField(default=0)
    m10_transport_agreed = FloatField(default=0)
    m11_transport_agreed = FloatField(default=0)
    m12_transport_agreed = FloatField(default=0)
    m1_transport_agreed = FloatField(default=0)
    m2_transport_agreed = FloatField(default=0)
    m3_transport_agreed = FloatField(default=0)
    m4_transport_agreed = FloatField(default=0)
    m5_transport_agreed = FloatField(default=0)
    m6_transport_agreed = FloatField(default=0)
    
    insurance_agreed = FloatField(default=0)

class RealPayments(EmbeddedDocument):
    m9_real = FloatField(default=0)
    m10_real = FloatField(default=0)
    m11_real = FloatField(default=0)
    m12_real = FloatField(default=0)
    m1_real = FloatField(default=0)
    m2_real = FloatField(default=0)
    m3_real = FloatField(default=0)
    m4_real = FloatField(default=0)
    m5_real = FloatField(default=0)
    m6_real = FloatField(default=0)
    
    m9_transport_real = FloatField(default=0)
    m10_transport_real = FloatField(default=0)
    m11_transport_real = FloatField(default=0)
    m12_transport_real = FloatField(default=0)
    m1_transport_real = FloatField(default=0)
    m2_transport_real = FloatField(default=0)
    m3_transport_real = FloatField(default=0)
    m4_transport_real = FloatField(default=0)
    m5_transport_real = FloatField(default=0)
    m6_transport_real = FloatField(default=0)
    
    insurance_real = FloatField(default=0)

class PaymentInfo(EmbeddedDocument):
    agreed_payments = EmbeddedDocumentField(AgreedPayments)
    real_payments = EmbeddedDocumentField(RealPayments)

# ----------------------------------------
# Primary Models
# ----------------------------------------

class SchoolYearPeriod(db.Document):
    name = StringField(required=True, unique=True)
    start_date = DateTimeField(required=True)
    end_date = DateTimeField(required=True)

    meta = {
        'collection': 'school_year_periods',
        'indexes': [
            {'fields': ['name'], 'unique': True}
        ]
    }

    def to_json(self):
        return {
            '_id': {'$oid': str(self.id)}, 
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat()
        }

class User(db.Document):
    username = StringField(required=True, unique=True)
    password_hash = StringField(required=True)

    meta = {
        'collection': 'users',
        'indexes': [
            {'fields': ['username'], 'unique': True}
        ]
    }

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

    def to_json(self):
        return {
            'id': str(self.id),
            'username': self.username
            # Do not expose password_hash
        }

class Student(db.Document):
    name = StringField(required=True)
    school_year = ReferenceField('SchoolYearPeriod', required=True, reverse_delete_rule=CASCADE)
    isNew = BooleanField(default=False)
    isLeft = BooleanField(default=False)
    joined_month = IntField(min_value=1, max_value=12, default=9)
    observations = StringField()
    payments = EmbeddedDocumentField(PaymentInfo)
    left_date = DateTimeField()
    isSpecial = BooleanField(default=False)

    meta = {
        'collection': 'students',
        'indexes': [
            'name',
            'school_year'
        ]
    }

    def to_json(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'school_year': str(self.school_year.id) if self.school_year else None,
            'isNew': self.isNew,
            'isLeft': self.isLeft,
            'joined_month': self.joined_month,
            'observations': self.observations,
            'payments': self.payments.to_mongo() if self.payments else {},
            'left_date': self.left_date.isoformat() if self.left_date else None
        }

class Save(db.Document):
    student = ReferenceField('Student', required=True, reverse_delete_rule=CASCADE)
    user = ReferenceField('User', required=True, reverse_delete_rule=NULLIFY)
    date = DateTimeField(default=datetime.utcnow)
    types = ListField(StringField(choices=['payment', 'other']), required=True)
    changes = ListField(EmbeddedDocumentField(ChangeDetail), required=True)

    meta = {
        'collection': 'saves',
        'indexes': [
            'date',
            'types',
            'student'
        ]
    }

    def to_json(self):
        return {
            'id': str(self.id),
            'student': str(self.student.id) if self.student else None,
            'user': str(self.user.id) if self.user else None,
            'date': self.date.isoformat(),
            'types': self.types,
            'changes': [change.to_mongo() for change in self.changes]
        }

# Embedded document for Fixed Expenses
class FixedExpense(EmbeddedDocument):
    expense_type = StringField(required=True)
    expense_amount = FloatField(required=True)

# Main model for monthly expenses (Depence)
class Depence(db.Document):
    type = StringField(required=True)  # For example, 'monthly'
    description = StringField()
    date = DateTimeField(required=True)  # The month for which these expenses apply
    fixed_expenses = ListField(EmbeddedDocumentField(FixedExpense))  # List of fixed expenses for the month
    amount = FloatField(required=True)  # Total amount for all fixed expenses in that month

    def to_json(self):
        return {
            "id": str(self.id),
            "type": self.type,
            "description": self.description,
            "date": self.date.strftime('%Y-%m-%d'),  # Returning the date as a string
            "fixed_expenses": [
                {
                    "expense_type": fe.expense_type,
                    "expense_amount": fe.expense_amount
                } for fe in self.fixed_expenses
            ],
            "amount": self.amount  # Total amount for the month
        }

class Payment(db.Document):
    student = ReferenceField('Student', required=True, reverse_delete_rule=CASCADE)
    user = ReferenceField('User', required=True, reverse_delete_rule=NULLIFY)
    date = DateTimeField(default=datetime.utcnow)
    amount = FloatField(required=True, min_value=0)
    payment_type = StringField(choices=[
        'monthly', 'monthly_agreed',
        'transport', 'transport_agreed',
        'insurance', 'insurance_agreed'
    ], required=True)
    month = IntField(min_value=1, max_value=12, required=False, null=True)

    meta = {
        'collection': 'payments',
        'indexes': [
            'date',
            'payment_type',
            'student'
        ]
    }

    def to_json(self):
        return {
            'id': str(self.id),
            'student': str(self.student.id) if self.student else None,
            'user': str(self.user.id) if self.user else None,
            'date': self.date.isoformat(),
            'amount': self.amount,
            'payment_type': self.payment_type,
            'month': self.month
        }

class DailyAccounting(db.Document):
    date = DateTimeField(required=True, unique=True)
    payments = ListField(ReferenceField('Payment', reverse_delete_rule=PULL))
    daily_expenses = ListField(ReferenceField('Depence', reverse_delete_rule=PULL))
    total_payments = FloatField(default=0)
    total_expenses = FloatField(default=0)
    net_profit = FloatField(default=0)
    isValidated = BooleanField(default=False)

    meta = {
        'collection': 'daily_accounting',
        'indexes': [
            {'fields': ['date'], 'unique': True}
        ]
    }

    def calculate_totals(self):
        self.total_payments = sum(payment.amount for payment in self.payments)
        self.total_expenses = sum(expense.amount for expense in self.daily_expenses)
        self.net_profit = self.total_payments - self.total_expenses

    def to_json(self):
        return {
            'id': str(self.id),
            'date': self.date.isoformat(),
            'payments': [str(payment.id) for payment in self.payments],
            'daily_expenses': [str(expense.id) for expense in self.daily_expenses],
            'total_payments': self.total_payments,
            'total_expenses': self.total_expenses,
            'net_profit': self.net_profit,
            'isValidated': self.isValidated
        }
