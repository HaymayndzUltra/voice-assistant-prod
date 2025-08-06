#!/usr/bin/env python3
"""
Session Continuity Manager
Fixes consistency issues across multiple sessions by properly syncing state files
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

@dataclass
class SessionState:
    """Current session state"""
    current_task: str
    progress: float
    last_activity: str
    disconnected_at: Optional[str] = None
    current_file: str = ""
    cursor_line: int = 0

class SessionContinuityManager:
    """Manages session continuity and state consistency"""
    
    def __init__(self):
        self.state_files = {
            'cursor_state': 'cursor_state.json',
            'task_state': 'task-state.json',
            'task_interruption': 'task_interruption_state.json',
            'active_tasks': 'memory-bank/queue-system/tasks_active.json',
            'current_session': 'memory-bank/current-session.md'
        }
        logger.info("🔄 SessionContinuityManager initialized")
    
    def sync_all_states(self) -> Dict[str, Any]:
        """Sync all state files to ensure consistency"""
        logger.info("🔄 Starting full state synchronization...")
        
        try:
            # Step 1: Read current state from active tasks (new system)
            current_tasks = self._get_current_active_tasks()
            
            # Step 2: Determine the most recent active task
            active_task = self._get_most_recent_active_task(current_tasks)
            
            # Step 3: Update all state files
            self._update_cursor_state(active_task)
            self._update_task_state(active_task)
            self._update_task_interruption_state(active_task)
            self._update_current_session(active_task, current_tasks)
            
            logger.info("✅ All state files synchronized")
            return {
                "status": "success",
                "active_task": active_task,
                "total_tasks": len(current_tasks)
            }
            
        except Exception as e:
            logger.error(f"❌ State synchronization failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_current_active_tasks(self) -> List[Dict[str, Any]]:
        """Get current active tasks from queue system"""
        try:
            with open(self.state_files['active_tasks'], 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("Active tasks file not found - creating empty")
            return []
        except Exception as e:
            logger.error(f"❌ Failed to read active tasks: {e}")
            return []
    
    def _get_most_recent_active_task(self, tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Get the most recent active task"""
        if not tasks:
            return None
        
        # Filter for in_progress tasks
        active_tasks = [task for task in tasks if task.get('status') == 'in_progress']
        
        if not active_tasks:
            # If no in_progress tasks, get the most recent task
            active_tasks = tasks
        
        # Sort by updated timestamp (most recent first)
        active_tasks.sort(key=lambda x: x.get('updated', ''), reverse=True)
        
        return active_tasks[0] if active_tasks else None
    
    def _update_cursor_state(self, active_task: Optional[Dict[str, Any]]):
        """Update cursor_state.json"""
        try:
            cursor_state = {
                "cursor_session": {
                    "disconnected_at": datetime.now().isoformat(),
                    "current_task": active_task.get('description', '') if active_task else '',
                    "progress": self._calculate_progress(active_task) if active_task else 0.0,
                    "last_activity": active_task.get('updated', datetime.now().isoformat()) if active_task else datetime.now().isoformat()
                }
            }
            
            with open(self.state_files['cursor_state'], 'w') as f:
                json.dump(cursor_state, f, indent=2)
            
            logger.info("✅ cursor_state.json updated")
            
        except Exception as e:
            logger.error(f"❌ Failed to update cursor_state.json: {e}")
    
    def _update_task_state(self, active_task: Optional[Dict[str, Any]]):
        """Update task-state.json"""
        try:
            if active_task:
                task_state = {
                    "current_task_id": active_task.get('id', ''),
                    "current_task_description": active_task.get('description', ''),
                    "status": active_task.get('status', ''),
                    "last_updated": active_task.get('updated', datetime.now().isoformat()),
                    "todos_count": len(active_task.get('todos', [])),
                    "completed_todos": len([todo for todo in active_task.get('todos', []) if todo.get('done', False)])
                }
            else:
                task_state = {}
            
            with open(self.state_files['task_state'], 'w') as f:
                json.dump(task_state, f, indent=2)
            
            logger.info("✅ task-state.json updated")
            
        except Exception as e:
            logger.error(f"❌ Failed to update task-state.json: {e}")
    
    def _update_task_interruption_state(self, active_task: Optional[Dict[str, Any]]):
        """Update task_interruption_state.json"""
        try:
            interruption_state = {
                "current_task": active_task.get('id', None) if active_task else None,
                "interrupted_tasks": [],
                "last_updated": datetime.now().isoformat()
            }
            
            with open(self.state_files['task_interruption'], 'w') as f:
                json.dump(interruption_state, f, indent=2)
            
            logger.info("✅ task_interruption_state.json updated")
            
        except Exception as e:
            logger.error(f"❌ Failed to update task_interruption_state.json: {e}")
    
    def _update_current_session(self, active_task: Optional[Dict[str, Any]], all_tasks: List[Dict[str, Any]]):
        """Update memory-bank/current-session.md"""
        try:
            # Get in_progress tasks for display
            in_progress_tasks = [task for task in all_tasks if task.get('status') == 'in_progress']
            
            session_content = f"""# 📝 Current Cursor Session — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC

| Field | Value |
|-------|-------|
| current_file | — |
| cursor_line | — |
| current_task | {active_task.get('description', 'No active task') if active_task else 'No active task'} |
| progress | {self._calculate_progress(active_task) if active_task else 0.0} |
| last_activity | {active_task.get('updated', datetime.now().isoformat()) if active_task else datetime.now().isoformat()} |
| disconnected_at | {datetime.now().isoformat()} |

## 🕒 Open Tasks (Todo Manager)
"""
            
            for task in in_progress_tasks:
                todos_left = len([todo for todo in task.get('todos', []) if not todo.get('done', False)])
                session_content += f"- **{task.get('description', 'Unknown task')}** ({todos_left} todos left)\n"
            
            if not in_progress_tasks:
                session_content += "- No active tasks\n"
            
            # Ensure memory-bank directory exists
            os.makedirs('memory-bank', exist_ok=True)
            
            with open(self.state_files['current_session'], 'w') as f:
                f.write(session_content)
            
            logger.info("✅ current-session.md updated")
            
        except Exception as e:
            logger.error(f"❌ Failed to update current-session.md: {e}")
    
    def _calculate_progress(self, task: Optional[Dict[str, Any]]) -> float:
        """Calculate progress based on completed TODOs"""
        if not task or not task.get('todos'):
            return 0.0
        
        todos = task.get('todos', [])
        completed = len([todo for todo in todos if todo.get('done', False)])
        total = len(todos)
        
        return completed / total if total > 0 else 0.0
    
    def cleanup_duplicate_tasks(self) -> Dict[str, Any]:
        """Clean up duplicate tasks in todo-tasks.json"""
        logger.info("🧹 Starting duplicate task cleanup...")
        
        try:
            tasks = self._get_current_active_tasks()
            original_count = len(tasks)
            
            # Group tasks by description
            tasks_by_description = {}
            for task in tasks:
                description = task.get('description', '').strip()
                if description not in tasks_by_description:
                    tasks_by_description[description] = []
                tasks_by_description[description].append(task)
            
            # Keep only the most recent task for each description
            cleaned_tasks = []
            duplicates_removed = 0
            
            for description, task_list in tasks_by_description.items():
                if len(task_list) > 1:
                    # Sort by updated timestamp (most recent first)
                    task_list.sort(key=lambda x: x.get('updated', ''), reverse=True)
                    cleaned_tasks.append(task_list[0])
                    duplicates_removed += len(task_list) - 1
                    logger.info(f"🔍 Removed {len(task_list) - 1} duplicates for: {description[:50]}...")
                else:
                    cleaned_tasks.append(task_list[0])
            
            # Update active tasks file
            with open(self.state_files['active_tasks'], 'w') as f:
                json.dump(cleaned_tasks, f, indent=2)
            
            logger.info(f"✅ Cleanup complete: {duplicates_removed} duplicates removed")
            
            return {
                "status": "success",
                "original_count": original_count,
                "final_count": len(cleaned_tasks),
                "duplicates_removed": duplicates_removed
            }
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

def main():
    """Main function to run session continuity fixes"""
    manager = SessionContinuityManager()
    
    print("🔄 Session Continuity Manager")
    print("=" * 40)
    
    # Step 1: Clean up duplicates
    print("\n1️⃣ Cleaning up duplicate tasks...")
    cleanup_result = manager.cleanup_duplicate_tasks()
    print(f"   Result: {cleanup_result}")
    
    # Step 2: Sync all states
    print("\n2️⃣ Syncing all state files...")
    sync_result = manager.sync_all_states()
    print(f"   Result: {sync_result}")
    
    print("\n✅ Session continuity fixes completed!")

if __name__ == "__main__":
    main() 