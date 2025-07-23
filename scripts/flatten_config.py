#!/usr/bin/env python3
import sys
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / 'main_pc_code' / 'config' / 'startup_config.yaml'

def flatten_config():
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
    
    agents = []
    agent_groups = config.get('agent_groups', {})
    for group in agent_groups.values():
        for agent_name, agent_cfg in group.items():
            agent_cfg['name'] = agent_name
            agents.append(agent_cfg)
    
    # Output flattened list
    print(yaml.safe_dump({'agents': agents}))

if __name__ == '__main__':
    flatten_config() 