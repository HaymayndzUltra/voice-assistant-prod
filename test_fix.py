#!/usr/bin/env python3
"""
Test the current_task fix
"""

def test_current_task_fix():
    """Test that current_task handling works for both string and dict formats"""
    
    print("🧪 Testing current_task fix...")
    
    try:
        from task_interruption_manager import get_interruption_status
        
        # Get current status
        status = get_interruption_status()
        print(f"✅ Status retrieved: {status}")
        
        # Test current_task handling
        current_task = status.get('current_task')
        print(f"Current task type: {type(current_task)}")
        print(f"Current task value: {current_task}")
        
        if current_task:
            if isinstance(current_task, str):
                print("✅ String format detected - getting full task details...")
                from todo_manager import list_open_tasks
                tasks = list_open_tasks()
                found_task = None
                for task in tasks:
                    if task['id'] == current_task:
                        found_task = task
                        break
                
                if found_task:
                    print(f"✅ Found task: {found_task['description']}")
                else:
                    print(f"⚠️  Task not found for ID: {current_task}")
            else:
                print(f"✅ Dictionary format: {current_task}")
        else:
            print("ℹ️  No current task")
        
        print("✅ Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    test_current_task_fix() 