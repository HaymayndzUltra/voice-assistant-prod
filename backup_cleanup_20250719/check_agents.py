#!/usr/bin/env python3
"""
Check if all agents in startup_config.yaml exist and are compliant
"""
import yaml
import os
import sys
from pathlib import Path

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
PC2_CONFIG_PATH = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'
SCRIPTS_DIR = PROJECT_ROOT / 'scripts'

# Add scripts directory to path to import from enhanced_system_audit.py
sys.path.append(str(SCRIPTS_DIR))
try:
    from enhanced_system_audit import check_compliance
except ImportError:
    print("Error: Could not import check_compliance from enhanced_system_audit.py")
    sys.exit(1)

def check_agents():
    """Check if all agents in startup_config.yaml exist and are compliant"""
    try:
        with open(PC2_CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"Total agents in config: {len(config.get('pc2_services', []))}")
        
        missing_agents = []
        non_compliant_agents = []
        
        for agent in config.get('pc2_services', []):
            name = agent.get('name', '')
            script_path = agent.get('script_path', '')
            full_path = PROJECT_ROOT / 'pc2_code' / script_path
            
            if not os.path.exists(full_path):
                missing_agents.append(f"{name}: {script_path}")
                continue
            
            # Check compliance
            compliance_status, issues = check_compliance(str(full_path))
            if issues:
                non_compliant_agents.append(f"{name}: {', '.join(issues)}")
        
        if missing_agents:
            print("\nMissing agents:")
            for agent in missing_agents:
                print(f"  - {agent}")
        else:
            print("\nAll agents exist!")
            
        if non_compliant_agents:
            print("\nNon-compliant agents:")
            for agent in non_compliant_agents:
                print(f"  - {agent}")
        else:
            print("\nAll agents are compliant!")
            
    except Exception as e:
        print(f"Error checking agents: {e}")

if __name__ == "__main__":
    check_agents() 