#!/usr/bin/env python3
"""
Simple script to run HealthMonitor agent from PC2
"""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))

# Override arguments to prevent parsing issues
sys.argv = [sys.argv[0]]

# Import after setting paths
from pc2_code.agents.health_monitor import HealthMonitorAgent

if __name__ == "__main__":
    print("Starting HealthMonitorAgent from PC2...")
    agent = HealthMonitorAgent()
    print(f"Agent initialized on port {agent.port}")
    try:
        agent.run()
    except KeyboardInterrupt:
        print("Agent stopped by user")
    except Exception as e:
        print(f"Error running agent: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Cleaning up...")
        agent.cleanup() 