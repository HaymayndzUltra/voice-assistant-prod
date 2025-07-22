#!/usr/bin/env python3
"""
Comprehensive SOT Agent Import Validator
Tests all 54 MainPC agents + 27 PC2 agents for import issues
"""

import sys
import os
from pathlib import Path
import importlib.util
import traceback

# Add project root to path
sys.path.insert(0, '.')

def test_agent_import(agent_path, agent_name):
    """Test if an agent can be imported successfully"""
    try:
        spec = importlib.util.spec_from_file_location(agent_name, agent_path)
        if spec is None:
            return False, f"Could not create spec for {agent_path}"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, "Import successful"
    except Exception as e:
        return False, str(e)

def get_mainpc_sot_agents():
    """Get all MainPC SOT agents from startup_config.yaml"""
    agents = []
    try:
        with open('main_pc_code/config/startup_config.yaml', 'r') as f:
            content = f.read()
            
        # Extract script_path entries
        import re
        script_paths = re.findall(r'script_path:\s*([^\s,]+)', content)
        
        for path in script_paths:
            path = path.strip()
            if path and not path.startswith('#'):
                agents.append(path)
                
    except Exception as e:
        print(f"Error reading MainPC config: {e}")
    
    return agents

def get_pc2_sot_agents():
    """Get all PC2 SOT agents from startup_config.yaml"""
    agents = []
    try:
        with open('pc2_code/config/startup_config.yaml', 'r') as f:
            content = f.read()
            
        # Extract script_path entries  
        import re
        script_paths = re.findall(r'script_path:\s*([^\s,]+)', content)
        
        for path in script_paths:
            path = path.strip()
            if path and not path.startswith('#'):
                agents.append(path)
                
    except Exception as e:
        print(f"Error reading PC2 config: {e}")
    
    return agents

def main():
    print("🔍 SOT AGENT IMPORT VALIDATION")
    print("=" * 50)
    
    # Test MainPC agents
    print("\n�� TESTING MAINPC SOT AGENTS:")
    mainpc_agents = get_mainpc_sot_agents()
    mainpc_passed = 0
    mainpc_failed = []
    
    for agent_path in mainpc_agents:
        agent_name = Path(agent_path).stem
        success, message = test_agent_import(agent_path, agent_name)
        
        if success:
            print(f"✅ {agent_name}")
            mainpc_passed += 1
        else:
            print(f"❌ {agent_name}: {message}")
            mainpc_failed.append((agent_name, message))
    
    # Test PC2 agents
    print(f"\n📋 TESTING PC2 SOT AGENTS:")
    pc2_agents = get_pc2_sot_agents()
    pc2_passed = 0
    pc2_failed = []
    
    for agent_path in pc2_agents:
        agent_name = Path(agent_path).stem
        success, message = test_agent_import(agent_path, agent_name)
        
        if success:
            print(f"✅ {agent_name}")
            pc2_passed += 1
        else:
            print(f"❌ {agent_name}: {message}")
            pc2_failed.append((agent_name, message))
    
    # Summary
    print(f"\n📊 VALIDATION SUMMARY:")
    print(f"MainPC: {mainpc_passed}/{len(mainpc_agents)} passed ({len(mainpc_failed)} failed)")
    print(f"PC2: {pc2_passed}/{len(pc2_agents)} passed ({len(pc2_failed)} failed)")
    print(f"TOTAL: {mainpc_passed + pc2_passed}/{len(mainpc_agents) + len(pc2_agents)} passed")
    
    # Failed details
    if mainpc_failed:
        print(f"\n❌ MAINPC FAILURES:")
        for name, error in mainpc_failed:
            print(f"  • {name}: {error}")
    
    if pc2_failed:
        print(f"\n❌ PC2 FAILURES:")
        for name, error in pc2_failed:
            print(f"  • {name}: {error}")
    
    if not mainpc_failed and not pc2_failed:
        print(f"\n🎉 ALL AGENTS IMPORT SUCCESSFULLY!")
        print(f"System is ready for Docker deployment! 🐳")
    else:
        print(f"\n⚠️  Fix failed imports before Docker deployment")

if __name__ == "__main__":
    main()
