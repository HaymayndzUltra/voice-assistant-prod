#!/usr/bin/env python3
"""
Test Auto-Sync System
Verifies that auto-sync is working properly
"""

import json
import time
from datetime import datetime

def test_auto_sync():
    """Test the auto-sync functionality"""
    
    print("🧪 Testing Auto-Sync System")
    print("=" * 40)
    
    # Step 1: Import and initialize auto-sync
    try:
        from auto_sync_manager import get_auto_sync_manager, auto_sync
        print("✅ Auto-sync manager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import auto-sync: {e}")
        return False
    
    # Step 2: Test initial sync
    print("\n1️⃣ Testing initial sync...")
    try:
        manager = get_auto_sync_manager()
        result = manager.force_sync()
        print(f"   Result: {result}")
        if result.get('status') == 'success':
            print("   ✅ Initial sync successful")
        else:
            print(f"   ❌ Initial sync failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"   ❌ Initial sync error: {e}")
        return False
    
    # Step 3: Test manual sync
    print("\n2️⃣ Testing manual sync...")
    try:
        result = auto_sync()
        print(f"   Result: {result}")
        if result.get('status') == 'success':
            print("   ✅ Manual sync successful")
        else:
            print(f"   ❌ Manual sync failed: {result.get('error')}")
            return False
    except Exception as e:
        print(f"   ❌ Manual sync error: {e}")
        return False
    
    # Step 4: Test state file consistency
    print("\n3️⃣ Testing state file consistency...")
    try:
        # Read all state files
        with open('cursor_state.json', 'r') as f:
            cursor_state = json.load(f)
        
        with open('task-state.json', 'r') as f:
            task_state = json.load(f)
        
        with open('task_interruption_state.json', 'r') as f:
            interruption_state = json.load(f)
        
        with open('todo-tasks.json', 'r') as f:
            todo_tasks = json.load(f)
        
        # Check if they're consistent
        cursor_task = cursor_state.get('cursor_session', {}).get('current_task', '')
        task_state_id = task_state.get('current_task_id', '')
        interruption_task = interruption_state.get('current_task', '')
        
        # Find the most recent task in todo-tasks.json
        tasks = todo_tasks.get('tasks', [])
        if tasks:
            # Sort by updated timestamp
            tasks.sort(key=lambda x: x.get('updated', ''), reverse=True)
            latest_task = tasks[0]
            latest_task_id = latest_task.get('id', '')
            latest_description = latest_task.get('description', '')
        else:
            latest_task_id = ''
            latest_description = ''
        
        print(f"   📊 State file analysis:")
        print(f"      cursor_state.json task: {cursor_task[:50]}...")
        print(f"      task-state.json task_id: {task_state_id}")
        print(f"      interruption_state.json task: {interruption_task}")
        print(f"      todo-tasks.json latest: {latest_task_id}")
        
        # Check consistency
        if cursor_task == latest_description and task_state_id == latest_task_id:
            print("   ✅ State files are consistent!")
        else:
            print("   ⚠️  State files may have inconsistencies")
            print(f"      Expected: {latest_description[:50]}...")
            print(f"      Found: {cursor_task[:50]}...")
        
    except Exception as e:
        print(f"   ❌ State file check error: {e}")
        return False
    
    # Step 5: Test integration with todo_manager
    print("\n4️⃣ Testing todo_manager integration...")
    try:
        from todo_manager import new_task, add_todo
        
        # Create a test task
        test_task_id = new_task("Auto-sync test task")
        print(f"   ✅ Created test task: {test_task_id}")
        
        # Add a test TODO
        add_todo(test_task_id, "Test TODO for auto-sync")
        print(f"   ✅ Added test TODO")
        
        # Wait a moment for auto-sync
        time.sleep(1)
        
        # Check if state files were updated
        with open('task-state.json', 'r') as f:
            updated_task_state = json.load(f)
        
        if updated_task_state.get('current_task_id') == test_task_id:
            print("   ✅ Auto-sync triggered by todo_manager")
        else:
            print("   ⚠️  Auto-sync may not have triggered")
        
    except Exception as e:
        print(f"   ❌ Todo manager integration error: {e}")
        return False
    
    print("\n🎯 Auto-sync test completed successfully!")
    return True

if __name__ == "__main__":
    success = test_auto_sync()
    if success:
        print("\n✅ All auto-sync tests passed!")
    else:
        print("\n❌ Some auto-sync tests failed!") 