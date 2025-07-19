#!/usr/bin/env python3
"""
Quick validation script to check if all syntax errors are fixed.
"""

import ast
import sys
from pathlib import Path

def check_syntax_errors():
    """Check for syntax errors in all Python files."""
    
    project_root = Path("/workspace")
    mainpc_root = project_root / "main_pc_code"
    
    dirs_to_check = [
        mainpc_root / "agents",
        mainpc_root / "services", 
        mainpc_root / "FORMAINPC",
        mainpc_root / "scripts"
    ]
    
    error_count = 0
    checked_count = 0
    errors = []
    
    print("Checking Python syntax in MainPC codebase...")
    print("-" * 60)
    
    for check_dir in dirs_to_check:
        if not check_dir.exists():
            continue
            
        for py_file in check_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or '.bak' in str(py_file):
                continue
                
            checked_count += 1
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                error_count += 1
                rel_path = py_file.relative_to(project_root)
                errors.append(f"{rel_path}:{e.lineno}: {e.msg}")
                print(f"❌ {py_file.name}: Line {e.lineno} - {e.msg}")
            except Exception as e:
                print(f"⚠️  Could not check {py_file.name}: {e}")
    
    print("\n" + "=" * 60)
    print(f"SUMMARY: Checked {checked_count} files")
    print(f"Found {error_count} syntax errors")
    
    if error_count == 0:
        print("\n✅ All syntax errors have been fixed!")
        return True
    else:
        print("\n❌ Remaining syntax errors:")
        for error in errors:
            print(f"  - {error}")
        return False


def check_incomplete_self():
    """Check for any remaining incomplete self. statements."""
    
    import re
    
    project_root = Path("/workspace")
    mainpc_root = project_root / "main_pc_code"
    
    pattern = re.compile(r'^\s*self\.\s*$', re.MULTILINE)
    
    print("\n\nChecking for incomplete self. statements...")
    print("-" * 60)
    
    found_count = 0
    
    for py_file in mainpc_root.rglob("*.py"):
        if '__pycache__' in str(py_file) or '.bak' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            matches = list(pattern.finditer(content))
            if matches:
                found_count += len(matches)
                print(f"⚠️  {py_file.name}: {len(matches)} incomplete self. statements")
                
        except Exception as e:
            pass
    
    if found_count == 0:
        print("\n✅ No incomplete self. statements found!")
        return True
    else:
        print(f"\n⚠️  Found {found_count} incomplete self. statements")
        return False


def check_port_conflicts():
    """Check for port conflicts in configuration."""
    
    import yaml
    
    config_path = Path("/workspace/main_pc_code/config/startup_config.yaml")
    
    print("\n\nChecking for port conflicts...")
    print("-" * 60)
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        ports_used = {}
        health_ports_used = {}
        conflicts = []
        
        for group_name, agents in config.get('agent_groups', {}).items():
            for agent_name, agent_config in agents.items():
                port = agent_config.get('port')
                health_port = agent_config.get('health_check_port')
                
                if port:
                    if port in ports_used:
                        conflicts.append(f"Port {port}: {agent_name} vs {ports_used[port]}")
                    ports_used[port] = agent_name
                    
                if health_port:
                    if health_port in health_ports_used:
                        conflicts.append(f"Health port {health_port}: {agent_name} vs {health_ports_used[health_port]}")
                    health_ports_used[health_port] = agent_name
        
        if conflicts:
            print("❌ Port conflicts found:")
            for conflict in conflicts:
                print(f"  - {conflict}")
            return False
        else:
            print(f"✅ No port conflicts found ({len(ports_used)} agents configured)")
            return True
            
    except Exception as e:
        print(f"❌ Error checking configuration: {e}")
        return False


def main():
    """Main validation function."""
    
    print("=" * 80)
    print("MAINPC QUICK VALIDATION")
    print("=" * 80)
    
    all_good = True
    
    # Check syntax errors
    if not check_syntax_errors():
        all_good = False
        
    # Check incomplete self statements
    if not check_incomplete_self():
        all_good = False
        
    # Check port conflicts
    if not check_port_conflicts():
        all_good = False
    
    print("\n" + "=" * 80)
    if all_good:
        print("✅ VALIDATION PASSED - System is ready to start!")
        print("\nNext steps:")
        print("1. Start Docker services: docker-compose -f docker/docker-compose.mainpc.yml up -d redis nats")
        print("2. Start the system: python3 main_pc_code/scripts/start_system.py")
    else:
        print("❌ VALIDATION FAILED - Please fix the issues above")
    
    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())