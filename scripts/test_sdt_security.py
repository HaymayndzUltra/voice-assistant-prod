#!/usr/bin/env python3
"""
Test SystemDigitalTwin Security

This script tests the secure ZMQ connection to SystemDigitalTwin by:
1. Starting SystemDigitalTwin in a separate process with secure ZMQ enabled
2. Running the secure_sdt_client.py to connect and register an agent
3. Verifying that the agent was successfully registered
"""

import os
import sys
import subprocess
import time
import logging
import signal
import argparse
from pathlib import Path
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("TestSDTSecurity")

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def start_system_digital_twin(secure: bool = False) -> subprocess.Popen:
    """
    Start SystemDigitalTwin in a separate process.
    
    Args:
        secure: Whether to use secure ZMQ
        
    Returns:
        The process object
    """
    logger.info(f"Starting SystemDigitalTwin with secure ZMQ {'enabled' if secure else 'disabled'}...")
    
    # Set environment variable for secure ZMQ
    env = os.environ.copy()
    env["SECURE_ZMQ"] = "1" if secure else "0"
    
    # Start the process
    process = subprocess.Popen(
        [sys.executable, "-m", "main_pc_code.agents.system_digital_twin"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Wait for it to start
    logger.info("Waiting for SystemDigitalTwin to start...")
    time.sleep(3)
    
    return process
    
def run_secure_client(secure: bool = False, register: bool = True) -> int:
    """
    Run the secure client to test the connection.
    
    Args:
        secure: Whether to use secure ZMQ
        register: Whether to register a test agent
        
    Returns:
        The exit code of the client process
    """
    logger.info(f"Running secure client with secure ZMQ {'enabled' if secure else 'disabled'}...")
    
    # Build command
    cmd = [
        sys.executable, 
        "scripts/secure_sdt_client.py",
    ]
    if secure:
        cmd.append("--secure")
    if register:
        cmd.append("--register")
        cmd.append("--agent-name")
        cmd.append("TestAgent")
    
    # Run the client
    logger.info(f"Command: {' '.join(cmd)}")
    process = subprocess.run(cmd, capture_output=True, text=True)
    
    # Log the output
    if process.stdout:
        logger.info("Client output:")
        for line in process.stdout.splitlines():
            logger.info(f"  {line}")
    
    if process.stderr:
        logger.error("Client error output:")
        for line in process.stderr.splitlines():
            logger.error(f"  {line}")
    
    # Return the exit code
    return process.returncode
    
def main():
    parser = argparse.ArgumentParser(description="Test SystemDigitalTwin security")
    parser.add_argument("--secure", action="store_true", help="Use secure ZMQ")
    parser.add_argument("--no-register", action="store_true", help="Do not register a test agent")
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 80)
    print("TEST SYSTEMDIGITALTWIN SECURITY")
    print("=" * 80)
    print(f"Secure ZMQ: {'ENABLED' if args.secure else 'DISABLED'}")
    print(f"Register Agent: {'NO' if args.no_register else 'YES'}")
    print("=" * 80)
    print()
    
    # Start SystemDigitalTwin
    sdt_process = None
    try:
        sdt_process = start_system_digital_twin(secure=args.secure)
        
        # Run the secure client
        exit_code = run_secure_client(secure=args.secure, register=not args.no_register)
        
        # Check the result
        if exit_code == 0:
            print("✅ Test completed successfully!")
        else:
            print(f"❌ Test failed with exit code {exit_code}!")
            
    except KeyboardInterrupt:
        print("Test interrupted by user")
    except Exception as e:
        print(f"Error in test: {e}")
    finally:
        # Stop SystemDigitalTwin
        if sdt_process:
            logger.info("Stopping SystemDigitalTwin...")
            sdt_process.send_signal(signal.SIGINT)
            time.sleep(2)
            if sdt_process.poll() is None:
                sdt_process.terminate()
                logger.info("SystemDigitalTwin terminated")
                
if __name__ == "__main__":
    main() 