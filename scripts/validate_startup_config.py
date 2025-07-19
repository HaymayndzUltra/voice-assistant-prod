#!/usr/bin/env python3
"""
Startup Configuration Validation Script

Validates startup_config.yaml structure before deployment to catch
configuration issues early and prevent "0 phases detected" errors.
"""

import sys
import yaml
from pathlib import Path

def validate_startup_config(config_path):
    """Validate startup configuration file structure and contents."""
    print(f"Validating startup configuration: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ YAML parsing error: {e}")
        return False
    
    errors = []
    warnings = []
    
    # 1. Check agent_groups exists and is a mapping
    if 'agent_groups' not in config:
        errors.append("Missing 'agent_groups' section")
    elif not isinstance(config['agent_groups'], dict):
        errors.append("'agent_groups' must be a dictionary/mapping")
    else:
        agent_groups = config['agent_groups']
        
        # 2. Check each group contains at least one agent
        for group_name, group_data in agent_groups.items():
            if not isinstance(group_data, dict):
                errors.append(f"Group '{group_name}' must be a dictionary")
                continue
                
            if not group_data:
                warnings.append(f"Group '{group_name}' is empty")
                continue
            
            # 3. Validate each agent in the group
            for agent_name, agent_cfg in group_data.items():
                if not isinstance(agent_cfg, dict):
                    errors.append(f"Agent '{agent_name}' in group '{group_name}' must be a dictionary")
                    continue
                
                # Check mandatory keys
                if 'script_path' not in agent_cfg:
                    errors.append(f"Agent '{agent_name}' missing required 'script_path'")
                
                if 'port' not in agent_cfg:
                    errors.append(f"Agent '{agent_name}' missing required 'port'")
                
                # Validate script path exists
                if 'script_path' in agent_cfg:
                    script_path = agent_cfg['script_path']
                    
                    # Try multiple possible locations
                    base_path = Path(config_path).parent.parent
                    possible_paths = [
                        base_path / script_path,
                        base_path / "main_pc_code" / script_path,
                        Path(script_path)
                    ]
                    
                    path_exists = any(p.exists() for p in possible_paths)
                    if not path_exists:
                        warnings.append(f"Agent '{agent_name}' script_path '{script_path}' not found")
    
    # 4. Validate dependencies reference existing agents
    all_agent_names = set()
    if 'agent_groups' in config and isinstance(config['agent_groups'], dict):
        for group_data in config['agent_groups'].values():
            if isinstance(group_data, dict):
                all_agent_names.update(group_data.keys())
    
    if 'agent_groups' in config:
        for group_name, group_data in config['agent_groups'].items():
            if isinstance(group_data, dict):
                for agent_name, agent_cfg in group_data.items():
                    if isinstance(agent_cfg, dict) and 'dependencies' in agent_cfg:
                        for dep in agent_cfg['dependencies']:
                            if dep not in all_agent_names:
                                errors.append(f"Agent '{agent_name}' depends on undefined agent '{dep}'")
    
    # 5. Check for port conflicts
    used_ports = {}
    if 'agent_groups' in config:
        for group_name, group_data in config['agent_groups'].items():
            if isinstance(group_data, dict):
                for agent_name, agent_cfg in group_data.items():
                    if isinstance(agent_cfg, dict):
                        port = agent_cfg.get('port')
                        health_port = agent_cfg.get('health_check_port', port + 1000 if port else None)
                        
                        if port:
                            if port in used_ports:
                                errors.append(f"Port {port} used by both '{agent_name}' and '{used_ports[port]}'")
                            else:
                                used_ports[port] = agent_name
                        
                        if health_port and health_port != port:
                            if health_port in used_ports:
                                errors.append(f"Health port {health_port} used by both '{agent_name}' and '{used_ports[health_port]}'")
                            else:
                                used_ports[health_port] = f"{agent_name} (health)"
    
    # Report results
    print(f"\n📊 Validation Results:")
    print(f"   Groups found: {len(config.get('agent_groups', {}))}")
    print(f"   Total agents: {len(all_agent_names)}")
    print(f"   Ports allocated: {len([p for p in used_ports.keys() if isinstance(p, int)])}")
    
    if errors:
        print(f"\n❌ {len(errors)} Error(s):")
        for error in errors:
            print(f"   • {error}")
    
    if warnings:
        print(f"\n⚠️  {len(warnings)} Warning(s):")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not errors:
        print("\n✅ Configuration validation passed!")
        return True
    else:
        print(f"\n❌ Configuration validation failed with {len(errors)} error(s)")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_startup_config.py <path_to_startup_config.yaml>")
        sys.exit(1)
    
    config_path = Path(sys.argv[1])
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    success = validate_startup_config(config_path)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 