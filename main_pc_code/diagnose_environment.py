import os
import sys
import logging
from pathlib import Path

def setup_logging():
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "diagnose.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def check_environment():
    logger = setup_logging()
    
    # Check Python version
    logger.info(f"Python version: {sys.version}")
    
    # Check current working directory
    logger.info(f"Current working directory: {os.getcwd()}")
    
    # Check PYTHONPATH
    logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    # Check if we can import required modules
    try:
        import zmq
        logger.info(f"PyZMQ version: {zmq.__version__}")
    except ImportError as e:
        logger.error(f"Failed to import PyZMQ: {e}")
    
    try:
        import requests
        logger.info(f"Requests version: {requests.__version__}")
    except ImportError as e:
        logger.error(f"Failed to import requests: {e}")
    
    # Check if we can access the src directory
    src_path = Path("src")
    if src_path.exists():
        logger.info(f"src directory exists at: {src_path.absolute()}")
        logger.info(f"Contents of src directory: {list(src_path.iterdir())}")
    else:
        logger.error("src directory not found!")
    
    # Check if we can write to logs directory
    log_dir = Path("logs")
    if log_dir.exists():
        logger.info(f"logs directory exists at: {log_dir.absolute()}")
        test_file = log_dir / "test_write.log"
        try:
            test_file.write_text("Test write successful")
            logger.info("Successfully wrote to logs directory")
            test_file.unlink()
        except Exception as e:
            logger.error(f"Failed to write to logs directory: {e}")
    else:
        logger.error("logs directory not found!")

if __name__ == "__main__":
    check_environment() 