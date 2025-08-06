#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Service Discovery Integration Test

This script tests the complete service discovery mechanism by:
1. Starting SystemDigitalTwin service
2. Starting UnifiedMemoryReasoningAgent that registers with SystemDigitalTwin
3. Verifying that the registration is successful
4. Testing service discovery by discovering the registered services
"""

import os
import sys
import subprocess
import time
import logging
import signal
import argparse
from pathlib import Path
import json
import zmq
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger("ServiceDiscoveryTest")

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import service discovery client
from main_pc_code.utils.service_discovery_client import register_service, discover_service
from common.env_helpers import get_env

# ANSI color codes for terminal output
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

def print_heading(text: str):
    """Print a section heading."""
    print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{text:^80}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")

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

def start_unified_memory_agent(secure: bool = False) -> subprocess.Popen:
    """
    Start UnifiedMemoryReasoningAgent in a separate process.
    
    Args:
        secure: Whether to use secure ZMQ
        
    Returns:
        The process object
    """
    logger.info(f"Starting UnifiedMemoryReasoningAgent with secure ZMQ {'enabled' if secure else 'disabled'}...")
    
    # Set environment variables for testing
    env = os.environ.copy()
    env["SECURE_ZMQ"] = "1" if secure else "0"
    
    # Force local IP addresses for testing
    env["MAINPC_IP"] = "localhost"
    env["PC2_IP"] = "localhost"
    
    # Start the process 
    process = subprocess.Popen(
        [sys.executable, "-m", "pc2_code.agents.UnifiedMemoryReasoningAgent"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Wait for it to start
    logger.info("Waiting for UnifiedMemoryReasoningAgent to start...")
    time.sleep(3)
    
    return process

def test_service_discovery(host: str = get_env("BIND_ADDRESS", "0.0.0.0"), secure: bool = False) -> bool:
    """
    Test the service discovery mechanism.
    
    Args:
        host: Host address
        secure: Whether to use secure ZMQ
        
    Returns:
        True if tests pass, False otherwise
    """
    # Set environment variable for secure ZMQ
    os.environ["SECURE_ZMQ"] = "1" if secure else "0"
    
    print_heading("TESTING SERVICE DISCOVERY")
    
    # Test 1: Register a test service
    print(f"\n{COLORS['BLUE']}Test 1: Register a test service{COLORS['END']}")
    try:
        test_service = {
            "name": "TestService",
            "location": "TestLocation",
            "ip": host,
            "port": 9999,
            "capabilities": ["test", "debug"]
        }
        
        response = register_service(
            name=test_service["name"],
            location=test_service["location"],
            ip=test_service["ip"],
            port=test_service["port"],
            additional_info={"capabilities": test_service["capabilities"]}
        )
        
        if response.get("status") == "SUCCESS":
            print(f"{COLORS['GREEN']}✅ Test service registered successfully{COLORS['END']}")
        else:
            print(f"{COLORS['RED']}❌ Failed to register test service: {response}{COLORS['END']}")
            return False
    except Exception as e:
        print(f"{COLORS['RED']}❌ Exception during service registration: {e}{COLORS['END']}")
        return False
    
    # Test 2: Discover the test service
    print(f"\n{COLORS['BLUE']}Test 2: Discover the test service{COLORS['END']}")
    try:
        response = discover_service("TestService")
        
        if response.get("status") == "SUCCESS":
            print(f"{COLORS['GREEN']}✅ Test service discovered successfully{COLORS['END']}")
            service_info = response.get("payload", {})
            print(f"Service info: {json.dumps(service_info, indent=2)}")
            
            # Verify service info matches what we registered
            if (service_info.get("name") == test_service["name"] and
                service_info.get("location") == test_service["location"] and
                service_info.get("ip") == test_service["ip"] and
                service_info.get("port") == test_service["port"]):
                print(f"{COLORS['GREEN']}✅ Service info matches registration data{COLORS['END']}")
            else:
                print(f"{COLORS['RED']}❌ Service info doesn't match registration data{COLORS['END']}")
                return False
        else:
            print(f"{COLORS['RED']}❌ Failed to discover test service: {response}{COLORS['END']}")
            return False
    except Exception as e:
        print(f"{COLORS['RED']}❌ Exception during service discovery: {e}{COLORS['END']}")
        return False
    
    # Test 3: Discover the UnifiedMemoryReasoningAgent
    print(f"\n{COLORS['BLUE']}Test 3: Discover UnifiedMemoryReasoningAgent{COLORS['END']}")
    try:
        response = discover_service("UnifiedMemoryReasoningAgent")
        
        if response.get("status") == "SUCCESS":
            print(f"{COLORS['GREEN']}✅ UnifiedMemoryReasoningAgent discovered successfully{COLORS['END']}")
            service_info = response.get("payload", {})
            print(f"Service info: {json.dumps(service_info, indent=2)}")
            
            # Verify key fields are present
            if all(key in service_info for key in ["name", "location", "ip", "port"]):
                print(f"{COLORS['GREEN']}✅ All required fields are present{COLORS['END']}")
            else:
                print(f"{COLORS['RED']}❌ Some required fields are missing{COLORS['END']}")
                return False
        else:
            print(f"{COLORS['RED']}❌ Failed to discover UnifiedMemoryReasoningAgent: {response}{COLORS['END']}")
            return False
    except Exception as e:
        print(f"{COLORS['RED']}❌ Exception during agent discovery: {e}{COLORS['END']}")
        return False
    
    # Test 4: Try to discover a non-existent service
    print(f"\n{COLORS['BLUE']}Test 4: Try to discover a non-existent service{COLORS['END']}")
    try:
        response = discover_service("NonExistentService")
        
        if response.get("status") == "NOT_FOUND":
            print(f"{COLORS['GREEN']}✅ Correctly returned NOT_FOUND for non-existent service{COLORS['END']}")
        else:
            print(f"{COLORS['RED']}❌ Incorrect response for non-existent service: {response}{COLORS['END']}")
            return False
    except Exception as e:
        print(f"{COLORS['RED']}❌ Exception during non-existent service discovery: {e}{COLORS['END']}")
        return False
    
    print(f"\n{COLORS['GREEN']}✅ All service discovery tests passed successfully!{COLORS['END']}")
    return True

def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Test the service discovery mechanism")
    parser.add_argument("--secure", action="store_true", help="Use secure ZMQ")
    parser.add_argument("--host", default=get_env("BIND_ADDRESS", "0.0.0.0"), help="Host address for testing")
    parser.add_argument("--skip-agents", action="store_true", help="Skip starting agents (assume they are already running)")
    
    args = parser.parse_args()
    
    # Print header
    print_heading("SERVICE DISCOVERY SYSTEM TEST")
    print(f"Secure ZMQ: {COLORS['GREEN'] if args.secure else COLORS['RED']}{args.secure}{COLORS['END']}")
    print(f"Host: {args.host}")
    print(f"Skip starting agents: {args.skip_agents}")
    print()
    
    # Start processes if not skipping
    sdt_process = None
    umr_process = None
    
    try:
        if not args.skip_agents:
            # Start SystemDigitalTwin
            sdt_process = start_system_digital_twin(secure=args.secure)
            
            # Start UnifiedMemoryReasoningAgent
            umr_process = start_unified_memory_agent(secure=args.secure)
            
            # Wait for agents to initialize
            logger.info("Waiting for agents to initialize...")
            time.sleep(5)
        
        # Run service discovery tests
        success = test_service_discovery(host=args.host, secure=args.secure)
        
        if success:
            print(f"\n{COLORS['GREEN']}🎉 Service discovery system test completed successfully!{COLORS['END']}")
            return 0
        else:
            print(f"\n{COLORS['RED']}❌ Service discovery system test failed!{COLORS['END']}")
            return 1
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 0
    except Exception as e:
        print(f"\n{COLORS['RED']}Error in test: {e}{COLORS['END']}")
        return 1
    finally:
        # Stop processes
        if not args.skip_agents:
            print("\nStopping processes...")
            if umr_process:
                umr_process.send_signal(signal.SIGINT)
                time.sleep(1)
                if umr_process.poll() is None:
                    umr_process.terminate()
            if sdt_process:
                sdt_process.send_signal(signal.SIGINT)
                time.sleep(1)
                if sdt_process.poll() is None:
                    sdt_process.terminate()
                
if __name__ == "__main__":
    sys.exit(main()) 