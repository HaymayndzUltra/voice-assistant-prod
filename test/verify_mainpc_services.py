#!/usr/bin/env python3
"""
MainPC Foundation Services Verification
=======================================

Verifies that all MainPC foundation services are running and healthy.
"""

import requests
import sys
import time

def check_mainpc_services():
    """Check all MainPC foundation services"""
    
    mainpc_services = {
        'ServiceRegistry': 8200,
        'SystemDigitalTwin': 8220,
        'RequestCoordinator': 27002,
        'ModelManagerSuite': 8211,
        'VRAMOptimizerAgent': 6572,
        'UnifiedSystemAgent': 8201
    }
    
    print("🔍 Verifying MainPC foundation services...")
    
    all_healthy = True
    
    for service, health_port in mainpc_services.items():
        try:
            response = requests.get(f'http://localhost:{health_port}/health', timeout=5)
            if response.status_code == 200:
                print(f'✅ {service}: Healthy')
            else:
                print(f'❌ {service}: Health check failed ({response.status_code})')
                all_healthy = False
        except Exception as e:
            print(f'❌ {service}: Connection error - {e}')
            all_healthy = False
    
    if all_healthy:
        print('🎉 All MainPC foundation services are healthy!')
        return True
    else:
        print('❌ Some MainPC foundation services are unhealthy!')
        return False

if __name__ == "__main__":
    success = check_mainpc_services()
    sys.exit(0 if success else 1) 