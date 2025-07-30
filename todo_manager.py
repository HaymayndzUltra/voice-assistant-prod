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

DATA_FILE = Path(os.getcwd()) / "memory-bank" / "queue-system" / "tasks_active.json"

# ------------------------------------------------------------------
# Configuration -----------------------------------------------------
# ------------------------------------------------------------------
# How many days a *completed* task should be retained before it is
# automatically purged from the JSON storage.  This can be overridden
# at runtime via the TODO_CLEANUP_DAYS environment variable so teams
# can easily adjust retention without touching code.
DEFAULT_CLEANUP_DAYS = int(os.getenv("TODO_CLEANUP_DAYS", "7"))


def _load() -> List[Dict[str, Any]]:
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text("utf-8"))
            # Handle both old format {"tasks": [...]} and new format [...]
            if isinstance(data, dict) and "tasks" in data:
                data = data["tasks"]  # Convert old format to new
            # Opportunistically clean up outdated tasks on every load
            if _cleanup_outdated_tasks(data):
                _save(data)
            return data
        except json.JSONDecodeError:
            pass
    return []


# ------------------------------------------------------------------
# House-keeping helpers --------------------------------------------
# ------------------------------------------------------------------


def _cleanup_outdated_tasks(data: List[Dict[str, Any]]) -> bool:
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

    before = len(data)
    data[:] = [t for t in data if not _is_stale(t)]  # In-place modification
    return len(data) < before


def _save(data: List[Dict[str, Any]]) -> None:
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


