# routes/reports.py

from flask import Blueprint, jsonify, request
from models import Student, Depence, SchoolYearPeriod
from mongoengine import Q
from datetime import datetime,timezone
import json
import logging



reports_bp = Blueprint('reports', __name__)

def calculate_monthly_data(month_num, year, school_year_period_id):
    """
    Returns:
      - month
      - total_monthly_agreed_payments
      - total_transport_agreed_payments
      - total_expenses
      - net_profit
      - total_insurance_students
    """

    # Totals
    total_monthly_agreed_payments = 0
    total_transport_agreed_payments = 0
    total_insurance_students = 0

    # Sum payments from all students in the given SchoolYearPeriod
    students = Student.objects(school_year=school_year_period_id)
    for student in students:
        if student.payments and student.payments.agreed_payments:
            monthly_payment = getattr(student.payments.agreed_payments, f'm{month_num}_agreed', 0)
            transport_payment = getattr(student.payments.agreed_payments, f'm{month_num}_transport_agreed', 0)
            total_monthly_agreed_payments += monthly_payment
            total_transport_agreed_payments += transport_payment

            # If insurance is paid
            if student.payments.agreed_payments.insurance_agreed > 0:
                total_insurance_students += 1

    # Make start_date and end_date timezone-aware (UTC)
    start_date = datetime(year, month_num, 1, tzinfo=timezone.utc)
    if month_num == 12:
        end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end_date = datetime(year, month_num + 1, 1, tzinfo=timezone.utc)

    print(f"Querying Depence from {start_date} to {end_date}")

    # Sum expenses
    expenses = Depence.objects(Q(date__gte=start_date) & Q(date__lt=end_date))
    total_expenses = sum(dep.amount for dep in expenses)

    print(f"Total expenses found: {total_expenses}")

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



@reports_bp.route('/normal_profit_report', methods=['GET'])
def normal_profit_report():
    try:
        school_year_period_id = request.args.get('schoolyear_id')
        if not school_year_period_id:
            return jsonify({"status": "error", "message": "School Year Period ID is required"}), 400

        school_year_period = SchoolYearPeriod.objects.get(id=school_year_period_id)
        start_year = school_year_period.start_date.year  # e.g. 2024
        end_year = school_year_period.end_date.year      # e.g. 2025

        report_data = []
        # Months: 9..12 of start_year
        for month_num in range(9, 13):
            month_data = calculate_monthly_data(month_num, start_year, school_year_period_id)
            report_data.append(month_data)

        # Months: 1..6 of end_year
        for month_num in range(1, 7):
            month_data = calculate_monthly_data(month_num, end_year, school_year_period_id)
            report_data.append(month_data)

        # Calculate total insurance & students with insurance
        total_insurance = sum(
            s.payments.agreed_payments.insurance_agreed
            for s in Student.objects(school_year=school_year_period_id)
            if s.payments and s.payments.agreed_payments
        )
        total_students_with_insurance = Student.objects(
            school_year=school_year_period_id,
            payments__agreed_payments__insurance_agreed__gt=0
        ).count()

        # Add a row for total insurance
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

@reports_bp.route('/unknown_agreed_payments', methods=['GET'])
def unknown_agreed_payments():
    """Lists students who have all monthly agreed payments = 0."""
    try:
        school_year_period_id = request.args.get('schoolyear_id')
        if not school_year_period_id:
            return jsonify({"status": "error", "message": "School Year Period ID is required"}), 400

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
