#!/usr/bin/env python3

import os
import sys

# Set up the Python path to include the project root
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import and run the agent
if __name__ == "__main__":
    try:
        # Change to the directory containing the script
        os.chdir(os.path.join(project_root, "main_pc_code/agents"))

        # Import and run the agent
        from main_pc_code.agents.system_digital_twin import SystemDigitalTwinAgent

        agent = SystemDigitalTwinAgent()
        agent.run()
    except KeyboardInterrupt:
        print("Shutting down agent...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred: {e}")
        traceback.print_exc()
