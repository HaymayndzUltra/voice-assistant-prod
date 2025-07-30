#!/usr/bin/env python3
"""
Test script for PerformanceMonitor agent validation
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

def test_performance_monitor():
    """Test PerformanceMonitor agent for stability"""
    print("=== Testing PerformanceMonitor Agent ===")
    print("Starting PerformanceMonitor...")
    
    try:
        # Import the agent
        from performance_monitor import PerformanceMonitor
        
        # Create agent instance
        agent = PerformanceMonitor()
        
        # Start the agent in a separate thread
        agent_thread = threading.Thread(target=agent.run, daemon=True)
        agent_thread.start()
        
        print("PerformanceMonitor started successfully")
        print("Running for 10 seconds to validate stability...")
        
        # Wait for 10 seconds
        time.sleep(10)
        
        # Check if agent is still running
        if agent_thread.is_alive():
            print("SUCCESS: PerformanceMonitor validation SUCCESS")
            print("Agent ran for 10+ seconds without crashing")
            return True
        else:
            print("FAILED: PerformanceMonitor validation FAILED")
            print("Agent thread stopped unexpectedly")
            return False
            
    except Exception as e:
        print(f"FAILED: PerformanceMonitor validation FAILED")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_performance_monitor()
    sys.exit(0 if success else 1) 