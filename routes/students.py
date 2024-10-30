# routes/students.py

from flask import Blueprint, request, jsonify
from models import PaymentInfo, Student, SchoolYearPeriod, User, Save, ChangeDetail, db
from mongoengine import DoesNotExist, ValidationError
from datetime import datetime
import json

students_bp = Blueprint('students', __name__)

# ----------------------------------------
# Define the currentUserId (Hardcoded for Now)
# ----------------------------------------
# In production, obtain this from the authenticated user context
currentUserId = "670ac94fc3d3342280ec3d62"

# ----------------------------------------
# Create a New Student
# ----------------------------------------
@students_bp.route('', methods=['POST'])
def create_student():
    data = request.get_json()
    # Handling basic fields
    name = data.get('name')
    school_year_id = data.get('school_year_id')
    joined_month = data.get('joined_month', 9)
    observations = data.get('observations', '')

    if not name or not school_year_id:
        return jsonify({'message': 'Name and School Year are required.'}), 400

    # Find the School Year
    try:
        school_year = SchoolYearPeriod.objects.get(id=school_year_id)
    except DoesNotExist:
        return jsonify({'message': 'School Year not found.'}), 404

    # Extract payments data
    payments_data = data.get('payments', {})
    agreed_payments = payments_data.get('agreed_payments', {})
    real_payments = payments_data.get('real_payments', {})

    # Convert payments to have flat numerical values
    agreed_payments_converted = {}
    for key, value in agreed_payments.items():
        # Ensure value is a number; if it's a dict with 'amount', extract it
        if isinstance(value, dict) and 'amount' in value:
            agreed_payments_converted[key] = value['amount']
        else:
            agreed_payments_converted[key] = value

    real_payments_converted = {}
    for key, value in real_payments.items():
        # Ensure value is a number; if it's a dict with 'amount', extract it
        if isinstance(value, dict) and 'amount' in value:
            real_payments_converted[key] = value['amount']
        else:
            real_payments_converted[key] = value

    # Create PaymentInfo instance
    payment_info = PaymentInfo(
        agreed_payments=agreed_payments_converted,
        real_payments=real_payments_converted
    )

    # Create the new student
    student = Student(
        name=name,
        school_year=school_year,
        isNew=True,
        isLeft=False,
        joined_month=joined_month,
        observations=observations,
        payments=payment_info,
        left_date=None
    )
    student.save()

    return jsonify({
        'message': 'Student created successfully.',
        'student_id': str(student.id)
    }), 201

# ----------------------------------------
# Get All Students (with SchoolYearPeriod Filter)
# ----------------------------------------
@students_bp.route('/', methods=['GET'])
def get_students():
    # Get the 'schoolyearperiod' query parameter
    school_year_id = request.args.get('schoolyearperiod', None)

    if not school_year_id:
        # Return an error if 'schoolyearperiod' is not provided
        return jsonify({"message": "School Year Period parameter is required."}), 400

    try:
        # Validate the SchoolYearPeriod ID
        school_year = SchoolYearPeriod.objects.get(id=school_year_id)
        
        # Fetch students belonging to the specified SchoolYearPeriod
        students = Student.objects(school_year=school_year).to_json()
        
        # Convert JSON string to Python objects
        students_data = json.loads(students)
        
        return jsonify({"message": "Students retrieved successfully.", "students": students_data}), 200
    except DoesNotExist:
        return jsonify({"message": "School Year Period not found."}), 404
    except Exception as e:
        return jsonify({
            "message": "An error occurred while fetching students.",
            "error": str(e)
        }), 500

# ----------------------------------------
# Get a Specific Student by ID
# ----------------------------------------
@students_bp.route('/<student_id>', methods=['GET'])
def get_student(student_id):
    try:
        student = Student.objects.get(id=student_id)
        return jsonify({"message": "Student retrieved successfully.", "student": json.loads(student.to_json())}), 200
    except DoesNotExist:
        return jsonify({'message': 'Student not found.'}), 404
    except Exception as e:
        return jsonify({'message': 'An error occurred while fetching the student.', 'error': str(e)}), 500

# ----------------------------------------
# Update a Student
# ----------------------------------------
@students_bp.route('/<student_id>', methods=['PUT'])
def update_student(student_id):
    data = request.get_json()
    try:
        student = Student.objects.get(id=student_id)
    except DoesNotExist:
        return jsonify({'message': 'Student not found.'}), 404

    changes = []
    if 'name' in data:
        changes.append(ChangeDetail(field_name='name', old_value=student.name, new_value=data['name']))
        student.name = data['name']
    if 'observations' in data:
        changes.append(ChangeDetail(field_name='observations', old_value=student.observations, new_value=data['observations']))
        student.observations = data['observations']
    if 'joined_month' in data:
        changes.append(ChangeDetail(field_name='joined_month', old_value=student.joined_month, new_value=data['joined_month']))
        student.joined_month = data['joined_month']
    if 'payments' in data:
        payments_data = data['payments']
        if 'agreed_payments' in payments_data:
            for key, value in payments_data['agreed_payments'].items():
                # Handle both flat numbers and dicts with 'amount'
                new_amount = value['amount'] if isinstance(value, dict) and 'amount' in value else value
                old_amount = student.payments.agreed_payments.get(key, 0)
                if old_amount != new_amount:
                    changes.append(ChangeDetail(field_name=f'agreed_payments.{key}', old_value=old_amount, new_value=new_amount))
                    student.payments.agreed_payments[key] = new_amount
        if 'real_payments' in payments_data:
            for key, value in payments_data['real_payments'].items():
                # Handle both flat numbers and dicts with 'amount'
                new_amount = value['amount'] if isinstance(value, dict) and 'amount' in value else value
                old_amount = student.payments.real_payments.get(key, 0)
                if old_amount != new_amount:
                    changes.append(ChangeDetail(field_name=f'real_payments.{key}', old_value=old_amount, new_value=new_amount))
                    student.payments.real_payments[key] = new_amount

    if changes:
        student.save()
        # Create a Save record
        try:
            user = User.objects.get(id=currentUserId)  # Use the defined currentUserId
        except DoesNotExist:
            return jsonify({'message': 'User not found.'}), 500

        # save = Save(
        #     student=student,
        #     user=user,
        #     types=['update'],
        #     changes=changes,
        #     date=datetime.utcnow()
        # )
        # save.save()

    return jsonify({'message': 'Student updated successfully.'}), 200

# ----------------------------------------
# Flag a Student as Left
# ----------------------------------------
@students_bp.route('/<student_id>/delete', methods=['PUT'])
def flag_student_left(student_id):
    try:
        student = Student.objects.get(id=student_id)
    except DoesNotExist:
        return jsonify({'message': 'Student not found.'}), 404

    if student.isLeft:
        return jsonify({'message': 'Student is already flagged as left.'}), 400

    student.isLeft = True
    student.left_date = datetime.utcnow()
    student.save()

    # Create a Save record
    # try:
    #     user = User.objects.get(id=currentUserId)  # Use the defined currentUserId
    # except DoesNotExist:
    #     return jsonify({'message': 'User not found.'}), 500

    # changes = [
    #     ChangeDetail(field_name='isLeft', old_value=False, new_value=True),
    #     ChangeDetail(field_name='left_date', old_value=None, new_value=student.left_date.isoformat())
    # ]

    # save = Save(
    #     student=student,
    #     user=user,
    #     types=['flag_left'],
    #     changes=changes,
    #     date=student.left_date
    # )
    # save.save()

    return jsonify({'message': 'Student flagged as left successfully.'}), 200
