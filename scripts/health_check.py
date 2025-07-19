#!/usr/bin/env python3
"""
Universal Health Check Script for AI System Containers
Used by Docker HEALTHCHECK and validation scripts
"""

import sys
import zmq
import json
import time
import os
from typing import Dict, List, Optional

def check_zmq_service(host: str, port: int, timeout: int = 5) -> bool:
    """Check if ZMQ service is responding"""
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        socket.setsockopt(zmq.SNDTIMEO, timeout * 1000)
        socket.connect(f"tcp://{host}:{port}")
        
        socket.send_string("health_check")
        response = socket.recv_string()
        
        socket.close()
        context.term()
        
        return response == "OK" or "healthy" in response.lower()
    except Exception as e:
        print(f"Health check failed for {host}:{port} - {e}")
        return False

def check_container_health() -> Dict:
    """Check health of services in current container"""
    # Get service list from environment
    services = os.getenv("HEALTH_CHECK_SERVICES", "").split(",")
    
    if not services or services == [""]:
        # Default health check - just verify Python is working
        return {"status": "healthy", "services": [], "timestamp": time.time()}
    
    results = {}
    all_healthy = True
    
    for service in services:
        if ":" in service:
            name, port = service.split(":")
            port = int(port)
            healthy = check_zmq_service("localhost", port)
            results[name] = {"healthy": healthy, "port": port}
            if not healthy:
                all_healthy = False
        else:
            # Just mark as healthy if no port specified
            results[service] = {"healthy": True, "port": None}
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "services": results,
        "timestamp": time.time()
    }

def main():
    """Main health check execution"""
    if len(sys.argv) > 1:
        # Check specific service
        if ":" in sys.argv[1]:
            host, port = sys.argv[1].split(":")
            port = int(port)
        else:
            host = "localhost"
            port = int(sys.argv[1])
        
        if check_zmq_service(host, port):
            print("OK")
            sys.exit(0)
        else:
            print("FAIL")
            sys.exit(1)
    else:
        # Check container health
        health = check_container_health()
        print(json.dumps(health, indent=2))
        
        if health["status"] == "healthy":
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    main() 