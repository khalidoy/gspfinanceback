# routes/students.py

from flask import Blueprint, request, jsonify
from models import PaymentInfo, Student, SchoolYearPeriod, User, Save, ChangeDetail, db, RealPayments, AgreedPayments, Classe
from mongoengine import DoesNotExist, ValidationError, Q
from datetime import datetime
import json
import traceback # Add traceback for better error logging

students_bp = Blueprint('students', __name__, url_prefix='/students')

# ----------------------------------------
# Define the currentUserId (Hardcoded for Now)
# ----------------------------------------
# In production, obtain this from the authenticated user context
currentUserId = "670ac94fc3d3342280ec3d62"

# Define month order for subsequent updates
MONTH_ORDER = ['m9', 'm10', 'm11', 'm12', 'm1', 'm2', 'm3', 'm4', 'm5', 'm6']

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
    classe_id = data.get('classe')  # Get classe ID

    if not name or not school_year_id:
        return jsonify({'message': 'Name and School Year are required.'}), 400
    
    if not classe_id:
        return jsonify({'message': 'Class is required.'}), 400

    # Find the School Year
    try:
        school_year = SchoolYearPeriod.objects.get(id=school_year_id)
    except DoesNotExist:
        return jsonify({'message': 'School Year not found.'}), 404
        
    # Find the Class
    try:
        classe = Classe.objects.get(id=classe_id)
    except DoesNotExist:
        return jsonify({'message': 'Class not found.'}), 404

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
        left_date=None,
        classe=classe  # Add classe reference
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
        
        # Fetch students with classe data
        students = Student.objects(school_year=school_year)
        
        # Convert to JSON manually to handle the classe reference properly
        students_data = []
        for student in students:
            # Get basic student data
            student_dict = {
                '_id': str(student.id),
                'name': student.name,
                'school_year': str(student.school_year.id),
                'isNew': student.isNew,
                'isLeft': student.isLeft,
                'joined_month': student.joined_month,
                'observations': student.observations,
                'payments': {
                    'agreed_payments': student.payments.agreed_payments.to_mongo(),
                    'real_payments': student.payments.real_payments.to_mongo()
                },
                'left_date': student.left_date.isoformat() if student.left_date else None,
                'isSpecial': getattr(student, 'isSpecial', False)
            }
            
            # Handle classe reference - fetch it separately to avoid errors
            if student.classe:
                try:
                    classe = student.classe
                    student_dict['classe'] = {
                        'id': str(classe.id),
                        'name': classe.name
                    }
                except Exception as e:
                    # If there's an error fetching classe details, just include the ID
                    student_dict['classe'] = {
                        'id': str(student.classe.id),
                        'name': 'Unknown'
                    }
            else:
                student_dict['classe'] = None
                
            # Handle group reference
            if hasattr(student, 'group') and student.group:
                student_dict['group'] = str(student.group.id)
            else:
                student_dict['group'] = None
                
            students_data.append(student_dict)
        
        return jsonify({"message": "Students retrieved successfully.", "students": students_data}), 200
    except DoesNotExist:
        return jsonify({"message": "School Year Period not found."}), 404
    except Exception as e:
        return jsonify({
            "message": "An error occurred while fetching students.",
            "error": str(e),
            "traceback": traceback.format_exc()
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
        # Ensure payments structure exists and initialize if necessary
        if not student.payments:
            student.payments = PaymentInfo(agreed_payments=AgreedPayments(), real_payments=RealPayments())
        if not student.payments.agreed_payments:
            student.payments.agreed_payments = AgreedPayments()
        if not student.payments.real_payments:
            student.payments.real_payments = RealPayments()

    except DoesNotExist:
        return jsonify({'message': 'Student not found.'}), 404
    except Exception as e:
        # Catch potential errors during initialization or fetching
        return jsonify({'message': f'Error fetching or initializing student data: {str(e)}'}), 500

    changes = []
    
    # --- Standard Field Updates ---
    if 'name' in data:
        if student.name != data['name']:
            changes.append(ChangeDetail(field_name='name', old_value=student.name, new_value=data['name']))
            student.name = data['name']
    if 'observations' in data:
        if student.observations != data['observations']:
            changes.append(ChangeDetail(field_name='observations', old_value=student.observations, new_value=data['observations']))
            student.observations = data['observations']
    if 'joined_month' in data:
        if student.joined_month != data['joined_month']:
            changes.append(ChangeDetail(field_name='joined_month', old_value=str(student.joined_month), new_value=str(data['joined_month'])))
            student.joined_month = data['joined_month']

    # --- Payments Update ---
    if 'payments' in data:
        payments_data = data['payments']

        # Update Agreed Payments (if provided directly)
        if 'agreed_payments' in payments_data and student.payments.agreed_payments:
            for key, value in payments_data['agreed_payments'].items():
                try:
                    new_amount = float(value['amount'] if isinstance(value, dict) and 'amount' in value else value)
                    old_amount = getattr(student.payments.agreed_payments, key, 0.0)
                    if old_amount != new_amount:
                        changes.append(ChangeDetail(field_name=f'agreed_payments.{key}', old_value=str(old_amount), new_value=str(new_amount)))
                        setattr(student.payments.agreed_payments, key, new_amount)
                except (ValueError, TypeError, AttributeError) as e:
                    print(f"Warning: Could not process agreed_payments key '{key}' value '{value}': {e}")

        # Update Real Payments
        if 'real_payments' in payments_data and student.payments.real_payments:
            for key, value in payments_data['real_payments'].items():
                try:
                    # Parse the new value properly
                    new_amount = float(value['amount'] if isinstance(value, dict) and 'amount' in value else value)
                    old_amount = float(getattr(student.payments.real_payments, key, 0.0))
                    
                    # Only process if value changed
                    if abs(old_amount - new_amount) > 0.001:  # Using small epsilon for float comparison
                        # Record the change
                        changes.append(ChangeDetail(
                            field_name=f'real_payments.{key}', 
                            old_value=str(old_amount), 
                            new_value=str(new_amount)
                        ))
                        
                        # Update the real payment
                        setattr(student.payments.real_payments, key, new_amount)
                        print(f"PAYMENT UPDATE: Changed {key} from {old_amount} to {new_amount}")
                        
                        # Get the corresponding agreed payment key and check if update needed
                        if key.endswith('_real'):
                            # Determine the payment type and month
                            agreed_key = key.replace('_real', '_agreed')
                            month_key = None
                            payment_type = None
                            
                            if key == 'insurance_real':
                                payment_type = 'insurance'
                            elif '_transport_' in key:
                                payment_type = 'transport'
                                month_key = key.split('_')[0]  # e.g., 'm9'
                            else:
                                payment_type = 'tuition'
                                month_key = key.split('_')[0]  # e.g., 'm9'
                            
                            # Get current agreed value
                            current_agreed = float(getattr(student.payments.agreed_payments, agreed_key, 0.0))
                            
                            # If real payment > agreed payment, update agreed and propagate to future months
                            if new_amount > current_agreed:
                                print(f"PAYMENT PROPAGATION: {key} real payment ({new_amount}) > agreed payment ({current_agreed})")
                                print(f"PAYMENT PROPAGATION: Updating {agreed_key} to {new_amount}")
                                
                                # Update current month's agreed payment
                                setattr(student.payments.agreed_payments, agreed_key, new_amount)
                                changes.append(ChangeDetail(
                                    field_name=f'agreed_payments.{agreed_key}',
                                    old_value=str(current_agreed),
                                    new_value=str(new_amount)
                                ))
                                
                                # Only propagate for tuition and transport payments that have a month
                                if payment_type in ['tuition', 'transport'] and month_key:
                                    try:
                                        current_month_index = MONTH_ORDER.index(month_key)
                                        print(f"PAYMENT PROPAGATION: Will update subsequent months after {month_key} with value {new_amount}")
                                        
                                        # Update all subsequent months
                                        for i in range(current_month_index + 1, len(MONTH_ORDER)):
                                            next_month = MONTH_ORDER[i]
                                            next_agreed_key = None
                                            
                                            if payment_type == 'tuition':
                                                next_agreed_key = f"{next_month}_agreed"
                                            elif payment_type == 'transport':
                                                next_agreed_key = f"{next_month}_transport_agreed"
                                            
                                            if next_agreed_key:
                                                next_agreed_value = float(getattr(student.payments.agreed_payments, next_agreed_key, 0.0))
                                                print(f"PAYMENT PROPAGATION: Checking {next_agreed_key}: current={next_agreed_value}, new={new_amount}")
                                                
                                                # Update the next month if it's different from the propagation value
                                                if abs(next_agreed_value - new_amount) > 0.001:
                                                    print(f"PAYMENT PROPAGATION: Updating {next_agreed_key} from {next_agreed_value} to {new_amount}")
                                                    setattr(student.payments.agreed_payments, next_agreed_key, new_amount)
                                                    changes.append(ChangeDetail(
                                                        field_name=f'agreed_payments.{next_agreed_key}',
                                                        old_value=str(next_agreed_value),
                                                        new_value=str(new_amount)
                                                    ))
                                    except ValueError:
                                        print(f"PAYMENT PROPAGATION ERROR: Invalid month key {month_key}")
                                    except Exception as e:
                                        print(f"PAYMENT PROPAGATION ERROR: {str(e)}")
                                        traceback.print_exc()
                except (ValueError, TypeError) as e:
                    print(f"WARNING: Error processing payment value for {key}: {str(e)}")
                except Exception as e:
                    print(f"ERROR: Unexpected error processing payment: {str(e)}")
                    traceback.print_exc()

    # --- Classe Update ---
    if 'classe' in data:
        try:
            classe_id_data = data['classe']
            classe_id = None

            if isinstance(classe_id_data, str):
                classe_id = classe_id_data
            elif isinstance(classe_id_data, dict):
                classe_id = classe_id_data.get('id') or classe_id_data.get('$oid') or classe_id_data.get('_id')

            if classe_id:
                classe = Classe.objects.get(id=classe_id)
                old_classe_id = str(student.classe.id) if student.classe else None
                if old_classe_id != str(classe.id):
                    changes.append(ChangeDetail(field_name='classe', old_value=old_classe_id, new_value=str(classe.id)))
                    student.classe = classe
            else:
                print(f"Warning: Could not extract valid classe ID from data: {classe_id_data}")

        except DoesNotExist:
            return jsonify({'message': 'Class not found.'}), 404
        except Exception as e:
            print(f"Error processing classe update: {e}")

    # --- Save Student and Create Save Record (if changes occurred) ---
    if changes:
        try:
            # Ensure all payment values are floats before saving
            if student.payments and student.payments.agreed_payments:
                for field in student.payments.agreed_payments._fields:
                    current_val = getattr(student.payments.agreed_payments, field, 0.0)
                    if current_val is None:
                        current_val = 0.0
                    setattr(student.payments.agreed_payments, field, float(current_val))
            
            if student.payments and student.payments.real_payments:
                for field in student.payments.real_payments._fields:
                    current_val = getattr(student.payments.real_payments, field, 0.0)
                    if current_val is None:
                        current_val = 0.0
                    setattr(student.payments.real_payments, field, float(current_val))
            
            print(f"SAVE: Saving student {student_id} with {len(changes)} changes")
            student.save()
            print(f"SAVE: Student {student_id} saved successfully")
            
        except ValidationError as e:
            print(f"VALIDATION ERROR: {str(e)}")
            traceback.print_exc()
            return jsonify({'message': f'Validation Error: {str(e)}'}), 400
        except Exception as e:
            print(f"SAVE ERROR: {str(e)}")
            traceback.print_exc()
            return jsonify({'message': f'Error saving student: {str(e)}'}), 500

    # --- Prepare and Return Response ---
    try:
        # Re-fetch the student to ensure the response reflects all saved changes
        updated_student = Student.objects.get(id=student_id)
        # Use the model's to_json method for consistent output
        response_student_dict = json.loads(updated_student.to_json())
        return jsonify({
            'message': 'Student updated successfully.',
            'student': response_student_dict
        }), 200
    except DoesNotExist:
         # Should not happen if save was successful, but handle defensively
        print(f"Error: Student {student_id} not found after successful update.")
        return jsonify({'message': 'Student updated successfully, but failed to retrieve updated data.'}), 200 # Or 500
    except Exception as e:
        print(f"Error formatting response for student {student_id}: {e}")
        traceback.print_exc()
        # Return success but indicate potential response issue
        return jsonify({'message': 'Student updated successfully (response formatting error).'}), 200

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

    # New: Map real payments to agreed payments
    try:
        if student.payments and student.payments.real_payments:
            real_payments_dict = student.payments.real_payments.to_mongo().to_dict()
            agreed_payments_dict = {
                key.replace('_real', '_agreed'): value
                for key, value in real_payments_dict.items()
            }
            student.payments.agreed_payments = AgreedPayments(**agreed_payments_dict)
        else:
            return jsonify({'message': 'Real payments data is missing or invalid.'}), 500
    except Exception as e:
        return jsonify({'message': 'Failed to process real payments.', 'error': str(e)}), 500

    student.save()

    return jsonify({'message': 'Student flagged as left successfully.'}), 200

# ----------------------------------------
# Batch Mark Students as Left
# ----------------------------------------
@students_bp.route('/batch-mark-left', methods=['POST'])
def batch_mark_left():
    data = request.get_json()
    student_ids = data.get('student_ids')

    if not student_ids or not isinstance(student_ids, list):
        return jsonify({'status': 'error', 'message': 'Invalid input. "student_ids" must be a list.'}), 400

    updated_count = 0
    errors = []
    updated_students_list = []

    try:
        students_to_update = Student.objects(id__in=student_ids)

        for student in students_to_update:
            if not student.isLeft:
                student.isLeft = True
                student.left_date = datetime.utcnow()

                # Map real payments to agreed payments
                try:
                    if student.payments and student.payments.real_payments:
                        real_payments_dict = student.payments.real_payments.to_mongo().to_dict()
                        # Filter out internal mongo keys like '_id' if they exist
                        real_payments_dict_clean = {k: v for k, v in real_payments_dict.items() if not k.startswith('_')}

                        agreed_payments_dict = {
                            key.replace('_real', '_agreed'): value
                            for key, value in real_payments_dict_clean.items()
                        }
                        # Ensure the target AgreedPayments object exists
                        if not student.payments.agreed_payments:
                             student.payments.agreed_payments = AgreedPayments()
                        # Update fields individually to handle potential schema differences
                        for key, value in agreed_payments_dict.items():
                             setattr(student.payments.agreed_payments, key, value)

                    else:
                        # Handle case where payments structure might be missing
                        print(f"Warning: Real payments data missing for student {student.id}. Cannot map to agreed.")
                        # Optionally initialize agreed payments to zero or skip
                        if not student.payments:
                            student.payments = PaymentInfo()
                        if not student.payments.agreed_payments:
                            student.payments.agreed_payments = AgreedPayments() # Initialize empty/zeroed

                    student.save()
                    updated_count += 1
                    updated_students_list.append(student.to_json()) # Append updated student data
                except Exception as e:
                    errors.append(f"Failed to update student {student.id}: {str(e)}")
                    # Optionally rollback or log more details
            else:
                 # If already left, still include in the response list if needed
                 updated_students_list.append(student.to_json())


        if errors:
             return jsonify({
                 'status': 'partial_success',
                 'message': f'Successfully marked {updated_count} students as left, but encountered errors.',
                 'errors': errors,
                 'updated_students': updated_students_list # Return even with errors
             }), 207 # Multi-Status

        if updated_count == 0 and len(student_ids) > 0:
             # Check if they were already left
             already_left_count = Student.objects(id__in=student_ids, isLeft=True).count()
             if already_left_count == len(student_ids):
                 return jsonify({
                     'status': 'success', # Or 'warning'
                     'message': 'All selected students were already marked as left.',
                     'updated_students': updated_students_list
                 }), 200
             else:
                 return jsonify({'status': 'warning', 'message': 'No students were newly marked as left (some might not exist or were already left).' , 'updated_students': updated_students_list}), 404


        return jsonify({
            'status': 'success',
            'message': f'Successfully marked {updated_count} students as left.',
            'updated_students': updated_students_list
        }), 200

    except ValidationError as e:
        return jsonify({'status': 'error', 'message': f'Invalid student ID format: {str(e)}'}), 400
    except Exception as e:
        traceback.print_exc() # Log the full traceback for debugging
        return jsonify({'status': 'error', 'message': f'An internal error occurred: {str(e)}'}), 500

# ----------------------------------------
# Batch Delete Students
# ----------------------------------------
@students_bp.route('/batch-delete', methods=['POST'])
def batch_delete_students():
    data = request.get_json()
    student_ids = data.get('student_ids')

    if not student_ids or not isinstance(student_ids, list):
        return jsonify({'status': 'error', 'message': 'Invalid input. "student_ids" must be a list.'}), 400

    try:
        # Perform the deletion
        deleted_count = Student.objects(id__in=student_ids).delete()

        if deleted_count == 0 and len(student_ids) > 0:
            return jsonify({'status': 'warning', 'message': 'No matching students found to delete.'}), 404

        return jsonify({
            'status': 'success',
            'message': f'Successfully deleted {deleted_count} students.'
        }), 200

    except ValidationError as e:
        return jsonify({'status': 'error', 'message': f'Invalid student ID format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'An internal error occurred during deletion.'}), 500

# ----------------------------------------
# Batch Affect Class for Students
# ----------------------------------------
@students_bp.route('/batch-affect-class', methods=['POST'])
def batch_affect_class():
    data = request.get_json()
    student_ids = data.get('student_ids')
    classe_id = data.get('classe_id')

    if not student_ids or not isinstance(student_ids, list):
        return jsonify({'status': 'error', 'message': 'Invalid input. "student_ids" must be a list.'}), 400
    if not classe_id:
        return jsonify({'status': 'error', 'message': 'Invalid input. "classe_id" is required.'}), 400

    try:
        # Validate the target class
        target_classe = Classe.objects.get(id=classe_id)

        # Update the students
        update_result = Student.objects(id__in=student_ids).update(set__classe=target_classe)

        if update_result == 0 and len(student_ids) > 0:
            return jsonify({'status': 'warning', 'message': 'No matching students found to update.'}), 404

        # Fetch the updated students to return their new state
        updated_students = Student.objects(id__in=student_ids)
        updated_students_data = [s.to_json() for s in updated_students]

        return jsonify({
            'status': 'success',
            'message': f'Successfully assigned {update_result} students to class "{target_classe.name}".',
            'updated_students': updated_students_data
        }), 200

    except DoesNotExist:
        return jsonify({'status': 'error', 'message': 'Target class not found.'}), 404
    except ValidationError as e:
        return jsonify({'status': 'error', 'message': f'Invalid ID format: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': 'An internal error occurred during class assignment.'}), 500
