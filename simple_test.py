#!/usr/bin/env python3

import sys
import json

print("🧪 Simple Test for Option #10")
print("=" * 30)

try:
    print("1. Testing basic imports...")
    from todo_manager import new_task, add_todo, list_open_tasks, set_task_status
    print("✅ todo_manager imports OK")
    
    print("\n2. Testing workflow_memory_intelligence import...")
    from workflow_memory_intelligence import execute_task_intelligently
    print("✅ workflow_memory_intelligence import OK")
    
    print("\n3. Testing basic todo_manager functions...")
    current_tasks = list_open_tasks()
    print(f"Current tasks: {len(current_tasks)}")
    
    print("\n4. Testing intelligent execution...")
    result = execute_task_intelligently("test task")
    print("✅ Intelligent execution completed")
    print(f"Result type: {type(result)}")
    print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n🎯 Test completed!") 