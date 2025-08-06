#!/usr/bin/env python3
"""
PC2 Cross-Machine Automation Script
---------------------------------
Master script that runs both the cross-machine compliance fixer and
functionality restoration to ensure PC2 agents are both compliant and functional.

This script:
1. Runs the cross-machine compliance fixer
2. Runs the functionality restoration script
3. Generates a comprehensive report
"""

import os
import sys
import logging
import subprocess
import datetime
from pathlib import Path
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pc2_cross_machine_automation")

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXER_SCRIPT = PROJECT_ROOT / 'scripts' / 'pc2_cross_machine_fixer.py'
RESTORE_SCRIPT = PROJECT_ROOT / 'scripts' / 'pc2_restore_functionality.py'

def run_script(script_path: Path) -> bool:
    """Run a Python script and return whether it was successful."""
    logger.info(f"Running {script_path.name}...")
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Log the output
        for line in result.stdout.splitlines():
            logger.info(f"[{script_path.name}] {line}")
        
        logger.info(f"Successfully ran {script_path.name}")
        return True
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running {script_path.name}: {e}")
        
        # Log the error output
        for line in e.stdout.splitlines():
            logger.info(f"[{script_path.name}] {line}")
        for line in e.stderr.splitlines():
            logger.error(f"[{script_path.name}] {line}")
        
        return False

def generate_report(fixer_success: bool, restore_success: bool) -> Path:
    """Generate a comprehensive report."""
    report_path = PROJECT_ROOT / 'scripts' / f'pc2_automation_report_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"PC2 Cross-Machine Automation Report\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"Cross-Machine Compliance Fixer: {'SUCCESS' if fixer_success else 'FAILED'}\n")
        f.write(f"Functionality Restoration: {'SUCCESS' if restore_success else 'FAILED'}\n\n")
        
        f.write(f"Overall Status: {'SUCCESS' if fixer_success and restore_success else 'PARTIAL SUCCESS' if fixer_success or restore_success else 'FAILED'}\n\n")
        
        f.write("Next Steps:\n")
        if not fixer_success:
            f.write("- Run the cross-machine fixer script manually to fix any issues\n")
        if not restore_success:
            f.write("- Run the functionality restoration script manually to fix any issues\n")
        if fixer_success and restore_success:
            f.write("- All agents have been successfully fixed and functionality restored\n")
            f.write("- Test the agents to ensure they work correctly\n")
        
        f.write("\nRecommendations:\n")
        f.write("1. Check the logs for any specific errors\n")
        f.write("2. Manually inspect any agents that failed to be fixed\n")
        f.write("3. Run health checks on all agents to verify functionality\n")
    
    logger.info(f"Report written to {report_path}")
    return report_path

def main():
    """Main function to run the automation."""
    logger.info("Starting PC2 Cross-Machine Automation")
    
    # Check if scripts exist
    if not FIXER_SCRIPT.exists():
        logger.error(f"Fixer script not found: {FIXER_SCRIPT}")
        return
    
    if not RESTORE_SCRIPT.exists():
        logger.error(f"Restore script not found: {RESTORE_SCRIPT}")
        return
    
    # Run the fixer script
    fixer_success = run_script(FIXER_SCRIPT)
    
    # Run the restore script
    restore_success = run_script(RESTORE_SCRIPT)
    
    # Generate report
    report_path = generate_report(fixer_success, restore_success)
    
    # Print summary
    logger.info("\n" + "=" * 50)
    logger.info("PC2 Cross-Machine Automation Summary")
    logger.info("=" * 50)
    logger.info(f"Cross-Machine Compliance Fixer: {'SUCCESS' if fixer_success else 'FAILED'}")
    logger.info(f"Functionality Restoration: {'SUCCESS' if restore_success else 'FAILED'}")
    logger.info(f"Overall Status: {'SUCCESS' if fixer_success and restore_success else 'PARTIAL SUCCESS' if fixer_success or restore_success else 'FAILED'}")
    logger.info(f"Report: {report_path}")
    logger.info("=" * 50)

if __name__ == "__main__":
    main() 