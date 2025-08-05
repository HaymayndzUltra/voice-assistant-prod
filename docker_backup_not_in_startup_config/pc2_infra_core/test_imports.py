#!/usr/bin/env python3
"""
Test imports for PC2 Infrastructure Core
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, '/app')

print("Testing PC2 Infrastructure Core imports...")

try:
    # Test ResourceManager imports
    print("1. Testing ResourceManager dependencies...")
    from common.config_manager import get_service_ip, get_service_url, get_redis_url
    print("   ✓ common.config_manager imported")
    
    from common.utils.path_manager import PathManager
    print("   ✓ common.utils.path_manager imported")
    
    from common.core.base_agent import BaseAgent
    print("   ✓ common.core.base_agent imported")
    
    from pc2_code.agents.utils.config_loader import Config
    print("   ✓ pc2_code.agents.utils.config_loader imported")
    
    from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env
    print("   ✓ common.utils.env_standardizer imported")
    
    print("2. Testing ObservabilityHub dependencies...")
    from common.utils.data_models import ErrorSeverity
    print("   ✓ common.utils.data_models imported")
    
    from common.health.standardized_health import StandardizedHealthChecker, HealthStatus
    print("   ✓ common.health.standardized_health imported")
    
    print("3. Testing external libraries...")
    import zmq
    print("   ✓ zmq imported")
    
    import yaml
    print("   ✓ yaml imported")
    
    import redis
    print("   ✓ redis imported")
    
    import fastapi
    print("   ✓ fastapi imported")

    import torch
    print("   ✓ torch imported")
    
    print("\n🎉 All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
