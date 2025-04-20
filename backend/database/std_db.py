import pymysql
from datetime import date
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Student:
    def __init__(self, roll_no=0, name="", student_class=""):
        self.roll_no = roll_no
        self.name = name
        self.student_class = student_class

    def __str__(self):
        return f"Roll No: {self.roll_no}, Name: {self.name}, Class: {self.student_class}"  

class AttendanceSystem:
    def __init__(self, host=None, port=None, user=None, password=None, database=None, db_type='mysql', charset='utf8mb4'):
        # MySQL config
        self.db_config = {
            'host': host or os.getenv('DB_HOST'),
            'port': port or int(os.getenv('DB_PORT', 3306)),
            'user': user or os.getenv('DB_USER'),
            'password': password or os.getenv('DB_PASSWORD'),
            'database': database or os.getenv('DB_NAME'),
            'charset': charset,
            'cursorclass': pymysql.cursors.DictCursor
        }

    def connect_db(self):
        try:
            # MySQL connection
            conn = pymysql.connect(**self.db_config)
            print("MySQL DB connected")
            return conn
        except Exception as err:
            print(f"Error connecting to DB: {err}")
            return None

    def disconnect_db(self, conn):
        if conn:
            conn.close()
            print("DB disconnected")

    def create_database(self):
        try:
            # MySQL: Connect without database to create it
            cfg = self.db_config.copy()
            cfg.pop('database')
            conn = pymysql.connect(**cfg)
            cursor = conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS attendance_db;")
            print("Database 'attendance_db' ensured.")
            cursor.close()
            conn.close()
        except Exception as err:
            print(f"Error creating database: {err}")

    def create_tables(self):
        conn = self.connect_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            
            # MySQL tables
            # Student table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS students (
                    id INT PRIMARY KEY,
                    roll_no INT UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    class VARCHAR(50) NOT NULL
                );
                """
            )
            # Attendance table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    student_id INT NOT NULL,
                    date DATE NOT NULL,
                    status ENUM('Present','Absent') NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES students(id)
                );
                """
            )
            
            conn.commit()
            print("Tables 'students' and 'attendance' ensured.")
        except Exception as err:
            print(f"Error creating tables: {err}")
            conn.rollback()
        finally:
            cursor.close()
            self.disconnect_db(conn)

    def add_student(self, student: Student, student_id: int = None):
        conn = self.connect_db()
        if not conn:
            raise Exception("Failed to connect to database")
            
        try:
            cursor = conn.cursor()
            
            # Check if student ID is provided
            if student_id is None:
                raise Exception("Student ID is required")
                
            # Check if student ID already exists
            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            existing_id = cursor.fetchone()
                
            if existing_id:
                raise Exception(f"Student with ID {student_id} already exists")
            
            # Check if roll number already exists
            cursor.execute("SELECT id FROM students WHERE roll_no = %s", (student.roll_no,))
            existing_roll = cursor.fetchone()
                
            if existing_roll:
                raise Exception(f"Student with roll number {student.roll_no} already exists")
            
            # Insert student
            query = "INSERT INTO students (id, roll_no, name, class) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (student_id, student.roll_no, student.name, student.student_class))
            conn.commit()
            print(f"Student added with id={student_id}")
            return student_id
        except Exception as err:
            print(f"Error adding student: {err}")
            conn.rollback()
            raise Exception(f"Database error: {str(err)}")
        finally:
            if cursor:
                cursor.close()
            self.disconnect_db(conn)

    def update_student(self, sid, new_data: Student):
        conn = self.connect_db()
        cursor = conn.cursor()
        query = "UPDATE students SET roll_no=%s, name=%s, class=%s WHERE id=%s"
        cursor.execute(query, (new_data.roll_no, new_data.name, new_data.student_class, sid))
        conn.commit()
        print(f"Student id={sid} updated.")
        cursor.close()
        self.disconnect_db(conn)

    def delete_student(self, sid):
        conn = self.connect_db()
        cursor = conn.cursor()
        # Optionally cascade delete attendance first
        cursor.execute("DELETE FROM attendance WHERE student_id=%s", (sid,))
        cursor.execute("DELETE FROM students WHERE id=%s", (sid,))
        conn.commit()
        print(f"Student id={sid} and related attendance deleted.")
        cursor.close()
        self.disconnect_db(conn)

    def get_student(self, sid):
        conn = self.connect_db()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, roll_no, name, class FROM students WHERE id=%s", (sid,))
            row = cursor.fetchone()
            return row
        except Exception as err:
            print(f"Error getting student: {err}")
            return None
        finally:
            cursor.close()
            self.disconnect_db(conn)

    def list_students(self):
        conn = self.connect_db()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, roll_no, name, class FROM students")
            rows = cursor.fetchall()
            return rows
        except Exception as err:
            print(f"Error listing students: {err}")
            return []
        finally:
            cursor.close()
            self.disconnect_db(conn)

    # Attendance operations
    def mark_attendance(self, student_id, at_date: date, status: str):
        conn = self.connect_db()
        if not conn:
            raise Exception("Failed to connect to database")
            
        try:
            cursor = conn.cursor()
            
            # First check if student exists
            cursor.execute("SELECT id FROM students WHERE id = %s", (student_id,))
            if not cursor.fetchone():
                raise Exception(f"Student with ID {student_id} not found")
            
            # Check if attendance already marked for this date
            cursor.execute(
                "SELECT id FROM attendance WHERE student_id = %s AND date = %s",
                (student_id, at_date)
            )
            if cursor.fetchone():
                raise Exception(f"Attendance already marked for student {student_id} on {at_date}")
            
            # Insert attendance record
            query = "INSERT INTO attendance (student_id, date, status) VALUES (%s, %s, %s)"
            cursor.execute(query, (student_id, at_date, status))
            conn.commit()
            
            # Get the last inserted ID
            aid = cursor.lastrowid
                
            print(f"Attendance marked id={aid} for student_id={student_id}")
            return aid
            
        except Exception as err:
            print(f"Error marking attendance: {err}")
            conn.rollback()
            raise Exception(f"Database error: {str(err)}")
        finally:
            if cursor:
                cursor.close()
            self.disconnect_db(conn)

    def update_attendance(self, aid, new_status: str):
        conn = self.connect_db()
        cursor = conn.cursor()
        query = "UPDATE attendance SET status=%s WHERE id=%s"
        cursor.execute(query, (new_status, aid))
        conn.commit()
        print(f"Attendance id={aid} updated to {new_status}.")
        cursor.close()
        self.disconnect_db(conn)

    def delete_attendance(self, aid):
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM attendance WHERE id=%s", (aid,))
        conn.commit()
        print(f"Attendance id={aid} deleted.")
        cursor.close()
        self.disconnect_db(conn)

    def get_attendance(self, aid):
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM attendance WHERE id=%s", (aid,))
        row = cursor.fetchone()
        cursor.close()
        self.disconnect_db(conn)
        return row

    def list_attendance_by_student(self, student_id):
        conn = self.connect_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, status FROM attendance WHERE student_id=%s", (student_id,))
        rows = cursor.fetchall()
        for r in rows:
            print(r)
        cursor.close()
        self.disconnect_db(conn)
        return rows

    def list_all_attendance(self):
        conn = self.connect_db()
        cursor = conn.cursor()
        # Join with students table to get student information including class
        cursor.execute("SELECT a.id, s.roll_no, s.name, s.class, a.date, a.status FROM attendance a JOIN students s ON a.student_id=s.id")
        rows = cursor.fetchall()
        
        # Process rows to ensure class is properly defined
        result = []
        for r in rows:
            record = {
                'id': r['id'],
                'roll_no': r['roll_no'],
                'name': r['name'],
                'date': r['date'],
                'status': r['status']
            }
            
            # Ensure class is never undefined
            if 'class' in r and r['class']:
                record['class'] = r['class']
            else:
                record['class'] = 'N/A'  # Fallback value
                
            result.append(record)
            print(record)
            
        cursor.close()
        self.disconnect_db(conn)
        return result 