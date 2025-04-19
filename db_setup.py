from std_db import AttendanceSystem
import os
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

def get_db_config():
    # Check if DATABASE_URL is provided (Heroku)
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Parse the URL to get components
        try:
            # Example: mysql://username:password@host:port/dbname
            match = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
            if match:
                user, password, host, port, dbname = match.groups()
                return {
                    'host': host,
                    'port': int(port),
                    'user': user,
                    'password': password,
                    'database': dbname
                }
        except Exception as e:
            print(f"Error parsing DATABASE_URL: {e}")
    
    # If no DATABASE_URL or parsing failed, use local .env settings
    return {
        'host': os.getenv('DB_HOST'),
        'port': int(os.getenv('DB_PORT')),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'database': os.getenv('DB_NAME')
    }

def setup_database():
    print("Setting up database...")
    config = get_db_config()
    system = AttendanceSystem(
        host=config['host'],
        port=config['port'],
        user=config['user'],
        password=config['password'],
        database=config['database']
    )
    
    # Create database and tables
    system.create_database()
    system.create_tables()
    print("Database setup complete!")

if __name__ == "__main__":
    setup_database() 