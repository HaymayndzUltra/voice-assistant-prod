#!/usr/bin/env python3
import yaml
import json

# Analyze MainPC config
try:
    with open('main_pc_code/config/startup_config.yaml', 'r') as f:
        mainpc = yaml.safe_load(f)
    
    print("=== MainPC Agent Groups ===")
    groups = mainpc.get('agent_groups', {})
    for group_name, agents in groups.items():
        if agents:
            print(f"{group_name}: {len(agents)} agents")
        else:
            print(f"{group_name}: (empty)")
    
    # Analyze PC2 config
    with open('pc2_code/config/startup_config.yaml', 'r') as f:
        pc2 = yaml.safe_load(f)
    
    print("\n=== PC2 Agents ===")
    agents = pc2.get('agents', [])
    print(f"Total agents: {len(agents)}")
    
    # Show first few PC2 agents
    print("\nFirst 10 PC2 agents:")
    for i, agent in enumerate(agents[:10]):
        if isinstance(agent, dict):
            print(f"  {i+1}. {agent.get('name', 'Unknown')}")
        else:
            print(f"  {i+1}. {agent}")
            
except Exception as e:
    print(f"Error: {e}")
