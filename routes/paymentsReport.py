# routes/paymentsReport.py

from flask import Blueprint, jsonify, request
from models import Student, SchoolYearPeriod
from collections import defaultdict

payments_report_bp = Blueprint('payments_report', __name__)

@payments_report_bp.route('/payments-report', methods=['GET'])
def payments_report():
    """
    Generates a payments report filtered by school year, including:
    - List of students with payments for each month
    - Payment statistics per month
    - Payment distribution per month for students who have non-zero agreed payments

    Query Parameters:
    - school_year (str): The name of the school year period to filter the report.
    """
    # Retrieve the school_year from query parameters
    school_year_name = request.args.get('school_year')
    
    if not school_year_name:
        return jsonify({"error": "Missing 'school_year' query parameter."}), 400
    
    try:
        # Fetch the SchoolYearPeriod document based on the provided name
        school_year = SchoolYearPeriod.objects.get(name=school_year_name)
    except SchoolYearPeriod.DoesNotExist:
        return jsonify({"error": f"SchoolYearPeriod with name '{school_year_name}' does not exist."}), 400

    # Define the months mapping in desired order
    months = [
        (9, 'September'),
        (10, 'October'),
        (11, 'November'),
        (12, 'December'),
        (1, 'January'),
        (2, 'February'),
        (3, 'March'),
        (4, 'April'),
        (5, 'May'),
        (6, 'June')
    ]

    # Initialize data structures
    monthly_payment_data = {}
    for _, month_name in months:
        monthly_payment_data[month_name] = {
            'students': [],
            'total_agreed': 0,
            'payment_statistics': {},
            'payment_distribution': defaultdict(int)
        }

    # Fetch students enrolled in the specified school year
    students = Student.objects(school_year=school_year)

    for student in students:
        # Access the agreed payments for this student
        if not student.payments or not student.payments.agreed_payments:
            continue  # Skip if no payments data

        payments = student.payments.agreed_payments

        for month_num, month_name in months:
            agreed_payment = getattr(payments, f'm{month_num}_agreed', 0)
            agreed_payment_int = int(agreed_payment)

            if agreed_payment_int > 0:
                # Update monthly payment data
                monthly_payment_data[month_name]['students'].append({
                    'id': str(student.id),
                    'name': student.name,
                    'agreed_payment': agreed_payment_int
                })
                monthly_payment_data[month_name]['total_agreed'] += agreed_payment_int

                # Collect payments for statistics
                monthly_payment_data[month_name].setdefault('agreed_payments', []).append(agreed_payment_int)
                # Count the payment amounts
                monthly_payment_data[month_name]['payment_distribution'][agreed_payment_int] += 1

    # Calculate payment statistics and format payment distribution per month
    for _, month_name in months:
        agreed_payments = monthly_payment_data[month_name].get('agreed_payments', [])
        if agreed_payments:
            average_agreed_payment = int(round(sum(agreed_payments) / len(agreed_payments)))
            min_agreed_payment = min(agreed_payments)
            max_agreed_payment = max(agreed_payments)
        else:
            average_agreed_payment = 0
            min_agreed_payment = 0
            max_agreed_payment = 0

        # Update payment statistics
        monthly_payment_data[month_name]['payment_statistics'] = {
            'average_agreed_payment': average_agreed_payment,
            'min_agreed_payment': min_agreed_payment,
            'max_agreed_payment': max_agreed_payment
        }

        # Format payment distribution
        payment_distribution = monthly_payment_data[month_name]['payment_distribution']
        monthly_payment_data[month_name]['payment_distribution'] = [
            {'amount': amount, 'student_count': count}
            for amount, count in sorted(payment_distribution.items())
        ]

        # Remove agreed_payments list to clean up data
        monthly_payment_data[month_name].pop('agreed_payments', None)

    # Prepare the final report
    report = {
        'monthly_payment_data': monthly_payment_data
    }

    return jsonify(report), 200
