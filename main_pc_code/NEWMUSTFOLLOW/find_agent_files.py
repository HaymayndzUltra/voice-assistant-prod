#!/usr/bin/env python3

"""
Agent File Finder
----------------
Helps locate agent implementation files in the repository
"""

import os
import sys
import yaml
import argparse
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

def find_config_file():
    """Find the minimal system configuration file."""
    possible_paths = [
        os.path.join(SCRIPT_DIR, "minimal_system_config.yaml"),
        PathManager.join_path("config", PathManager.join_path("config", "minimal_system_config.yaml")),
        PathManager.join_path("main_pc_code", PathManager.join_path("config", "minimal_system_config.yaml")),
        PathManager.join_path("main_pc_code", "NEWMUSTFOLLOW/minimal_system_config.yaml"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Found config at: {path}")
            return path
    
    print(f"{RED}Error: Could not find minimal_system_config.yaml{RESET}")
    for path in possible_paths:
        print(f"  - {path}")
    return None

def load_config():
    """Load the MVS configuration."""
    config_path = find_config_file()
    if not config_path:
        sys.exit(1)
        
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"{RED}Error loading config: {e}{RESET}")
        sys.exit(1)

def find_files_by_pattern(root_dir, pattern):
    """Find files matching a pattern in the repository."""
    results = []
    for root, dirs, files in os.walk(root_dir):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', 'venv', 'cache']):
            continue
            
        for file in files:
            if pattern.lower() in file.lower() and file.endswith('.py'):
                results.append(os.path.join(root, file))
    return results

def find_agent_file(agent_name):
    """Find the Python file for an agent."""
    # First try direct matches in common locations
    possible_locations = [
        PathManager.join_path("main_pc_code", "agents/{agent_name}.py"),
        PathManager.join_path("main_pc_code", "src/agents/{agent_name}.py"),
        os.path.join(PROJECT_ROOT, "src", "agents", f"{agent_name}.py"),
        PathManager.join_path("pc2_code", "agents/{agent_name}.py"),
    ]
    
    for location in possible_locations:
        if os.path.exists(location):
            return location
    
    # If no direct match, search the repository
    results = find_files_by_pattern(PROJECT_ROOT, agent_name)
    return results

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Find agent files in the repository")
    parser.add_argument("--agent", help="Specific agent to find")
    parser.add_argument("--update-config", action="store_true", help="Update the config file with found paths")
    args = parser.parse_args()
    
    print(f"{BLUE}{BOLD}Agent File Finder{RESET}")
    print(f"Project root: {PROJECT_ROOT}\n")
    
    if args.agent:
        # Find a specific agent
        agent_name = args.agent
        print(f"Searching for agent: {agent_name}")
        results = find_agent_file(agent_name)
        
        if isinstance(results, str):
            print(f"[{GREEN}✓{RESET}] Found exact match: {results}")
        elif results:
            print(f"Found {len(results)} possible matches:")
            for i, path in enumerate(results, 1):
                print(f"  {i}. {path}")
        else:
            print(f"[{RED}✗{RESET}] No files found for {agent_name}")
    else:
        # Find all agents in the config
        config = load_config()
        all_agents = []
        if 'core_agents' in config:
            all_agents.extend(config['core_agents'])
        if 'dependencies' in config:
            all_agents.extend(config['dependencies'])
        
        print(f"Searching for {len(all_agents)} agents from config...\n")
        
        found_count = 0
        not_found = []
        
        for agent in all_agents:
            name = agent.get('name', 'Unknown')
            print(f"\nAgent: {BOLD}{name}{RESET}")
            
            # Check if file_path is already specified
            if 'file_path' in agent and os.path.exists(agent['file_path']):
                print(f"[{GREEN}✓{RESET}] Using specified path: {agent['file_path']}")
                found_count += 1
                continue
            
            # Try to find the file
            results = find_agent_file(name)
            
            if isinstance(results, str):
                print(f"[{GREEN}✓{RESET}] Found exact match: {results}")
                if args.update_config:
                    agent['file_path'] = results
                found_count += 1
            elif results:
                print(f"Found {len(results)} possible matches:")
                for i, path in enumerate(results, 1):
                    print(f"  {i}. {path}")
                not_found.append((name, results))
            else:
                print(f"[{RED}✗{RESET}] No files found")
                not_found.append((name, []))
        
        print(f"\n{BOLD}Summary:{RESET}")
        print(f"  Total agents: {len(all_agents)}")
        print(f"  {GREEN}Found: {found_count}{RESET}")
        print(f"  {RED}Not found or ambiguous: {len(not_found)}{RESET}")
        
        if not_found:
            print(f"\n{YELLOW}{BOLD}Agents requiring manual resolution:{RESET}")
            for name, results in not_found:
                print(f"  - {name}: {len(results)} possible matches")
        
        if args.update_config and found_count > 0:
            # Save the updated config
            config_path = find_config_file()
            try:
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
                print(f"\n{GREEN}Updated config file with found paths{RESET}")
            except Exception as e:
                print(f"\n{RED}Error updating config: {e}{RESET}")

if __name__ == "__main__":
    main() 