# Core System Files (Level 1 Dependencies)

## 1. task_command_center.py

```python
#!/usr/bin/env python3
"""
Task Command & Control Center - Interactive menu system for task management
"""

import sys
import os
import json
from typing import List, Dict, Any
from task_interruption_manager import auto_task_handler, get_interruption_status, resume_all_interrupted_tasks
from todo_manager import list_open_tasks, add_todo, mark_done, delete_todo, show_task_details, new_task, hard_delete_task
# 🚀 Intelligent workflow integration (FIXED VERSION)
try:
    from workflow_memory_intelligence_fixed import execute_task_intelligently
    print("✅ Using fixed intelligent execution system")
except ImportError:
    from workflow_memory_intelligence import execute_task_intelligently
    print("⚠️ Using original intelligent execution system")

# 🔄 AUTO-SYNC INTEGRATION
try:
    from auto_sync_manager import get_auto_sync_manager, auto_sync
    print("✅ Auto-sync system integrated")
except ImportError:
    print("⚠️ Auto-sync system not available")
    def get_auto_sync_manager():
        return None
    def auto_sync():
        return {"status": "error", "error": "Auto-sync not available"}

class TaskCommandCenter:
    """Interactive command and control center for task management"""
    
    def __init__(self):
        self.running = True
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def show_header(self):
        """Show the command center header"""
        print("=" * 60)
        print("🎮 TASK COMMAND & CONTROL CENTER")
        print("=" * 60)
        print()
    
    def show_current_status(self):
        """Show current task status"""
        status = get_interruption_status()
        
        print("📊 CURRENT STATUS:")
        print("-" * 30)
        
        if status['current_task']:
            print(f"🚀 ACTIVE TASK:")
            # Handle both string (task ID) and dict formats
            if isinstance(status['current_task'], str):
                # It's a task ID, get the full task details
                from todo_manager import list_open_tasks
                tasks = list_open_tasks()
                current_task = None
                for task in tasks:
                    if task['id'] == status['current_task']:
                        current_task = task
                        break
                
                if current_task:
                    print(f"   {current_task['description']}")
                    print(f"   ID: {current_task['id']}")
                else:
                    print(f"   Task ID: {status['current_task']} (details not found)")
            else:
                # It's already a dictionary
                print(f"   {status['current_task']['description']}")
                print(f"   ID: {status['current_task']['task_id']}")
        else:
            print("ℹ️  No active task")
        
        if status['interrupted_tasks_count'] > 0:
            print(f"\n⏸️  INTERRUPTED TASKS ({status['interrupted_tasks_count']}):")
            for i, task in enumerate(status['interrupted_tasks'], 1):
                print(f"   {i}. {task['description']}")
        else:
            print("\nℹ️  No interrupted tasks")
        
        print()
    
    def show_main_menu(self):
        """Show the main menu"""
        print("🎯 MAIN MENU:")
        print("1. 📋 View All Tasks")
        print("2. 🚀 Start New Task")
        print("3. ⏸️  Interrupt Current Task")
        print("4. 🔄 Resume Interrupted Tasks")
        print("5. ✏️  Add TODO to Task")
        print("6. ✅ Mark TODO as Done")
        print("7. 🗑️  Delete TODO")
        print("8. 📖 Show Task Details")
        print("9. 🗑️  Delete Task")
        print("10. 🧠 Intelligent Task Execution")
        print("0. ❌ Exit")
        print()

    # ... (additional methods for menu options)

    def intelligent_task_execution(self):
        """Execute a task using intelligent workflow integration"""
        self.clear_screen()
        self.show_header()

        print("🧠 INTELLIGENT TASK EXECUTION:")
        print("=" * 35)
        print("Enter your task description (multi-line supported – auto-chunked):")

        task_description = self._collect_multiline_input()

        if not task_description:
            print("❌ Task description cannot be empty")
            input("\nPress Enter to continue...")
            return
        
        # Show a preview of the task description
        if len(task_description) > 100:
            print(f"\n📋 Task Preview: {task_description[:100]}...")
            print(f"📏 Total length: {len(task_description)} characters")
            print("🔄 This will be automatically chunked into manageable TODOs")
        else:
            print(f"\n📋 Task: {task_description}")

        # Execute task using intelligent workflow system
        print("\n🚀 Processing task with intelligent executor...\n")
        try:
            result = execute_task_intelligently(task_description)
            # Pretty-print the JSON result for the user
            print("\n✅ Intelligent Execution Result:")
            print(json.dumps(result, indent=2))
            
            # 🔄 Auto-sync after intelligent execution
            auto_sync()
            print("🔄 State files auto-synced")
        except Exception as e:
            # Catch any unexpected errors to ensure command center stability
            print(f"❌ An error occurred during intelligent execution: {e}")

        input("\nPress Enter to continue...")

    def run(self):
        """Run the command center"""
        while self.running:
            self.clear_screen()
            self.show_header()
            self.show_current_status()
            self.show_main_menu()
            
            choice = self.get_user_choice(10)
            
            if choice == 0:
                print("👋 Goodbye!")
                self.running = False
            elif choice == 1:
                self.view_all_tasks()
            elif choice == 2:
                self.start_new_task()
            elif choice == 3:
                self.interrupt_current_task()
            elif choice == 4:
                self.resume_interrupted_tasks()
            elif choice == 5:
                self.add_todo_to_task()
            elif choice == 6:
                self.mark_todo_done()
            elif choice == 7:
                self.delete_todo_item()
            elif choice == 8:
                self.show_task_details()
            elif choice == 9:
                self.delete_task()
            elif choice == 10:
                self.intelligent_task_execution()

def main():
    """Main function"""
    command_center = TaskCommandCenter()
    command_center.run()

if __name__ == "__main__":
    main()
```

