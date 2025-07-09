#!/usr/bin/env python3
"""
Simple wrapper to run agents with correct Python paths
"""

import os
import sys
import importlib.util
import argparse

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Parse arguments
parser = argparse.ArgumentParser(description='Run an agent with correct paths')
parser.add_argument('agent_path', help='Path to agent script (e.g., main_pc_code/agents/system_digital_twin.py)')
parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode')
parser.add_argument('--debug', action='store_true', help='Enable debug logging')
args = parser.parse_args()

# Set environment variables
os.environ['PYTHONPATH'] = project_root
if args.debug:
    os.environ['LOG_LEVEL'] = 'DEBUG'

print(f"Running agent: {args.agent_path}")
print(f"Project root: {project_root}")
print(f"Python path: {sys.path}")

# Import and run the agent module
try:
    # Load the module from file path
    agent_path = args.agent_path
    if not os.path.exists(agent_path):
        print(f"Error: Agent file not found: {agent_path}")
        sys.exit(1)
        
    module_name = os.path.basename(agent_path).replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, agent_path)
    
    if spec is None:
        print(f"Error: Could not create spec from file location: {agent_path}")
        sys.exit(1)
    
    module = importlib.util.module_from_spec(spec)
    
    # Add dry-run argument to sys.argv if specified
    if args.dry_run and '--dry-run' not in sys.argv:
        sys.argv.append('--dry-run')
    
    # Execute the module
    if spec.loader is None:
        print(f"Error: Module loader is None for {agent_path}")
        sys.exit(1)
        
    spec.loader.exec_module(module)
    
except Exception as e:
    print(f"Error running agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1) 