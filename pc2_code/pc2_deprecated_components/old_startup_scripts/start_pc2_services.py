#!/usr/bin/env python3
"""
PC2 Services Startup Script

This script automates the startup of all critical PC2 services in the correct order:
1. NLLB Translation Adapter
2. TinyLlama Service
3. Translator Agent

Features:
- Proper service dependency management
- Verification of successful startup
- Comprehensive logging
- Optional health check after startup

Usage:
    python start_pc2_services.py [--healthcheck]
"""

import subprocess
import time
import os
import sys
import argparse
import logging
import signal
import json
import zmq
import socket
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path("logs") / f"pc2_startup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("PC2StartupManager")

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Service configuration
SERVICES = [
    {
        "name": "NLLB Translation Adapter",
        "script": "agents/nllb_translation_adapter.py",
        "port": 5581,
        "startup_time": 30,  # Seconds to wait for startup (model loading takes time)
        "health_check": {
            "supported": False,
            "test_action": "translate",
            "test_payload": {
                "action": "translate", 
                "text": "Magandang umaga", 
                "source_lang": "tgl_Latn", 
                "target_lang": "eng_Latn"
            }
        }
    },
    {
        "name": "TinyLlama Service",
        "script": "agents/tinyllama_service_enhanced.py",
        "port": 5615,
        "startup_time": 10,
        "health_check": {
            "supported": True,
            "test_action": "health_check",
            "test_payload": {"action": "health_check"}
        }
    },
    {
        "name": "Translator Agent",
        "script": "agents/translator_fixed.py",
        "port": 5563,
        "startup_time": 5,
        "health_check": {
            "supported": True,
            "test_action": "health_check",
            "test_payload": {"action": "health_check"}
        }
    }
]

# Process tracking
processes = {}

def check_port_open(port, host="localhost"):
    """Check if a port is open on the local machine."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex((host, port))
    sock.close()
    return result == 0

def verify_external_binding(port):
    """Verify that a service is binding to all interfaces (0.0.0.0) and not just localhost."""
    try:
        # Get all listening sockets and their addresses
        cmd = f"netstat -ano | findstr LISTENING | findstr :{port}"
        import subprocess
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0 or not result.stdout.strip():
            logger.warning(f"Port {port} not found in netstat output, might not be listening")
            return False
            
        # Check if 0.0.0.0 appears in the output (indicates binding to all interfaces)
        if "0.0.0.0:" + str(port) in result.stdout:
            logger.info(f"Port {port} is correctly bound to 0.0.0.0 (all interfaces)")
            return True
        else:
            logger.warning(f"Port {port} may not be bound to all interfaces. Netstat output: {result.stdout.strip()}")
            return False
    except Exception as e:
        logger.error(f"Error verifying external binding for port {port}: {str(e)}")
        return False

def send_zmq_request(port, request, timeout=5000, retries=1, retry_delay=2):
    """Send a ZMQ request to the specified port with retry logic."""
    # Apply longer timeout for NLLB adapter (heavy model loading)
    if port == 5581 and timeout < 30000:
        logger.info(f"Using extended timeout (30s) for NLLB adapter on port {port}")
        timeout = 30000  # 30 seconds for NLLB
    
    for attempt in range(retries + 1):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout)
        socket.connect(f"tcp://localhost:{port}")
        
        try:
            logger.debug(f"Sending request to port {port}: {request} (attempt {attempt+1}/{retries+1})")
            socket.send_json(request)
            response = socket.recv_json()
            return response
        except zmq.error.Again:
            if attempt < retries:
                logger.warning(f"Request to port {port} timed out, retrying in {retry_delay}s... ({attempt+1}/{retries})")
                time.sleep(retry_delay)
            else:
                logger.error(f"Request to port {port} timed out after {retries+1} attempts")
                return {"status": "error", "message": "Request timed out after multiple attempts"}
        except Exception as e:
            logger.error(f"Error communicating with port {port}: {str(e)}")
            return {"status": "error", "message": f"Error: {str(e)}"}
        finally:
            socket.close()
            context.term()

def health_check_service(service, max_retries=2):
    """Perform a health check on a service with retry logic."""
    service_name = service["name"]
    port = service["port"]
    
    # Special handling for NLLB adapter which may take longer to initialize
    if "NLLB" in service_name:
        max_retries = 3  # More retries for NLLB
        retry_delay = 5  # Longer delay between retries
    else:
        retry_delay = 2
    
    # Verify port is open locally
    port_open = False
    for attempt in range(max_retries + 1):
        if check_port_open(port):
            port_open = True
            break
        elif attempt < max_retries:
            logger.warning(f"Port {port} for {service_name} not open, retrying in {retry_delay}s (attempt {attempt+1}/{max_retries})")
            time.sleep(retry_delay)
    
    if not port_open:
        logger.error(f"Health check failed: {service_name} port {port} is not open after {max_retries+1} attempts")
        return False
        
    # Verify that the service is binding to all interfaces (0.0.0.0) and not just localhost
    if not verify_external_binding(port):
        logger.error(f"Health check warning: {service_name} port {port} may not be accessible from external machines")
        # We'll continue with the health check, but log this as a warning
    
    # If service doesn't support health checks, test with the alternative method
    if not service["health_check"]["supported"]:
        test_action = service["health_check"]["test_action"]
        test_payload = service["health_check"]["test_payload"]
        
        logger.info(f"Testing {service_name} with {test_action} action")
        
        # For NLLB, use more retries and longer timeout
        if "NLLB" in service_name:
            logger.info(f"Using extended parameters for NLLB adapter health check")
            response = send_zmq_request(port, test_payload, timeout=30000, retries=2, retry_delay=5)
        else:
            response = send_zmq_request(port, test_payload, retries=1)
        
        if response.get("status") == "success":
            logger.info(f"Health check passed: {service_name} responded successfully to {test_action}")
            return True
        else:
            logger.error(f"Health check failed: {service_name} response: {response}")
            return False
    else:
        # Use health_check action
        logger.info(f"Performing health check on {service_name}")
        response = send_zmq_request(port, {"action": "health_check"}, retries=1)
        
        if response.get("status") in ["success", "ok"]:
            logger.info(f"Health check passed: {service_name} is healthy. Response: {response}")
            return True
        else:
            logger.error(f"Health check failed: {service_name} health check failed with response: {response}")
            return False

def start_service(service):
    """Start a service and verify it's running."""
    service_name = service["name"]
    script_path = service["script"]
    port = service["port"]
    startup_time = service["startup_time"]
    
    # Check if the port is already in use
    if check_port_open(port):
        logger.warning(f"Port {port} for {service_name} is already in use. Service might already be running.")
        
        # Try to health check the service
        if health_check_service(service):
            logger.info(f"{service_name} appears to be already running and healthy.")
            return True
        else:
            logger.warning(f"Port {port} is in use but {service_name} health check failed.")
            return False
    
    # Start the service
    logger.info(f"Starting {service_name}...")
    try:
        # Use subprocess.Popen to start the process without waiting for it to complete
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        processes[service_name] = process
        logger.info(f"Started {service_name} (PID: {process.pid})")
        
        # Wait for service to start up
        logger.info(f"Waiting {startup_time} seconds for {service_name} to initialize...")
        
        # Check every second if the port is open
        port_open = False
        for i in range(startup_time):
            time.sleep(1)
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"{service_name} exited prematurely with code {process.returncode}")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
            
            if check_port_open(port):
                port_open = True
                logger.info(f"{service_name} port {port} is now open after {i+1} seconds")
                break
                
        if not port_open:
            logger.error(f"Timeout waiting for {service_name} to open port {port}")
            return False
        
        # Additional wait for service to fully initialize
        time.sleep(2)
        
        # Perform health check
        return health_check_service(service)
        
    except Exception as e:
        logger.error(f"Error starting {service_name}: {str(e)}")
        return False

