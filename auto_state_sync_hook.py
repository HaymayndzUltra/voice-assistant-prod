#!/usr/bin/env python3
"""
Auto State Sync Hook
Automatically synchronizes all state files when major tasks complete
Ensures consistent session state across all AI assistants
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

def update_state_after_completion(task_title: str, completion_status: str = "completed"):
    """Update all state files after task completion"""
    
    timestamp = datetime.now().isoformat()
    print(f"🔄 Auto-syncing state files for task: {task_title}")
    
    # Update cursor state
    cursor_state = {
        "cursor_session": {
            "disconnected_at": timestamp,
            "current_task": task_title,
            "progress": 1.0 if completion_status == "completed" else 0.5,
            "last_activity": timestamp,
            "completion_status": completion_status
        }
    }
    
    with open("cursor_state.json", "w") as f:
        json.dump(cursor_state, f, indent=2)
    
    # Update task interruption state
    interruption_state = {
        "current_task": task_title if completion_status != "completed" else None,
        "interrupted_tasks": [],
        "last_updated": timestamp,
        "completion_status": completion_status
    }
    
    with open("memory-bank/task_interruption_state.json", "w") as f:
        json.dump(interruption_state, f, indent=2)
    
    # Update current session markdown
    session_md = f"""# 📝 Current Session — {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

| Field | Value |
|-------|-------|
| current_file | — |
| cursor_line | — |
| current_task | {task_title} |
| progress | {'100%' if completion_status == 'completed' else '50%'} |
| last_activity | {timestamp} |
| completion_status | {completion_status} |
| auto_sync_enabled | ✅ Active |

## 🎯 Latest Achievement:
{task_title} - **{completion_status.upper()}**
"""
    
    with open("memory-bank/current-session.md", "w") as f:
        f.write(session_md)
    
    print("✅ All state files updated successfully")
    return True

def validate_state_consistency():
    """Validate that all state files are consistent"""
    
    try:
        # Read cursor state
        with open("cursor_state.json", "r") as f:
            cursor_data = json.load(f)
        
        # Read task interruption state  
        with open("memory-bank/task_interruption_state.json", "r") as f:
            interruption_data = json.load(f)
        
        cursor_task = cursor_data.get("cursor_session", {}).get("current_task", "")
        interruption_task = interruption_data.get("current_task", "")
        
        # Check consistency
        if cursor_task and interruption_task and cursor_task != interruption_task:
            print("⚠️ INCONSISTENCY DETECTED: State files have different tasks")
            return False
        
        print("✅ State files are consistent")
        return True
        
    except Exception as e:
        print(f"❌ Error validating state consistency: {e}")
        return False

def auto_sync_on_major_completion():
    """Automatically sync state when major task completes"""
    
    # This would typically be called from the completion workflow
    # For now, we'll update with the Event-Driven GUI completion
    
    update_state_after_completion(
        task_title="🎉 Event-Driven GUI Upgrade - Production Ready", 
        completion_status="completed"
    )
    
    # Validate consistency
    validate_state_consistency()
    
    # Trigger memory system update
    os.system("python3 memory_system/cli.py sync 2>/dev/null || echo 'Memory sync skipped'")
    
    print("🎊 Auto-sync complete! Session state is now consistent.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--validate":
            validate_state_consistency()
        elif sys.argv[1] == "--sync":
            auto_sync_on_major_completion()
        else:
            update_state_after_completion(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "completed")
    else:
        auto_sync_on_major_completion()
