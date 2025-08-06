#!/usr/bin/env python3
"""
PC2 Compliance Automation Script
-------------------------------
Master script that automates the process of making PC2 agents compliant with architectural standards
while preserving their original functionality.

This script:
1. Runs pc2_agents_compliance_fixer.py to fix compliance issues
2. Runs pc2_restore_functionality.py to restore any lost functionality
3. Verifies compliance and functionality are both preserved
"""

import os
import sys
import subprocess
from pathlib import Path
import logging
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger("pc2_compliance_automation")

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPLIANCE_FIXER = PROJECT_ROOT / 'scripts' / 'pc2_agents_compliance_fixer.py'
FUNCTIONALITY_RESTORE = PROJECT_ROOT / 'scripts' / 'pc2_restore_functionality.py'
ENHANCED_AUDIT = PROJECT_ROOT / 'scripts' / 'enhanced_system_audit.py'

def run_script(script_path: Path) -> bool:
    """Run a Python script and return True if successful."""
    logger.info(f"Running {script_path.name}...")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Output from {script_path.name}:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"Errors from {script_path.name}:\n{result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {script_path.name}: {e}")
        logger.error(f"Output: {e.stdout}")
        logger.error(f"Errors: {e.stderr}")
        return False

def main():
    """Main function to run the automation process."""
    logger.info("Starting PC2 compliance automation process")
    
    # Step 1: Run compliance fixer
    if not run_script(COMPLIANCE_FIXER):
        logger.error("Compliance fixing failed, aborting")
        return 1
    logger.info("Compliance fixing completed successfully")
    
    # Step 2: Run functionality restoration
    if not run_script(FUNCTIONALITY_RESTORE):
        logger.error("Functionality restoration failed")
        return 2
    logger.info("Functionality restoration completed successfully")
    
    # Step 3: Run enhanced audit to verify
    if not run_script(ENHANCED_AUDIT):
        logger.error("Final compliance verification failed")
        return 3
    
    logger.info("PC2 compliance automation completed successfully!")
    logger.info("All agents are now compliant with architectural standards and retain their original functionality.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 