# routes/schoolyearperiods.py

from flask import Blueprint, request, jsonify
from models import SchoolYearPeriod, Student, PaymentInfo, AgreedPayments, RealPayments
from mongoengine import DoesNotExist, ValidationError
from datetime import datetime
import json

schoolyearperiods_bp = Blueprint('schoolyearperiods', __name__)

@schoolyearperiods_bp.route('/', methods=['GET'])
def get_schoolyearperiods():
    try:
        school_years = SchoolYearPeriod.objects().order_by('-start_date').to_json()
        return jsonify({"status": "success", "data": json.loads(school_years)}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@schoolyearperiods_bp.route('/', methods=['POST'])
def create_schoolyearperiod():
    data = request.get_json()
    name = data.get('name')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    if not name or not start_date_str or not end_date_str:
        return jsonify({'message': 'Name, start_date, and end_date are required.'}), 400

    try:
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)
    except ValueError:
        return jsonify({'message': 'Invalid date format. Use ISO format (YYYY-MM-DD).'}), 400

    try:
        # Find the most recent previous SchoolYearPeriod
        previous_school_year = SchoolYearPeriod.objects(
            end_date__lt=start_date
        ).order_by('-end_date').first()

        if not previous_school_year:
            return jsonify({'message': 'No previous school year period found.'}), 400

        # Create and save the new SchoolYearPeriod
        school_year = SchoolYearPeriod(
            name=name,
            start_date=start_date,
            end_date=end_date
        )
        school_year.save()

        # Query students from the previous school year period who are still active
        past_year_students = Student.objects(
            school_year=previous_school_year,
            isLeft=False
        )

        # List to hold new student documents
        new_students = []

        for student in past_year_students:
            # Create a new PaymentInfo with all payments reset to 0
            new_payment_info = PaymentInfo(
                agreed_payments=AgreedPayments(),
                real_payments=RealPayments()
            )

            # Create a new Student instance
            new_student = Student(
                name=student.name,
                school_year=school_year,  # Assign to the new SchoolYearPeriod
                isNew=False,              # Set isNew to False
                isLeft=False,             # Set isLeft to False
                joined_month=student.joined_month,  # Retain the same joined_month
                observations=student.observations,  # Retain the same observations
                payments=new_payment_info,          # Reset payments
                left_date=None                      # Reset left_date
            )

            # Append to the list of new students
            new_students.append(new_student)

        # Bulk save all new students
        if new_students:
            Student.objects.insert(new_students)

        return jsonify({
            "status": "success",
            "data": school_year.to_json(),
            "message": f"School Year Period created successfully with {len(new_students)} students duplicated."
        }), 201

    except ValidationError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@schoolyearperiods_bp.route('/<schoolyear_id>', methods=['GET'])
def get_schoolyearperiod(schoolyear_id):
    try:
        school_year = SchoolYearPeriod.objects.get(id=schoolyear_id)
        return jsonify({"status": "success", "data": school_year.to_json()}), 200
    except DoesNotExist:
        return jsonify({"status": "error", "message": "School Year Period not found."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@schoolyearperiods_bp.route('/<schoolyear_id>', methods=['PUT'])
def update_schoolyearperiod(schoolyear_id):
    data = request.get_json()
    try:
        school_year = SchoolYearPeriod.objects.get(id=schoolyear_id)
    except DoesNotExist:
        return jsonify({"status": "error", "message": "School Year Period not found."}), 404

    if 'name' in data:
        school_year.name = data['name']
    if 'start_date' in data:
        try:
            school_year.start_date = datetime.fromisoformat(data['start_date'])
        except ValueError:
            return jsonify({'message': 'Invalid start_date format. Use ISO format (YYYY-MM-DD).'}), 400
    if 'end_date' in data:
        try:
            school_year.end_date = datetime.fromisoformat(data['end_date'])
        except ValueError:
            return jsonify({'message': 'Invalid end_date format. Use ISO format (YYYY-MM-DD).'}), 400

    try:
        school_year.save()
        return jsonify({"status": "success", "data": school_year.to_json()}), 200
    except ValidationError as ve:
        return jsonify({"status": "error", "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@schoolyearperiods_bp.route('/<schoolyear_id>', methods=['DELETE'])
def delete_schoolyearperiod(schoolyear_id):
    try:
        school_year = SchoolYearPeriod.objects.get(id=schoolyear_id)
        school_year.delete()
        return jsonify({"status": "success", "message": "School Year Period deleted."}), 200
    except DoesNotExist:
        return jsonify({"status": "error", "message": "School Year Period not found."}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
