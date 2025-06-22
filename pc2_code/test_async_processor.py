#!/usr/bin/env python3
"""
Test script for AsyncProcessor agent validation
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

def test_async_processor():
    """Test AsyncProcessor agent for stability"""
    print("=== Testing AsyncProcessor Agent ===")
    print("Starting AsyncProcessor...")
    
    try:
        # Import the agent
        from async_processor import AsyncProcessor
        
        # Create agent instance
        agent = AsyncProcessor()
        
        # Start the agent in a separate thread
        agent_thread = threading.Thread(target=agent.run, daemon=True)
        agent_thread.start()
        
        print("AsyncProcessor started successfully")
        print("Running for 10 seconds to validate stability...")
        
        # Wait for 10 seconds
        time.sleep(10)
        
        # Check if agent is still running
        if agent_thread.is_alive():
            print("SUCCESS: AsyncProcessor validation SUCCESS")
            print("Agent ran for 10+ seconds without crashing")
            return True
        else:
            print("FAILED: AsyncProcessor validation FAILED")
            print("Agent thread stopped unexpectedly")
            return False
            
    except Exception as e:
        print(f"FAILED: AsyncProcessor validation FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_async_processor()
    sys.exit(0 if success else 1) 