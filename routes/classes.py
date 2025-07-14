from flask import Blueprint, request, jsonify
from models import Classe, Student
from mongoengine.errors import NotUniqueError, ValidationError, DoesNotExist

# Use strict_slashes=False to handle both /classes and /classes/
classes_bp = Blueprint('classes', __name__, url_prefix='/classes')

# Helper to convert MongoEngine doc to dict with string ID
def classe_to_dict(classe):
    return {
        "_id": str(classe.id),
        "name": classe.name,
        "order": classe.order
    }

@classes_bp.route('', methods=['GET'], strict_slashes=False)
def get_classes():
    classes = Classe.objects().order_by('order')
    return jsonify({
        "status": "success",
        "data": [classe_to_dict(classe) for classe in classes]
    }), 200

@classes_bp.route('', methods=['POST'], strict_slashes=False)
def create_class():
    data = request.get_json()
    name = data.get("name", "").strip()
    order = data.get("order", 999)
    
    if not name:
        return jsonify({"status": "error", "message": "Name is required"}), 400
    try:
        classe = Classe(name=name, order=order)
        classe.save()
        return jsonify({
            "status": "success",
            "data": classe_to_dict(classe)
        }), 201
    except NotUniqueError:
        return jsonify({"status": "error", "message": "Class name must be unique"}), 400
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@classes_bp.route('/<string:classe_id>', methods=['GET'], strict_slashes=False)
def get_class(classe_id):
    try:
        classe = Classe.objects.get(id=classe_id)
        return jsonify({
            "status": "success",
            "data": classe_to_dict(classe)
        }), 200
    except DoesNotExist:
        return jsonify({"status": "error", "message": "Class not found"}), 404

@classes_bp.route('/<string:classe_id>', methods=['PUT'], strict_slashes=False)
def update_class(classe_id):
    data = request.get_json()
    
    try:
        classe = Classe.objects.get(id=classe_id)
        
        # If name is provided, update it (it must be non-empty)
        if "name" in data:
            name = data.get("name", "").strip()
            if not name:
                return jsonify({"status": "error", "message": "Name cannot be empty"}), 400
            classe.name = name
        
        # If order is provided, update it
        if "order" in data:
            try:
                classe.order = int(data.get("order"))
            except (ValueError, TypeError):
                return jsonify({"status": "error", "message": "Order must be a valid number"}), 400
        
        # Ensure at least one field was updated
        if not any(field in data for field in ["name", "order"]):
            return jsonify({"status": "error", "message": "No fields to update were provided"}), 400
            
        classe.save()
        return jsonify({
            "status": "success",
            "data": classe_to_dict(classe)
        }), 200
    except DoesNotExist:
        return jsonify({"status": "error", "message": "Class not found"}), 404
    except NotUniqueError:
        return jsonify({"status": "error", "message": "Class name must be unique"}), 400
    except ValidationError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@classes_bp.route('/<string:classe_id>', methods=['DELETE'], strict_slashes=False)
def delete_class(classe_id):
    try:
        classe = Classe.objects.get(id=classe_id)
        
        # Check if there are students in this class
        students_in_class = Student.objects(classe=classe.id)
        if students_in_class.count() > 0 and not request.args.get('force'):
            return jsonify({
                "status": "error", 
                "message": f"Cannot delete class. {students_in_class.count()} students are assigned to this class.",
                "students": [{"id": str(s.id), "name": s.name} for s in students_in_class]
            }), 400
            
        classe.delete()
        return jsonify({"status": "success", "message": "Class deleted"}), 200
    except DoesNotExist:
        return jsonify({"status": "error", "message": "Class not found"}), 404

