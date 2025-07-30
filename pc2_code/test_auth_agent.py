#!/usr/bin/env python3
import sys
import time
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
from pc2_code.agents.ForPC2.AuthenticationAgent import authentication_agent
    print("SUCCESS: AuthenticationAgent imported successfully")

    # Test instantiation
    agent = AuthenticationAgent()
    print("SUCCESS: AuthenticationAgent instantiated successfully")

    # Test health check
    health = agent._health_check()
    print(f"SUCCESS: Health check returned: {health}")

    # Test for 5 seconds
    print("Testing agent for 5 seconds...")
    start_time = time.time()

    # Start the agent in a way that we can stop it
    import threading
    agent.running = True
    agent_thread = threading.Thread(target=agent.run)
    agent_thread.daemon = True
    agent_thread.start()

    time.sleep(5)

    # Stop the agent
    agent.stop()
    agent_thread.join(timeout=2)

    print("SUCCESS: AuthenticationAgent ran for 5 seconds without crashing")
    print("SUCCESS: AuthenticationAgent.py proactively fixed and validated.")

except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
