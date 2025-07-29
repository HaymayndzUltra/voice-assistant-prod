#!/usr/bin/env python3

import sys
import json
import traceback

print("🔍 Debugging Option #10 Step by Step")
print("=" * 40)

# Step 1: Test basic imports
print("\n1️⃣ Testing basic imports...")
try:
    from todo_manager import new_task, add_todo, list_open_tasks, set_task_status, mark_done
    print("✅ todo_manager imports successful")
except Exception as e:
    print(f"❌ todo_manager import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 2: Test basic todo_manager functions
print("\n2️⃣ Testing basic todo_manager functions...")
try:
    current_tasks = list_open_tasks()
    print(f"✅ list_open_tasks() works: {len(current_tasks)} tasks found")
    
    # Test creating a simple task
    test_task_id = new_task("Debug test task")
    print(f"✅ new_task() works: {test_task_id}")
    
    # Test adding a TODO
    add_todo(test_task_id, "Debug TODO item")
    print("✅ add_todo() works")
    
    # Test setting status
    set_task_status(test_task_id, "completed")
    print("✅ set_task_status() works")
    
except Exception as e:
    print(f"❌ todo_manager function test failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test workflow_memory_intelligence import
print("\n3️⃣ Testing workflow_memory_intelligence import...")
try:
    from workflow_memory_intelligence import execute_task_intelligently
    print("✅ workflow_memory_intelligence import successful")
except Exception as e:
    print(f"❌ workflow_memory_intelligence import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 4: Test intelligent execution
print("\n4️⃣ Testing intelligent execution...")
try:
    test_description = "Create a test task with automatic TODO generation"
    print(f"Executing: {test_description}")
    
    result = execute_task_intelligently(test_description)
    print("✅ Intelligent execution completed")
    print(f"Result type: {type(result)}")
    
    if isinstance(result, dict):
        print("Result keys:", list(result.keys()))
        print("Status:", result.get('status', 'unknown'))
        print("Execution type:", result.get('execution_type', 'unknown'))
        print("Task ID:", result.get('task_id', 'unknown'))
        print("TODOs added:", result.get('todos_added', 'unknown'))
    else:
        print("Result is not a dict:", result)
        
except Exception as e:
    print(f"❌ Intelligent execution failed: {e}")
    traceback.print_exc()
    sys.exit(1)

# Step 5: Verify TODO was actually added
print("\n5️⃣ Verifying TODO was added...")
try:
    updated_tasks = list_open_tasks()
    print(f"Updated tasks: {len(updated_tasks)}")
    
    # Look for our test task
    test_task_found = False
    for task in updated_tasks:
        if "test task with automatic TODO generation" in task.get('description', ''):
            print(f"✅ Found test task: {task['id']}")
            print(f"   Status: {task['status']}")
            print(f"   TODOs: {len(task['todos'])}")
            for i, todo in enumerate(task['todos']):
                print(f"     [{i}] {todo['text']} - {'✅' if todo['done'] else '❌'}")
            test_task_found = True
            break
    
    if not test_task_found:
        print("❌ Test task not found in updated tasks")
        print("Available tasks:")
        for task in updated_tasks:
            print(f"  - {task['id']}: {task['description'][:50]}...")
            
except Exception as e:
    print(f"❌ Verification failed: {e}")
    traceback.print_exc()

print("\n�� Debug completed!") 