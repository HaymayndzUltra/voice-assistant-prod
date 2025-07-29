#!/usr/bin/env python3

print("🔍 Simple Check - Option #10 Status")
print("=" * 35)

# Check 1: Basic imports
print("1. Testing basic imports...")
try:
    from todo_manager import list_open_tasks, new_task, add_todo
    print("   ✅ todo_manager imports OK")
except Exception as e:
    print(f"   ❌ todo_manager import failed: {e}")

# Check 2: Current tasks
print("\n2. Checking current tasks...")
try:
    tasks = list_open_tasks()
    print(f"   Total tasks: {len(tasks)}")
    print(f"   In-progress: {len([t for t in tasks if t['status'] == 'in_progress'])}")
    print(f"   Completed: {len([t for t in tasks if t['status'] == 'completed'])}")
except Exception as e:
    print(f"   ❌ Error checking tasks: {e}")

# Check 3: Test task creation
print("\n3. Testing task creation...")
try:
    test_id = new_task("Simple test task")
    print(f"   ✅ Task created: {test_id}")
    
    add_todo(test_id, "Test TODO item")
    print("   ✅ TODO added")
    
except Exception as e:
    print(f"   ❌ Error creating task: {e}")

# Check 4: Test workflow import
print("\n4. Testing workflow import...")
try:
    from workflow_memory_intelligence_fixed import execute_task_intelligently
    print("   ✅ workflow_memory_intelligence_fixed import OK")
except Exception as e:
    print(f"   ❌ workflow_memory_intelligence_fixed import failed: {e}")
    try:
        from workflow_memory_intelligence import execute_task_intelligently
        print("   ✅ Original workflow_memory_intelligence import OK")
    except Exception as e2:
        print(f"   ❌ Original import also failed: {e2}")

print("\n�� Check completed!") 