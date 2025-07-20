#!/usr/bin/env python3
"""
Generic health check script for PC2 agents
"""

import os
import sys
import requests
import socket
import time
from urllib.parse import urlparse

def check_port_open(host, port, timeout=5):
    """Check if a port is open and accepting connections"""
    try:
        sock = socket.create_connection((host, port), timeout)
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def check_http_health(health_url, timeout=5):
    """Check HTTP health endpoint"""
    try:
        response = requests.get(health_url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False

def main():
    """Main health check logic"""
    # Get configuration from environment variables
    agent_name = os.getenv('AGENT_NAME', 'Unknown')
    agent_port = int(os.getenv('AGENT_PORT', '7000'))
    health_check_port = int(os.getenv('HEALTH_CHECK_PORT', '8000'))
    bind_address = os.getenv('BIND_ADDRESS', '0.0.0.0')
    
    print(f"Health check for {agent_name}")
    print(f"Agent port: {agent_port}, Health port: {health_check_port}")
    
    # Convert bind address for health check
    if bind_address == '0.0.0.0':
        check_host = 'localhost'
    else:
        check_host = bind_address
    
    # Check if agent port is responding
    if not check_port_open(check_host, agent_port):
        print(f"❌ Agent port {agent_port} is not responding")
        sys.exit(1)
    
    # Check if health check port is responding
    if not check_port_open(check_host, health_check_port):
        print(f"❌ Health check port {health_check_port} is not responding")
        sys.exit(1)
    
    # Try HTTP health check if available
    health_url = f"http://{check_host}:{health_check_port}/health"
    if check_http_health(health_url):
        print(f"✅ HTTP health check passed: {health_url}")
    else:
        print(f"⚠️  HTTP health check failed, but ports are open")
    
    # Check if required directories exist
    required_dirs = ['/app/logs', '/app/data', '/app/config']
    for directory in required_dirs:
        if not os.path.exists(directory):
            print(f"❌ Required directory missing: {directory}")
            sys.exit(1)
    
    print(f"✅ Health check passed for {agent_name}")
    sys.exit(0)

if __name__ == "__main__":
    main()