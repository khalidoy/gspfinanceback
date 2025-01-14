# routes/depences.py

from flask import Blueprint, request, jsonify, Response
from models import Depence, FixedExpense, SchoolYearPeriod
from mongoengine import DoesNotExist, ValidationError
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from bson import json_util

depences_bp = Blueprint('depences', __name__)

def make_aware(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

@depences_bp.route('/', methods=['GET', 'POST'])
@depences_bp.route('/<depence_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_depences(depence_id=None):
    if request.method == 'GET':
        if depence_id: 
            return get_depence(depence_id)
        else:
            return get_depences()
    elif request.method == 'POST':
        return create_depence()
    elif request.method == 'PUT':
        return update_depence(depence_id)
    elif request.method == 'DELETE':
        return delete_depence(depence_id)

# Daily expenses logic remains unchanged
def get_depences():
    try:
        today = datetime.now(timezone.utc).date()
        depences = Depence.objects(type='daily', date__date=today)
        depences_json = json_util.dumps(depences)
        return Response(depences_json, mimetype='application/json'), 200
    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500

def get_depence(depence_id):
    try:
        depence = Depence.objects.get(id=depence_id)
        depence_json = json_util.dumps({"status": "success", "data": depence.to_mongo().to_dict()})
        return Response(depence_json, mimetype='application/json'), 200
    except DoesNotExist:
        error_response = json_util.dumps({"status": "error", "message": "Depence not found"})
        return Response(error_response, mimetype='application/json'), 404
    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500

def create_depence():
    data = request.get_json()
    try:
        depence_date = make_aware(datetime.strptime(data['date'], '%Y-%m-%d')) if 'date' in data else datetime.now(timezone.utc)
        depence = Depence(
            type=data['type'],
            description=data.get('description', ''),
            amount=data['amount'],
            date=depence_date
        )
        depence.save()
        depence_data = depence.to_mongo().to_dict()
        depence_json = json_util.dumps({"status": "success", "data": depence_data})
        return Response(depence_json, mimetype='application/json'), 201
    except KeyError as e:
        error_response = json_util.dumps({"status": "error", "message": f"Missing field {str(e)}"})
        return Response(error_response, mimetype='application/json'), 400
    except ValidationError as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 400
    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500

def update_depence(depence_id):
    data = request.get_json()
    try:
        if 'date' in data:
            data['date'] = make_aware(datetime.strptime(data['date'], '%Y-%m-%d'))
        depence = Depence.objects.get(id=depence_id)
        depence.update(**data)
        depence.reload()
        depence_data = depence.to_mongo().to_dict()
        depence_json = json_util.dumps({"status": "success", "data": depence_data})
        return Response(depence_json, mimetype='application/json'), 200
    except DoesNotExist:
        error_response = json_util.dumps({"status": "error", "message": "Depence not found"})
        return Response(error_response, mimetype='application/json'), 404
    except ValidationError as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 400
    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500

def delete_depence(depence_id):
    try:
        depence = Depence.objects.get(id=depence_id)
        depence.delete()
        success_response = json_util.dumps({"status": "success", "message": "Depence deleted"})
        return Response(success_response, mimetype='application/json'), 200
    except DoesNotExist:
        error_response = json_util.dumps({"status": "error", "message": "Depence not found"})
        return Response(error_response, mimetype='application/json'), 404
    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500

# --------- Monthly Expenses Routes -----------------------------------------------------------------------------

# Fetch all monthly expenses from September (month 9) to June (month 6) of the following year
@depences_bp.route('/monthly', methods=['GET'])
def get_all_monthly_expenses():
    try:
        # Retrieve 'schoolyear_id' from query parameters
        schoolyear_id = request.args.get('schoolyear_id')
        if not schoolyear_id:
            error_response = json_util.dumps({"message": "School Year Period ID is required", "status": "error"})
            return Response(error_response, mimetype='application/json'), 400

        # Fetch the SchoolYearPeriod document
        try:
            school_year = SchoolYearPeriod.objects.get(id=schoolyear_id)
        except DoesNotExist:
            error_response = json_util.dumps({"message": "Invalid School Year Period ID", "status": "error"})
            return Response(error_response, mimetype='application/json'), 404

        # Extract start and end dates
        start_date = make_aware(school_year.start_date)  # Ensure timezone-aware
        end_date = make_aware(school_year.end_date)      # Ensure timezone-aware

        # Validate that the school year spans September to June
        expected_start_month = 9  # September
        expected_end_month = 6    # June
        if start_date.month != expected_start_month or end_date.month != expected_end_month:
            error_response = json_util.dumps({"message": "School Year Period should start in September and end in June", "status": "error"})
            return Response(error_response, mimetype='application/json'), 400

        # Initialize list to hold expenses
        expenses = []

        # Generate list of month-year combinations from September to June
        current = start_date.replace(day=1)
        while current <= end_date:
            # Fetch Depence for the current month
            depence = Depence.objects(date=current).first()
            if depence:
                expenses.append(depence.to_mongo().to_dict())

            # Move to the next month
            current += relativedelta(months=1)

        # Serialize the expenses using json_util
        expenses_json = json_util.dumps({"status": "success", "data": expenses})
        return Response(expenses_json, mimetype='application/json'), 200

    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500

# Fetch monthly expenses
@depences_bp.route('/monthly/<int:month>', methods=['GET'])
def get_monthly_expenses(month):
    try:
        # Retrieve 'schoolyear_id' from query parameters
        schoolyear_id = request.args.get('schoolyear_id')
        if not schoolyear_id:
            error_response = json_util.dumps({"message": "School Year Period ID is required", "status": "error"})
            return Response(error_response, mimetype='application/json'), 400

        # Validate the month parameter
        if month < 1 or month > 12:
            error_response = json_util.dumps({"message": "Invalid month. Must be between 1 and 12.", "status": "error"})
            return Response(error_response, mimetype='application/json'), 400

        # Fetch the SchoolYearPeriod document
        try:
            school_year = SchoolYearPeriod.objects.get(id=schoolyear_id)
        except DoesNotExist:
            error_response = json_util.dumps({"message": "Invalid School Year Period ID", "status": "error"})
            return Response(error_response, mimetype='application/json'), 404

        # Extract start and end dates
        start_date = make_aware(school_year.start_date)  # Ensure timezone-aware
        end_date = make_aware(school_year.end_date)      # Ensure timezone-aware

        # Determine the year for the given month based on the SchoolYearPeriod
        if month >= 9:  # September to December belong to the start year
            year = start_date.year
        elif 1 <= month <= 6:  # January to June belong to the end year
            year = end_date.year
        else:
            error_response = json_util.dumps({"status": "error", "message": "Invalid month."})
            return Response(error_response, mimetype='application/json'), 400

        # Construct the month_date to search
        month_date = make_aware(datetime(year, month, 1))

        # Fetch the expense for the specific month
        depence = Depence.objects(date=month_date).first()

        if not depence:
            success_response = json_util.dumps({"status": "success", "data": []})
            return Response(success_response, mimetype='application/json'), 200

        depence_data = depence.to_mongo().to_dict()
        depence_json = json_util.dumps({"status": "success", "data": depence_data})
        return Response(depence_json, mimetype='application/json'), 200
    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500

# ------------- Route to Create or Update Monthly Expenses -------------------

@depences_bp.route('/monthly/<int:month_id>', methods=['POST'])
def create_or_update_monthly_expenses(month_id):
    try:
        # Retrieve 'schoolyear_id' from query parameters
        schoolyear_id = request.args.get('schoolyear_id')
        if not schoolyear_id:
            error_response = json_util.dumps({"message": "School Year Period ID is required", "status": "error"})
            return Response(error_response, mimetype='application/json'), 400

        # Validate the month_id
        if month_id < 1 or month_id > 12:
            error_response = json_util.dumps({"status": "error", "message": "Invalid month. Must be between 1 and 12."})
            return Response(error_response, mimetype='application/json'), 400

        # Fetch the SchoolYearPeriod document
        try:
            school_year = SchoolYearPeriod.objects.get(id=schoolyear_id)
        except DoesNotExist:
            error_response = json_util.dumps({"message": "Invalid School Year Period ID", "status": "error"})
            return Response(error_response, mimetype='application/json'), 404

        # Extract start and end dates
        start_date = make_aware(school_year.start_date)
        end_date = make_aware(school_year.end_date)

        # Determine the year based on the month
        if month_id >= 9:
            year = start_date.year
        elif 1 <= month_id <= 6:
            year = end_date.year
        else:
            error_response = json_util.dumps({"status": "error", "message": "Invalid month."})
            return Response(error_response, mimetype='application/json'), 400

        # Get the date for the first day of the month
        month_date = make_aware(datetime(year, month_id, 1))

        # Get the request data
        data = request.get_json()
        fixed_expenses_data = data.get('fixed_expenses', [])
        total_amount = data.get('amount', 0)

        # Validate fixed expenses list
        if not isinstance(fixed_expenses_data, list):
            error_response = json_util.dumps({"status": "error", "message": "Invalid format for fixed expenses."})
            return Response(error_response, mimetype='application/json'), 400

        # Parse fixed expenses into a list of FixedExpense objects
        fixed_expenses = [FixedExpense(**expense) for expense in fixed_expenses_data]

        # Check if a record already exists for this month
        depence = Depence.objects(date=month_date).first()

        if depence:
            # If it exists, update the record
            depence.fixed_expenses = fixed_expenses
            depence.amount = total_amount
            depence.description = f"Updated monthly expenses for {month_date.strftime('%B %Y')}"
            depence.save()
            depence_data = depence.to_mongo().to_dict()
            depence_json = json_util.dumps({"status": "success", "data": depence_data})
            return Response(depence_json, mimetype='application/json'), 200
        else:
            # If it doesn't exist, create a new record
            new_depence = Depence(
                type='monthly',
                description=data.get('description', ''),
                date=month_date,
                fixed_expenses=fixed_expenses,
                amount=total_amount
            )
            new_depence.save()
            depence_data = new_depence.to_mongo().to_dict()
            depence_json = json_util.dumps({"status": "success", "data": depence_data})
            return Response(depence_json, mimetype='application/json'), 201

    except KeyError as e:
        error_response = json_util.dumps({"status": "error", "message": f"Missing field {str(e)}"})
        return Response(error_response, mimetype='application/json'), 400
    except ValidationError as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 400
    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500

@depences_bp.route('/monthly/populate_defaults', methods=['POST'])
def populate_default_monthly_expenses():
    try:
        # Retrieve 'schoolyear_id' from query parameters or JSON body
        schoolyear_id = request.args.get('schoolyear_id') or (request.json.get('schoolyear_id') if request.is_json else None)
        if not schoolyear_id:
            error_response = json_util.dumps({"status": "error", "message": "School Year Period ID is required"})
            return Response(error_response, mimetype='application/json'), 400

        # Fetch the SchoolYearPeriod document
        try:
            school_year = SchoolYearPeriod.objects.get(id=schoolyear_id)
        except DoesNotExist:
            error_response = json_util.dumps({"status": "error", "message": "SchoolYearPeriod not found"})
            return Response(error_response, mimetype='application/json'), 404

        # Extract start and end dates
        start_year = school_year.start_date.year  # e.g. 2024
        end_year = school_year.end_date.year      # e.g. 2025

        # Define default expenses for each month
        monthly_expenses = {
            "MOIS_09": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 286680},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 2656.67},
                {"expense_type": "Photocopie", "expense_amount": 6300},
                {"expense_type": "Photocopie Divers", "expense_amount": 1939},
                {"expense_type": "Comptable", "expense_amount": 5000},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 4673.15},
                {"expense_type": "Assurance Eleves", "expense_amount": 5371.51},
                {"expense_type": "Diesel", "expense_amount": 4900},
                {"expense_type": "Communication", "expense_amount": 3000},
                {"expense_type": "Khadija Divers", "expense_amount": 6683},
            ],
            "MOIS_10": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 314145},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 5057.66},
                {"expense_type": "Photocopie", "expense_amount": 5750},
                {"expense_type": "Photocopie Divers", "expense_amount": 3055},
                {"expense_type": "Comptable", "expense_amount": 0},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 4673.15},
                {"expense_type": "Assurance Eleves", "expense_amount": 5000},
                {"expense_type": "Diesel", "expense_amount": 4900},
                {"expense_type": "Communication", "expense_amount": 3000},
                {"expense_type": "Khadija Divers", "expense_amount": 6559},
            ],
            "MOIS_11": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 321925},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 4984.25},
                {"expense_type": "Photocopie", "expense_amount": 3000},
                {"expense_type": "Photocopie Divers", "expense_amount": 4000},
                {"expense_type": "Comptable", "expense_amount": 0},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 4673.15},
                {"expense_type": "Assurance Eleves", "expense_amount": 5000},
                {"expense_type": "Diesel", "expense_amount": 5600},
                {"expense_type": "Communication", "expense_amount": 3000},
                {"expense_type": "Khadija Divers", "expense_amount": 5526},
            ],
            "MOIS_12": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 308070},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 4978.48},
                {"expense_type": "Photocopie", "expense_amount": 6000},
                {"expense_type": "Photocopie Divers", "expense_amount": 4000},
                {"expense_type": "Comptable", "expense_amount": 0},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 4673.15},
                {"expense_type": "Assurance Eleves", "expense_amount": 5000},
                {"expense_type": "Diesel", "expense_amount": 4170},
                {"expense_type": "Communication", "expense_amount": 3000},
                {"expense_type": "Khadija Divers", "expense_amount": 6799},
            ],
            "MOIS_01": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 310000},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 5000},
                {"expense_type": "Photocopie", "expense_amount": 5000},
                {"expense_type": "Photocopie Divers", "expense_amount": 4000},
                {"expense_type": "Comptable", "expense_amount": 600},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 0},
                {"expense_type": "Assurance Eleves", "expense_amount": 0},
                {"expense_type": "Diesel", "expense_amount": 5000},
                {"expense_type": "Communication", "expense_amount": 6000},
                {"expense_type": "Khadija Divers", "expense_amount": 6000},
            ],
            "MOIS_02": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 310000},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 5000},
                {"expense_type": "Photocopie", "expense_amount": 5000},
                {"expense_type": "Photocopie Divers", "expense_amount": 4000},
                {"expense_type": "Comptable", "expense_amount": 600},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 0},
                {"expense_type": "Assurance Eleves", "expense_amount": 0},
                {"expense_type": "Diesel", "expense_amount": 5000},
                {"expense_type": "Communication", "expense_amount": 6000},
                {"expense_type": "Khadija Divers", "expense_amount": 6000},
            ],
            "MOIS_03": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 310000},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 5000},
                {"expense_type": "Photocopie", "expense_amount": 5000},
                {"expense_type": "Photocopie Divers", "expense_amount": 4000},
                {"expense_type": "Comptable", "expense_amount": 600},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 0},
                {"expense_type": "Assurance Eleves", "expense_amount": 0},
                {"expense_type": "Diesel", "expense_amount": 5000},
                {"expense_type": "Communication", "expense_amount": 6000},
                {"expense_type": "Khadija Divers", "expense_amount": 6000},
            ],
            "MOIS_04": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 310000},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 5000},
                {"expense_type": "Photocopie", "expense_amount": 5000},
                {"expense_type": "Photocopie Divers", "expense_amount": 4000},
                {"expense_type": "Comptable", "expense_amount": 600},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 0},
                {"expense_type": "Assurance Eleves", "expense_amount": 0},
                {"expense_type": "Diesel", "expense_amount": 5000},
                {"expense_type": "Communication", "expense_amount": 6000},
                {"expense_type": "Khadija Divers", "expense_amount": 6000},
            ],
            "MOIS_05": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 310000},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 5000},
                {"expense_type": "Photocopie", "expense_amount": 5000},
                {"expense_type": "Photocopie Divers", "expense_amount": 4000},
                {"expense_type": "Comptable", "expense_amount": 600},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 0},
                {"expense_type": "Assurance Eleves", "expense_amount": 0},
                {"expense_type": "Diesel", "expense_amount": 5000},
                {"expense_type": "Communication", "expense_amount": 6000},
                {"expense_type": "Khadija Divers", "expense_amount": 6000},
            ],
            "MOIS_06": [
                {"expense_type": "FONCTIONNAIRE", "expense_amount": 310000},
                {"expense_type": "FONCTIONNAIRE Mois ETE", "expense_amount": 10000},
                {"expense_type": "CREDIT BANK", "expense_amount": 135151},
                {"expense_type": "CNSS", "expense_amount": 23906},
                {"expense_type": "WIFI", "expense_amount": 500},
                {"expense_type": "Electricité+eau", "expense_amount": 5000},
                {"expense_type": "Photocopie", "expense_amount": 5000},
                {"expense_type": "Photocopie Divers", "expense_amount": 4000},
                {"expense_type": "Comptable", "expense_amount": 600},
                {"expense_type": "Transport", "expense_amount": 30000},
                {"expense_type": "Assurance Transport", "expense_amount": 0},
                {"expense_type": "Assurance Eleves", "expense_amount": 0},
                {"expense_type": "Diesel", "expense_amount": 5000},
                {"expense_type": "Communication", "expense_amount": 6000},
                {"expense_type": "Khadija Divers", "expense_amount": 6000},
            ]
        }

        # Populate or update Depence for each month
        for month_key, expenses_list in monthly_expenses.items():
            month_num = int(month_key.split("_")[1])
            if 9 <= month_num <= 12:
                year = start_year
            elif 1 <= month_num <= 6:
                year = end_year
            else:
                continue  # Skip invalid months

            month_date = make_aware(datetime(year, month_num, 1))
            depence = Depence.objects(date=month_date).first()

            if depence:
                depence.fixed_expenses = [FixedExpense(**exp) for exp in expenses_list]
                depence.amount = sum(exp["expense_amount"] for exp in expenses_list)
                depence.description = f"Updated monthly expenses for {month_date.strftime('%B %Y')}"
                depence.save()
            else:
                fixed_expenses = [FixedExpense(**exp) for exp in expenses_list]
                total_amount = sum(exp["expense_amount"] for exp in expenses_list)
                new_depence = Depence(
                    type="monthly",
                    description=f"Monthly expenses for {month_date.strftime('%B %Y')}",
                    date=month_date,
                    fixed_expenses=fixed_expenses,
                    amount=total_amount
                )
                new_depence.save()

        success_response = json_util.dumps({"status": "success", "message": "Monthly expenses populated successfully."})
        return Response(success_response, mimetype='application/json'), 201

    except DoesNotExist:
        error_response = json_util.dumps({"status": "error", "message": "SchoolYearPeriod not found"})
        return Response(error_response, mimetype='application/json'), 404
    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500

# --------- Route to Get Current SchoolYearPeriod -----------------------------------------------------------------------------

@depences_bp.route('/current_schoolyear', methods=['GET'])
def get_current_schoolyear():
    try:
        today = make_aware(datetime.now())
        school_year = SchoolYearPeriod.objects(start_date__lte=today, end_date__gte=today).first()
        if not school_year:
            error_response = json_util.dumps({"status": "error", "message": "No active School Year Period found"})
            return Response(error_response, mimetype='application/json'), 404
        success_response = json_util.dumps({"status": "success", "schoolyear_id": str(school_year.id)})
        return Response(success_response, mimetype='application/json'), 200
    except Exception as e:
        error_response = json_util.dumps({"status": "error", "message": str(e)})
        return Response(error_response, mimetype='application/json'), 500
