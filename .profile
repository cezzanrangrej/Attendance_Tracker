#!/bin/bash
# Add Python path to PATH
export PATH=$PATH:/opt/python/latest/bin
# Print Python and pip info for debugging
which python
python --version
which pip
pip --version
which gunicorn 