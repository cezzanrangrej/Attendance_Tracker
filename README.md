📚 Student Attendance Management System

A Flask-based web application to manage student records and track attendance efficiently using a MySQL backend.

🚀 Features
	•	✅ Add, edit, view, and delete student records
	•	📅 Mark and update student attendance
	•	📊 View attendance history for individual students or all at once
	•	🌐 RESTful API with JSON responses
	•	⚙️ Automatic database initialization and retry logic on startup
	•	🔒 CORS enabled for cross-origin requests
	•	💡 User-friendly error messages and HTTP status handling

🛠️ Tech Stack
	•	Backend: Python (Flask)
	•	Database: MySQL
	•	Frontend: HTML (rendered via Flask templates)
	•	Others: Flask-CORS, PyMySQL

📬 API Endpoints

📚 Students

Method	Endpoint	Description
GET	/students	List all students
POST	/students	Add a new student
GET	/students/<id>	Get student by ID
PUT	/students/<id>	Update student details
DELETE	/students/<id>	Delete student

🕓 Attendance

Method	Endpoint	Description
GET	/attendance	List all attendance records
POST	/attendance	Mark new attendance
GET	/attendance/<id>	Get attendance by record ID
GET	/attendance/student/<student_id>	List attendance for specific student
PUT	/attendance/<id>	Update attendance status
DELETE	/attendance/<id>	Delete an attendance record

❗ Notes
	•	This app will automatically create the required database and tables on the first run.
	•	If the MySQL connection fails, it will retry up to 5 times before exiting.
	•	CORS is enabled for all origins ('*').
