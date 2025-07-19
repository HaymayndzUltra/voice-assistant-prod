#!/usr/bin/env python3
"""
Check ports in startup_config.yaml
"""
import yaml
from pathlib import Path

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
PC2_CONFIG_PATH = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'

def check_ports():
    """Check ports in startup_config.yaml"""
    try:
        with open(PC2_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"Total agents in config: {len(config.get('pc2_services', []))}")
        print("Agent ports from startup_config.yaml:")
        print("-" * 60)
        print(f"{'Agent Name':<30} {'Port':<10} {'Health Port':<10}")
        print("-" * 60)
        
        for agent in config.get('pc2_services', []):
            name = agent.get('name', '')
            port = agent.get('port', '')
            health_port = agent.get('health_check_port', '')
            print(f"{name:<30} {port:<10} {health_port:<10}")
        
    except Exception as e:
        print(f"Error checking ports: {e}")

if __name__ == "__main__":
    check_ports() 