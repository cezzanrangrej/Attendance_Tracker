#!/usr/bin/env python
import os
import sys
from backend.api.attendance_api import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port) 