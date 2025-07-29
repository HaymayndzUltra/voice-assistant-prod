#!/usr/bin/env python3
"""
Test script to debug Option #10 (Intelligent Task Execution)
"""

import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def test_option_10():
    """Test Option #10 functionality"""
    
    print("🧪 Testing Option #10: Intelligent Task Execution")
    print("=" * 50)
    
    try:
        # Test 1: Import check
        print("1. Testing imports...")
        from workflow_memory_intelligence import execute_task_intelligently
        from todo_manager import new_task, add_todo, list_open_tasks
        print("✅ Imports successful")
        
        # Test 2: Check current tasks
        print("\n2. Checking current tasks...")
        current_tasks = list_open_tasks()
        print(f"Current tasks: {len(current_tasks)}")
        for task in current_tasks:
            print(f"  - {task['id']}: {task['status']}")
        
        # Test 3: Execute intelligent task
        print("\n3. Testing intelligent task execution...")
        test_task = "Create a simple test task with automatic TODO generation"
        
        print(f"Executing: {test_task}")
        result = execute_task_intelligently(test_task)
        
        print("✅ Execution completed!")
        print("Result:")
        print(json.dumps(result, indent=2))
        
        # Test 4: Check if TODO was added
        print("\n4. Checking if TODO was added...")
        updated_tasks = list_open_tasks()
        print(f"Updated tasks: {len(updated_tasks)}")
        
        # Find the new task
        new_task_found = False
        for task in updated_tasks:
            if task['description'] == test_task:
                print(f"✅ Found new task: {task['id']}")
                print(f"   Status: {task['status']}")
                print(f"   TODOs: {len(task['todos'])}")
                for i, todo in enumerate(task['todos']):
                    print(f"     [{i}] {todo['text']} - {'✅' if todo['done'] else '❌'}")
                new_task_found = True
                break
        
        if not new_task_found:
            print("❌ New task not found!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_option_10()
    if success:
        print("\n🎉 Test completed successfully!")
    else:
        print("\n💥 Test failed!")
        sys.exit(1) 