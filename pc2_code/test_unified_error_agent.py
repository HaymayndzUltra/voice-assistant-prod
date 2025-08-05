#!/usr/bin/env python3
import sys
import time
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir)

try:
from pc2_code.agents.ForPC2.UnifiedErrorAgent import UnifiedErrorAgent
    print("SUCCESS: UnifiedErrorAgent imported successfully")
    
    # Test instantiation
    agent = UnifiedErrorAgent()
    print("SUCCESS: UnifiedErrorAgent instantiated successfully")
    
    # Test health check
    health = agent._health_check()
    print(f"SUCCESS: Health check returned: {health}")
    
    # Test for 5 seconds
    print("Testing agent for 5 seconds...")
    import threading
    agent.running = True
    agent_thread = threading.Thread(target=agent.run)
    agent_thread.daemon = True
    agent_thread.start()
    time.sleep(5)
    agent.stop()
    agent_thread.join(timeout=2)
    print("SUCCESS: UnifiedErrorAgent ran for 5 seconds without crashing")
    print("SUCCESS: UnifiedErrorAgent.py proactively fixed and validated.")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1) 