@classes_bp.route('/counts', methods=['GET'], strict_slashes=False)
def get_class_counts():
    """
    Get the count of students in each class for a specific school year period.
    Query param: school_year_id - The ID of the school year to filter by
    """
    school_year_id = request.args.get('school_year_id')
    
    if not school_year_id:
        return jsonify({"status": "error", "message": "School year ID is required"}), 400
    
    try:
        # Get all classes
        classes = Classe.objects()
        
        # Create a dictionary to store counts
        class_counts = {}
        
        # Count students for each class in the specified school year
        for classe in classes:
            # Query students directly with both class and school year filters
            count = Student.objects(classe=classe.id, school_year=school_year_id).count()
            class_counts[str(classe.id)] = count
            
        return jsonify({
            "status": "success",
            "data": class_counts
        }), 200
    except Exception as e:
        print(f"Error in get_class_counts: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@classes_bp.route('/debug-counts', methods=['GET'], strict_slashes=False)
def debug_class_counts():
    """Debug endpoint to help troubleshoot student counts by class"""
    school_year_id = request.args.get('school_year_id')
    
    if not school_year_id:
        return jsonify({"status": "error", "message": "School year ID is required"}), 400
    
    try:
        # Get all classes
        classes = list(Classe.objects())
        
        # Get students in the specified school year
        all_students = list(Student.objects(school_year=school_year_id))
        
        debug_info = {
            "school_year_id": school_year_id,
            "total_classes": len(classes),
            "total_students_in_year": len(all_students),
            "classes": [],
            "students_without_class": []
        }
        
        # Group students by class
        class_map = {}
        for student in all_students:
            if not student.classe:
                debug_info["students_without_class"].append({
                    "id": str(student.id),
                    "name": student.name
                })
                continue
                
            class_id = str(student.classe.id)
            if class_id not in class_map:
                class_map[class_id] = []
            class_map[class_id].append({
                "id": str(student.id),
                "name": student.name
            })
        
        # Collect class info
        for classe in classes:
            class_id = str(classe.id)
            students = class_map.get(class_id, [])
            debug_info["classes"].append({
                "id": class_id,
                "name": classe.name,
                "student_count": len(students),
                "students": students
            })
        
        return jsonify({
            "status": "success",
            "debug_info": debug_info
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@classes_bp.route('/normalize-order', methods=['POST'], strict_slashes=False)
def normalize_class_order():
    """
    Reset and normalize the order values for all classes.
    This ensures consistent spacing between order values.
    """
    try:
        # Get all classes, sorted by current order
        classes = Classe.objects().order_by('order')
        
        # Start with base order and increment by a large value
        base_order = 1000
        increment = 1000
        
        # Update each class with new order value
        updated_classes_data = []
        for index, classe in enumerate(classes):
            new_order = base_order + (index * increment)
            classe.order = new_order
            classe.save()
            updated_classes_data.append(classe_to_dict(classe))
        
        return jsonify({
            "status": "success",
            "message": f"Successfully normalized order for {len(classes)} classes",
            "data": updated_classes_data
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@classes_bp.route('/batch-update-order', methods=['POST'], strict_slashes=False)
def batch_update_order():
    """
    Update the order of multiple classes in a single request.
    Expects a JSON with format: {"classes": [{"id": "class_id", "order": order_value}, ...]}
    """
    try:
        data = request.get_json()
        
        if not data or 'classes' not in data or not isinstance(data['classes'], list):
            return jsonify({"status": "error", "message": "Invalid data format. Expected {'classes': [...]}"}), 400
        
        class_updates = data['classes']
        updated_ids = []
        
        for update in class_updates:
            class_id = update.get('id')
            new_order = update.get('order')
            
            if not class_id or not isinstance(new_order, (int, float)):
                continue
                
            try:
                classe = Classe.objects.get(id=class_id)
                classe.order = new_order
                classe.save()
                updated_ids.append(class_id)
            except (DoesNotExist, ValidationError) as e:
                print(f"Error updating class {class_id}: {str(e)}")
        
        all_classes = Classe.objects().order_by('order')
        
        return jsonify({
            "status": "success",
            "message": f"Attempted to update {len(class_updates)} classes. Successfully updated {len(updated_ids)}.",
            "data": [classe_to_dict(classe) for classe in all_classes]
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
