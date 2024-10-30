from flask import Blueprint, jsonify, request
from models import DailyAccounting
from mongoengine import Q
from datetime import datetime

dailyacc_bp = Blueprint('dailyacc', __name__)

@dailyacc_bp.route('/daily_accounting_report', methods=['GET'])
def daily_accounting_report():
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if not start_date_str or not end_date_str:
            return jsonify({"status": "error", "message": "Start and end dates are required"}), 400

        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)

        # Query DailyAccounting data within the date range
        daily_accounting_data = DailyAccounting.objects(Q(date__gte=start_date) & Q(date__lte=end_date))

        report_data = []
        for record in daily_accounting_data:
            # Fetch detailed payment and expense data
            payments_data = []
            for payment in record.payments:
                payments_data.append({
                    "student_name": payment.student.name,
                    "amount": payment.amount,
                    "payment_type": payment.payment_type,
                    "date": payment.date.isoformat()
                })

            expenses_data = []
            for expense in record.daily_expenses:
                expenses_data.append({
                    "description": expense.description,
                    "amount": expense.amount,
                    "date": expense.date.isoformat()
                })

            report_data.append({
                "date": record.date.isoformat(),
                "total_payments": record.total_payments,
                "total_expenses": record.total_expenses,
                "net_profit": record.net_profit,
                "details": {
                    "payments": payments_data,
                    "daily_expenses": expenses_data
                }
            })

        return jsonify({"status": "success", "data": report_data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
