#!/usr/bin/env python3
"""
Script to verify that all agents have Error Bus integration.
This script will:
1. Read the startup configuration files to identify active agents
2. Check if each agent has Error Bus connection code
3. Generate a report of agents with and without Error Bus integration
"""

import os
import re
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Set

# Define patterns to look for in agent files
ERROR_BUS_PATTERNS = [
    r"error_bus_port\s*=\s*\d+",
    r"error_bus_host\s*=\s*os\.environ\.get\(['\"]PC2_IP['\"]",
    r"error_bus_endpoint\s*=\s*f['\"]tcp://",
    r"error_bus_pub\s*=\s*self\.context\.socket\(zmq\.PUB\)",
    r"error_bus_pub\.connect\(.*?\)",
    r"report_error\s*\([^)]*\)"
]

# Define agent directories to scan
AGENT_DIRS = [
    "main_pc_code/agents",
    "main_pc_code/src",
    "pc2_code/agents",
    "pc2_code/src"
]

# Define startup config files
STARTUP_CONFIG_FILES = [
    "main_pc_code/config/startup_config.yaml",
    "pc2_code/config/startup_config.yaml"
]

def load_startup_config(config_path: str) -> Dict:
    """Load a startup configuration file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {config_path}: {e}")
        return {}

def get_active_agents() -> List[Dict[str, Any]]:
    """Get a list of all active agents from startup configs."""
    agents = []
    
    for config_file in STARTUP_CONFIG_FILES:
        if not os.path.exists(config_file):
            continue
            
        config = load_startup_config(config_file)
        if not config:
            continue
            
        # Extract agents from different sections
        for section_name, section in config.items():
            if isinstance(section, list) and section_name.endswith('_agents'):
                for agent in section:
                    if isinstance(agent, dict) and 'name' in agent and 'script' in agent:
                        # Get the absolute path to the script
                        script_path = agent['script']
                        if script_path.startswith('src/') or script_path.startswith('agents/'):
                            base_dir = os.path.dirname(os.path.dirname(config_file))
                            script_path = os.path.join(base_dir, script_path)
                        
                        agents.append({
                            'name': agent['name'],
                            'script_path': script_path
                        })
    
    return agents

def find_all_agent_files() -> List[str]:
    """Find all potential agent files in the codebase."""
    agent_files = []
    
    for dir_path in AGENT_DIRS:
        if not os.path.exists(dir_path):
            continue
            
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    agent_files.append(file_path)
    
    return agent_files

def check_file_for_error_bus(file_path: str) -> Dict[str, Any]:
    """Check if a file has Error Bus integration."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except Exception as e:
        return {
            'file_path': file_path,
            'has_error_bus': False,
            'error': str(e)
        }
    
    # Check if the file has agent class
    class_match = re.search(r'class\s+(\w+)\(.*?BaseAgent.*?\):', content, re.DOTALL)
    if not class_match:
        return {
            'file_path': file_path,
            'has_error_bus': False,
            'reason': 'Not an agent class (no BaseAgent)'
        }
    
    agent_name = class_match.group(1)
    
    # Check for error bus patterns
    missing_patterns = []
    for pattern in ERROR_BUS_PATTERNS:
        if not re.search(pattern, content):
            missing_patterns.append(pattern)
    
    has_error_bus = len(missing_patterns) == 0
    
    return {
        'file_path': file_path,
        'agent_name': agent_name,
        'has_error_bus': has_error_bus,
        'missing_patterns': missing_patterns if not has_error_bus else []
    }

def main():
    """Main function to verify Error Bus integration."""
    print("Scanning for agent files...")
    agent_files = find_all_agent_files()
    print(f"Found {len(agent_files)} potential agent files")
    
    # Get active agents from startup configs
    active_agents = get_active_agents()
    active_agent_paths = {agent['script_path'] for agent in active_agents}
    
    # Check each file for Error Bus integration
    results = []
    for file_path in agent_files:
        result = check_file_for_error_bus(file_path)
        results.append(result)
    
    # Separate active agents
    active_results = []
    inactive_results = []
    
    for result in results:
        if result.get('has_error_bus') is False and 'agent_name' in result:
            # Check if this is an active agent
            is_active = any(os.path.normpath(result['file_path']).endswith(os.path.normpath(path)) 
                            for path in active_agent_paths)
            
            if is_active:
                active_results.append(result)
            else:
                inactive_results.append(result)
    
    # Print report
    print("\n=== ERROR BUS INTEGRATION REPORT ===")
    print(f"Total agent files checked: {len(results)}")
    print(f"Agents with Error Bus integration: {len([r for r in results if r.get('has_error_bus')])} ({len(results) - len(active_results) - len(inactive_results)})")
    print(f"Active agents missing Error Bus integration: {len(active_results)}")
    print(f"Inactive agents missing Error Bus integration: {len(inactive_results)}")
    
    if active_results:
        print("\n=== ACTIVE AGENTS MISSING ERROR BUS INTEGRATION ===")
        for result in active_results:
            print(f"- {result['agent_name']} ({result['file_path']})")
            print(f"  Missing patterns: {', '.join(result['missing_patterns'])}")
    
    # Save detailed report to file
    report = {
        'summary': {
            'total_agents': len(results),
            'with_error_bus': len([r for r in results if r.get('has_error_bus')]),
            'active_missing': len(active_results),
            'inactive_missing': len(inactive_results)
        },
        'active_missing': active_results,
        'inactive_missing': inactive_results
    }
    
    with open('error_bus_integration_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\nDetailed report saved to error_bus_integration_report.json")

if __name__ == "__main__":
    main() 