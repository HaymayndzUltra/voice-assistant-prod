#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Test UnifiedMemoryReasoningAgent with SystemDigitalTwin

This script sets up a test environment with:
1. SystemDigitalTwin running on MainPC
2. UnifiedMemoryReasoningAgent connecting to SystemDigitalTwin
"""

import os
import sys
import subprocess
import time
import logging
import signal
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
import json
import zmq

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger("TestUnifiedMemoryAgent")

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import service discovery client to get agent info
from main_pc_code.utils.service_discovery_client import discover_service
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

def format_status(status: str) -> str:
    """Format agent status with color."""
    if status == "HEALTHY":
        return f"{COLORS['GREEN']}{status}{COLORS['END']}"
    elif status == "UNHEALTHY":
        return f"{COLORS['RED']}{status}{COLORS['END']}"
    elif status == "NO_RESPONSE":
        return f"{COLORS['YELLOW']}{status}{COLORS['END']}"
    return f"{COLORS['YELLOW']}{status}{COLORS['END']}"

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
    
    # Start the process using the module directly now that it uses service discovery
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

def check_system_health(host: str = get_env("BIND_ADDRESS", "0.0.0.0"), port: int = 7120, secure: bool = False) -> Dict[str, Any]:
    """
    Check the health of the system by connecting to SystemDigitalTwin.
    
    Args:
        host: Host address of SystemDigitalTwin
        port: Port of SystemDigitalTwin
        secure: Whether to use secure ZMQ
        
    Returns:
        Dictionary with agent statuses
    """
    logger.info(f"Checking system health with secure ZMQ {'enabled' if secure else 'disabled'}...")
    
    try:
        # Set environment variable for secure ZMQ
        os.environ["SECURE_ZMQ"] = "1" if secure else "0"
        
        # Create ZMQ socket
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        
        # Set timeout
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        
        # Configure secure ZMQ if needed
        if secure:
            try:
                from main_pc_code.src.network.secure_zmq import secure_client_socket
                socket = secure_client_socket(socket)
                logger.info("Socket configured for secure communication")
            except Exception as e:
                logger.error(f"Error configuring secure ZMQ: {e}")
                return {}
        
        # Connect to SystemDigitalTwin
        target_address = f"tcp://{host}:{port}"
        logger.info(f"Connecting to SystemDigitalTwin at {target_address}...")
        socket.connect(target_address)
        
        # Send health check request
        logger.info("Requesting health status of all agents...")
        socket.send_string("GET_ALL_STATUS")
        
        # Get response
        try:
            response = socket.recv_json()
            logger.info(f"Received response with {len(response)} agents")
            
            # Print the agent statuses
            print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
            print(f"{COLORS['BOLD']}{'AGENT STATUS':^80}{COLORS['END']}")
            print(f"{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
            
            if not response:
                print(f"{COLORS['YELLOW']}No agents registered{COLORS['END']}")
            else:
                # Group agents by location
                mainpc_agents = {}
                pc2_agents = {}
                unknown_agents = {}
                
                for name, info in response.items():
                    location = info.get("location", "Unknown").upper()
                    if location == "MAINPC":
                        mainpc_agents[name] = info
                    elif location == "PC2":
                        pc2_agents[name] = info
                    else:
                        unknown_agents[name] = info
                
                # Print MainPC agents
                if mainpc_agents:
                    print(f"\n{COLORS['BOLD']}MAINPC AGENTS:{COLORS['END']}")
                    for name, info in sorted(mainpc_agents.items()):
                        status = format_status(info.get("status", "UNKNOWN"))
                        last_seen = info.get("last_seen", "N/A")
                        print(f"  {COLORS['BOLD']}{name:<30}{COLORS['END']} | Status: {status:<20} | Last Seen: {last_seen}")
                
                # Print PC2 agents
                if pc2_agents:
                    print(f"\n{COLORS['BOLD']}PC2 AGENTS:{COLORS['END']}")
                    for name, info in sorted(pc2_agents.items()):
                        status = format_status(info.get("status", "UNKNOWN"))
                        last_seen = info.get("last_seen", "N/A")
                        print(f"  {COLORS['BOLD']}{name:<30}{COLORS['END']} | Status: {status:<20} | Last Seen: {last_seen}")
                
                # Print unknown location agents
                if unknown_agents:
                    print(f"\n{COLORS['BOLD']}UNKNOWN LOCATION AGENTS:{COLORS['END']}")
                    for name, info in sorted(unknown_agents.items()):
                        status = format_status(info.get("status", "UNKNOWN"))
                        last_seen = info.get("last_seen", "N/A")
                        print(f"  {COLORS['BOLD']}{name:<30}{COLORS['END']} | Status: {status:<20} | Last Seen: {last_seen}")
                
            print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
            
            return response
            
        except zmq.error.Again:
            logger.error(f"{COLORS['RED']}Timeout waiting for response{COLORS['END']}")
            return {}
            
    except Exception as e:
        logger.error(f"Error checking system health: {e}")
        return {}
        
    finally:
        if 'socket' in locals():
            socket.close()
        if 'context' in locals():
            context.term()

def check_service_registry() -> bool:
    """
    Check the service registry for UnifiedMemoryReasoningAgent.
    
    Returns:
        True if the agent is found in the registry
    """
    logger.info("Checking service registry for UnifiedMemoryReasoningAgent...")
    
    try:
        # Discover the UnifiedMemoryReasoningAgent using service discovery
        response = discover_service("UnifiedMemoryReasoningAgent")
        
        # Print results
        print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
        print(f"{COLORS['BOLD']}{'SERVICE DISCOVERY RESULTS':^80}{COLORS['END']}")
        print(f"{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
        
        if response.get("status") == "SUCCESS":
            # Get service information
            service_info = response.get("payload", {})
            
            # Print service details
            print(f"{COLORS['GREEN']}✅ UnifiedMemoryReasoningAgent found in service registry{COLORS['END']}")
            print(f"\n{COLORS['BOLD']}Service Details:{COLORS['END']}")
            print(f"  Name:     {service_info.get('name', 'N/A')}")
            print(f"  Location: {service_info.get('location', 'N/A')}")
            print(f"  IP:       {service_info.get('ip', 'N/A')}")
            print(f"  Port:     {service_info.get('port', 'N/A')}")
            
            # Print additional information
            print(f"\n{COLORS['BOLD']}Additional Information:{COLORS['END']}")
            for key, value in service_info.items():
                if key not in ["name", "location", "ip", "port"]:
                    print(f"  {key}: {value}")
            
            print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
            return True
        else:
            print(f"{COLORS['RED']}❌ UnifiedMemoryReasoningAgent not found in service registry{COLORS['END']}")
            print(f"Error: {response.get('message', 'Unknown error')}")
            print(f"\n{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
            return False
            
    except Exception as e:
        print(f"{COLORS['RED']}❌ Error checking service registry: {e}{COLORS['END']}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test UnifiedMemoryReasoningAgent with SystemDigitalTwin")
    parser.add_argument("--secure", action="store_true", help="Use secure ZMQ")
    parser.add_argument("--host", default=get_env("BIND_ADDRESS", "0.0.0.0"), help="SystemDigitalTwin host address")
    parser.add_argument("--port", type=int, default=7120, help="SystemDigitalTwin port number")
    
    args = parser.parse_args()
    
    # Print header
    print(f"{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{'TEST UNIFIEDMEMORYREASONINGAGENT WITH SYSTEMDIGITALTWIN':^80}{COLORS['END']}")
    print(f"{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
    print(f"Secure ZMQ: {COLORS['GREEN'] if args.secure else COLORS['RED']}{args.secure}{COLORS['END']}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"{COLORS['BOLD']}{'=' * 80}{COLORS['END']}")
    print()
    
    # Start processes
    sdt_process = None
    umr_process = None
    try:
        # Start SystemDigitalTwin
        sdt_process = start_system_digital_twin(secure=args.secure)
        
        # Start UnifiedMemoryReasoningAgent
        umr_process = start_unified_memory_agent(secure=args.secure)
        
        # Wait for agents to initialize
        logger.info("Waiting for agents to initialize...")
        time.sleep(5)
        
        # Check if UnifiedMemoryReasoningAgent registered with service discovery
        if check_service_registry():
            print(f"{COLORS['GREEN']}✅ SUCCESS: UnifiedMemoryReasoningAgent successfully registered with service discovery!{COLORS['END']}")
            # Check traditional agent status too
            check_system_health(host=args.host, port=args.port, secure=args.secure)
            return 0
        else:
            print(f"{COLORS['RED']}❌ FAILURE: UnifiedMemoryReasoningAgent not registered with service discovery!{COLORS['END']}")
            return 1
            
    except KeyboardInterrupt:
        print("Test interrupted by user")
        return 0
    except Exception as e:
        print(f"{COLORS['RED']}Error in test: {e}{COLORS['END']}")
        return 1
    finally:
        # Stop processes
        print("Stopping processes...")
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