## 2. task_interruption_manager.py

```python
#!/usr/bin/env python3
"""
Task Interruption Manager - Automatically handles task switching and resumption
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Import existing managers
from todo_manager import new_task, add_todo, list_open_tasks, set_task_status
from task_state_manager import save_task_state, load_task_state

class TaskInterruptionManager:
    """Manages automatic task interruption and resumption"""
    
    def __init__(self):
        self.interruption_file = Path("task_interruption_state.json")
        self.current_task = None
        self.interrupted_tasks = []
        self.load_state()
    
    def load_state(self):
        """Load interruption state from file"""
        if self.interruption_file.exists():
            try:
                with open(self.interruption_file, 'r') as f:
                    data = json.load(f)
                    self.current_task = data.get('current_task')
                    self.interrupted_tasks = data.get('interrupted_tasks', [])
            except Exception as e:
                print(f"⚠️  Error loading interruption state: {e}")
    
    def save_state(self):
        """Save interruption state to file"""
        data = {
            'current_task': self.current_task,
            'interrupted_tasks': self.interrupted_tasks,
            'last_updated': datetime.utcnow().isoformat()
        }
        try:
            with open(self.interruption_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Error saving interruption state: {e}")
    
    def start_task(self, task_description: str) -> str:
        """Start a new task, interrupting current if any"""
        
        # If there's a current task, interrupt it
        if self.current_task:
            self.interrupt_current_task()
        
        # Create new task
        task_id = new_task(task_description)
        self.current_task = {
            'task_id': task_id,
            'description': task_description,
            'started_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        
        self.save_state()
        print(f"🚀 Started new task: {task_description}")
        print(f"   Task ID: {task_id}")
        
        return task_id
    
    def interrupt_current_task(self):
        """Interrupt the current task and save it for later resumption"""
        if self.current_task:
            self.current_task['status'] = 'interrupted'
            self.current_task['interrupted_at'] = datetime.utcnow().isoformat()
            self.interrupted_tasks.append(self.current_task)
            
            print(f"⏸️  Interrupted task: {self.current_task['description']}")
            print(f"   Task ID: {self.current_task['task_id']}")
            print(f"   Will resume automatically after current task")
            
            # Update task status in todo_manager
            set_task_status(self.current_task['task_id'], 'interrupted')
    
    def resume_interrupted_tasks(self):
        """Resume all interrupted tasks"""
        if not self.interrupted_tasks:
            print("ℹ️  No interrupted tasks to resume")
            return
        
        print(f"🔄 Resuming {len(self.interrupted_tasks)} interrupted task(s)...")
        
        for task in self.interrupted_tasks:
            print(f"   📋 Resuming: {task['description']}")
            print(f"      Task ID: {task['task_id']}")
            
            # Update task status back to in_progress
            set_task_status(task['task_id'], 'in_progress')
        
        # Clear interrupted tasks list
        self.interrupted_tasks = []
        self.current_task = None
        self.save_state()
        
        print("✅ All interrupted tasks resumed")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current interruption status"""
        return {
            'current_task': self.current_task,
            'interrupted_tasks_count': len(self.interrupted_tasks),
            'interrupted_tasks': self.interrupted_tasks
        }
    
    def auto_detect_new_task(self, command: str) -> bool:
        """Auto-detect if command is a new task"""
        new_task_indicators = [
            'new task', 'create task', 'add task', 'start task',
            'gawa', 'gawin', 'gawain', 'task', 'trabaho',
            'implement', 'create', 'build', 'develop',
            'fix', 'solve', 'resolve', 'address'
        ]
        
        command_lower = command.lower()
        return any(indicator in command_lower for indicator in new_task_indicators)
    
    def process_command(self, command: str) -> str:
        """Process command and handle task interruption automatically"""
        
        # Check if this is a new task
        if self.auto_detect_new_task(command):
            # Start new task (will automatically interrupt current)
            task_id = self.start_task(command)
            return f"🔄 Automatically interrupted previous task and started new task: {task_id}"
        
        # Check for resume command
        if 'resume' in command.lower() or 'ipagpatuloy' in command.lower():
            self.resume_interrupted_tasks()
            return "✅ Resumed all interrupted tasks"
        
        # Check for status command
        if 'status' in command.lower() or 'anong ginagawa' in command.lower():
            status = self.get_current_status()
            return self.format_status(status)
        
        # Regular command - continue with current task
        return f"📋 Continuing with current task: {self._get_current_task_desc()}"

# Global instance
interruption_manager = TaskInterruptionManager()

def auto_task_handler(command: str) -> str:
    """Main function to handle automatic task interruption"""
    return interruption_manager.process_command(command)

def start_interrupted_task(task_description: str) -> str:
    """Start a new task with automatic interruption"""
    return interruption_manager.start_task(task_description)

def resume_all_interrupted_tasks():
    """Resume all interrupted tasks"""
    interruption_manager.resume_interrupted_tasks()

def get_interruption_status() -> Dict[str, Any]:
    """Get current interruption status"""
    return interruption_manager.get_current_status()
```

