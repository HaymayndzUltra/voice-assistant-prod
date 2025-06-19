#!/usr/bin/env python3
"""
Test script for CacheManager agent validation
Part of PC2 Phase 1 - Core Agents Implementation
"""

import sys
import os
import time
import threading
import signal
import zmq
import json
from pathlib import Path

# Add agents directory to path
sys.path.insert(0, str(Path(__file__).parent / 'agents'))

def test_cache_manager():
    """Test CacheManager agent for stability"""
    print("=== Testing CacheManager Agent ===")
    print("Starting CacheManager...")
    
    try:
        # Import the agent
        from cache_manager import CacheManager
        
        # Create agent instance
        agent = CacheManager()
        
        # Start the agent in a separate thread
        agent_thread = threading.Thread(target=agent.run, daemon=True)
        agent_thread.start()
        
        print("CacheManager started successfully")
        print("Running for 10 seconds to validate stability...")
        
        # Wait for 10 seconds
        time.sleep(10)
        
        # Check if agent is still running
        if agent_thread.is_alive():
            print("SUCCESS: CacheManager validation SUCCESS")
            print("Agent ran for 10+ seconds without crashing")
            return True
        else:
            print("FAILED: CacheManager validation FAILED")
            print("Agent thread stopped unexpectedly")
            return False
            
    except Exception as e:
        print(f"FAILED: CacheManager validation FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_cache_manager()
    sys.exit(0 if success else 1) 