# routes/depences.py

from flask import Blueprint, request, jsonify
from models import Depence, FixedExpense
from mongoengine import DoesNotExist, ValidationError
from datetime import datetime, timedelta
import json

depences_bp = Blueprint('depences', __name__)

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
        today = datetime.utcnow().date()
        depences = Depence.objects(type='daily', date=today).to_json()
        return jsonify({"status": "success", "data": depences}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def get_depence(depence_id):
    try:
        depence = Depence.objects.get(id=depence_id)
        return jsonify({"status": "success", "data": depence.to_json()}), 200
    except DoesNotExist:
        return jsonify({"status": "error", "message": "Depence not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def create_depence():
    data = request.get_json()
    try:
        depence = Depence(
            type=data['type'],
            description=data.get('description', ''),
            amount=data['amount'],
            date=datetime.strptime(data['date'], '%Y-%m-%d') if 'date' in data else datetime.utcnow()
        )
        depence.save()
        return jsonify({"status": "success", "data": depence.to_json()}), 201
    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing field {str(e)}"}), 400
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def update_depence(depence_id):
    data = request.get_json()
    try:
        depence = Depence.objects.get(id=depence_id)
        depence.update(**data)
        depence.reload()
        return jsonify({"status": "success", "data": depence.to_json()}), 200
    except DoesNotExist:
        return jsonify({"status": "error", "message": "Depence not found"}), 404
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def delete_depence(depence_id):
    try:
        depence = Depence.objects.get(id=depence_id)
        depence.delete()
        return jsonify({"status": "success", "message": "Depence deleted"}), 200
    except DoesNotExist:
        return jsonify({"status": "error", "message": "Depence not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --------- Monthly Expenses Routes -----------------------------------------------------------------------------

# Fetch all monthly expenses from September (month 9) to August (month 8) of the following year
@depences_bp.route('/monthly', methods=['GET'])
def get_all_monthly_expenses():
    try:
        # Determine the current year
        current_year = datetime.now().year
        
        # Get all months from September (month 9) to August (month 8)
        expenses = []
        for month in range(9, 13):  # September to December in the current year
            month_date = datetime(current_year, month, 1)
            depence = Depence.objects(date=month_date).first()
            if depence:
                expenses.append(depence.to_json())

        for month in range(1, 9):  # January to August in the next year
            month_date = datetime(current_year + 1, month, 1)
            depence = Depence.objects(date=month_date).first()
            if depence:
                expenses.append(depence.to_json())

        # Return the list of all found monthly expenses
        return jsonify({"status": "success", "data": expenses}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Fetch monthly expenses
@depences_bp.route('/monthly/<int:month>', methods=['GET'])
def get_monthly_expenses(month):
    try:
        # Determine the current year based on the current date and the month
        current_year = datetime.now().year
        if month >= 9:  # For months September through December, it's the current year
            year = current_year
        else:  # For months January through August, it's the next year
            year = current_year + 1

        # Construct the month_date to search
        month_date = datetime(year, month, 1)

        # Fetch the expense for the specific month
        depence = Depence.objects(date=month_date).first()

        if not depence:
            return jsonify({"status": "success", "data": []}), 200
        return jsonify({"status": "success", "data": depence.to_json()}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ------------- Route to Create or Update Monthly Expenses -------------------

@depences_bp.route('/monthly/<int:month_id>', methods=['POST'])
def create_or_update_monthly_expenses(month_id):
    try:
        # Determine the current year based on the month_id
        current_year = datetime.now().year
        if month_id >= 9:
            year = current_year
        else:
            year = current_year + 1

        # Get the date for the first day of the month
        month_date = datetime(year, month_id, 1)

        # Get the request data
        data = request.get_json()
        fixed_expenses_data = data.get('fixed_expenses', [])
        total_amount = data.get('amount', 0)

        # Validate fixed expenses list
        if not isinstance(fixed_expenses_data, list):
            return jsonify({"status": "error", "message": "Invalid format for fixed expenses."}), 400

        # Parse fixed expenses into a list of FixedExpense objects
        fixed_expenses = [FixedExpense(**expense) for expense in fixed_expenses_data]

        # Check if a record already exists for this month
        depence = Depence.objects(date=month_date).first()

        if depence:
            # If it exists, update the record
            depence.fixed_expenses = fixed_expenses
            depence.amount = total_amount
            depence.save()
            return jsonify({"status": "success", "data": depence.to_json()}), 200
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
            return jsonify({"status": "success", "data": new_depence.to_json()}), 201

    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing field {str(e)}"}), 400
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# # ------------- Route to Populate Default Monthly Expenses -------------------

# @depences_bp.route('/monthly/populate_defaults', methods=['POST'])
# def populate_default_monthly_expenses():
#     try:
#         default_expenses = [
#             {"expense_type": "staff", "expense_amount": 290000},
#             {"expense_type": "credit transport", "expense_amount": 30000},
#             {"expense_type": "credit banque", "expense_amount": 138000},
#             {"expense_type": "cnss", "expense_amount": 25000},
#             {"expense_type": "Wifi", "expense_amount": 500},
#             {"expense_type": "electricity/eau", "expense_amount": 5000},
#             {"expense_type": "staf ete", "expense_amount": 10500},
#             {"expense_type": "comptable", "expense_amount": 500},
#         ]

#         current_year = datetime.now().year

#         for month_id in range(9, 13):  # September to December
#             month_date = datetime(current_year, month_id, 1)
#             depence = Depence.objects(date=month_date).first()
#             if not depence:
#                 fixed_expenses = [FixedExpense(**expense) for expense in default_expenses]
#                 total_amount = sum(exp["expense_amount"] for exp in default_expenses)
#                 new_depence = Depence(
#                     type='monthly',
#                     description=f'Default expenses for {month_date.strftime("%B")}',
#                     date=month_date,
#                     fixed_expenses=fixed_expenses,
#                     amount=total_amount
#                 )
#                 new_depence.save()

#         for month_id in range(1, 9):  # January to August
#             month_date = datetime(current_year + 1, month_id, 1)
#             depence = Depence.objects(date=month_date).first()
#             if not depence:
#                 fixed_expenses = [FixedExpense(**expense) for expense in default_expenses]
#                 total_amount = sum(exp["expense_amount"] for exp in default_expenses)
#                 new_depence = Depence(
#                     type='monthly',
#                     description=f'Default expenses for {month_date.strftime("%B")}',
#                     date=month_date,
#                     fixed_expenses=fixed_expenses,
#                     amount=total_amount
#                 )
#                 new_depence.save()

#         return jsonify({"status": "success", "message": "Default monthly expenses populated successfully."}), 201

#     except Exception as e:
#         return jsonify({"status": "error", "message": str(e)}), 500



@depences_bp.route('/monthly/populate_defaults', methods=['POST'])
def populate_default_monthly_expenses():
    try:
        # -------------------------------------------------
        # 1) Accept a schoolyear_id so we know which year(s) to populate
        # -------------------------------------------------
        school_year_period_id = request.args.get('schoolyear_id')
        if not school_year_period_id:
            return jsonify({"status": "error", "message": "School Year Period ID is required"}), 400

        # Fetch the SchoolYearPeriod (e.g. 2024-09-01 -> 2025-06-30)
        school_year_period = SchoolYearPeriod.objects.get(id=school_year_period_id)
        start_year = school_year_period.start_date.year  # e.g. 2024
        end_year   = school_year_period.end_date.year    # e.g. 2025

        # -------------------------------------------------
        # 2) Define monthly_expenses for all months (Sep -> Jun)
        # -------------------------------------------------
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

        # -------------------------------------------------
        # 3) For each MOIS_XX, decide which year to use
        #    - If month >= 9 => use start_year
        #    - Else => use end_year
        # -------------------------------------------------
        for month_key, expenses_list in monthly_expenses.items():
            month_num = int(month_key.split("_")[1])

            if 9 <= month_num <= 12:
                year = start_year  # e.g., 2024
            else:
                year = end_year    # e.g., 2025

            month_date = datetime(year, month_num, 1)

            # Check if entry already exists for this date
            depence = Depence.objects(date=month_date).first()

            if depence:
                # Update existing entry
                depence.fixed_expenses = [
                    FixedExpense(**expense) for expense in expenses_list
                ]
                depence.amount = sum(exp["expense_amount"] for exp in expenses_list)
                depence.description = f"Updated monthly expenses for {month_date.strftime('%B %Y')}"
                depence.save()
            else:
                # Create new entry
                fixed_expenses = [FixedExpense(**expense) for expense in expenses_list]
                total_amount = sum(exp["expense_amount"] for exp in expenses_list)

                new_depence = Depence(
                    type="monthly",
                    description=f"Monthly expenses for {month_date.strftime('%B %Y')}",
                    date=month_date,
                    fixed_expenses=fixed_expenses,
                    amount=total_amount
                )
                new_depence.save()

        return jsonify({"status": "success", "message": "Monthly expenses populated successfully."}), 201

    except DoesNotExist:
        return jsonify({"status": "error", "message": "SchoolYearPeriod not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
