#!/usr/bin/env python3
"""
Simple script to run SystemDigitalTwinAgent agent
"""

import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))

# Override arguments to prevent parsing issues
sys.argv = [sys.argv[0]]

from main_pc_code.agents.system_digital_twin import SystemDigitalTwinAgent

if __name__ == "__main__":
    print("Starting SystemDigitalTwinAgent agent...")
    agent = SystemDigitalTwinAgent()
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