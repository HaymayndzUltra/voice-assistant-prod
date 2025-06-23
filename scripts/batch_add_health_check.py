#!/usr/bin/env python3
"""
Batch Add Health Check Implementation

This script adds health check implementation to multiple agents that are missing it.
It uses the add_health_check_implementation.py script to add health check to each agent.

Usage:
    python scripts/batch_add_health_check.py
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Main PC agents that need health check implementation
MAIN_PC_AGENTS = [
    "main_pc_code/src/core/rca_agent.py",
    "main_pc_code/src/core/secure_agent_template.py",
    "main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py",
    "main_pc_code/FORMAINPC/GOT_TOTAgent.py",
    "main_pc_code/FORMAINPC/CognitiveModelAgent.py",
    "main_pc_code/FORMAINPC/LearningAdjusterAgent.py",
    "main_pc_code/FORMAINPC/LocalFineTunerAgent.py",
]

# PC2 agents that need health check implementation
PC2_AGENTS = [
    "pc2_code/agents/tutoring_service_agent.py",
    "pc2_code/agents/filesystem_assistant_agent.py",
    "pc2_code/agents/PerformanceLoggerAgent.py",
    "pc2_code/agents/remote_connector_agent.py",
]

def add_health_check_to_agent(agent_path: str) -> bool:
    """Add health check implementation to an agent."""
    print(f"Adding health check to {agent_path}...")
    
    # Check if file exists
    if not os.path.exists(agent_path):
        print(f"Error: File {agent_path} does not exist")
        return False
    
    # Run the add_health_check_implementation.py script
    try:
        subprocess.run(
            ["python3", "scripts/add_health_check_implementation.py", agent_path],
            check=True
        )
        print(f"Successfully added health check to {agent_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error adding health check to {agent_path}: {e}")
        return False

def main():
    """Main function."""
    print("Batch adding health check implementation to agents...")
    
    # Add health check to Main PC agents
    print("\nProcessing Main PC agents:")
    main_pc_success = 0
    for agent in MAIN_PC_AGENTS:
        if add_health_check_to_agent(agent):
            main_pc_success += 1
    
    # Add health check to PC2 agents
    print("\nProcessing PC2 agents:")
    pc2_success = 0
    for agent in PC2_AGENTS:
        if add_health_check_to_agent(agent):
            pc2_success += 1
    
    # Print summary
    print("\nSummary:")
    print(f"Main PC: {main_pc_success}/{len(MAIN_PC_AGENTS)} agents updated")
    print(f"PC2: {pc2_success}/{len(PC2_AGENTS)} agents updated")
    
    if main_pc_success < len(MAIN_PC_AGENTS) or pc2_success < len(PC2_AGENTS):
        print("\nSome agents could not be updated. Please check the logs above.")
        return 1
    
    print("\nAll agents successfully updated!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 