## 3. todo_manager.py

```python
from __future__ import annotations

"""Task & TODO manager that persists to a single JSON file.

The intention is to complement Cursor's session memory by giving you a quick
CLI for creating tasks, adding TODO items, marking them done, and listing
anything still pending.  The data structure purposefully mirrors the session
state design so they can be merged later if needed.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

DATA_FILE = Path(os.getcwd()) / "todo-tasks.json"

# ------------------------------------------------------------------
# Configuration -----------------------------------------------------
# ------------------------------------------------------------------
# How many days a *completed* task should be retained before it is
# automatically purged from the JSON storage.  This can be overridden
# at runtime via the TODO_CLEANUP_DAYS environment variable so teams
# can easily adjust retention without touching code.
DEFAULT_CLEANUP_DAYS = int(os.getenv("TODO_CLEANUP_DAYS", "7"))

def _load() -> Dict[str, Any]:
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text("utf-8"))
            # Opportunistically clean up outdated tasks on every load so the
            # JSON never grows unbounded even if explicit cleanup commands
            # are forgotten.
            if _cleanup_outdated_tasks(data):
                # Persist the pruned dataset immediately so the rest of the
                # call-sites operate on a consistent view.
                _save(data)
            return data
        except json.JSONDecodeError:
            pass
    return {"tasks": []}

def _cleanup_outdated_tasks(data: Dict[str, Any]) -> bool:
    """Auto-purge completed tasks older than *DEFAULT_CLEANUP_DAYS*.

    Returns True if the dataset was modified (i.e. tasks removed).
    """

    now = datetime.utcnow()

    def _is_stale(task: Dict[str, Any]) -> bool:
        if task.get("status") != "completed":
            return False

        try:
            # Prefer the last *updated* timestamp so we keep recently reopened
            # tasks even if originally created long ago.
            last = datetime.fromisoformat(task.get("updated", task.get("created")))
            return (now - last).days >= DEFAULT_CLEANUP_DAYS
        except Exception:
            # If parsing fails for whatever reason, be conservative and keep
            # the task – we don't want to delete user data accidentally.
            return False

    before = len(data.get("tasks", []))
    data["tasks"] = [t for t in data.get("tasks", []) if not _is_stale(t)]
    return len(data["tasks"]) < before

def _save(data: Dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # Update Markdown session dump for visibility.
    try:
        from cursor_memory_bridge import dump_markdown  # type: ignore

        dump_markdown()
    except Exception:
        pass
    
    # 🔄 Auto-sync state files after any data change
    try:
        from auto_sync_manager import auto_sync
        auto_sync()
    except Exception:
        pass  # Don't fail if auto-sync is not available

def _timestamp() -> str:
    """Get current Philippines time in ISO format"""
    from datetime import timezone, timedelta
    utc_now = datetime.utcnow()
    philippines_tz = timezone(timedelta(hours=8))
    ph_time = utc_now.astimezone(philippines_tz)
    return ph_time.isoformat()

def new_task(description: str) -> str:
    data = _load()
    # Create a more descriptive task ID that's not truncated
    from datetime import timezone, timedelta
    utc_now = datetime.utcnow()
    philippines_tz = timezone(timedelta(hours=8))
    ph_time = utc_now.astimezone(philippines_tz)
    timestamp = ph_time.strftime('%Y%m%dT%H%M%S')
    # Use first 50 characters of description for better readability
    desc_part = description.replace(' ', '_')[:50]
    task_id = f"{timestamp}_{desc_part}"
    
    data["tasks"].append(
        {
            "id": task_id,
            "description": description,
            "todos": [],
            "status": "in_progress",
            "created": _timestamp(),
            "updated": _timestamp(),
        }
    )
    _save(data)
    print(f"✅ Created task: {task_id}")
    print(f"   Description: {description}")
    return task_id

def add_todo(task_id: str, text: str) -> None:
    data = _load()
    task = next((t for t in data["tasks"] if t["id"] == task_id), None)
    if task is None:
        print(f"❌ Task '{task_id}' not found.")
        return
    task["todos"].append({"text": text, "done": False})
    task["updated"] = _timestamp()
    _save(data)
    print(f"✅ Added TODO: {text}")

def mark_done(task_id: str, index: int) -> None:
    data = _load()
    task = next((t for t in data["tasks"] if t["id"] == task_id), None)
    if task is None:
        print(f"❌ Task '{task_id}' not found.")
        return
    
    if not task["todos"]:
        print(f"❌ Task '{task_id}' has no TODO items to mark as done.")
        return
    
    try:
        if index < 0 or index >= len(task["todos"]):
            print(f"❌ Invalid index {index}. Valid range is 0 to {len(task['todos']) - 1}")
            return
        
        task["todos"][index]["done"] = True
        task["updated"] = _timestamp()

        # Auto-completion logic: if *all* TODO items are now done we will mark
        # the parent task as completed so downstream tooling can react accordingly
        if all(t["done"] for t in task["todos"]):
            task["status"] = "completed"

        _save(data)
        print(f"✅ Marked TODO {index} as done: {task['todos'][index]['text']}")
    except (IndexError, ValueError) as e:
        print(f"❌ Error marking TODO {index} as done: {e}")

def delete_todo(task_id: str, index: int) -> None:
    """Delete a TODO item completely from the task"""
    data = _load()
    task = next((t for t in data["tasks"] if t["id"] == task_id), None)
    if task is None:
        print(f"❌ Task '{task_id}' not found.")
        return
    
    if not task["todos"]:
        print(f"❌ Task '{task_id}' has no TODO items to delete.")
        return
    
    try:
        if index < 0 or index >= len(task["todos"]):
            print(f"❌ Invalid index {index}. Valid range is 0 to {len(task['todos']) - 1}")
            return
        
        # Get the TODO text before deleting
        todo_text = task["todos"][index]["text"]
        
        # Remove the TODO item
        deleted_todo = task["todos"].pop(index)
        task["updated"] = _timestamp()
        _save(data)
        
        print(f"🗑️  Deleted TODO {index}: {todo_text}")
        
    except (IndexError, ValueError) as e:
        print(f"❌ Error deleting TODO {index}: {e}")

def list_open_tasks() -> List[Dict[str, Any]]:
    data = _load()

    # Return newest tasks first so fresh items always grab the user's
    # attention at the top of interactive menus.
    open_tasks = [t for t in data["tasks"] if t.get("status") != "completed"]
    try:
        open_tasks.sort(key=lambda t: t.get("created", ""), reverse=True)
    except Exception:
        # Fallback – if timestamps are malformed we still return unsorted list.
        pass

    return open_tasks

def set_task_status(task_id: str, status: str) -> None:
    data = _load()
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            t["updated"] = _timestamp()
            _save(data)
            print(f"✅ Updated task '{task_id}' status to '{status}'")
            return
    print(f"❌ Task '{task_id}' not found.")

def hard_delete_task(task_id: str) -> None:
    """Completely remove task from memory (hard delete)"""
    data = _load()
    original_count = len(data["tasks"])
    
    # Remove task completely
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    
    if len(data["tasks"]) < original_count:
        _save(data)
        print(f"🗑️  Completely deleted task '{task_id}' from memory")
        
        # Also clean up from interruption manager if exists
        try:
            from task_interruption_manager import interruption_manager
            # Remove from current task if it matches
            if interruption_manager.current_task and interruption_manager.current_task['task_id'] == task_id:
                interruption_manager.current_task = None
                interruption_manager.save_state()
                print(f"   Also removed from active task")
            
            # Remove from interrupted tasks if it matches
            interruption_manager.interrupted_tasks = [
                t for t in interruption_manager.interrupted_tasks 
                if t['task_id'] != task_id
            ]
            interruption_manager.save_state()
            print(f"   Also removed from interrupted tasks")
            
        except Exception as e:
            print(f"   Note: Could not clean up interruption state: {e}")
    else:
        print(f"❌ Task '{task_id}' not found.")

def show_task_details(task_id: str) -> None:
    """Show detailed information about a specific task"""
    data = _load()
    task = next((t for t in data["tasks"] if t["id"] == task_id), None)
    if task is None:
        print(f"❌ Task '{task_id}' not found.")
        return
    
    print(f"\n📋 Task Details:")
    print(f"   ID: {task['id']}")
    print(f"   Description: {task['description']}")
    print(f"   Status: {task['status']}")
    print(f"   Created: {task['created']}")
    print(f"   Updated: {task['updated']}")
    
    if task["todos"]:
        print(f"   TODO Items ({len(task['todos'])}):")
        for i, todo in enumerate(task["todos"]):
            mark = "✔" if todo["done"] else "✗"
            status = "DONE" if todo["done"] else "PENDING"
            print(f"     [{mark}] {i}. {todo['text']} ({status})")
    else:
        print(f"   TODO Items: None (use 'add' command to add TODO items)")

# CLI implementation
def main(argv: Optional[List[str]] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Todo manager")
    sub = parser.add_subparsers(dest="cmd")

    sub_new = sub.add_parser("new", help="create a new task")
    sub_new.add_argument("description")

    sub_add = sub.add_parser("add", help="add todo to task")
    sub_add.add_argument("task_id")
    sub_add.add_argument("text")

    sub_done = sub.add_parser("done", help="mark todo item done")
    sub_done.add_argument("task_id")
    sub_done.add_argument("index", help="TODO item index (0-based)")

    sub_delete = sub.add_parser("delete", help="delete todo item completely")
    sub_delete.add_argument("task_id")
    sub_delete.add_argument("index", help="TODO item index (0-based)")

    sub_list = sub.add_parser("list", help="list open tasks")
    
    sub_show = sub.add_parser("show", help="show detailed task information")
    sub_show.add_argument("task_id")

    sub_hard_delete = sub.add_parser("hard_delete", help="completely remove task from memory")
    sub_hard_delete.add_argument("task_id")

    args = parser.parse_args(argv)

    if args.cmd == "new":
        new_task(args.description)
    elif args.cmd == "add":
        add_todo(args.task_id, args.text)
    elif args.cmd == "done":
        try:
            index = int(args.index)
        except ValueError:
            print("❌ Invalid index format. Please use a number (0, 1, 2, etc.)")
            return
        mark_done(args.task_id, index)
    elif args.cmd == "delete":
        try:
            index = int(args.index)
        except ValueError:
            print("❌ Invalid index format. Please use a number (0, 1, 2, etc.)")
            return
        delete_todo(args.task_id, index)
    elif args.cmd == "show":
        show_task_details(args.task_id)
    elif args.cmd == "hard_delete":
        hard_delete_task(args.task_id)
    else:
        tasks = list_open_tasks()
        if tasks:
            print(f"🔎 {len(tasks)} open tasks:")
            for t in tasks:
                print(f"🗒️  {t['id']}")
                print(f"   Description: {t['description']}")
                print(f"   Status: {t['status']}")
                if t["todos"]:
                    print(f"   TODO Items ({len(t['todos'])}):")
                    for i, todo in enumerate(t["todos"]):
                        mark = "✔" if todo["done"] else "✗"
                        print(f"     [{mark}] {i}. {todo['text']}")
                else:
                    print(f"   📝 No TODO items (use 'add' command to add TODO items)")
                print()
        else:
            print("🔎 No open tasks found.")
            print("   Use 'python3 todo_manager.py new <description>' to create a new task")

if __name__ == "__main__":
    main(sys.argv[1:])
``` 