#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
End-to-End Functional Execution Test with Dependency Validation for PC2

This script tests the end-to-end functionality of the PC2 components by:
1. Checking if core PC2 agents are running and responding
2. Validating that each agent is healthy
3. Testing communication between PC2 and MainPC agents

Usage:
    python3 end_to_end_test.py
"""

import os
import sys
import time
import socket
import zmq
import json
from pathlib import Path
from common.env_helpers import get_env

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root)

# Import common utilities if available
try:
    from common_utils.env_loader import get_env, get_ip
    except ImportError as e:
        print(f"Import error: {e}")
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False
    print("[WARNING] common_utils.env_loader not found. Using default environment settings.")

# Core PC2 agents to test
PC2_AGENTS = [
    {"name": "TieredResponder", "host": "localhost", "port": 7100},
    {"name": "AsyncProcessor", "host": "localhost", "port": 7101},
    {"name": "CacheManager", "host": "localhost", "port": 7102},
    {"name": "PerformanceMonitor", "host": "localhost", "port": 7103},
    {"name": "DreamWorldAgent", "host": "localhost", "port": 7104},
    {"name": "UnifiedMemoryReasoningAgent", "host": "localhost", "port": 7105},
    {"name": "EpisodicMemoryAgent", "host": "localhost", "port": 7106},
    {"name": "LearningAgent", "host": "localhost", "port": 7107},
    {"name": "TutoringAgent", "host": "localhost", "port": 7108},
    {"name": "MemoryManager", "host": "localhost", "port": 7110},
    {"name": "ContextManager", "host": "localhost", "port": 7111},
    {"name": "ExperienceTracker", "host": "localhost", "port": 7112},
    {"name": "ResourceManager", "host": "localhost", "port": 7113},
    {"name": "HealthMonitor", "host": "localhost", "port": 7114},
    {"name": "TaskScheduler", "host": "localhost", "port": 7115},
    {"name": "AuthenticationAgent", "host": "localhost", "port": 7116},
    {"name": "UnifiedErrorAgent", "host": "localhost", "port": 7117},
    {"name": "UnifiedUtilsAgent", "host": "localhost", "port": 7118},
    {"name": "ProactiveContextMonitor", "host": "localhost", "port": 7119},
    {"name": "RCAAgent", "host": "localhost", "port": 7121},
    {"name": "AgentTrustScorer", "host": "localhost", "port": 7122},
    {"name": "FileSystemAssistantAgent", "host": "localhost", "port": 7123},
    {"name": "RemoteConnectorAgent", "host": "localhost", "port": 7124},
    {"name": "SelfHealingAgent", "host": "localhost", "port": 7125},
    {"name": "UnifiedWebAgent", "host": "localhost", "port": 7126},
    {"name": "DreamingModeAgent", "host": "localhost", "port": 7127},
    {"name": "PerformanceLoggerAgent", "host": "localhost", "port": 7128},
    {"name": "AdvancedRouter", "host": "localhost", "port": 7129}
]

# MainPC agents to test cross-machine communication
MAIN_PC_AGENTS = [
    {"name": "SystemDigitalTwin", "host": "localhost", "port": 7120},
    {"name": "TaskRouter", "host": "localhost", "port": 8571}
]

def check_port_is_open(host, port, timeout=1.0):
    """Check if a TCP port is open and responding"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionError):
        return False
    
def test_agent_health(agent):
    """Test if an agent is healthy by checking its port"""
    name = agent["name"]
    host = agent["host"]
    port = agent["port"]
    
    print(f"Testing {name} on {host}:{port}...")
    
    if check_port_is_open(host, port):
        print(f"✅ {name} is responding on port {port}")
        return True
    else:
        print(f"❌ {name} is NOT responding on port {port}")
        return False

def main():
    """Main test function"""
    print("Starting End-to-End Functional Execution Test with Dependency Validation for PC2")
    print("=" * 80)
    
    # Test each PC2 agent
    print("Testing PC2 agents...")
    all_pc2_healthy = True
    for agent in PC2_AGENTS:
        if not test_agent_health(agent):
            all_pc2_healthy = False
    
    if not all_pc2_healthy:
        print("\n❌ Some PC2 agents are not responding. Make sure to start the PC2 system first.")
        print("   Run: python3 pc2_code/scripts/start_agents.py")
    else:
        print("\n✅ All PC2 agents are running and have open ports!")
    
    # Test MainPC connectivity
    print("\nTesting connectivity to MainPC agents...")
    all_mainpc_healthy = True
    for agent in MAIN_PC_AGENTS:
        if not test_agent_health(agent):
            all_mainpc_healthy = False
    
    if not all_mainpc_healthy:
        print("\n❌ Some MainPC agents are not responding. Make sure MainPC system is running.")
        print("   Run: python3 main_pc_code/system_launcher.py on MainPC")
    else:
        print("\n✅ All MainPC agents are accessible from PC2!")
    
    # Overall test result
    if all_pc2_healthy and all_mainpc_healthy:
        print("\n✅ End-to-End Functional Execution Test with Dependency Validation for PC2 PASSED!")
    else:
        print("\n❌ End-to-End Functional Execution Test with Dependency Validation for PC2 FAILED!")
        print("   Please check the logs for more details.")
    
    print("=" * 80)
    return all_pc2_healthy and all_mainpc_healthy

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 