#!/usr/bin/env python3
"""
Validate Scanner Paths
---------------------
Test script to validate path resolution and understand the actual project structure
"""

import os
import yaml
from pathlib import Path

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_PC_CODE = PROJECT_ROOT / 'main_pc_code'
PC2_CODE = PROJECT_ROOT / 'pc2_code'
MAIN_PC_CONFIG_PATH = MAIN_PC_CODE / 'config' / 'startup_config.yaml'
PC2_CONFIG_PATH = PC2_CODE / 'config' / 'startup_config.yaml'

def test_path_resolution():
    """Test path resolution logic"""
    print("🔍 TESTING PATH RESOLUTION")
    print("=" * 50)
    
    # Test MainPC config loading
    print(f"MainPC Config Path: {MAIN_PC_CONFIG_PATH}")
    print(f"MainPC Config Exists: {MAIN_PC_CONFIG_PATH.exists()}")
    
    if MAIN_PC_CONFIG_PATH.exists():
        with open(MAIN_PC_CONFIG_PATH, 'r') as f:
            mainpc_config = yaml.safe_load(f)
        
        print(f"\nMainPC Config Keys: {list(mainpc_config.keys())}")
        
        # Test agent_groups structure
        agent_groups = mainpc_config.get('agent_groups', {})
        print(f"Agent Groups: {list(agent_groups.keys())}")
        
        # Test specific path resolution
        for group_name, group_data in agent_groups.items():
            print(f"\n--- Group: {group_name} ---")
            for agent_name, agent_data in group_data.items():
                if isinstance(agent_data, dict) and 'script_path' in agent_data:
                    script_path = agent_data.get('script_path', '')
                    print(f"  Agent: {agent_name}")
                    print(f"  Script Path: {script_path}")
                    
                    # Test different path resolution strategies
                    if script_path.startswith('main_pc_code/'):
                        relative_path = script_path.replace('main_pc_code/', '')
                        full_path = MAIN_PC_CODE / relative_path
                        print(f"  Strategy 1 (main_pc_code/): {full_path}")
                        print(f"  Strategy 1 Exists: {full_path.exists()}")
                    elif script_path.startswith('phase1_implementation/'):
                        full_path = PROJECT_ROOT / script_path
                        print(f"  Strategy 2 (phase1_implementation/): {full_path}")
                        print(f"  Strategy 2 Exists: {full_path.exists()}")
                    else:
                        full_path = MAIN_PC_CODE / script_path
                        print(f"  Strategy 3 (default): {full_path}")
                        print(f"  Strategy 3 Exists: {full_path.exists()}")
                    
                    # Test direct path
                    direct_path = PROJECT_ROOT / script_path
                    print(f"  Direct Path: {direct_path}")
                    print(f"  Direct Path Exists: {direct_path.exists()}")
                    print()

def test_pc2_config():
    """Test PC2 config structure"""
    print("\n🔍 TESTING PC2 CONFIG")
    print("=" * 50)
    
    print(f"PC2 Config Path: {PC2_CONFIG_PATH}")
    print(f"PC2 Config Exists: {PC2_CONFIG_PATH.exists()}")
    
    if PC2_CONFIG_PATH.exists():
        with open(PC2_CONFIG_PATH, 'r') as f:
            pc2_config = yaml.safe_load(f)
        
        print(f"PC2 Config Keys: {list(pc2_config.keys())}")
        
        pc2_services = pc2_config.get('pc2_services', [])
        print(f"PC2 Services Count: {len(pc2_services)}")
        
        for i, agent_data in enumerate(pc2_services[:5]):  # Test first 5
            if isinstance(agent_data, dict) and 'name' in agent_data:
                name = agent_data.get('name')
                script_path = agent_data.get('script_path', '')
                print(f"\n  Agent {i+1}: {name}")
                print(f"  Script Path: {script_path}")
                
                # Test path resolution
                if script_path.startswith('pc2_code/'):
                    relative_path = script_path.replace('pc2_code/', '')
                    full_path = PC2_CODE / relative_path
                    print(f"  Resolved Path: {full_path}")
                    print(f"  Exists: {full_path.exists()}")
                else:
                    full_path = PC2_CODE / script_path
                    print(f"  Resolved Path: {full_path}")
                    print(f"  Exists: {full_path.exists()}")

def test_observability_hub_specific():
    """Test ObservabilityHub path specifically"""
    print("\n🔍 TESTING OBSERVABILITYHUB SPECIFIC")
    print("=" * 50)
    
    script_path = "phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py"
    
    print(f"Script Path: {script_path}")
    
    # Test different resolution strategies
    strategies = [
        ("PROJECT_ROOT", PROJECT_ROOT / script_path),
        ("MAIN_PC_CODE", MAIN_PC_CODE / script_path),
        ("PC2_CODE", PC2_CODE / script_path),
    ]
    
    for strategy_name, full_path in strategies:
        print(f"\nStrategy: {strategy_name}")
        print(f"Full Path: {full_path}")
        print(f"Exists: {full_path.exists()}")
        if full_path.exists():
            print(f"File Size: {full_path.stat().st_size} bytes")

def main():
    """Main validation function"""
    print("🚀 VALIDATING SCANNER PATH RESOLUTION")
    print("=" * 60)
    
    test_path_resolution()
    test_pc2_config()
    test_observability_hub_specific()
    
    print("\n✅ VALIDATION COMPLETE")

if __name__ == "__main__":
    main() 