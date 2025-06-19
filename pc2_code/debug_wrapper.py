#!/usr/bin/env python
"""
Debug Wrapper Script
- Runs any Python script with enhanced logging and timeout protection
- Useful for troubleshooting stuck scripts
- Usage: python debug_wrapper.py your_script.py [args]
"""
import sys
import os
import time
import signal
import subprocess
import logging
from datetime import datetime

# Configure logging
log_file = f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

def signal_handler(sig, frame):
    logging.warning(f"Caught signal {sig}, shutting down...")
    sys.exit(0)

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_wrapper.py your_script.py [args]")
        sys.exit(1)

    script_path = sys.argv[1]
    script_args = sys.argv[2:]
    
    if not os.path.exists(script_path):
        logging.error(f"Script not found: {script_path}")
        sys.exit(1)
    
    # Set up signal handler for clean exit
    signal.signal(signal.SIGINT, signal_handler)
    
    # Log start of execution
    logging.info(f"Starting script: {script_path} with args: {' '.join(script_args)}")
    logging.info(f"Working directory: {os.getcwd()}")
    logging.info(f"Python executable: {sys.executable}")
    
    # Start time for timeout tracking
    start_time = time.time()
    
    # Prepare command with unbuffered output
    cmd = [sys.executable, "-u", script_path] + script_args
    
    try:
        # Run the process with output piped to both console and log
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Track if we've seen output recently
        last_output_time = time.time()
        
        # Process output in real-time
        while process.poll() is None:
            # Read one line (non-blocking)
            line = process.stdout.readline()
            if line:
                print(line, end='')  # Print to console
                logging.info(f"SCRIPT: {line.rstrip()}")
                last_output_time = time.time()
            else:
                # No output, check if we should print a heartbeat
                current_time = time.time()
                if current_time - last_output_time > 5:  # No output for 5 seconds
                    elapsed = int(current_time - start_time)
                    print(f"[DEBUG] Still running... (elapsed: {elapsed}s)", flush=True)
                    logging.info(f"Heartbeat - No output for 5 seconds. Total elapsed: {elapsed}s")
                    last_output_time = current_time
                time.sleep(0.1)  # Short sleep to prevent CPU spinning
        
        # Get final return code
        return_code = process.returncode
        logging.info(f"Script finished with return code: {return_code}")
        return return_code
        
    except Exception as e:
        logging.error(f"Error running script: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
