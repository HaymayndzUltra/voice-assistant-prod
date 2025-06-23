#!/usr/bin/env python3
"""
Service Discovery Fix Verification Test

This script tests the fixed service discovery mechanism by:
1. Starting SystemDigitalTwin with detailed logging
2. Starting UnifiedMemoryReasoningAgent
3. Verifying that successful registration occurs
"""

import os
import sys
import subprocess
import time
import logging
import signal
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Terminal colors
COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BLUE": "\033[94m",
    "PURPLE": "\033[95m",
    "CYAN": "\033[96m",
    "BOLD": "\033[1m",
    "END": "\033[0m"
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=f'{COLORS["BLUE"]}%(asctime)s{COLORS["END"]} - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("ServiceDiscoveryTest")

def print_section(title):
    """Print a section title."""
    print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{title.center(80)}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")

def start_agent(module_path, log_file=None, secure=False, env_vars=None):
    """
    Start an agent process and return the process object.
    
    Args:
        module_path: Python module path to run (e.g. "main_pc_code.agents.system_digital_twin")
        log_file: Path to log file (if None, logging to stdout/stderr)
        secure: Whether to enable secure ZMQ
        env_vars: Dictionary of additional environment variables
        
    Returns:
        Process object
    """
    # Set environment variables
    env = os.environ.copy()
    env["SECURE_ZMQ"] = "1" if secure else "0"
    env["PYTHONUNBUFFERED"] = "1"  # Unbuffered output
    
    # Add any additional environment variables
    if env_vars:
        env.update(env_vars)
    
    # Prepare command
    cmd = [sys.executable, "-m", module_path]
    
    # Prepare file output redirection if specified
    if log_file:
        log_path = os.path.join(project_root, log_file)
        output = open(log_path, "w")
    else:
        output = subprocess.PIPE
    
    # Start process
    logger.info(f"Starting {module_path} with secure ZMQ {'enabled' if secure else 'disabled'}")
    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=output,
        stderr=output if log_file else subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1  # Line buffered
    )
    
    return process

