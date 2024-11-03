# accounting.py

from flask import Blueprint, app, jsonify, request
from models import Payment, Depence, DailyAccounting
from datetime import datetime, time
from mongoengine import ValidationError
# Create the blueprint for daily accounting routes
accounting_bp = Blueprint('accounting_bp', __name__)
# ------------------- Get Today's Payments and Expenses ----------------------------------------

@accounting_bp.route('/daily/today', methods=['GET'])
def get_today_payments_expenses(): 
    try:
        print("Entered get_today_payments_expenses")
        # Get today's date with time part set to 00:00:00
        today_start = datetime.combine(datetime.now().date(), time.min)
        today_end = datetime.combine(datetime.now().date(), time.max)

        # Fetch all payments made today, including the student name
        today_payments = Payment.objects(date__gte=today_start, date__lt=today_end)
        payments_list = []
        for payment in today_payments:
            payment_data = payment.to_json()
            # Fetch and include the student name
            if payment.student:
                payment_data['student'] = payment.student.name  # Add the student name
            payments_list.append(payment_data)

        # Fetch only daily-type expenses made today
        today_expenses = Depence.objects(type='daily', date__gte=today_start, date__lt=today_end)
        expenses_list = [expense.to_json() for expense in today_expenses]

        return jsonify({
            'status': 'success',
            'payments': payments_list,
            'expenses': expenses_list
        }), 200

    except Exception as e:
        print(f"Error in get_today_payments_expenses: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------- Validate Daily Accounting for Today ----------------------------------------

@accounting_bp.route('/daily/validate', methods=['POST'])
def validate_daily_accounting():
    try:
        # Get today's date with time part set to 00:00:00 and 23:59:59
        today_start = datetime.combine(datetime.now().date(), time.min)
        today_end = datetime.combine(datetime.now().date(), time.max)

        # Check if the accounting for today has already been validated
        existing_accounting = DailyAccounting.objects(date__gte=today_start, date__lt=today_end).first()
        if existing_accounting and existing_accounting.isValidated:
            return jsonify({"status": "error", "message": "Today's accounting has already been validated."}), 400

        # Fetch today's payments and expenses
        today_payments = Payment.objects(date__gte=today_start, date__lt=today_end)
        today_expenses = Depence.objects(date__gte=today_start, date__lt=today_end)

        # Calculate totals
        total_payments = sum(payment.amount for payment in today_payments)
        total_expenses = sum(expense.amount for expense in today_expenses)
        net_profit = total_payments - total_expenses

        # Create or update the daily accounting for today
        if existing_accounting:
            existing_accounting.payments = today_payments
            existing_accounting.daily_expenses = today_expenses
            existing_accounting.total_payments = total_payments
            existing_accounting.total_expenses = total_expenses
            existing_accounting.net_profit = net_profit
            existing_accounting.isValidated = True
            existing_accounting.save()
        else:
            new_accounting = DailyAccounting(
                date=today_start,
                payments=today_payments,
                daily_expenses=today_expenses,
                total_payments=total_payments,
                total_expenses=total_expenses,
                net_profit=net_profit,
                isValidated=True
            )
            new_accounting.save()

        return jsonify({"status": "success", "message": "Today's accounting has been validated."}), 201

    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------------- Get Daily Accounting Status ----------------------------------------

@accounting_bp.route('/daily/status', methods=['GET'])
def get_daily_accounting_status():
    try:
        today = datetime.now().date()
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)

        existing_accounting = DailyAccounting.objects(
            date__gte=today_start, 
            date__lt=today_end
        ).first()

        if existing_accounting:
            return jsonify({
                "status": "success",
                "isValidated": existing_accounting.isValidated,
                "net_profit": existing_accounting.net_profit,
                "total_payments": existing_accounting.total_payments,
                "total_expenses": existing_accounting.total_expenses
            }), 200
        else:
            return jsonify({
                "status": "success",
                "isValidated": False
            }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
