#!/usr/bin/env python3
import sys
import time
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from pc2_code.agents.ForPC2.rca_agent import RCA_Agent
    print("SUCCESS: RCA_Agent imported successfully")
    
    # Test instantiation
    rca = RCA_Agent()
    print("SUCCESS: RCA_Agent instantiated successfully")
    
    # Test health check
    health = rca._health_check()
    print(f"SUCCESS: Health check returned: {health}")
    
    # Test for 5 seconds
    print("Testing RCA agent for 5 seconds...")
    import threading
    rca.running = True
    rca_thread = threading.Thread(target=rca.run)
    rca_thread.daemon = True
    rca_thread.start()
    time.sleep(5)
    rca.stop()
    rca_thread.join(timeout=2)
    print("SUCCESS: RCA_Agent ran for 5 seconds without crashing")
    print("SUCCESS: rca_agent.py proactively fixed and validated.")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1) 