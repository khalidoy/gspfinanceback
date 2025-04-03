# routes/creditreports.py

from flask import Blueprint, jsonify, request
from models import Student, SchoolYearPeriod, Depence
from collections import defaultdict
from datetime import datetime

creditreports_bp = Blueprint('creditreports', __name__)

# Helper function to map calendar month to school year index
def map_school_year_month(month):
    """
    Maps a calendar month to the school year index.
    September (9) -> 1, October (10) -> 2, ..., June (6) -> 10
    """
    if 9 <= month <= 12:
        return month - 8  # 9->1, 10->2, 11->3, 12->4
    elif 1 <= month <= 6:
        return month + 4  # 1->5, 2->6, ..., 6->10
    else:
        return None  # Invalid month

# Helper function to check if a student has joined by the current month
def has_joined_by_month(student_join_month, current_month):
    """
    Returns True if the student has joined by the current month in the school year.
    """
    student_join_index = map_school_year_month(student_join_month)
    current_month_index = map_school_year_month(current_month)
    
    if student_join_index is None or current_month_index is None:
        return False  # Invalid month numbers
    
    return student_join_index <= current_month_index

# Helper function to calculate monthly payments and unpaid students
def calculate_monthly_payments(month, school_year_period):
    total_paid = 0
    total_left = 0
    unpaid_students = []
    payment_distribution = defaultdict(int)

    # Retrieve all students for the school year period
    students = Student.objects(school_year=school_year_period)

    for student in students:
        # Ensure the student has a 'joined_month' attribute
        if not hasattr(student, 'joined_month'):
            continue  # Skip if no join month information

        # Check if the student has joined by the current month
        if not has_joined_by_month(student.joined_month, month):
            continue  # Skip this student for the current month

        # Check if the student has left and exclude months after they left
        if hasattr(student, 'left_month') and student.left_month:
            if not has_joined_by_month(month, student.left_month):
                continue  # Skip this student for months after they left

        # Get the agreed and real payments for the current month
        agreed_payment = getattr(student.payments.agreed_payments, f'm{month}_agreed', 0)
        real_payment = getattr(student.payments.real_payments, f'm{month}_real', 0)
        
        # Get the agreed and real transport payments for the current month
        agreed_transport = getattr(student.payments.agreed_payments, f'm{month}_transport_agreed', 0)
        real_transport = getattr(student.payments.real_payments, f'm{month}_transport_real', 0)

        # Calculate the total paid
        total_paid += real_payment + real_transport

        # Calculate the total left only for students who are still active
        if not hasattr(student, 'left_month') or not student.left_month or has_joined_by_month(month, student.left_month):
            total_left += (agreed_payment + agreed_transport) - (real_payment + real_transport)

            # Check if the student is unpaid
            is_unpaid = False
            if real_payment < agreed_payment or real_transport < agreed_transport:
                is_unpaid = True

            # If the student is unpaid, add to the unpaid_students list
            if is_unpaid:
                unpaid_students.append({
                    'name': student.name,
                    'agreed_payment': agreed_payment,
                    'real_payment': real_payment,
                    'agreed_transport': agreed_transport,
                    'real_transport': real_transport
                })

    # Determine the corresponding year based on the school year period
    if month >= 9:
        year = school_year_period.start_date.year
    else:
        year = school_year_period.end_date.year

    # Define the start and end dates for the month
    start_of_month = datetime(year, month, 1)
    if month == 12:
        start_of_next_month = datetime(year + 1, 1, 1)
    else:
        start_of_next_month = datetime(year, month + 1, 1)

    # Retrieve depence for the month
    depence = Depence.objects(
        date__gte=start_of_month,
        date__lt=start_of_next_month
    ).first()
    depence_amount = depence.amount if depence else 0

    return {
        'month': month,
        'total_paid': total_paid,
        'total_left': total_left,
        'depence': depence_amount,
        'unpaid_students': unpaid_students,
        'payment_distribution': payment_distribution  # Placeholder if needed for further extensions
    }

# Route to fetch the monthly payments report for all months of the selected school year period
@creditreports_bp.route('/all_months_report', methods=['GET'])
def all_months_report():
    try:
        school_year_period_id = request.args.get('schoolyear_id')

        if not school_year_period_id:
            return jsonify({"status": "error", "message": "School Year Period ID is required"}), 400

        school_year_period = SchoolYearPeriod.objects(id=school_year_period_id).first()
        if not school_year_period:
            return jsonify({"status": "error", "message": "Invalid School Year Period ID"}), 400

        report_data = []

        # Define the sequence of months in the school year
        school_year_months = list(range(9, 13)) + list(range(1, 7))  # September to June

        # Loop through each month in the school year
        for month_num in school_year_months:
            month_data = calculate_monthly_payments(month_num, school_year_period)
            # Calculate additional columns
            total_payee_restant = month_data['total_paid'] + month_data['total_left']
            net_profit = total_payee_restant - month_data['depence']
            current_net_profit = month_data['total_paid'] - month_data['depence']
            part_au_tant_que_associe = net_profit / 2
            current_part_au_tant_que_associe = current_net_profit / 2

            month_data.update({
                'total_payee_restant': total_payee_restant,
                'net_profit': net_profit,
                'current_net_profit': current_net_profit,
                'part_au_tant_que_associe': part_au_tant_que_associe,
                'current_part_au_tant_que_associe': current_part_au_tant_que_associe
            })

            report_data.append(month_data)

        return jsonify({"status": "success", "data": report_data}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
