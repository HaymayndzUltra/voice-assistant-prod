#!/usr/bin/env python3
"""
Run MainPC Agents Script
-----------------------
This script runs MainPC agents with the correct PYTHONPATH setup.
It adds the main_pc_code directory to PYTHONPATH and then executes the agents.

Usage:
    python run_mainpc_agents.py [agent_script_path]
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_agent(agent_path):
    """Run an agent with the correct PYTHONPATH"""
    # Get the absolute path to the agent script
    agent_path = Path(agent_path).resolve()
    
    # Get the main_pc_code directory
    main_pc_code_dir = Path(__file__).resolve().parent / 'main_pc_code'
    
    # Verify the agent script exists
    if not agent_path.exists():
        print(f"❌ Agent script not found: {agent_path}")
        return False
    
    # Set up the environment
    env = os.environ.copy()
    
    # Add main_pc_code to PYTHONPATH
    if 'PYTHONPATH' in env:
        env['PYTHONPATH'] = f"{main_pc_code_dir}:{env['PYTHONPATH']}"
    else:
        env['PYTHONPATH'] = str(main_pc_code_dir)
    
    print(f"Running agent: {agent_path}")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")
    
    # Execute the agent script
    try:
        # Change to the main_pc_code directory
        os.chdir(main_pc_code_dir)
        
        # Run the agent script
        process = subprocess.Popen(
            [sys.executable, str(agent_path)],
            env=env,
            cwd=main_pc_code_dir
        )
        
        # Wait for the process to complete
        process.wait()
        
        if process.returncode == 0:
            print(f"✅ Agent {agent_path.name} completed successfully")
            return True
        else:
            print(f"❌ Agent {agent_path.name} failed with return code {process.returncode}")
            return False
    
    except Exception as e:
        print(f"❌ Error running agent {agent_path.name}: {e}")
        return False

def run_core_agents():
    """Run all core MainPC agents"""
    # Core agents to run
    core_agents = [
        "src/core/task_router.py",
        "FORMAINPC/ChainOfThoughtAgent.py",
        "FORMAINPC/GOT_TOTAgent.py",
        "agents/model_manager_agent.py",
        "agents/coordinator_agent.py",
        "agents/system_digital_twin.py"
    ]
    
    # Get the main_pc_code directory
    main_pc_code_dir = Path(__file__).resolve().parent / 'main_pc_code'
    
    # Run each agent
    for agent in core_agents:
        agent_path = main_pc_code_dir / agent
        success = run_agent(agent_path)
        if not success:
            print(f"❌ Failed to run {agent}")
            return False
    
    return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run MainPC agents with correct PYTHONPATH")
    parser.add_argument("agent_path", nargs="?", help="Path to the agent script to run")
    args = parser.parse_args()
    
    if args.agent_path:
        # Run a specific agent
        success = run_agent(args.agent_path)
    else:
        # Run all core agents
        success = run_core_agents()
    
    if success:
        print("✅ All agents started successfully!")
        return 0
    else:
        print("❌ Failed to start some agents")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 