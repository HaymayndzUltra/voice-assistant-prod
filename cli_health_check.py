#!/usr/bin/env python3
"""
CLI System Health Check
Verifies all components are working and integrated properly
"""

import sys
import json
import os
from pathlib import Path

def check_state_files():
    """Check if all state files exist and are valid"""
    required_files = [
        'todo-tasks.json',
        'cursor_state.json', 
        'task-state.json',
        'task_interruption_state.json',
        'memory-bank/current-session.md'
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    return missing

def check_cli_system():
    """Check if CLI system is working"""
    try:
        import memory_system.cli
        return True
    except ImportError as e:
        return str(e)

def check_integrations():
    """Check if integration modules are working"""
    results = {}
    
    try:
        import auto_sync_manager
        results['auto_sync'] = 'OK'
    except ImportError as e:
        results['auto_sync'] = f'ERROR: {e}'
    
    try:
        import cursor_memory_bridge
        results['memory_bridge'] = 'OK'
    except ImportError as e:
        results['memory_bridge'] = f'ERROR: {e}'
    
    try:
        import todo_manager
        results['todo_manager'] = 'OK'
    except ImportError as e:
        results['todo_manager'] = f'ERROR: {e}'
    
    return results

def main():
    print("🏥 CLI System Health Check")
    print("=" * 40)
    
    # Check state files
    missing_files = check_state_files()
    if missing_files:
        print(f"❌ Missing state files: {missing_files}")
    else:
        print("✅ All state files present")
    
    # Check CLI system
    cli_status = check_cli_system()
    if cli_status is True:
        print("✅ CLI system importable")
    else:
        print(f"❌ CLI system error: {cli_status}")
    
    # Check integrations
    integrations = check_integrations()
    print("\n🔗 Integration Status:")
    for name, status in integrations.items():
        if status == 'OK':
            print(f"  ✅ {name}: {status}")
        else:
            print(f"  ❌ {name}: {status}")
    
    print("\n" + "=" * 40)
    print("Health check completed!")

if __name__ == "__main__":
    main()
