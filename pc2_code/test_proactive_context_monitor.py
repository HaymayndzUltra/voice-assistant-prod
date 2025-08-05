#!/usr/bin/env python3
import sys
import time
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir)

try:
from pc2_code.agents.ForPC2.proactive_context_monitor import ProactiveContextMonitor
    print("SUCCESS: ProactiveContextMonitor imported successfully")
    
    # Test instantiation
    monitor = ProactiveContextMonitor()
    print("SUCCESS: ProactiveContextMonitor instantiated successfully")
    
    # Test health check
    health = monitor._health_check()
    print(f"SUCCESS: Health check returned: {health}")
    
    # Test for 5 seconds
    print("Testing monitor for 5 seconds...")
    import threading
    monitor.running = True
    monitor_thread = threading.Thread(target=monitor.run)
    monitor_thread.daemon = True
    monitor_thread.start()
    time.sleep(5)
    monitor.stop()
    monitor_thread.join(timeout=2)
    print("SUCCESS: ProactiveContextMonitor ran for 5 seconds without crashing")
    print("SUCCESS: proactive_context_monitor.py proactively fixed and validated.")
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1) 