import sys
import logging

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   stream=sys.stdout)
logger = logging.getLogger("wsgi")

logger.info("Starting WSGI application initialization")

try:
    from attendance_api import app
    logger.info("Successfully imported app from attendance_api")
except Exception as e:
    logger.error(f"Error importing app: {e}")
    import traceback
    logger.error(traceback.format_exc())
    raise

if __name__ == "__main__":
    logger.info("Running app directly through wsgi.py")
    app.run() 