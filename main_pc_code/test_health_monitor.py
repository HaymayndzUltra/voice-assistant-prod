#!/usr/bin/env python3
import os
import sys
import logging

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Test 1: Log directory creation
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
print(f"✓ Log directory '{log_dir}' created successfully")

# Test 2: Log file creation
log_file = os.path.join(log_dir, str(PathManager.get_logs_dir() / "health_monitor.log"))
try:
    with open(log_file, 'w') as f:
        f.write('Test log entry\n')
    print(f"✓ Log file '{log_file}' created successfully")
except Exception as e:
    print(f"✗ Failed to create log file: {e}")
    sys.exit(1)

# Test 3: Logging configuration
try:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger('TestHealthMonitor')
    logger.info('Test log message')
    print("✓ Logging configuration successful")
except Exception as e:
    print(f"✗ Failed to configure logging: {e}")
    sys.exit(1)

print("\nAll tests passed successfully!") 