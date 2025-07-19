#!/usr/bin/env python3
"""
Check if UnifiedMemoryReasoningAgent is registered with SystemDigitalTwin
"""

import os
import sys
import json
import zmq
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import service discovery client
from main_pc_code.utils.service_discovery_client import discover_service

# ANSI color codes for terminal output
COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BLUE": "\033[94m",
    "END": "\033[0m",
    "BOLD": "\033[1m"
}

def main():
    print(f"{COLORS['BOLD']}Checking UnifiedMemoryReasoningAgent Registration{COLORS['END']}")
    print()
    
    try:
        # Use the service discovery client to discover UnifiedMemoryReasoningAgent
        response = discover_service("UnifiedMemoryReasoningAgent")
        
        print(f"Discovery response status: {response.get('status', 'UNKNOWN')}")
        
        if response.get("status") == "SUCCESS":
            print(f"{COLORS['GREEN']}✓ UnifiedMemoryReasoningAgent is registered!{COLORS['END']}")
            service_info = response.get("payload", {})
            print("\nService Information:")
            print(json.dumps(service_info, indent=2))
            return 0
        else:
            print(f"{COLORS['RED']}✗ UnifiedMemoryReasoningAgent is not registered{COLORS['END']}")
            print(f"Error: {response.get('message', 'Unknown error')}")
            return 1
            
    except Exception as e:
        print(f"{COLORS['RED']}✗ Error checking registration: {e}{COLORS['END']}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 