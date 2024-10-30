# routes/saves.py

from flask import Blueprint, request, jsonify
from models import Save, Student, User, ChangeDetail, db
from mongoengine import DoesNotExist, ValidationError
from datetime import datetime
import json

saves_bp = Blueprint('saves', __name__)

@saves_bp.route('/create', methods=['POST'])
def create_save():
    data = request.get_json()
    try:
        # Validate required fields
        required_fields = ['student_id', 'user_id', 'field_name', 'new_value', 'date']
        for field in required_fields:
            if field not in data:
                raise KeyError(field)

        # Retrieve student and user
        student = Student.objects.get(id=data['student_id'])
        user = User.objects.get(id=data['user_id'])
        field_name = data['field_name']
        new_value = data['new_value']
        date = data['date']

        # Optionally, retrieve the old value if needed
        # For now, we'll set old_value as 'null' since we don't have it
        # Ideally, you should pass the old value from the frontend or retrieve it from the Student object

        changes = [
            ChangeDetail(
                field_name=field_name,
                old_value='null',  # Replace with actual old value if available
                new_value=str(new_value)
            )
        ]

        save_record = Save(
            student=student,
            user=user,
            types=['agreed_payment'],
            changes=changes,
            date=datetime.fromisoformat(date.replace("Z", "+00:00"))  # Convert to datetime object
        )
        save_record.save()

        return jsonify({"status": "success", "message": "Agreed payment saved"}), 201

    except KeyError as e:
        return jsonify({"status": "error", "message": f"Missing field: {str(e)}"}), 400
    except DoesNotExist as e:
        return jsonify({"status": "error", "message": str(e)}), 404
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
