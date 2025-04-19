#!/bin/bash
# Exit on error
set -e

echo "Python version:"
python --version

echo "Installing pip packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Checking gunicorn installation:"
pip show gunicorn 