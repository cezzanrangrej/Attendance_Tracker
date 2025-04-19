# Attendance Tracker

📚 Student Attendance Management System

A Flask-based web application to manage student records and track attendance efficiently using a MySQL backend.

## Features

🚀 Features
* ✅ Add, edit, view, and delete student records
* 📆 Mark and update student attendance
* 📊 View attendance history for individual students or all at once
* 🌐 RESTful API with JSON responses
* ⚙️ Automatic database initialization and retry logic on startup
* 🔒 CORS enabled for cross-origin requests
* 💡 User-friendly error messages and HTTP status handling

## Tech Stack

🛠 Tech Stack
* Backend: Python (Flask)
* Database: MySQL
* Frontend: HTML (rendered via Flask templates)
* Others: Flask-CORS, PyMySQL

## Deployment Instructions

### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/attendance-tracker.git
   cd attendance-tracker
   ```

2. Create a `.env` file with your MySQL credentials:
   ```
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_NAME=attendance_db
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python attendance_api.py
   ```

5. Access the application at http://localhost:5173

### Heroku Deployment

1. Create a Heroku account at [heroku.com](https://heroku.com)

2. Install the [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)

3. Login to Heroku:
   ```
   heroku login
   ```

4. Create a new Heroku app:
   ```
   heroku create your-app-name
   ```

5. Provision a MySQL database:
   ```
   heroku addons:create jawsdb:kitefin
   ```

6. Push your code to Heroku:
   ```
   git push heroku main
   ```

7. Run the database setup script:
   ```
   heroku run python db_setup.py
   ```

8. Open your application:
   ```
   heroku open
   ```

## API Endpoints

### Students

| Method | Endpoint      | Description              |
|--------|---------------|--------------------------|
| GET    | /api/student-list | List all students        |
| POST   | /api/student-add  | Add a new student        |
| GET    | /students/    | Get student by ID        |
| PUT    | /students/    | Update student details   |
| DELETE | /students/    | Delete student           |

### Attendance

| Method | Endpoint           | Description                    |
|--------|-------------------|--------------------------------|
| GET    | /api/attendance   | List all attendance records     |
| POST   | /api/attendance   | Mark new attendance             |
| GET    | /attendance/      | Get attendance by record ID     |
| GET    | /attendance/student/ | List attendance for specific student |
| PUT    | /attendance/      | Update attendance status        |
| DELETE | /attendance/      | Delete an attendance record     |

## Notes

⚠️ Notes
* This app will automatically create the required database and tables on the first run.
* If the MySQL connection fails, it will retry up to 5 times before exiting.
* CORS is enabled for all origins ("*").
