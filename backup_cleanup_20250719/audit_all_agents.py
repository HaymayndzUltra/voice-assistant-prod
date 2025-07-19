#!/usr/bin/env python3
import os
import subprocess
import yaml
import sys
from pathlib import Path

def get_agent_paths():
    """Extract all agent script paths from the startup config file."""
    with open('main_pc_code/config/startup_config.yaml', 'r') as f:
        data = yaml.safe_load(f)
    
    agent_paths = []
    for section_name, section in data.items():
        if isinstance(section, list):
            for agent in section:
                if isinstance(agent, dict) and 'script_path' in agent:
                    path = agent['script_path']
                    # Skip agents that are not in main_pc_code
                    if path.startswith('FORMAINPC/') or path.startswith('agents/_referencefolderpc2/'):
                        continue
                    
                    # Prepend main_pc_code/ if not already there
                    if not path.startswith('main_pc_code/'):
                        path = f"main_pc_code/{path}"
                    
                    # Check if the file exists
                    if os.path.exists(path):
                        agent_paths.append(path)
    
    return agent_paths

def audit_agents(agent_paths):
    """Run the audit script on all agent paths."""
    print(f"Auditing {len(agent_paths)} agents...")
    
    # Run the audit script
    cmd = ["python3", "main_pc_code/scripts/agent_audit.py", "--agent_list"] + agent_paths
    try:
        output = subprocess.check_output(cmd, universal_newlines=True)
        print(output)
    except subprocess.CalledProcessError as e:
        print(f"Error running audit: {e}")
        print(e.output)

if __name__ == "__main__":
    agent_paths = get_agent_paths()
    print(f"Found {len(agent_paths)} agents to audit.")
    audit_agents(agent_paths) 