def stop_services():
    """Stop all running services gracefully."""
    logger.info("Stopping all services...")
    for name, process in processes.items():
        if process.poll() is None:  # Process is still running
            logger.info(f"Stopping {name} (PID: {process.pid})...")
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Stopped {name}")
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} did not terminate gracefully, killing...")
                process.kill()
                logger.info(f"Killed {name}")
            except Exception as e:
                logger.error(f"Error stopping {name}: {str(e)}")

def run_health_check():
    """Run the comprehensive health check script."""
    try:
        logger.info("Running comprehensive health check...")
        health_check_path = Path("pc2_health_check.py")
        if not health_check_path.exists():
            logger.error("Health check script not found")
            return False
        
        result = subprocess.run(
            [sys.executable, str(health_check_path)],
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info("Health check completed successfully")
        print("\nHealth Check Results:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Health check failed with exit code {e.returncode}")
        logger.error(f"STDOUT: {e.stdout}")
        logger.error(f"STDERR: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error running health check: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="PC2 Services Startup Script")
    parser.add_argument("--healthcheck", action="store_true", help="Run a comprehensive health check after startup")
    args = parser.parse_args()
    
    logger.info("Starting PC2 Services...")
    
    # Register signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        stop_services()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start each service in the defined order
    all_services_started = True
    for service in SERVICES:
        if not start_service(service):
            all_services_started = False
            logger.error(f"Failed to start {service['name']}. Aborting startup sequence.")
            stop_services()
            sys.exit(1)
        
        logger.info(f"{service['name']} started successfully")
    
    if all_services_started:
        logger.info("All PC2 services started successfully!")
        
        # Run health check if requested
        if args.healthcheck:
            run_health_check()
        
        print("\nPC2 Services Status:")
        for service in SERVICES:
            print(f"[ACTIVE] {service['name']} - Running on port {service['port']}")
        
        print("\nServices will continue running in the background.")
        print("Press Ctrl+C to stop all services.")
        
        # Keep the script running to maintain the processes
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
            stop_services()
    else:
        logger.error("Failed to start all services")
        stop_services()
        sys.exit(1)

if __name__ == "__main__":
    main()
