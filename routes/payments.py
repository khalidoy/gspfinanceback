# routes/payments.py

from flask import Blueprint, request, jsonify
from models import Payment, Student, User, PaymentInfo, AgreedPayments, RealPayments, Save, ChangeDetail
from mongoengine import DoesNotExist, ValidationError
from datetime import datetime
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
        # Only handle REAL payments
        if data['payment_type'].endswith('_agreed'):
            raise ValidationError("This endpoint only handles REAL payments.")

        # Validate required fields
        required_fields = ['student_id', 'user_id', 'payment_type', 'amount']
        for field in required_fields:
            if field not in data:
                raise KeyError(field)

        # Retrieve student and user
        student = Student.objects.get(id=data['student_id'])
        user = User.objects.get(id=data['user_id'])
        payment_type = data['payment_type']
        month = data.get('month')  # May be None for insurance payments

        # Validate 'month' field for non-insurance payments
        if payment_type not in ['insurance'] and month is None:
            raise ValidationError("Field 'month' is required for non-insurance payments.")

        new_amount = data['amount']

        # Find existing payment for the student in the specified month and type
        existing_payment = Payment.objects(
            student=student, payment_type=payment_type, month=month
        ).first()

        payment_info = student.payments or PaymentInfo()

        # Ensure that real_payments exists as an EmbeddedDocument
        if not payment_info.real_payments:
            payment_info.real_payments = RealPayments()

        # Determine the specific field to update
        field = get_field(payment_type, month)
        if not field:
            raise ValidationError(f"Invalid payment_type: {payment_type}")

        # If the amount is 0, delete the existing payment if it exists
        if new_amount == 0:
            if existing_payment:
                # Reset the specific field in real_payments
                setattr(payment_info.real_payments, field, 0)
                student.payments = payment_info
                student.save()

                # Delete payment
                existing_payment.delete()

                # Record the deletion
                changes = [
                    ChangeDetail(
                        field_name=field,
                        old_value=json.dumps(existing_payment.to_json()),
                        new_value='0'  # Indicates reset
                    )
                ]
                # save_record = Save(
                #     student=student,
                #     user=user,
                #     types=['payment'],
                #     changes=changes,
                #     date=datetime.utcnow()
                # )
                # save_record.save()

            return jsonify({"status": "success", "message": "Payment deleted"}), 200

        # If payment exists, update it (modification of the existing payment)
        if existing_payment:
            old_payment_data = existing_payment.to_json()
            existing_payment.amount = new_amount
            existing_payment.save()

            # Update payment info in student document
            setattr(payment_info.real_payments, field, new_amount)
            student.payments = payment_info
            student.save()

            # Record the update
            changes = [
                ChangeDetail(
                    field_name=field,
                    old_value=json.dumps(old_payment_data),
                    new_value=json.dumps(existing_payment.to_json())
                )
            ]
            # save_record = Save(
            #     student=student,
            #     user=user,
            #     types=['payment'],
            #     changes=changes,
            #     date=datetime.utcnow()
            # )
            # save_record.save()

            return jsonify({"status": "success", "data": existing_payment.to_json()}), 200

        # If no payment exists, create a new one
        else:
            # For insurance payments, 'month' is not required
            if payment_type == 'insurance':
                new_payment = Payment(
                    student=student,
                    user=user,
                    amount=new_amount,
                    payment_type=payment_type,
                    month=None,  # Explicitly set month to None for insurance payments
                    date=datetime.utcnow()
                )
            else:
                new_payment = Payment(
                    student=student,
                    user=user,
                    amount=new_amount,
                    payment_type=payment_type,
                    month=month,
                    date=datetime.utcnow()
                )
            new_payment.save()

            # Update payment info in student document
            setattr(payment_info.real_payments, field, new_payment.amount)
            student.payments = payment_info
            student.save()

            # Record the creation
            changes = [
                ChangeDetail(
                    field_name=field,
                    old_value='0',
                    new_value=json.dumps(new_payment.to_json())
                )
            ]
            # save_record = Save(
            #     student=student,
            #     user=user,
            #     types=['payment'],
            #     changes=changes,
            #     date=datetime.utcnow()
            # )
            # save_record.save()

            return jsonify({"status": "success", "data": new_payment.to_json()}), 201

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
