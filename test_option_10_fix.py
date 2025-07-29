#!/usr/bin/env python3

import sys
import json
from datetime import datetime

print("🧪 Testing Option #10 Fix")
print("=" * 30)
print(f"Time: {datetime.now()}")
print()

# Test 1: Check current tasks
print("1️⃣ Checking current tasks...")
try:
    from todo_manager import list_open_tasks
    current_tasks = list_open_tasks()
    print(f"   Current tasks: {len(current_tasks)}")
    for task in current_tasks:
        print(f"   - {task['id']}: {task['status']} ({len(task['todos'])} TODOs)")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()

# Test 2: Test intelligent execution
print("2️⃣ Testing intelligent execution...")
try:
    from workflow_memory_intelligence_fixed import execute_task_intelligently
    
    test_task = "Test Option 10 fix with automatic TODO generation"
    print(f"   Executing: {test_task}")
    
    result = execute_task_intelligently(test_task)
    
    print(f"   ✅ Execution completed")
    print(f"   Status: {result.get('status', 'unknown')}")
    print(f"   Task ID: {result.get('task_id', 'unknown')}")
    print(f"   TODOs added: {result.get('todos_added', 'unknown')}")
    print(f"   Execution type: {result.get('execution_type', 'unknown')}")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 3: Verify TODO was added
print("3️⃣ Verifying TODO was added...")
try:
    updated_tasks = list_open_tasks()
    print(f"   Updated tasks: {len(updated_tasks)}")
    
    # Look for our test task
    test_task_found = False
    for task in updated_tasks:
        if "Test Option 10 fix" in task.get('description', ''):
            print(f"   ✅ Found test task: {task['id']}")
            print(f"      Status: {task['status']}")
            print(f"      TODOs: {len(task['todos'])}")
            for i, todo in enumerate(task['todos']):
                status = "✅" if todo['done'] else "❌"
                print(f"        [{i}] {todo['text'][:50]}... {status}")
            test_task_found = True
            break
    
    if not test_task_found:
        print("   ❌ Test task not found")
        print("   Available tasks:")
        for task in updated_tasks[-3:]:  # Show last 3 tasks
            print(f"      - {task['id']}: {task['description'][:50]}...")
            
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("🎯 Test completed!") 