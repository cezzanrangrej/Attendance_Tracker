from flask import Flask, jsonify, request, render_template, send_from_directory
from std_db import Student, AttendanceSystem
from datetime import datetime
import traceback
import time
import pymysql
import psycopg2
from flask_cors import CORS
import os
from dotenv import load_dotenv
import re
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
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

# Get database URL from environment (for Railway)
def get_db_config():
    # First, check if we have a Railway DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        logger.info(f"Using DATABASE_URL environment variable")
        
        # Check if PostgreSQL URL (Railway format)
        if database_url.startswith('postgresql://'):
            logger.info("Detected PostgreSQL connection string")
            # Parse the PostgreSQL URL
            parsed = urlparse(database_url)
            
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'user': parsed.username,
                'password': parsed.password,
                'database': parsed.path[1:] if parsed.path else None,
                'db_type': 'postgresql'
            }
        # MySQL URL format
        elif database_url.startswith('mysql://'):
            logger.info("Detected MySQL connection string")
            # Parse the MySQL URL
            parsed = urlparse(database_url)
            
            return {
                'host': parsed.hostname,
                'port': parsed.port or 3306,
                'user': parsed.username,
                'password': parsed.password,
                'database': parsed.path[1:] if parsed.path else None,
                'db_type': 'mysql'
            }
        else:
            logger.warning(f"Unknown database URL format: {database_url[:10]}...")
    
    # Fallback to individual environment variables (default to MySQL)
    logger.info("Using individual DB environment variables")
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
    static_folder='static',
    template_folder='templates',
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
                    system.create_database()  # This will be skipped for PostgreSQL
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

# Initialize system before first request - compatible with Flask 2.x
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
    return send_from_directory('static', path)

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
                'id': r['id'] if isinstance(r, dict) else r[0],
                'roll_no': r['roll_no'] if isinstance(r, dict) else r[1],
                'name': r['name'] if isinstance(r, dict) else r[2]
            }
            
            # Add class, ensuring it's not undefined
            if isinstance(r, dict):
                if 'class' in r and r['class']:
                    student['class'] = r['class']
                else:
                    student['class'] = 'N/A'  # Fallback if class is missing or empty
            else:
                # PostgreSQL may return tuples
                student['class'] = r[3] if len(r) > 3 and r[3] else 'N/A'
                
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
        print("Received POST request for /api/student-add")
        if system is None:
            raise Exception("Database system not initialized")
            
        data = request.get_json()
        print(f"Received data: {data}")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['roll_no', 'name', 'class']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        try:
            # 'class' is a reserved keyword in Python, so ensure we're handling it correctly
            student_class = data.get('class')
            if not student_class or student_class.strip() == '':
                return jsonify({'error': 'Class cannot be empty'}), 400
                
            student = Student(
                roll_no=int(data['roll_no']),
                name=data['name'],
                student_class=student_class
            )
            print(f"Created student object: {student}")
        except ValueError as e:
            print(f"ValueError: {str(e)}")
            return jsonify({'error': 'Roll number must be a valid integer'}), 400
        
        try:
            sid = system.add_student(student)
            row = system.get_student(sid)
            
            # Ensure class is properly defined in the response
            response_data = {
                'id': row['id'],
                'roll_no': row['roll_no'],
                'name': row['name'],
                'class': row['class'] if 'class' in row else student_class  # Fallback if needed
            }
            print(f"Successfully added student: {response_data}")
            return jsonify(response_data), 201
        except Exception as e:
            print(f"Error adding student to database: {str(e)}")
            return jsonify({'error': str(e)}), 400
        
    except Exception as e:
        print(f"Error in create_student: {str(e)}")
        print(traceback.format_exc())
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
        print(f"Error in read_student: {str(e)}")
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
        if system is None:
            raise Exception("Database system not initialized")
            
        rows = system.list_all_attendance()
        records = []
        
        for row in rows:
            record = {
                'id': row['id'],
                'roll_no': row['roll_no'],
                'name': row['name'],
                'class': row['class'] if 'class' in row else 'N/A',
                'date': str(row['date']),
                'status': row['status']
            }
            records.append(record)
            
        return jsonify(records)
    except Exception as e:
        print(f"Error listing attendance: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/attendance', methods=['POST'])
def mark_attendance():
    try:
        print("Received POST request for /api/attendance")
        if system is None:
            raise Exception("Database system not initialized")
            
        data = request.get_json()
        print(f"Received attendance data: {data}")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['roll_no', 'date', 'status']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        try:
            roll_no = int(data['roll_no'])
            at_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            status = data['status']
            
            # Validate status
            if status not in ['Present', 'Absent']:
                return jsonify({'error': 'Status must be either Present or Absent'}), 400
                
            # Get student by roll number
            students = system.list_students()
            student = None
            for s in students:
                if s['roll_no'] == roll_no:
                    student = s
                    break
                    
            if not student:
                return jsonify({'error': f'Student with roll number {roll_no} not found'}), 404
                
            aid = system.mark_attendance(student['id'], at_date, status)
            if not aid:
                return jsonify({'error': 'Failed to mark attendance'}), 500
                
            row = system.get_attendance(aid)
            
            response_data = {
                'id': row['id'],
                'student_id': row['student_id'],
                'roll_no': student['roll_no'],
                'name': student['name'],
                'class': student['class'] if 'class' in student else 'N/A',
                'date': str(row['date']),
                'status': row['status']
            }
            return jsonify(response_data), 201
        except ValueError as e:
            return jsonify({'error': 'Roll number must be a valid integer'}), 400
    except Exception as e:
        print(f"Error marking attendance: {str(e)}")
        print(traceback.format_exc())
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

@app.route('/attendance/student/<int:roll_no>', methods=['GET'])
def list_attendance_for_student(roll_no):
    try:
        # Find student by roll number
        students = system.list_students()
        student = None
        for s in students:
            if s['roll_no'] == roll_no:
                student = s
                break
                
        if not student:
            return jsonify({'error': f'Student with roll number {roll_no} not found'}), 404
            
        rows = system.list_attendance_by_student(student['id'])
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
        
        # Get student details
        student = system.get_student(row['student_id'])
        
        return jsonify({
            'id': row['id'],
            'roll_no': student['roll_no'],
            'name': student['name'],
            'class': student['class'] if 'class' in student else 'N/A',
            'date': str(row['date']),
            'status': row['status']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/attendance/<int:aid>', methods=['DELETE'])
def delete_attendance(aid):
    try:
        print(f"Received DELETE request for /api/attendance/{aid}")
        existing = system.get_attendance(aid)
        if not existing:
            return jsonify({'message': 'Record not found'}), 404
        system.delete_attendance(aid)
        return jsonify({'message': f'Attendance id={aid} deleted'})
    except Exception as e:
        print(f"Error deleting attendance: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Use the port provided by Railway, or default to 5000
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting server on port {port}")
    app.run(debug=False, host='0.0.0.0', port=port)
