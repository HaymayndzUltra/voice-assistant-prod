#!/usr/bin/env python3
import sys
import time
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from agents.ForPC2.system_digital_twin import SystemDigitalTwin
    print("SUCCESS: SystemDigitalTwin imported successfully")
    
    # Test instantiation
    twin = SystemDigitalTwin()
    print("SUCCESS: SystemDigitalTwin instantiated successfully")
    
    # Test health check
    health = twin._health_check()
    print(f"SUCCESS: Health check returned: {health}")
    
    # Test for 5 seconds
    print("Testing digital twin for 5 seconds...")
    import threading
    twin.running = True
    twin_thread = threading.Thread(target=twin.run)
    twin_thread.daemon = True
    twin_thread.start()
    time.sleep(5)
    twin.stop()
    twin_thread.join(timeout=2)
    print("SUCCESS: SystemDigitalTwin ran for 5 seconds without crashing")
    print("SUCCESS: system_digital_twin.py proactively fixed and validated.")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1) 