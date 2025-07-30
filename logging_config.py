"""
Logging configuration for the application.
"""

import logging
import logging.config
import json
from pathlib import Path


def setup_logging(config_path: str = 'logging_config.json'):
    """Set up logging configuration."""
    config_file = Path(config_path)
    
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        # Fallback to basic config
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    return logging.getLogger(__name__)


# Example usage
if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Logging configured successfully")
