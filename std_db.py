import pymysql
import psycopg2
from psycopg2.extras import DictCursor
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
        self.db_type = db_type
        
        if self.db_type == 'postgresql':
            # PostgreSQL config (for Railway)
            self.db_config = {
                'host': host or os.getenv('DB_HOST'),
                'port': port or int(os.getenv('DB_PORT', 5432)),
                'user': user or os.getenv('DB_USER'),
                'password': password or os.getenv('DB_PASSWORD'),
                'dbname': database or os.getenv('DB_NAME')
            }
        else:
            # MySQL config (default)
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
            if self.db_type == 'postgresql':
                # PostgreSQL connection
                conn = psycopg2.connect(**self.db_config)
                print("PostgreSQL DB connected")
                return conn
            else:
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
        if self.db_type == 'postgresql':
            # In PostgreSQL, we don't need to create the database
            # It's already created by Railway
            return
        
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
            
            if self.db_type == 'postgresql':
                # PostgreSQL tables with proper data types
                # Create an enum type for attendance status
                cursor.execute(
                    """
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'attendance_status') THEN
                            CREATE TYPE attendance_status AS ENUM ('Present', 'Absent');
                        END IF;
                    END$$;
                    """
                )
                
                # Students table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS students (
                        id SERIAL PRIMARY KEY,
                        roll_no INTEGER UNIQUE NOT NULL,
                        name VARCHAR(100) NOT NULL,
                        class VARCHAR(50) NOT NULL
                    );
                    """
                )
                
                # Attendance table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS attendance (
                        id SERIAL PRIMARY KEY,
                        student_id INTEGER NOT NULL,
                        date DATE NOT NULL,
                        status attendance_status NOT NULL,
                        FOREIGN KEY (student_id) REFERENCES students(id)
                    );
                    """
                )
            else:
                # MySQL tables
                # Student table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS students (
                        id INT PRIMARY KEY AUTO_INCREMENT,
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

    def add_student(self, student: Student):
        conn = self.connect_db()
        if not conn:
            raise Exception("Failed to connect to database")
            
        try:
            if self.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=DictCursor)
            else:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # Check if roll number already exists
            if self.db_type == 'postgresql':
                cursor.execute("SELECT id FROM students WHERE roll_no = %s", (student.roll_no,))
                existing_roll = cursor.fetchone()
            else:
                cursor.execute("SELECT id FROM students WHERE roll_no = %s", (student.roll_no,))
                existing_roll = cursor.fetchone()
                
            if existing_roll:
                raise Exception(f"Student with roll number {student.roll_no} already exists")
            
            # Insert student
            if self.db_type == 'postgresql':
                query = "INSERT INTO students (roll_no, name, class) VALUES (%s, %s, %s) RETURNING id"
                cursor.execute(query, (student.roll_no, student.name, student.student_class))
                result = cursor.fetchone()
                student_id = result[0] if isinstance(result, tuple) else result['id']
            else:
                query = "INSERT INTO students (roll_no, name, class) VALUES (%s, %s, %s)"
                cursor.execute(query, (student.roll_no, student.name, student.student_class))
                student_id = cursor.lastrowid
                
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
            if self.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=DictCursor)
            else:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
            cursor.execute("SELECT id, roll_no, name, class FROM students WHERE id=%s", (sid,))
            row = cursor.fetchone()
            if row:
                # Convert to dict if it's not already (for PostgreSQL)
                if not isinstance(row, dict):
                    row = {
                        'id': row[0],
                        'roll_no': row[1],
                        'name': row[2],
                        'class': row[3]
                    }
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
            if self.db_type == 'postgresql':
                cursor = conn.cursor(cursor_factory=DictCursor)
            else:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                
            cursor.execute("SELECT id, roll_no, name, class FROM students ORDER BY roll_no")
            rows = cursor.fetchall()
            
            # Convert to list of dicts if needed (for PostgreSQL)
            if rows and not isinstance(rows[0], dict):
                rows = [
                    {
                        'id': row[0],
                        'roll_no': row[1],
                        'name': row[2],
                        'class': row[3]
                    }
                    for row in rows
                ]
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
            if self.db_type == 'postgresql':
                cursor.execute("SELECT lastval()")
                aid = cursor.fetchone()[0]
            else:
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
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT a.id, s.roll_no, s.name, s.class, a.date, a.status FROM attendance a JOIN students s ON a.student_id=s.id")
            rows = cursor.fetchall()
            
            # Process rows to ensure class is properly defined
            result = []
            for r in rows:
                record = {
                    'id': r['id'] if self.db_type == 'mysql' else r[0],
                    'roll_no': r['roll_no'] if self.db_type == 'mysql' else r[1],
                    'name': r['name'] if self.db_type == 'mysql' else r[2],
                    'date': r['date'] if self.db_type == 'mysql' else r[4],
                    'status': r['status'] if self.db_type == 'mysql' else r[5]
                }
                
                # Ensure class is never undefined
                if self.db_type == 'mysql':
                    if 'class' in r and r['class']:
                        record['class'] = r['class']
                    else:
                        record['class'] = 'N/A'  # Fallback value
                else:
                    # PostgreSQL returns tuples, not dicts
                    record['class'] = r[3] if r[3] else 'N/A'
                    
                result.append(record)
                
            return result
        except Exception as err:
            print(f"Error listing attendance: {err}")
            return []
        finally:
            cursor.close()
            self.disconnect_db(conn)