def tail_logs(sdt_log_file, umr_log_file, duration=10):
    """
    Tail and display the log files for a specified duration.
    
    Args:
        sdt_log_file: Path to SDT log file
        umr_log_file: Path to UMR log file
        duration: Duration in seconds to tail the logs
    """
    sdt_path = os.path.join(project_root, sdt_log_file)
    umr_path = os.path.join(project_root, umr_log_file)
    
    # Start the tail processes
    sdt_tail = subprocess.Popen(["tail", "-f", sdt_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    umr_tail = subprocess.Popen(["tail", "-f", umr_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    try:
        print_section("LIVE LOG OUTPUT")
        start_time = time.time()
        while time.time() - start_time < duration:
            # Check SDT log
            try:
                sdt_line = sdt_tail.stdout.readline().strip()
                if sdt_line:
                    print(f"{COLORS['CYAN']}[SDT]{COLORS['END']} {sdt_line}")
            except:
                pass
                
            # Check UMR log
            try:
                umr_line = umr_tail.stdout.readline().strip()
                if umr_line:
                    print(f"{COLORS['PURPLE']}[UMR]{COLORS['END']} {umr_line}")
            except:
                pass
                
            # Exit earlier if registration is successful
            if "Successfully registered with service discovery" in umr_line:
                print(f"{COLORS['GREEN']}Registration successful! Stopping log tail...{COLORS['END']}")
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        # Stop the tail processes
        sdt_tail.terminate()
        umr_tail.terminate()

def check_logs_for_success(sdt_log_file, umr_log_file):
    """
    Check log files for successful registration.
    
    Args:
        sdt_log_file: Path to SDT log file
        umr_log_file: Path to UMR log file
        
    Returns:
        (bool, str): Success status and diagnostics message
    """
    sdt_path = os.path.join(project_root, sdt_log_file)
    umr_path = os.path.join(project_root, umr_log_file)
    
    # Check UMR log for registration success
    with open(umr_path, 'r') as f:
        umr_content = f.read()
        if "Successfully registered with service discovery" in umr_content:
            return True, "Registration successful according to UMR log"
    
    # Check SDT log for registration receipt
    with open(sdt_path, 'r') as f:
        sdt_content = f.read()
        if "Registered service: UnifiedMemoryReasoningAgent" in sdt_content:
            return True, "Registration received according to SDT log"
    
    # Check for common errors
    failure_reasons = []
    
    if "Request to SystemDigitalTwin timed out" in umr_content:
        failure_reasons.append("Connection timeout")
    
    if "Error configuring secure ZMQ" in sdt_content or "Error configuring secure ZMQ" in umr_content:
        failure_reasons.append("ZMQ security configuration error")
    
    if "Failed to parse as JSON" in sdt_content:
        failure_reasons.append("JSON parsing error in SystemDigitalTwin")
    
    if len(failure_reasons) > 0:
        return False, f"Registration failed due to: {', '.join(failure_reasons)}"
    else:
        return False, "Registration failed for unknown reasons"

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test and verify the service discovery fix")
    parser.add_argument("--secure", action="store_true", help="Enable secure ZMQ")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    # Set log levels
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Log file paths
    sdt_log_file = "logs/test_sdt_fix.log"
    umr_log_file = "logs/test_umr_fix.log"
    
    # Print header
    print_section("SERVICE DISCOVERY FIX VERIFICATION TEST")
    print(f"Secure ZMQ: {COLORS['GREEN'] if args.secure else COLORS['RED']}{args.secure}{COLORS['END']}")
    print(f"Debug mode: {COLORS['CYAN'] if args.debug else COLORS['RED']}{args.debug}{COLORS['END']}")
    print(f"SDT log file: {sdt_log_file}")
    print(f"UMR log file: {umr_log_file}")
    
    # Make sure any previous processes are killed
    subprocess.run("pkill -f 'python.*-m.*system_digital_twin' || true", shell=True)
    subprocess.run("pkill -f 'python.*-m.*UnifiedMemoryReasoningAgent' || true", shell=True)
    time.sleep(1)
    
    # Start the agents
    sdt_process = None
    umr_process = None
    
    try:
        # Start SystemDigitalTwin
        sdt_process = start_agent(
            "main_pc_code.agents.system_digital_twin", 
            log_file=sdt_log_file, 
            secure=args.secure
        )
        time.sleep(2)  # Wait for SDT to start
        
        # Start UnifiedMemoryReasoningAgent with forced local mode
        umr_env = {
            "MAINPC_IP": "127.0.0.1",  # Force localhost connections for MainPC
            "PC2_IP": "127.0.0.1",     # Force localhost connections for PC2
            "FORCE_LOCAL_SDT": "1"     # Force local SDT mode
        }
        
        # Enable debug logging if requested
        if args.debug:
            umr_env["LOG_LEVEL"] = "DEBUG"
        
        umr_process = start_agent(
            "pc2_code.agents.UnifiedMemoryReasoningAgent", 
            log_file=umr_log_file, 
            secure=args.secure,
            env_vars=umr_env
        )
        
        # Tail and display logs
        tail_logs(sdt_log_file, umr_log_file, duration=10)  # Increased duration for more logs
        
        # Check logs for success
        success, message = check_logs_for_success(sdt_log_file, umr_log_file)
        
        # If the first check failed, let's add some manual diagnostics
        if not success:
            print("\nPerforming additional diagnostics...")
            # Check if SystemDigitalTwin is properly bound
            sdt_bound = False
            with open(sdt_log_file, 'r') as f:
                if "Successfully bound to tcp://0.0.0.0:7120" in f.read():
                    sdt_bound = True
            
            print(f"- SystemDigitalTwin socket binding: {COLORS['GREEN'] if sdt_bound else COLORS['RED']}{sdt_bound}{COLORS['END']}")
            
            # Check network configuration issues
            wrong_ip_config = False
            with open(umr_log_file, 'r') as f:
                if "doesn't match any configured machine IP" in f.read():
                    wrong_ip_config = True
            
            print(f"- Network configuration issues: {COLORS['RED'] if wrong_ip_config else COLORS['GREEN']}{wrong_ip_config}{COLORS['END']}")
            
            # Test direct connection with netcat
            print("- Testing direct connection to port 7120: ", end='')
            try:
                # Use a quick connection test to port 7120
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', 7120))
                if result == 0:
                    print(f"{COLORS['GREEN']}SUCCESS{COLORS['END']}")
                else:
                    print(f"{COLORS['RED']}FAILED (port likely closed or blocked){COLORS['END']}")
                s.close()
            except Exception as e:
                print(f"{COLORS['RED']}ERROR: {e}{COLORS['END']}")
        
        print_section("TEST RESULTS")
        if success:
            print(f"{COLORS['GREEN']}✓ SUCCESS: {message}{COLORS['END']}")
            print("\nLog analysis shows successful registration between:")
            print(f"  → SystemDigitalTwin (Server)")
            print(f"  → UnifiedMemoryReasoningAgent (Client)")
            print(f"\nThe service discovery fix has been verified!")
            return 0
        else:
            print(f"{COLORS['RED']}✗ FAILURE: {message}{COLORS['END']}")
            print("\nPlease check the log files for more details:")
            print(f"  → {sdt_log_file}")
            print(f"  → {umr_log_file}")
            return 1
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1
    except Exception as e:
        print(f"{COLORS['RED']}Error running test: {e}{COLORS['END']}")
        return 1
    finally:
        # Clean up processes
        if sdt_process:
            sdt_process.terminate()
        if umr_process:
            umr_process.terminate()
        time.sleep(1)
        
if __name__ == "__main__":
    sys.exit(main()) 