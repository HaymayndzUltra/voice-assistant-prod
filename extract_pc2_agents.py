#!/usr/bin/env python3

import yaml

def extract_agent_paths(config_file):
    """Extract agent file paths from the PC2 startup configuration file."""
    try:
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        agent_paths = []
        for item in data.get('pc2_services', []):
            if isinstance(item, dict) and 'script_path' in item:
                agent_paths.append(item['script_path'])
        
        return agent_paths
    except Exception as e:
        print(f"Error extracting agent paths: {e}")
        return []

if __name__ == "__main__":
    config_file = "pc2_code/config/startup_config_fixed.yaml"
    agent_paths = extract_agent_paths(config_file)
    
    # Print the paths, one per line
    for path in agent_paths:
        print(path) 