# app.py

from flask import Flask, jsonify
from flask_mongoengine import MongoEngine
from config import Config
import logging
from logging.handlers import RotatingFileHandler
import os
from flask_cors import CORS

# Initialize MongoEngine
db = MongoEngine()

def create_app():
    app = Flask(__name__)
    
    # Load configuration from Config class
    app.config.from_object(Config)
    
    # Log the MONGO_URI to verify it's being read correctly
    app.logger.debug(f"MONGO_URI from config: {app.config.get('MONGO_URI')}")
    # Initialize MongoDB with the app immediately
    db.init_app(app)
    
    # Enable CORS for all routes and origins
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

    # Register Blueprints
    register_blueprints(app)
    
    # Setup Logging
    setup_logging(app)
    
    # Log startup message
    app.logger.info('GSP Finance Backend Startup')

    # Test route to check MongoDB connection
    @app.route('/test-db', methods=['GET'])
    def test_db():
        """
        Test route to verify MongoDB connectivity and retrieve sample data from SchoolYearPeriod.
        """
        try:
            from models import SchoolYearPeriod  # Ensure correct import

            # Query the SchoolYearPeriod collection for the first 3 documents
            periods = SchoolYearPeriod.objects.limit(3)
            
            # Format data for the response
            period_data = [
                {
                    "name": period.name, 
                    "start_date": period.start_date.isoformat(), 
                    "end_date": period.end_date.isoformat()
                } 
                for period in periods
            ]
            
            return jsonify({"status": "success", "message": "Connected to MongoDB", "data": period_data}), 200

        except Exception as e:
            # Log the error if the database connection fails
            app.logger.error(f"Database connection failed: {e}")
            return jsonify({"status": "error", "message": f"Database connection failed: {str(e)}"}), 500

    return app

def register_blueprints(app):
    from routes.auth import auth_bp
    from routes.students import students_bp
    from routes.payments import payments_bp
    from routes.depences import depences_bp
    from routes.accounting import accounting_bp
    from routes.schoolyearperiods import schoolyearperiods_bp
    from routes.reports import reports_bp
    from routes.creditreports import creditreports_bp
    from routes.dailyaccreport import dailyacc_bp
    from routes.transportreport import transport_bp  
    from routes.paymentsReport import payments_report_bp
    
    # Register each blueprint with a URL prefix
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(students_bp, url_prefix='/students')
    app.register_blueprint(payments_bp, url_prefix='/payments')
    app.register_blueprint(depences_bp, url_prefix='/depences')
    app.register_blueprint(accounting_bp, url_prefix='/accounting')
    app.register_blueprint(schoolyearperiods_bp, url_prefix='/schoolyearperiods')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(creditreports_bp, url_prefix='/creditreports')
    app.register_blueprint(dailyacc_bp, url_prefix='/dailyacc')
    app.register_blueprint(transport_bp, url_prefix='/transport')
    app.register_blueprint(payments_report_bp, url_prefix='/payments-report')

def setup_logging(app):
    # Create logs directory if it doesn’t exist
    if not os.path.exists('logs'):
        os.mkdir('logs')
        
    # Setup file-based rotating logging
    file_handler = RotatingFileHandler('logs/gsp_finance.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.DEBUG)  # Set to DEBUG level for detailed logs
    
    # Add the file handler to Flask’s logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.DEBUG)

app = create_app()

# Run the app with host and port configured for production
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
