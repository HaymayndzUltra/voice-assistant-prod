#!/usr/bin/env python3
"""
System Status Reporter
Provides comprehensive status of the entire system
"""

import json
import os
from datetime import datetime

def get_system_status():
    """Get comprehensive system status"""
    status = {
        'timestamp': datetime.now().isoformat(),
        'files': {},
        'tasks': {},
        'integration': {}
    }
    
    # Check file status
    files_to_check = [
        'todo-tasks.json',
        'cursor_state.json',
        'task-state.json', 
        'task_interruption_state.json'
    ]
    
    for file in files_to_check:
        if os.path.exists(file):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                status['files'][file] = 'OK'
            except:
                status['files'][file] = 'INVALID_JSON'
        else:
            status['files'][file] = 'MISSING'
    
    # Get task statistics
    try:
        with open('todo-tasks.json', 'r') as f:
            todo_data = json.load(f)
        
        tasks = todo_data.get('tasks', [])
        status['tasks'] = {
            'total': len(tasks),
            'in_progress': len([t for t in tasks if t.get('status') == 'in_progress']),
            'completed': len([t for t in tasks if t.get('status') == 'completed']),
            'created': len([t for t in tasks if t.get('status') == 'created'])
        }
    except:
        status['tasks'] = {'error': 'Could not read todo-tasks.json'}
    
    # Check integration modules
    integrations = ['auto_sync_manager', 'cursor_memory_bridge', 'todo_manager']
    for module in integrations:
        try:
            __import__(module)
            status['integration'][module] = 'OK'
        except ImportError:
            status['integration'][module] = 'MISSING'
    
    return status

def main():
    status = get_system_status()
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()
