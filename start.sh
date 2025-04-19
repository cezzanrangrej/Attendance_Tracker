#!/bin/bash
# Ensure script stops on first error
set -e

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Print gunicorn version and path
echo "Gunicorn information:"
which gunicorn || echo "Gunicorn not found in PATH"
pip show gunicorn

# Start the application
echo "Starting application..."
gunicorn attendance_api:app 