# ------------------------------------------------------------------
# CRUD helpers ------------------------------------------------------
# ------------------------------------------------------------------

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
    
    data.append(
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
    task = next((t for t in data if t["id"] == task_id), None)
    if task is None:
        print(f"❌ Task '{task_id}' not found.")
        return
    task["todos"].append({"text": text, "done": False})
    task["updated"] = _timestamp()
    _save(data)
    print(f"✅ Added TODO: {text}")


def mark_done(task_id: str, index: int) -> None:
    data = _load()
    task = next((t for t in data if t["id"] == task_id), None)
    if task is None:
        print(f"❌ Task '{task_id}' not found.")
        return
    
    if not task["todos"]:
        print(f"❌ Task '{task_id}' has no TODO items to mark as done.")
        print(f"   Use 'python3 todo_manager.py add {task_id} <todo_text>' to add TODO items first.")
        return
    
    try:
        if index < 0 or index >= len(task["todos"]):
            print(f"❌ Invalid index {index}. Valid range is 0 to {len(task['todos']) - 1}")
            print(f"   Available TODO items:")
            for i, todo in enumerate(task["todos"]):
                mark = "✔" if todo["done"] else "✗"
                print(f"   [{mark}] {i}. {todo['text']}")
            return
        
        task["todos"][index]["done"] = True
        task["updated"] = _timestamp()

        # ------------------------------------------------------------------
        # Auto-completion logic: if *all* TODO items are now done we will mark
        # the parent task as completed so downstream tooling (e.g. UI lists,
        # cleanup) can react accordingly without relying on manual commands.
        # ------------------------------------------------------------------
        if all(t["done"] for t in task["todos"]):
            task["status"] = "completed"

        _save(data)
        print(f"✅ Marked TODO {index} as done: {task['todos'][index]['text']}")
    except (IndexError, ValueError) as e:
        print(f"❌ Error marking TODO {index} as done: {e}")
        print(f"   Available TODO items:")
        for i, todo in enumerate(task["todos"]):
            mark = "✔" if todo["done"] else "✗"
            print(f"   [{mark}] {i}. {todo['text']}")


def delete_todo(task_id: str, index: int) -> None:
    """Delete a TODO item completely from the task"""
    data = _load()
    task = next((t for t in data if t["id"] == task_id), None)
    if task is None:
        print(f"❌ Task '{task_id}' not found.")
        return
    
    if not task["todos"]:
        print(f"❌ Task '{task_id}' has no TODO items to delete.")
        return
    
    try:
        if index < 0 or index >= len(task["todos"]):
            print(f"❌ Invalid index {index}. Valid range is 0 to {len(task['todos']) - 1}")
            print(f"   Available TODO items:")
            for i, todo in enumerate(task["todos"]):
                mark = "✔" if todo["done"] else "✗"
                print(f"   [{mark}] {i}. {todo['text']}")
            return
        
        # Get the TODO text before deleting
        todo_text = task["todos"][index]["text"]
        
        # Remove the TODO item
        deleted_todo = task["todos"].pop(index)
        task["updated"] = _timestamp()
        _save(data)
        
        print(f"🗑️  Deleted TODO {index}: {todo_text}")
        
        # Show remaining TODO items
        if task["todos"]:
            print(f"   Remaining TODO items:")
            for i, todo in enumerate(task["todos"]):
                mark = "✔" if todo["done"] else "✗"
                print(f"   [{mark}] {i}. {todo['text']}")
        else:
            print(f"   No TODO items remaining.")
            
    except (IndexError, ValueError) as e:
        print(f"❌ Error deleting TODO {index}: {e}")
        print(f"   Available TODO items:")
        for i, todo in enumerate(task["todos"]):
            mark = "✔" if todo["done"] else "✗"
            print(f"   [{mark}] {i}. {todo['text']}")


def list_open_tasks() -> List[Dict[str, Any]]:
    data = _load()

    # Return newest tasks first so fresh items always grab the user's
    # attention at the top of interactive menus.
    open_tasks = [t for t in data if t.get("status") != "completed"]
    try:
        open_tasks.sort(key=lambda t: t.get("created", ""), reverse=True)
    except Exception:
        # Fallback – if timestamps are malformed we still return unsorted list.
        pass

    return open_tasks


def set_task_status(task_id: str, status: str) -> None:
    data = _load()
    for t in data:
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
    original_count = len(data)
    
    # Remove task completely  
    data[:] = [t for t in data if t["id"] != task_id]  # In-place modification
    
    if len(data) < original_count:
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
        
        # Clean up memory-bank files
        try:
            import os
            from pathlib import Path
            
            # Clean up current-session.md if it contains the deleted task
            session_file = Path("memory-bank/current-session.md")
            if session_file.exists():
                content = session_file.read_text(encoding='utf-8')
                if task_id in content:
                    # Remove the task reference from the session file
                    lines = content.split('\n')
                    cleaned_lines = []
                    skip_next = False
                    
                    for line in lines:
                        if task_id in line:
                            skip_next = True
                            continue
                        if skip_next and line.strip() == "":
                            skip_next = False
                            continue
                        if not skip_next:
                            cleaned_lines.append(line)
                    
                    session_file.write_text('\n'.join(cleaned_lines), encoding='utf-8')
                    print(f"   Also cleaned up memory-bank/current-session.md")
            
            # Clean up cursor_state.json if it contains the deleted task
            cursor_file = Path("cursor_state.json")
            if cursor_file.exists():
                import json
                try:
                    with open(cursor_file, 'r') as f:
                        cursor_data = json.load(f)
                    
                    # Check if current_task contains the deleted task description
                    current_task = cursor_data.get('cursor_session', {}).get('current_task', '')
                    if task_id in current_task:
                        # Clear the current task
                        cursor_data['cursor_session']['current_task'] = ""
                        cursor_data['cursor_session']['progress'] = 0.0
                        
                        with open(cursor_file, 'w') as f:
                            json.dump(cursor_data, f, indent=2)
                        print(f"   Also cleaned up cursor_state.json")
                except Exception as e:
                    print(f"   Note: Could not clean up cursor state: {e}")
                    
        except Exception as e:
            print(f"   Note: Could not clean up memory-bank files: {e}")
    else:
        print(f"❌ Task '{task_id}' not found.")


def cleanup_completed_tasks() -> None:
    """Remove all completed tasks from memory"""
    data = _load()
    original_count = len(data)
    
    # Keep only non-completed tasks
    data[:] = [t for t in data if t.get("status") != "completed"]  # In-place modification
    
    removed_count = original_count - len(data)
    
    if removed_count > 0:
        _save(data)
        print(f"🧹 Cleaned up {removed_count} completed task(s) from memory")
    else:
        print("ℹ️  No completed tasks to clean up")


def show_task_details(task_id: str) -> None:
    """Show detailed information about a specific task"""
    data = _load()
    task = next((t for t in data if t["id"] == task_id), None)
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


# ------------------------------------------------------------------
# CLI ----------------------------------------------------------------
# ------------------------------------------------------------------

def _print_task(task: Dict[str, Any]) -> None:
    print(f"🗒️  {task['id']}")
    print(f"   Description: {task['description']}")
    print(f"   Status: {task['status']}")
    if task["todos"]:
        print(f"   TODO Items ({len(task['todos'])}):")
        for i, todo in enumerate(task["todos"]):
            mark = "✔" if todo["done"] else "✗"
            print(f"     [{mark}] {i}. {todo['text']}")
    else:
        print(f"   📝 No TODO items (use 'add' command to add TODO items)")
    print()  # Add spacing for better readability


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

    sub_cleanup = sub.add_parser("cleanup", help="remove all completed tasks from memory")

    args = parser.parse_args(argv)

    if args.cmd == "new":
        new_task(args.description)
    elif args.cmd == "add":
        add_todo(args.task_id, args.text)
    elif args.cmd == "done":
        # Handle index parsing manually to support various formats
        try:
            # Try to parse as integer first
            index = int(args.index)
        except ValueError:
            # If it's not a number, check if it's a special format
            if args.index == "—" or args.index == "-":
                print("❌ Invalid index format. Please use a number (0, 1, 2, etc.)")
                print("   Example: python3 todo_manager.py done <task_id> 0")
                return
            else:
                print(f"❌ Invalid index '{args.index}'. Please use a number (0, 1, 2, etc.)")
                print("   Example: python3 todo_manager.py done <task_id> 0")
                return
        
        mark_done(args.task_id, index)
    elif args.cmd == "delete":
        # Handle index parsing manually to support various formats
        try:
            # Try to parse as integer first
            index = int(args.index)
        except ValueError:
            # If it's not a number, check if it's a special format
            if args.index == "—" or args.index == "-":
                print("❌ Invalid index format. Please use a number (0, 1, 2, etc.)")
                print("   Example: python3 todo_manager.py delete <task_id> 0")
                return
            else:
                print(f"❌ Invalid index '{args.index}'. Please use a number (0, 1, 2, etc.)")
                print("   Example: python3 todo_manager.py delete <task_id> 0")
                return
        
        delete_todo(args.task_id, index)
    elif args.cmd == "show":
        show_task_details(args.task_id)
    elif args.cmd == "hard_delete":
        hard_delete_task(args.task_id)
    elif args.cmd == "cleanup":
        cleanup_completed_tasks()
    else:
        tasks = list_open_tasks()
        if tasks:
            print(f"🔎 {len(tasks)} open tasks:")
            for t in tasks:
                _print_task(t)
                print()  # Add spacing between tasks
        else:
            print("🔎 No open tasks found.")
            print("   Use 'python3 todo_manager.py new <description>' to create a new task")


if __name__ == "__main__":
    main(sys.argv[1:])