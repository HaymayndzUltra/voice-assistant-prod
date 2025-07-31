#!/usr/bin/env python3
"""
Cursor AI Integration
Automatically marks TODOs as done when Cursor AI completes tasks
Integrates with the AI workflow for seamless task tracking
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

def cursor_ai_task_completed(task_description: str, completed_todos: List[str], completion_summary: str = ""):
    """
    Called by Cursor AI when it completes a task
    
    Args:
        task_description: Description of the completed task
        completed_todos: List of TODO texts that were completed
        completion_summary: Summary of what was accomplished
    """
    try:
        from ai_task_completion_hook import get_current_active_task, mark_todo_done_automatically
        
        print("🤖 Cursor AI Task Completion Detected")
        print("=" * 50)
        print(f"📋 Task: {task_description}")
        print(f"✅ Completed TODOs: {len(completed_todos)}")
        print(f"📝 Summary: {completion_summary}")
        
        # Get current active task
        active_task = get_current_active_task()
        
        if not active_task:
            print("❌ No active task found to update")
            return False
        
        task_id = active_task["id"]
        task_todos = active_task.get("todos", [])
        
        # Find and mark matching TODOs as done
        completed_count = 0
        for completed_todo_text in completed_todos:
            for i, todo in enumerate(task_todos):
                if not todo.get("done", False) and completed_todo_text.lower() in todo["text"].lower():
                    success = mark_todo_done_automatically(
                        task_id, 
                        i, 
                        f"AI completed: {completed_todo_text}"
                    )
                    if success:
                        completed_count += 1
                    break
        
        print(f"✅ Successfully marked {completed_count} TODOs as done")
        
        # Store completion in memory
        store_ai_completion_memory(task_description, completed_todos, completion_summary)
        
        return True
        
    except Exception as e:
        print(f"❌ Error in Cursor AI task completion: {e}")
        return False

def store_ai_completion_memory(task_description: str, completed_todos: List[str], completion_summary: str):
    """Store AI completion in memory system"""
    try:
        from mcp_my-memory_store_memory import mcp_my-memory_store_memory
        
        memory_data = {
            "task_description": task_description,
            "completed_todos": completed_todos,
            "completion_summary": completion_summary,
            "ai_assistant": "Cursor AI",
            "completion_type": "automatic"
        }
        
        # Store in memory system
        mcp_my-memory_store_memory(
            project_name="ai-system-deployment",
            session_name="cursor-ai-completion",
            sequence_number=int(datetime.now().timestamp()),
            request=f"Complete task: {task_description}",
            response=f"AI completed {len(completed_todos)} TODOs: {', '.join(completed_todos)}",
            metadata=memory_data
        )
        
        print("💾 AI completion stored in memory system")
        
    except Exception as e:
        print(f"⚠️ Could not store in memory system: {e}")

def cursor_ai_workflow_completed(workflow_name: str, results: Dict[str, Any]):
    """
    Called when Cursor AI completes a workflow
    
    Args:
        workflow_name: Name of the completed workflow
        results: Results and outputs from the workflow
    """
    try:
        print(f"🎉 Cursor AI Workflow Completed: {workflow_name}")
        print("=" * 50)
        
        # Extract completed tasks from workflow results
        completed_tasks = results.get("completed_tasks", [])
        completion_summary = results.get("summary", "")
        
        for task in completed_tasks:
            task_description = task.get("description", "")
            completed_todos = task.get("completed_todos", [])
            
            cursor_ai_task_completed(task_description, completed_todos, completion_summary)
        
        # Update session state
        update_session_after_ai_completion(workflow_name, results)
        
        return True
        
    except Exception as e:
        print(f"❌ Error in workflow completion: {e}")
        return False

def update_session_after_ai_completion(workflow_name: str, results: Dict[str, Any]):
    """Update session state after AI completion"""
    try:
        from auto_sync_manager import auto_sync
        
        # Trigger auto-sync to update all state files
        sync_result = auto_sync()
        
        print(f"🔄 Session state updated after AI completion")
        print(f"   Workflow: {workflow_name}")
        print(f"   Sync result: {sync_result.get('status', 'unknown')}")
        
    except Exception as e:
        print(f"⚠️ Could not update session state: {e}")

def get_ai_completion_commands():
    """Get the commands that Cursor AI can use to mark TODOs as done"""
    return {
        "mark_single_todo": "mark_todo_done_automatically(task_id, todo_index, message)",
        "mark_multiple_todos": "mark_multiple_todos_done(task_id, [0,1,2], message)",
        "complete_task": "auto_complete_task_by_description('task description', message)",
        "ai_workflow_completed": "cursor_ai_workflow_completed('workflow_name', results_dict)",
        "ai_task_completed": "cursor_ai_task_completed('task_description', ['todo1', 'todo2'], 'summary')"
    }

def show_ai_integration_help():
    """Show help for AI integration"""
    print("🤖 Cursor AI Integration Help")
    print("=" * 50)
    print("The AI can automatically mark TODOs as done using these functions:")
    print()
    
    commands = get_ai_completion_commands()
    for name, command in commands.items():
        print(f"📋 {name}:")
        print(f"   {command}")
        print()
    
    print("Example usage:")
    print("   cursor_ai_task_completed('Setup Docker environment', ['Install Docker', 'Configure Docker Compose'], 'Docker environment ready')")
    print("   mark_todo_done_automatically('20250731T201947_Local_AI_System_Deployment_&_Configuration', 0, 'Docker installed successfully')")

# CLI interface
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "help":
            show_ai_integration_help()
        elif command == "workflow" and len(sys.argv) >= 4:
            workflow_name = sys.argv[2]
            results_file = sys.argv[3]
            
            # Load results from file
            with open(results_file, 'r') as f:
                results = json.load(f)
            
            cursor_ai_workflow_completed(workflow_name, results)
        elif command == "task" and len(sys.argv) >= 4:
            task_description = sys.argv[2]
            completed_todos = sys.argv[3].split(",")
            summary = sys.argv[4] if len(sys.argv) > 4 else ""
            
            cursor_ai_task_completed(task_description, completed_todos, summary)
        else:
            print("Usage:")
            print("  python3 cursor_ai_integration.py help")
            print("  python3 cursor_ai_integration.py workflow <workflow_name> <results_file>")
            print("  python3 cursor_ai_integration.py task <description> <completed_todos> [summary]")
    else:
        show_ai_integration_help() 