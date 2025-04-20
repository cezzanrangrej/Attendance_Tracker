from flask import Flask, jsonify, request, render_template, send_from_directory
from backend.database.std_db import Student, AttendanceSystem
from datetime import datetime
import traceback
import time
import pymysql
from flask_cors import CORS
import os
from dotenv import load_dotenv
import logging
import sys

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Get database configuration
def get_db_config():
    # Use individual environment variables (MySQL)
    logger.info("Using database environment variables")
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'attendance_db'),
        'db_type': 'mysql'
    }

# Initialize Flask app
app = Flask(__name__, 
    static_folder='../../frontend/static',
    template_folder='../../frontend/templates',
    static_url_path='/static'
)

# Enable CORS with additional options
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Handle OPTIONS requests explicitly
@app.route('/', methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path=None):
    return jsonify({}), 200

# Add a simple diagnostic endpoint
@app.route('/api/ping', methods=['GET'])
def ping():
    return jsonify({"status": "ok", "message": "Server is running", "timestamp": datetime.now().isoformat()})

# Initialize DAO with retry mechanism
def init_system():
    logger.info("Initializing system...")
    try:
        config = get_db_config()
        logger.info(f"DB Config: {config}")
        
        # Extract the db_type
        db_type = config.pop('db_type', 'mysql')
        
        # Create the attendance system with the appropriate database type
        system = AttendanceSystem(**config, db_type=db_type)
        
        # Retry connection with backoff
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # Try to connect to the database
                conn = system.connect_db()
                if conn:
                    conn.close()
                    logger.info("Successfully connected to database")
                    
                    # Set up database tables
                    system.create_database()
                    system.create_tables()
                    return system
                else:
                    logger.warning(f"Connection failed on attempt {attempt+1}/{max_retries}")
            except Exception as e:
                logger.error(f"Error connecting to database (attempt {attempt+1}/{max_retries}): {e}")
            
            # Don't sleep on the last attempt
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt  # Exponential backoff: 1, 2, 4, 8...
                logger.info(f"Retrying in {sleep_time} seconds...")
                time.sleep(sleep_time)
        
        logger.error("Failed to connect to database after multiple attempts")
        return None  # Return None to indicate failure
    except Exception as e:
        logger.error(f"Error in init_system: {e}")
        logger.error(traceback.format_exc())
        return None

# Global system instance
system = None

# Initialize system before first request
try:
    logger.info("Trying to initialize system at startup")
    system = init_system()
    if system is None:
        logger.error("System initialization failed at startup")
except Exception as e:
    logger.error(f"Error during startup initialization: {e}")
    logger.error(traceback.format_exc())

# This will be called if the system wasn't initialized at startup
@app.before_request
def ensure_system_initialized():
    global system
    if system is None:
        logger.info("Initializing system before request")
        try:
            system = init_system()
            if system is None:
                logger.error("System initialization failed before request")
        except Exception as e:
            logger.error(f"Error initializing system before request: {e}")
            logger.error(traceback.format_exc())

@app.route('/')
def home():
    try:
        if system is None:
            logger.error("Database system not initialized")
            return render_template('error.html', error="Database system not initialized")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in home route: {e}")
        return render_template('error.html', error=str(e))

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('../../frontend/static', path)

# ----- Error Handlers -----
@app.errorhandler(500)
def handle_500(error):
    logger.error(f"500 error: {error}")
    return jsonify({'error': 'Internal server error', 'details': str(error)}), 500

@app.errorhandler(404)
def handle_404(error):
    return jsonify({'error': 'Not found', 'details': str(error)}), 404

