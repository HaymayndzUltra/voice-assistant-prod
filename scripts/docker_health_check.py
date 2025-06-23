#!/usr/bin/env python3
"""
Docker Health Check Script

This script checks the health of Docker containers running the voice pipeline components.
It can be used as a healthcheck command in Docker Compose.
"""

import sys
import socket
import os
import time
import json
import logging
import argparse
import zmq
from typing import Dict, Any, Optional, List, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("docker_health_check")

def check_port(host: str, port: int, timeout: int = 5) -> bool:
    """
    Check if a TCP port is open.
    
    Args:
        host: Host to check
        port: Port to check
        timeout: Timeout in seconds
        
    Returns:
        bool: True if port is open, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Error checking port {host}:{port}: {e}")
        return False

def check_zmq_service(host: str, port: int, service_name: str, timeout: int = 5000) -> bool:
    """
    Check if a ZMQ service is responding.
    
    Args:
        host: Host of the service
        port: Port of the service
        service_name: Name of the service
        timeout: Timeout in milliseconds
        
    Returns:
        bool: True if service is responding, False otherwise
    """
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, timeout)
        socket.connect(f"tcp://{host}:{port}")
        
        # Send a health check request
        request = {
            "action": "health_check",
            "timestamp": time.time()
        }
        socket.send_json(request)
        
        # Wait for response
        response = socket.recv_json()
        socket.close()
        context.term()
        
        # Check if response is valid
        if response.get("status") == "ok":
            logger.info(f"Service {service_name} is healthy")
            return True
        else:
            logger.warning(f"Service {service_name} returned invalid response: {response}")
            return False
    except Exception as e:
        logger.error(f"Error checking ZMQ service {service_name} at {host}:{port}: {e}")
        return False

def check_system_digital_twin(host: str = "localhost", port: int = 7120) -> bool:
    """
    Check if the System Digital Twin service is healthy.
    
    Args:
        host: Host of the service
        port: Port of the service
        
    Returns:
        bool: True if service is healthy, False otherwise
    """
    return check_zmq_service(host, port, "SystemDigitalTwin")

def check_task_router(host: str = "localhost", port: int = 8571) -> bool:
    """
    Check if the Task Router service is healthy.
    
    Args:
        host: Host of the service
        port: Port of the service
        
    Returns:
        bool: True if service is healthy, False otherwise
    """
    return check_zmq_service(host, port, "TaskRouter")

def check_streaming_tts(host: str = "localhost", port: int = 5562) -> bool:
    """
    Check if the Streaming TTS service is healthy.
    
    Args:
        host: Host of the service
        port: Port of the service
        
    Returns:
        bool: True if service is healthy, False otherwise
    """
    return check_zmq_service(host, port, "StreamingTtsAgent")

def check_tts(host: str = "localhost", port: int = 5563) -> bool:
    """
    Check if the TTS service is healthy.
    
    Args:
        host: Host of the service
        port: Port of the service
        
    Returns:
        bool: True if service is healthy, False otherwise
    """
    return check_zmq_service(host, port, "TTSAgent")

def check_responder(host: str = "localhost", port: int = 5637) -> bool:
    """
    Check if the Responder service is healthy.
    
    Args:
        host: Host of the service
        port: Port of the service
        
    Returns:
        bool: True if service is healthy, False otherwise
    """
    return check_zmq_service(host, port, "ResponderAgent")

def check_interrupt_handler(host: str = "localhost", port: int = 5576) -> bool:
    """
    Check if the Interrupt Handler service is healthy.
    
    Args:
        host: Host of the service
        port: Port of the service
        
    Returns:
        bool: True if service is healthy, False otherwise
    """
    return check_zmq_service(host, port, "StreamingInterruptHandler")

def main():
    """
    Main function to check the health of a service.
    """
    parser = argparse.ArgumentParser(description="Docker Health Check Script")
    parser.add_argument("--service", type=str, required=True, help="Service to check")
    parser.add_argument("--host", type=str, default="localhost", help="Host of the service")
    parser.add_argument("--port", type=int, help="Port of the service")
    args = parser.parse_args()
    
    service = args.service.lower()
    host = args.host
    
    # Define service check functions and default ports
    service_checks = {
        "system-digital-twin": (check_system_digital_twin, 7120),
        "task-router": (check_task_router, 8571),
        "streaming-tts-agent": (check_streaming_tts, 5562),
        "tts-agent": (check_tts, 5563),
        "responder": (check_responder, 5637),
        "streaming-interrupt-handler": (check_interrupt_handler, 5576)
    }
    
    if service not in service_checks:
        logger.error(f"Unknown service: {service}")
        sys.exit(1)
    
    check_func, default_port = service_checks[service]
    port = args.port if args.port else default_port
    
    # Check if port is open first
    if not check_port(host, port):
        logger.error(f"Port {host}:{port} is not open")
        sys.exit(1)
    
    # Check service health
    if check_func(host, port):
        logger.info(f"Service {service} is healthy")
        sys.exit(0)
    else:
        logger.error(f"Service {service} is not healthy")
        sys.exit(1)

if __name__ == "__main__":
    main() 