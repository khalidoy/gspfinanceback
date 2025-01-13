# routes/reports.py

from flask import Blueprint, json, jsonify, request
from models import Student, Depence, SchoolYearPeriod
from mongoengine import Q
from datetime import datetime

reports_bp = Blueprint('reports', __name__)


def calculate_monthly_data(month_num, year, school_year_period_id):
    """
    Calculates monthly data for a given month/year within a particular school year period.
    Returns a dictionary containing:
        - month
        - total_monthly_agreed_payments
        - total_transport_agreed_payments
        - total_expenses (sum of Depence.amount within the month)
        - net_profit (total_payments minus total_expenses)
        - total_insurance_students
    """

    # Initialize totals
    total_monthly_agreed_payments = 0
    total_transport_agreed_payments = 0
    total_insurance_students = 0  # To count students who have insurance_agreed > 0

    # Get all students for the given SchoolYearPeriod
    students = Student.objects(school_year=school_year_period_id)

    # Sum up agreed payments for monthly + transport
    for student in students:
        if student.payments and student.payments.agreed_payments:
            # Monthly agreed payments (e.g., m9_agreed, m10_agreed, etc.)
            monthly_payment = getattr(student.payments.agreed_payments, f'm{month_num}_agreed', 0)
            total_monthly_agreed_payments += monthly_payment

            # Transport agreed payments (e.g., m9_transport_agreed, m10_transport_agreed, etc.)
            transport_payment = getattr(student.payments.agreed_payments, f'm{month_num}_transport_agreed', 0)
            total_transport_agreed_payments += transport_payment

            # Check if insurance is paid
            if student.payments.agreed_payments.insurance_agreed > 0:
                total_insurance_students += 1

    # Construct the date range for the given month/year
    start_date = datetime(year, month_num, 1)
    if month_num == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month_num + 1, 1)

    # Fetch Depence entries within the month range and sum their amounts
    expenses = Depence.objects(Q(date__gte=start_date) & Q(date__lt=end_date))
    total_expenses = sum(expense.amount for expense in expenses)

    # Calculate net profit: total payments - total expenses
    total_payments = total_monthly_agreed_payments + total_transport_agreed_payments
    net_profit = total_payments - total_expenses

    return {
        "month": month_num,
        "total_monthly_agreed_payments": total_monthly_agreed_payments,
        "total_transport_agreed_payments": total_transport_agreed_payments,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "total_insurance_students": total_insurance_students
    }

# Route for normal school profit report
@reports_bp.route('/normal_profit_report', methods=['GET'])
def normal_profit_report():
    try:
        school_year_period_id = request.args.get('schoolyear_id')
        if not school_year_period_id:
            return jsonify({"status": "error", "message": "School Year Period ID is required"}), 400

        report_data = []
        school_year_period = SchoolYearPeriod.objects.get(id=school_year_period_id)

        start_year = school_year_period.start_date.year
        end_year = school_year_period.end_date.year

        # Loop through the months: from September (9) to June (6)
        for month_num in range(9, 13):  # September to December
            month_data = calculate_monthly_data(month_num, start_year, school_year_period_id)
            report_data.append(month_data)

        for month_num in range(1, 7):  # January to June
            month_data = calculate_monthly_data(month_num, end_year, school_year_period_id)
            report_data.append(month_data)

        # Calculate total insurance agreed payments (only once per school year period)
        total_insurance = sum(student.payments.agreed_payments.insurance_agreed for student in Student.objects(school_year=school_year_period_id))

        # Calculate total number of students who paid insurance
        total_students_with_insurance = Student.objects(school_year=school_year_period_id, payments__agreed_payments__insurance_agreed__gt=0).count()

        # Add a row for total insurance to the report data
        report_data.append({
            "month": "total_insurance",
            "total_monthly_agreed_payments": 0,
            "total_transport_agreed_payments": 0,
            "total_insurance_agreed_payments": total_insurance,
            "total_expenses": 0,
            "net_profit": total_insurance
        })

        return jsonify({
            "status": "success",
            "data": report_data,
            "total_students_with_insurance": total_students_with_insurance,
            "total_yearly_income": sum(row["net_profit"] for row in report_data)
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------- Route to Retrieve Unknown Students with Zero Agreed Payments -------------------

@reports_bp.route('/unknown_agreed_payments', methods=['GET'])
def unknown_agreed_payments():
    try:
        school_year_period_id = request.args.get('schoolyear_id')
        if not school_year_period_id:
            return jsonify({"status": "error", "message": "School Year Period ID is required"}), 400

        # Query students with all m9_agreed to m6_agreed equal to 0
        unknown_students = Student.objects(
            school_year=school_year_period_id,
            isLeft=False,
            payments__agreed_payments__m9_agreed=0,
            payments__agreed_payments__m10_agreed=0,
            payments__agreed_payments__m11_agreed=0,
            payments__agreed_payments__m12_agreed=0,
            payments__agreed_payments__m1_agreed=0,
            payments__agreed_payments__m2_agreed=0,
            payments__agreed_payments__m3_agreed=0,
            payments__agreed_payments__m4_agreed=0,
            payments__agreed_payments__m5_agreed=0,
            payments__agreed_payments__m6_agreed=0
        ).only('name').to_json()

        unknown_students_list = json.loads(unknown_students)

        return jsonify({
            "status": "success",
            "count": len(unknown_students_list),
            "students": unknown_students_list
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
