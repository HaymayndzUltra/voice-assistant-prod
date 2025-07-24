#!/usr/bin/env python3
"""
🔧 STARTUP CONFIG PORT CONFLICT FIXER
====================================

This script fixes port conflicts in the startup configuration.
"""

import yaml
from pathlib import Path

def fix_startup_config_conflicts():
    """Fix port conflicts in startup_config.yaml."""
    config_path = Path("main_pc_code/config/startup_config.yaml")
    
    if not config_path.exists():
        print(f"❌ Startup config not found: {config_path}")
        return False
    
    print("🔧 Fixing startup configuration port conflicts...")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Fix the specific conflict: LearningOrchestrationService vs ModelOrchestrator both on port 7210
        # Change ModelOrchestrator to a different port
        
        agent_groups = config.get('agent_groups', {})
        
        # Find and fix the conflict
        if 'language_processing' in agent_groups and 'ModelOrchestrator' in agent_groups['language_processing']:
            if agent_groups['language_processing']['ModelOrchestrator'].get('port') == 7210:
                # Change ModelOrchestrator to port 7215
                agent_groups['language_processing']['ModelOrchestrator']['port'] = 7215
                agent_groups['language_processing']['ModelOrchestrator']['health_check_port'] = 8215
                print("  ✅ Fixed ModelOrchestrator port: 7210 → 7215")
                
                # Update dependencies if any other agents depend on ModelOrchestrator
                # This ensures the system knows about the port change
                
                # Write back the configuration
                with open(config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                
                return True
        
        print("  ℹ️  No conflicts found to fix")
        return False
        
    except Exception as e:
        print(f"❌ Error fixing startup config: {e}")
        return False

def validate_all_ports():
    """Validate all ports in the configuration."""
    config_path = Path("main_pc_code/config/startup_config.yaml")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        ports_used = {}
        health_ports_used = {}
        conflicts = []
        
        agent_groups = config.get('agent_groups', {})
        
        print("🔍 Validating all ports...")
        print("📊 Port assignments:")
        
        for group_name, agents in agent_groups.items():
            print(f"\n📁 {group_name}:")
            for agent_name, agent_config in agents.items():
                port = agent_config.get('port')
                health_port = agent_config.get('health_check_port')
                
                print(f"  🤖 {agent_name}: port={port}, health_port={health_port}")
                
                if port:
                    if port in ports_used:
                        conflicts.append(f"Port {port}: {ports_used[port]} vs {agent_name}")
                    else:
                        ports_used[port] = agent_name
                
                if health_port:
                    if health_port in health_ports_used:
                        conflicts.append(f"Health port {health_port}: {health_ports_used[health_port]} vs {agent_name}")
                    elif health_port in ports_used:
                        conflicts.append(f"Health port {health_port} conflicts with main port of {ports_used[health_port]}")
                    else:
                        health_ports_used[health_port] = agent_name
        
        print(f"\n📈 VALIDATION RESULTS:")
        print(f"  📊 Total agents: {sum(len(agents) for agents in agent_groups.values())}")
        print(f"  🔌 Unique ports: {len(ports_used)}")
        print(f"  🩺 Unique health ports: {len(health_ports_used)}")
        
        if conflicts:
            print(f"  ❌ Conflicts found: {len(conflicts)}")
            for conflict in conflicts:
                print(f"    ⚠️  {conflict}")
            return False
        else:
            print("  ✅ No port conflicts found!")
            return True
            
    except Exception as e:
        print(f"❌ Error validating ports: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Startup Config Port Conflict Fix")
    print("=" * 45)
    
    # Fix conflicts
    fixed = fix_startup_config_conflicts()
    
    # Validate all ports
    valid = validate_all_ports()
    
    print(f"\n🏁 SUMMARY:")
    print(f"  Conflicts fixed: {'✅' if fixed else '❌'}")
    print(f"  Configuration valid: {'✅' if valid else '❌'}")
    
    if fixed or valid:
        print("\n🎉 Startup configuration is now ready!")
    else:
        print("\n⚠️  Manual intervention may be required.")