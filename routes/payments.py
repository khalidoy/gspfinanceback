# routes/payments.py

from flask import Blueprint, request, jsonify
from models import Payment, Student, User, PaymentInfo, AgreedPayments, RealPayments, Save, ChangeDetail
from mongoengine import DoesNotExist, ValidationError
from datetime import datetime, time
import json
import logging

payments_bp = Blueprint('payments', __name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Helper function to get the correct field for the month and payment type
def get_field(payment_type, month):
    if payment_type == 'monthly':
        return f"m{month}_real"
    elif payment_type == 'transport':
        return f"m{month}_transport_real"
    elif payment_type == 'insurance':
        return 'insurance_real'
    elif payment_type == 'monthly_agreed':
        return f"m{month}_agreed"
    elif payment_type == 'transport_agreed':
        return f"m{month}_transport_agreed"
    elif payment_type == 'insurance_agreed':
        return 'insurance_agreed'
    return None

@payments_bp.route('/create_or_update', methods=['POST'])
def create_or_update_payment():
    data = request.get_json()
    logging.info(f"Received data in create_or_update_payment: {data}")
    
    try:
        # Log request headers for debugging
        logging.info(f"Request headers: {dict(request.headers)}")
        
        # Only handle REAL payments
        if data.get('payment_type', '').endswith('_agreed'):
            raise ValidationError("This endpoint only handles REAL payments.")

        # Validate required fields
        required_fields = ['student_id', 'user_id', 'payment_type', 'amount']
        for field in required_fields:
            if field not in data:
                logging.error(f"Missing required field: {field}")
                raise KeyError(field)

        # Retrieve student and user
        student_id = data['student_id']
        user_id = data['user_id']
        payment_type = data['payment_type']
        
        try:
            student = Student.objects.get(id=student_id)
            logging.info(f"Found student: {student.name} (ID: {student_id})")
        except DoesNotExist:
            logging.error(f"Student not found: {student_id}")
            raise DoesNotExist(f"Student with ID {student_id} not found")
            
        try:
            user = User.objects.get(id=user_id)
            logging.info(f"Found user: {user.username} (ID: {user_id})")
        except DoesNotExist:
            logging.error(f"User not found: {user_id}")
            raise DoesNotExist(f"User with ID {user_id} not found")
            
        month = data.get('month')  # May be None for insurance payments
        amount = float(data['amount'])
        
        logging.info(f"Processing payment: Type={payment_type}, Month={month}, Amount={amount}")

        # Validate 'month' field for non-insurance payments
        if payment_type not in ['insurance'] and month is None:
            logging.error("Month is required for non-insurance payments")
            raise ValidationError("Field 'month' is required for non-insurance payments.")

        # Determine the real and agreed payment field names
        real_field = None
        agreed_field = None
        
        if payment_type == 'monthly':
            real_field = f"m{month}_real"
            agreed_field = f"m{month}_agreed"
        elif payment_type == 'transport':
            real_field = f"m{month}_transport_real"
            agreed_field = f"m{month}_transport_agreed"
        elif payment_type == 'insurance':
            real_field = 'insurance_real'
            agreed_field = 'insurance_agreed'
        else:
            raise ValidationError(f"Invalid payment_type: {payment_type}")

        # Find existing payment for the student in the specified month and type
        try:
            today_start = datetime.combine(datetime.now().date(), time.min)
            today_end = datetime.combine(datetime.now().date(), time.max)
            
            logging.info(f"Checking for existing payments between {today_start} and {today_end}")
            
            existing_payment = Payment.objects(
                student=student, 
                payment_type=payment_type, 
                month=month,
                date__gte=today_start,
                date__lt=today_end
            ).first()
            
            if existing_payment:
                logging.info(f"Found existing payment: {existing_payment.id}")
            else:
                logging.info("No existing payment found, will create new")
        except Exception as e:
            logging.error(f"Error checking for existing payments: {e}")
            raise

        # Make sure student has payment structures initialized
        if not student.payments:
            student.payments = PaymentInfo(agreed_payments=AgreedPayments(), real_payments=RealPayments())
        if not student.payments.agreed_payments:
            student.payments.agreed_payments = AgreedPayments()
        if not student.payments.real_payments:
            student.payments.real_payments = RealPayments()

        # Ensure real payment is not greater than agreed payment
        # If it is, update agreed payment AND propagate to future months
        changes = []
        current_agreed_value = getattr(student.payments.agreed_payments, agreed_field, 0.0)
        student_real_payment = getattr(student.payments.real_payments, real_field, 0.0)

        # Update the real payment field on the student
        setattr(student.payments.real_payments, real_field, amount)
        changes.append(ChangeDetail(
            field_name=f'real_payments.{real_field}', 
            old_value=str(student_real_payment), 
            new_value=str(amount)
        ))

        # If real > agreed, update agreed for this month and propagate to subsequent months
        if amount > current_agreed_value:
            setattr(student.payments.agreed_payments, agreed_field, amount)
            changes.append(ChangeDetail(
                field_name=f'agreed_payments.{agreed_field}', 
                old_value=str(current_agreed_value), 
                new_value=str(amount)
            ))

            # Propagate to subsequent months if it's monthly or transport payment
            if payment_type in ['monthly', 'transport'] and month is not None:
                # Define month order for subsequent updates
                MONTH_ORDER = ['m9', 'm10', 'm11', 'm12', 'm1', 'm2', 'm3', 'm4', 'm5', 'm6']
                month_key = f"m{month}"

                try:
                    current_month_index = MONTH_ORDER.index(month_key)
                    for i in range(current_month_index + 1, len(MONTH_ORDER)):
                        subsequent_month = MONTH_ORDER[i]
                        subsequent_agreed_field = None

                        if payment_type == 'monthly':
                            subsequent_agreed_field = f"{subsequent_month}_agreed"
                        elif payment_type == 'transport':
                            subsequent_agreed_field = f"{subsequent_month}_transport_agreed"

                        if subsequent_agreed_field:
                            old_subsequent_value = getattr(student.payments.agreed_payments, subsequent_agreed_field, 0.0)
                            if amount > old_subsequent_value:
                                setattr(student.payments.agreed_payments, subsequent_agreed_field, amount)
                                changes.append(ChangeDetail(
                                    field_name=f'agreed_payments.{subsequent_agreed_field}', 
                                    old_value=str(old_subsequent_value), 
                                    new_value=str(amount)
                                ))
                except ValueError:
                    logging.error(f"Invalid month key: {month_key}")
                except Exception as e:
                    logging.error(f"Error updating subsequent months: {e}")

        # Save the updated student record
        if changes:
            student.save()
            logging.info(f"Updated student payment information with {len(changes)} changes")

        # If payment exists, update it
        if existing_payment:
            old_amount = existing_payment.amount
            existing_payment.amount = amount
            existing_payment.save()
            logging.info(f"Updated payment {existing_payment.id}: {old_amount} -> {amount}")
            return jsonify({"status": "success", "data": existing_payment.to_json()}), 200

        # If no payment exists, create a new one
        else:
            try:
                new_payment = Payment(
                    student=student,
                    user=user,
                    amount=amount,
                    payment_type=payment_type,
                    month=month,
                    date=datetime.utcnow()
                )
                new_payment.save()
                logging.info(f"Created new payment with ID: {new_payment.id}")
                return jsonify({"status": "success", "data": new_payment.to_json()}), 201
            except Exception as e:
                logging.error(f"Error creating new payment: {e}")
                import traceback
                logging.error(traceback.format_exc())
                raise

    except KeyError as e:
        logging.error(f"KeyError: Missing field {e}")
        return jsonify({"status": "error", "message": f"Missing field: {str(e)}"}), 400
    except DoesNotExist as e:
        logging.error(f"DoesNotExist: {e}")
        return jsonify({"status": "error", "message": str(e)}), 404
    except ValidationError as e:
        logging.error(f"ValidationError: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Exception: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

@payments_bp.route('/agreed_changes', methods=['POST'])
def agreed_changes():
    data = request.get_json()
    logging.info(f"Received data in agreed_changes: {data}")
    try:
        # Validate required fields
        required_fields = ['student_id', 'user_id', 'agreed_payments', 'date']
        for field in required_fields:
            if field not in data:
                raise KeyError(field)

        student_id = data['student_id']
        user_id = data['user_id']
        agreed_payments = data['agreed_payments']  # Should be a dict with keys as field names
        date = data['date']

        # Retrieve student and user
        student = Student.objects.get(id=student_id)
        user = User.objects.get(id=user_id)

        # Ensure the student has a payments document
        if not student.payments:
            student.payments = PaymentInfo()
            student.payments.agreed_payments = AgreedPayments()
            student.payments.real_payments = RealPayments()
            student.save()

        # Fetch original agreed payments from the student data
        original_agreed = student.payments.agreed_payments.to_mongo().to_dict() if student.payments.agreed_payments else {}

        # Prepare a list to hold change details
        changes = []

        # Iterate through agreed_payments and compare with original
        for key, new_value in agreed_payments.items():
            if not key.endswith('_agreed'):
                raise ValidationError(f"Invalid agreed payment field: {key}")

            old_value = original_agreed.get(key, 0)
            if new_value != old_value:
                changes.append(
                    ChangeDetail(
                        field_name=key,
                        old_value=str(old_value),
                        new_value=str(new_value)
                    )
                )
                # Update the agreed_payments in the student document
                setattr(student.payments.agreed_payments, key, new_value)

        # Save the student document if there are changes
        if changes:
            student.save()

            # Create a Save record
            # save_record = Save(
            #     student=student,
            #     user=user,
            #     types=['agreed_payments'],
            #     changes=changes,
            #     date=datetime.fromisoformat(date.replace("Z", "+00:00"))  # Convert to datetime object
            # )
            # save_record.save()

            return jsonify({"status": "success", "message": "Agreed payments updated"}), 200
        else:
            return jsonify({"status": "success", "message": "No changes detected in agreed payments"}), 200

    except KeyError as e:
        logging.error(f"KeyError: Missing field {e}")
        return jsonify({"status": "error", "message": f"Missing field: {str(e)}"}), 400
    except DoesNotExist as e:
        logging.error(f"DoesNotExist: {e}")
        return jsonify({"status": "error", "message": str(e)}), 404
    except ValidationError as e:
        logging.error(f"ValidationError: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Exception in agreed_changes: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@payments_bp.route('/<payment_id>', methods=['DELETE'])
def delete_payment(payment_id):
    try:
        payment = Payment.objects.get(id=payment_id)
        student = payment.student
        payment_type = payment.payment_type
        month = payment.month

        original_payment_json = payment.to_json()

        payment_info = student.payments or PaymentInfo()

        # Determine the specific field to reset
        field = get_field(payment_type, month)
        if not field:
            raise ValidationError(f"Invalid payment_type: {payment_type}")

        # Ensure that real_payments exists as an EmbeddedDocument
        if not payment_info.real_payments:
            payment_info.real_payments = RealPayments()

        # Reset the specific field in real_payments
        setattr(payment_info.real_payments, field, 0)

        student.payments = payment_info
        student.save()

        # Delete payment
        payment.delete()

        # Record the deletion
        changes = [
            ChangeDetail(
                field_name=field,
                old_value=json.dumps(original_payment_json),
                new_value='0'  # Indicates reset
            )
        ]
        # save_record = Save(
        #     student=student,
        #     user=payment.user,  # Ensure 'user' is correctly retrieved if needed
        #     types=['payment'],
        #     changes=changes,
        #     date=datetime.utcnow()
        # )
        # save_record.save()

        return jsonify({"status": "success", "message": "Payment deleted"}), 200
    except DoesNotExist:
        logging.error(f"Payment with ID {payment_id} not found.")
        return jsonify({"status": "error", "message": "Payment not found"}), 404
    except ValidationError as e:
        logging.error(f"ValidationError: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.error(f"Exception in delete_payment: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
