import sys
import os
import logging

# Add parent directory to sys.path to allow imports from functions
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from functions.alcohol import reset_sensor_hardware

# Setup minimal logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def main():
    logger.info("=== Alcohol Sensor Hardware Reset Test ===")
    
    try:
        success = reset_sensor_hardware()
        if success:
            logger.info("RESULT: Reset function executed successfully (or skipped if no port).")
        else:
            logger.error("RESULT: Reset function failed or could not find a port.")
            
    except KeyboardInterrupt:
        logger.info("Test interrupted by user.")
    except Exception as e:
        logger.exception("An error occurred during reset test: %s", e)
    
    logger.info("=== Test Finished ===")

if __name__ == "__main__":
    main()
