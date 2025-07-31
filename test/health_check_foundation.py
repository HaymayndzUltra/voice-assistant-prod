#!/usr/bin/env python3
"""
Foundation Services Health Check
================================

Health check script for Docker container to verify all foundation services are running.
"""

import sys
import time
import requests
from typing import Dict, List

# Foundation services configuration
FOUNDATION_SERVICES = {
    'ServiceRegistry': {'port': 7200, 'health_port': 8200},
    'SystemDigitalTwin': {'port': 7220, 'health_port': 8220},
    'RequestCoordinator': {'port': 26002, 'health_port': 27002},
    'ModelManagerSuite': {'port': 7211, 'health_port': 8211},
    'VRAMOptimizerAgent': {'port': 5572, 'health_port': 6572},
    'ObservabilityHub': {'port': 9000, 'health_port': 9001},
    'UnifiedSystemAgent': {'port': 7201, 'health_port': 8201}
}

def check_port(port: int, timeout: int = 5) -> bool:
    """Check if a port is listening"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            result = s.connect_ex(('localhost', port))
            return result == 0
    except:
        return False

def check_health_endpoint(health_port: int, timeout: int = 5) -> bool:
    """Check health endpoint"""
    try:
        response = requests.get(f'http://localhost:{health_port}/health', timeout=timeout)
        return response.status_code == 200
    except:
        return False

def check_service(service_name: str, config: Dict) -> bool:
    """Check if a service is healthy"""
    port = config['port']
    health_port = config['health_port']
    
    # Check if port is listening
    if not check_port(port):
        print(f"❌ {service_name}: Port {port} not listening")
        return False
    
    # Check health endpoint
    if not check_health_endpoint(health_port):
        print(f"❌ {service_name}: Health check failed on port {health_port}")
        return False
    
    print(f"✅ {service_name}: Healthy")
    return True

def main():
    """Main health check function"""
    print("🔍 Checking Foundation Services Health...")
    
    all_healthy = True
    healthy_count = 0
    total_count = len(FOUNDATION_SERVICES)
    
    for service_name, config in FOUNDATION_SERVICES.items():
        if check_service(service_name, config):
            healthy_count += 1
        else:
            all_healthy = False
    
    print(f"\n📊 Health Summary: {healthy_count}/{total_count} services healthy")
    
    if all_healthy:
        print("✅ All foundation services are healthy!")
        sys.exit(0)
    else:
        print("❌ Some foundation services are unhealthy!")
        sys.exit(1)

if __name__ == "__main__":
    main() 