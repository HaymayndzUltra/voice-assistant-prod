#!/usr/bin/env python3
"""
AI Task Completion Hook
Automatically marks TODOs as done when AI completes tasks
Integrates with todo_manager.py for seamless task tracking
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

def mark_todo_done_automatically(task_id: str, todo_index: int, completion_message: str = ""):
    """
    Automatically mark a TODO as done when AI completes a task
    
    Args:
        task_id: The task ID to update
        todo_index: The index of the TODO to mark as done
        completion_message: Optional message about what was completed
    """
    try:
        # Import todo_manager functions
        from todo_manager import _load, _save, _timestamp
        
        # Load current tasks
        data = _load()
        task = next((t for t in data if t["id"] == task_id), None)
        
        if task is None:
            print(f"❌ Task '{task_id}' not found for auto-completion")
            return False
        
        if todo_index < 0 or todo_index >= len(task["todos"]):
            print(f"❌ Invalid TODO index {todo_index} for task '{task_id}'")
            return False
        
        # Mark TODO as done
        task["todos"][todo_index]["done"] = True
        task["updated"] = _timestamp()
        
        # Auto-completion logic: if all TODOs are done, mark task as completed
        if all(t["done"] for t in task["todos"]):
            task["status"] = "completed"
            print(f"🎉 Task '{task_id}' completed! All TODOs finished.")
        
        # Save changes (this triggers auto-sync automatically)
        _save(data)
        
        todo_text = task["todos"][todo_index]["text"]
        print(f"✅ AI Auto-Completed TODO {todo_index}: {todo_text}")
        
        if completion_message:
            print(f"   📝 Completion: {completion_message}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in auto-completion: {e}")
        return False

def mark_multiple_todos_done(task_id: str, todo_indices: List[int], completion_message: str = ""):
    """
    Mark multiple TODOs as done at once
    
    Args:
        task_id: The task ID to update
        todo_indices: List of TODO indices to mark as done
        completion_message: Optional message about what was completed
    """
    try:
        from todo_manager import _load, _save, _timestamp
        
        data = _load()
        task = next((t for t in data if t["id"] == task_id), None)
        
        if task is None:
            print(f"❌ Task '{task_id}' not found for batch auto-completion")
            return False
        
        # Mark all specified TODOs as done
        completed_todos = []
        for index in todo_indices:
            if 0 <= index < len(task["todos"]):
                task["todos"][index]["done"] = True
                completed_todos.append(task["todos"][index]["text"])
        
        task["updated"] = _timestamp()
        
        # Check if all TODOs are now done
        if all(t["done"] for t in task["todos"]):
            task["status"] = "completed"
            print(f"🎉 Task '{task_id}' completed! All TODOs finished.")
        
        # Save changes
        _save(data)
        
        print(f"✅ AI Auto-Completed {len(completed_todos)} TODOs:")
        for i, todo_text in enumerate(completed_todos):
            print(f"   [{i+1}] {todo_text}")
        
        if completion_message:
            print(f"   📝 Completion: {completion_message}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in batch auto-completion: {e}")
        return False

def auto_complete_task_by_description(task_description: str, completion_message: str = ""):
    """
    Automatically complete a task by matching its description
    
    Args:
        task_description: Partial or full task description to match
        completion_message: Optional message about what was completed
    """
    try:
        from todo_manager import _load, _save, _timestamp
        
        data = _load()
        
        # Find task by description (case-insensitive partial match)
        matching_tasks = []
        for task in data:
            if task_description.lower() in task.get("description", "").lower():
                matching_tasks.append(task)
        
        if not matching_tasks:
            print(f"❌ No tasks found matching description: '{task_description}'")
            return False
        
        if len(matching_tasks) > 1:
            print(f"⚠️ Multiple tasks found matching '{task_description}':")
            for i, task in enumerate(matching_tasks):
                print(f"   [{i}] {task.get('description', 'Unknown')}")
            return False
        
        # Mark all TODOs as done for the matching task
        task = matching_tasks[0]
        task_id = task["id"]
        
        # Mark all TODOs as done
        for i in range(len(task["todos"])):
            task["todos"][i]["done"] = True
        
        task["status"] = "completed"
        task["updated"] = _timestamp()
        
        # Save changes
        _save(data)
        
        print(f"🎉 AI Auto-Completed Task: {task.get('description', 'Unknown')}")
        print(f"   ✅ All {len(task['todos'])} TODOs marked as done")
        
        if completion_message:
            print(f"   📝 Completion: {completion_message}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in task auto-completion: {e}")
        return False

def get_current_active_task() -> Optional[Dict[str, Any]]:
    """Get the current active task for AI to work on"""
    try:
        from todo_manager import _load
        
        data = _load()
        active_tasks = [t for t in data if t.get("status") == "in_progress"]
        
        if not active_tasks:
            return None
        
        # Return the most recent active task
        active_tasks.sort(key=lambda x: x.get("updated", ""), reverse=True)
        return active_tasks[0]
        
    except Exception as e:
        print(f"❌ Error getting active task: {e}")
        return None

def ai_completion_workflow():
    """
    Main workflow for AI to automatically complete tasks
    This can be called by the AI when it finishes a task
    """
    print("🤖 AI Task Completion Workflow")
    print("=" * 50)
    
    # Get current active task
    active_task = get_current_active_task()
    
    if not active_task:
        print("ℹ️ No active tasks found")
        return
    
    task_id = active_task["id"]
    description = active_task.get("description", "Unknown")
    todos = active_task.get("todos", [])
    
    print(f"📋 Current Active Task: {description}")
    print(f"🆔 Task ID: {task_id}")
    print(f"📝 TODOs: {len(todos)} total")
    
    # Show incomplete TODOs
    incomplete_todos = [i for i, todo in enumerate(todos) if not todo.get("done", False)]
    
    if not incomplete_todos:
        print("✅ All TODOs are already completed!")
        return
    
    print(f"⏳ Incomplete TODOs: {len(incomplete_todos)}")
    for i in incomplete_todos:
        print(f"   [{i}] {todos[i]['text']}")
    
    print("\n🤖 AI can now automatically mark TODOs as done using:")
    print(f"   mark_todo_done_automatically('{task_id}', todo_index)")
    print(f"   mark_multiple_todos_done('{task_id}', [0, 1, 2])")
    print(f"   auto_complete_task_by_description('{description[:30]}...')")

# CLI interface for testing
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "workflow":
            ai_completion_workflow()
        elif command == "complete" and len(sys.argv) >= 4:
            task_id = sys.argv[2]
            todo_index = int(sys.argv[3])
            message = sys.argv[4] if len(sys.argv) > 4 else ""
            mark_todo_done_automatically(task_id, todo_index, message)
        elif command == "complete-multiple" and len(sys.argv) >= 4:
            task_id = sys.argv[2]
            indices = [int(x) for x in sys.argv[3].split(",")]
            message = sys.argv[4] if len(sys.argv) > 4 else ""
            mark_multiple_todos_done(task_id, indices, message)
        elif command == "complete-task" and len(sys.argv) >= 3:
            description = sys.argv[2]
            message = sys.argv[3] if len(sys.argv) > 3 else ""
            auto_complete_task_by_description(description, message)
        else:
            print("Usage:")
            print("  python3 ai_task_completion_hook.py workflow")
            print("  python3 ai_task_completion_hook.py complete <task_id> <todo_index> [message]")
            print("  python3 ai_task_completion_hook.py complete-multiple <task_id> <indices> [message]")
            print("  python3 ai_task_completion_hook.py complete-task <description> [message]")
    else:
        ai_completion_workflow() 