# ----- Student Endpoints -----
@app.route('/api/student-list', methods=['GET'])
def list_students():
    try:
        logger.info("Received GET request for /api/student-list")
        if system is None:
            logger.error("Database system not initialized")
            return jsonify({'error': 'Database system not initialized'}), 500
            
        rows = system.list_students()
        students = []
        
        for r in rows:
            # Ensure 'class' is properly included and not undefined
            student = {
                'id': r['id'],
                'roll_no': r['roll_no'],
                'name': r['name']
            }
            
            # Add class, ensuring it's not undefined
            if 'class' in r and r['class']:
                student['class'] = r['class']
            else:
                student['class'] = 'N/A'  # Fallback if class is missing or empty
                
            students.append(student)
            
        logger.info(f"Returning students: {students}")
        return jsonify(students)
    except Exception as e:
        logger.error(f"Error in list_students: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/student-add', methods=['POST'])
def create_student():
    try:
        logger.info("Received POST request for /api/student-add")
        if system is None:
            logger.error("Database system not initialized")
            return jsonify({'error': 'Database system not initialized'}), 500
            
        data = request.get_json()
        logger.info(f"Received data: {data}")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['id', 'roll_no', 'name', 'class']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        try:
            student_id = int(data['id'])
            
            # 'class' is a reserved keyword in Python, so ensure we're handling it correctly
            student_class = data.get('class')
            if not student_class or student_class.strip() == '':
                return jsonify({'error': 'Class cannot be empty'}), 400
                
            student = Student(
                roll_no=int(data['roll_no']),
                name=data['name'],
                student_class=student_class
            )
            logger.info(f"Created student object: {student}")
        except ValueError as e:
            logger.error(f"ValueError: {str(e)}")
            return jsonify({'error': 'ID and roll number must be valid integers'}), 400
        
        try:
            sid = system.add_student(student, student_id)
            row = system.get_student(sid)
            
            # Ensure class is properly defined in the response
            response_data = {
                'id': row['id'],
                'roll_no': row['roll_no'],
                'name': row['name'],
                'class': row['class'] if 'class' in row else student_class  # Fallback if needed
            }
            logger.info(f"Successfully added student: {response_data}")
            return jsonify(response_data), 201
        except Exception as e:
            logger.error(f"Error adding student to database: {str(e)}")
            return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        logger.error(f"Error in create_student: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/students/<int:sid>', methods=['GET'])
def read_student(sid):
    try:
        row = system.get_student(sid)
        if not row:
            return jsonify({'message': 'Student not found'}), 404
        return jsonify({
            'id': row['id'],
            'roll_no': row['roll_no'],
            'name': row['name'],
            'class': row['class']
        })
    except Exception as e:
        logger.error(f"Error in read_student: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/students/<int:sid>', methods=['PUT'])
def update_student(sid):
    try:
        data = request.get_json()
        existing = system.get_student(sid)
        if not existing:
            return jsonify({'message': 'Student not found'}), 404
        updated = Student(
            roll_no=data.get('roll_no'),
            name=data.get('name'),
            student_class=data.get('class')
        )
        system.update_student(sid, updated)
        row = system.get_student(sid)
        return jsonify({
            'id': row['id'],
            'roll_no': row['roll_no'],
            'name': row['name'],
            'class': row['class']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/students/<int:sid>', methods=['DELETE'])
def delete_student(sid):
    try:
        existing = system.get_student(sid)
        if not existing:
            return jsonify({'message': 'Student not found'}), 404
        system.delete_student(sid)
        return jsonify({'message': f'Student id={sid} deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ----- Attendance Endpoints -----
@app.route('/api/attendance', methods=['GET'])
def list_all_attendance():
    try:
        logger.info("Received GET request for /api/attendance")
        if system is None:
            logger.error("Database system not initialized")
            return jsonify({'error': 'Database system not initialized'}), 500
            
        rows = system.list_all_attendance()
        # No need to transform rows here as we've done that in the DB layer
        logger.info(f"Returning attendance records: {rows}")
        return jsonify(rows)
    except Exception as e:
        logger.error(f"Error in list_all_attendance: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance', methods=['POST'])
def mark_attendance():
    try:
        logger.info("Received POST request for /api/attendance")
        if system is None:
            logger.error("Database system not initialized")
            return jsonify({'error': 'Database system not initialized'}), 500
            
        data = request.get_json()
        logger.info(f"Received attendance data: {data}")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['student_id', 'date', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        try:
            student_id = int(data['student_id'])
            at_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            status = data['status']
            
            # Validate status
            if status not in ['Present', 'Absent']:
                return jsonify({'error': 'Status must be either Present or Absent'}), 400
                
            # Check if student exists
            student = system.get_student(student_id)
            if not student:
                return jsonify({'error': f'Student with ID {student_id} not found'}), 404
                
            aid = system.mark_attendance(student_id, at_date, status)
            if not aid:
                return jsonify({'error': 'Failed to mark attendance'}), 500
                
            row = system.get_attendance(aid)
            
            # Get student details to include class
            student_details = system.get_student(student_id)
            
            response_data = {
                'id': row['id'],
                'student_id': row['student_id'],
                'roll_no': student_details['roll_no'],
                'name': student_details['name'],
                'class': student_details['class'] if student_details and 'class' in student_details else 'N/A',
                'date': str(row['date']),
                'status': row['status']
            }
            
            logger.info(f"Successfully marked attendance: {response_data}")
            return jsonify(response_data), 201
            
        except ValueError as e:
            return jsonify({'error': f'Invalid data format: {str(e)}'}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 400
            
    except Exception as e:
        logger.error(f"Error in mark_attendance: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/attendance/<int:aid>', methods=['GET'])
def get_attendance(aid):
    try:
        row = system.get_attendance(aid)
        if not row:
            return jsonify({'message': 'Attendance record not found'}), 404
        return jsonify({
            'id': row['id'],
            'student_id': row['student_id'],
            'date': str(row['date']),
            'status': row['status']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/attendance/student/<int:student_id>', methods=['GET'])
def list_attendance_for_student(student_id):
    try:
        rows = system.list_attendance_by_student(student_id)
        records = [{'id': r['id'], 'date': str(r['date']), 'status': r['status']} for r in rows]
        return jsonify(records)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/attendance/<int:aid>', methods=['PUT'])
def update_attendance(aid):
    try:
        data = request.get_json()
        existing = system.get_attendance(aid)
        if not existing:
            return jsonify({'message': 'Record not found'}), 404
        new_status = data.get('status')
        system.update_attendance(aid, new_status)
        row = system.get_attendance(aid)
        return jsonify({
            'id': row['id'],
            'student_id': row['student_id'],
            'date': str(row['date']),
            'status': row['status']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/attendance/<int:aid>', methods=['DELETE'])
def delete_attendance(aid):
    try:
        logger.info(f"Received DELETE request for /api/attendance/{aid}")
        existing = system.get_attendance(aid)
        if not existing:
            return jsonify({'message': 'Record not found'}), 404
        system.delete_attendance(aid)
        return jsonify({'message': f'Attendance id={aid} deleted'})
    except Exception as e:
        logger.error(f"Error deleting attendance: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Use default port
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting server on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port) 