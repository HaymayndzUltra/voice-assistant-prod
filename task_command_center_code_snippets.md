# Task Command Center - Complete Code Snippets

This document contains the full source code for all modules related to the Task Command Center system, as requested for direct review and verification.

---

## `task_command_center.py`

```python
from __future__ import annotations

import argparse
import pprint

from auto_sync_manager import auto_sync
from task_interruption_manager import TaskInterruptionManager
from todo_manager import (add_todo, hard_delete_task, list_all_tasks, new_task,
                        toggle_todo)
from workflow_memory_intelligence import 
    IntelligentTaskChunker as FallbackIntelligentTaskChunker
from workflow_memory_intelligence import 
    SmartTaskExecutionManager as FallbackSmartTaskExecutionManager
from workflow_memory_intelligence_fixed import 
    IntelligentTaskChunker as FixedIntelligentTaskChunker
from workflow_memory_intelligence_fixed import 
    SmartTaskExecutionManager as FixedSmartTaskExecutionManager


class TaskCommandCenter:
    """Interactive command center for task management."""

    def __init__(self):
        auto_sync()  # Ensure all state files are in sync on startup
        self.interruption_manager = TaskInterruptionManager()
        self.interruption_manager.resume_all_interrupted_tasks()

    def view_tasks(self, show_completed: bool = False):
        """Display all tasks, optionally including completed ones."""
        tasks = list_all_tasks(include_completed=show_completed)
        if not tasks:
            print("No tasks found.")
            return
        for task in tasks:
            status = "✅" if task.get('done') else "🕒"
            print(f"\n{status} Task: {task['description']} (ID: {task['id']})")
            for todo in task.get('todos', []):
                todo_status = "✅" if todo.get('done') else "🔲"
                print(f"    {todo_status} {todo['text']}")

    def start_task(self, task_id: int):
        """Start a new task, interrupting any ongoing task."""
        self.interruption_manager.start_task(task_id)

    def interrupt_task(self):
        """Interrupt the currently active task."""
        self.interruption_manager.interrupt_task()

    def resume_task(self, task_id: int):
        """Resume an interrupted task."""
        self.interruption_manager.resume_task(task_id)

    def intelligent_execute(self, task_id: int, use_fallback: bool = False):
        """Execute a task with AI-powered chunking and intelligence."""
        if use_fallback:
            chunker = FallbackIntelligentTaskChunker()
            executor = FallbackSmartTaskExecutionManager()
        else:
            chunker = FixedIntelligentTaskChunker()
            executor = FixedSmartTaskExecutionManager()

        tasks = list_all_tasks()
        task = next((t for t in tasks if t['id'] == task_id), None)

        if not task:
            print(f"Error: Task with ID {task_id} not found.")
            return

        print(f"Executing task: {task['description']}")
        chunks, analysis = chunker.chunk_task(task)
        print("\nTask analysis:")
        pprint.pprint(analysis)

        print("\nExecuting chunks:")
        executor.execute_task_chunks(chunks)


def main():
    parser = argparse.ArgumentParser(description="Task Command Center")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # View command
    view_parser = subparsers.add_parser("view", help="View all tasks")
    view_parser.add_argument("--completed", action="store_true", help="Include completed tasks")

    # New task command
    new_parser = subparsers.add_parser("new", help="Create a new task")
    new_parser.add_argument("description", type=str, help="The task description")

    # Add todo command
    add_todo_parser = subparsers.add_parser("add_todo", help="Add a TODO item to a task")
    add_todo_parser.add_argument("task_id", type=int, help="The ID of the task")
    add_todo_parser.add_argument("text", type=str, help="The TODO item text")

    # Toggle todo command
    toggle_parser = subparsers.add_parser("toggle", help="Toggle a TODO item's status")
    toggle_parser.add_argument("task_id", type=int, help="The ID of the task")
    toggle_parser.add_argument("todo_index", type=int, help="The index of the TODO item")

    # Delete task command
    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("task_id", type=int, help="The ID of the task")

    # Start task command
    start_parser = subparsers.add_parser("start", help="Start a task")
    start_parser.add_argument("task_id", type=int, help="The ID of the task to start")

    # Interrupt task command
    subparsers.add_parser("interrupt", help="Interrupt the current task")

    # Resume task command
    resume_parser = subparsers.add_parser("resume", help="Resume an interrupted task")
    resume_parser.add_argument("task_id", type=int, help="The ID of the task to resume")

    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Intelligently execute a task")
    execute_parser.add_argument("task_id", type=int, help="The ID of the task to execute")
    execute_parser.add_argument("--fallback", action="store_true", help="Use fallback intelligence module")

    args = parser.parse_args()
    center = TaskCommandCenter()

    if args.command == "view":
        center.view_tasks(show_completed=args.completed)
    elif args.command == "new":
        new_task(args.description)
        print(f"New task created: {args.description}")
    elif args.command == "add_todo":
        add_todo(args.task_id, args.text)
        print(f"Added TODO to task {args.task_id}: {args.text}")
    elif args.command == "toggle":
        toggle_todo(args.task_id, args.todo_index)
        print(f"Toggled TODO {args.todo_index} for task {args.task_id}")
    elif args.command == "delete":
        hard_delete_task(args.task_id)
        print(f"Deleted task {args.task_id}")
    elif args.command == "start":
        center.start_task(args.task_id)
    elif args.command == "interrupt":
        center.interrupt_task()
    elif args.command == "resume":
        center.resume_task(args.task_id)
    elif args.command == "execute":
        center.intelligent_execute(args.task_id, use_fallback=args.fallback)


if __name__ == "__main__":
    main()

```

---

## `task_interruption_manager.py`

```python
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import todo_manager
from task_state_manager import add_completed_task, load_task_state, save_task_state

STATE_FILE = os.path.join(os.getcwd(), "task_interruption_state.json")


class TaskInterruptionManager:
    """Handles automatic task interruption and resumption."""

    def __init__(self):
        self._state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"active_task_id": None, "interrupted_tasks": []}

    def _save_state(self) -> None:
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except OSError:
            pass

    def get_current_task_id(self) -> Optional[int]:
        return self._state.get("active_task_id")

    def start_task(self, task_id: int) -> None:
        """Start a new task, interrupting the current one if it exists."""
        current_task_id = self.get_current_task_id()
        if current_task_id is not None and current_task_id != task_id:
            self.interrupt_task()

        self._state["active_task_id"] = task_id
        self._state["active_task_start_time"] = datetime.utcnow().isoformat()
        self._save_state()
        print(f"Task {task_id} started.")

    def interrupt_task(self) -> None:
        """Interrupt the currently active task and save its state."""
        task_id = self.get_current_task_id()
        if task_id is None:
            print("No active task to interrupt.")
            return

        task_details = todo_manager.get_task(task_id)
        if not task_details:
            print(f"Warning: Could not find details for active task {task_id}.")
            return

        interruption_time = datetime.utcnow().isoformat()
        interrupted_task = {
            "task_id": task_id,
            "description": task_details.get("description"),
            "interrupted_at": interruption_time,
            "state_snapshot": load_task_state(),  # Save current task state
        }

        self._state["interrupted_tasks"].append(interrupted_task)
        self._state["active_task_id"] = None
        self._state.pop("active_task_start_time", None)
        self._save_state()
        print(f"Task {task_id} interrupted.")

    def resume_task(self, task_id: int) -> None:
        """Resume an interrupted task, interrupting any other active task."""
        interrupted_task = self._find_interrupted(task_id)
        if not interrupted_task:
            print(f"No interrupted task with ID {task_id} found.")
            return

        # Interrupt current task before resuming another
        if self.get_current_task_id() is not None:
            self.interrupt_task()

        # Restore state and make active
        save_task_state(interrupted_task.get("state_snapshot", {}))
        self._state["interrupted_tasks"] = [
            t for t in self._state["interrupted_tasks"] if t["task_id"] != task_id
        ]
        self.start_task(task_id)
        print(f"Task {task_id} resumed.")

    def complete_task(self, task_id: int) -> None:
        """Mark the active task as complete."""
        if self.get_current_task_id() != task_id:
            print(f"Error: Task {task_id} is not the active task.")
            return

        task_details = todo_manager.get_task(task_id)
        if task_details:
            add_completed_task(task_details["description"])
            todo_manager.mark_task_done(task_id)

        self._state["active_task_id"] = None
        self._state.pop("active_task_start_time", None)
        self._save_state()
        print(f"Task {task_id} completed.")

    def list_interrupted_tasks(self) -> List[Dict[str, Any]]:
        return self._state.get("interrupted_tasks", [])

    def _find_interrupted(self, task_id: int) -> Optional[Dict[str, Any]]:
        return next(
            (t for t in self._state["interrupted_tasks"] if t["task_id"] == task_id),
            None,
        )

    def auto_task_handler(self, task_id: int, action: str):
        """Generic handler for CLI integration."""
        if action == "start":
            self.start_task(task_id)
        elif action == "interrupt":
            if self.get_current_task_id() == task_id:
                self.interrupt_task()
            else:
                print(f"Task {task_id} is not active.")
        elif action == "resume":
            self.resume_task(task_id)
        elif action == "complete":
            self.complete_task(task_id)
        else:
            print(f"Unknown action: {action}")

    def resume_all_interrupted_tasks(self):
        """Resume all tasks that were previously interrupted."""
        interrupted_tasks = self.list_interrupted_tasks()
        if not interrupted_tasks:
            print("No interrupted tasks to resume.")
            return

        print(f"Found {len(interrupted_tasks)} interrupted tasks. Resuming...")
        for task in list(interrupted_tasks):  # Iterate over a copy
            self.resume_task(task['task_id'])


# CLI for direct interaction
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Task Interruption Manager")
    parser.add_argument("action", choices=["start", "interrupt", "resume", "complete", "list", "resume_all"])
    parser.add_argument("task_id", type=int, nargs="?", help="Task ID for actions")

    args = parser.parse_args()
    manager = TaskInterruptionManager()

    if args.action == "list":
        tasks = manager.list_interrupted_tasks()
        if not tasks:
            print("No interrupted tasks.")
        else:
            print("Interrupted tasks:")
            for t in tasks:
                print(f"  - ID: {t['task_id']}, Desc: {t['description']}, At: {t['interrupted_at']}")
    elif args.action == "resume_all":
        manager.resume_all_interrupted_tasks()
    elif args.task_id is None:
        # Interrupt does not require a task_id, it acts on the current task
        if args.action == 'interrupt':
            manager.interrupt_task()
        else:
            print(f"Error: Action '{args.action}' requires a task_id.")
    else:
        manager.auto_task_handler(args.task_id, args.action)

```

---

## `todo_manager.py`

```python
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# Late import to prevent circular dependency
import auto_sync_manager

# Optional import for markdown dumping
try:
    from cursor_memory_bridge import dump_markdown
except ImportError:
    dump_markdown = None

TODO_FILE = os.path.join(os.getcwd(), "todo-tasks.json")


def _load_tasks() -> List[Dict[str, Any]]:
    if not os.path.exists(TODO_FILE):
        return []
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_tasks(tasks: List[Dict[str, Any]]) -> None:
    try:
        with open(TODO_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
        auto_sync_manager.auto_sync()  # Sync after every change
        if dump_markdown:
            dump_markdown()  # Update human-readable note
    except OSError:
        pass


def _get_next_id(tasks: List[Dict[str, Any]]) -> int:
    return max([task["id"] for task in tasks] + [0]) + 1


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def new_task(description: str) -> Dict[str, Any]:
    tasks = _load_tasks()
    task = {
        "id": _get_next_id(tasks),
        "description": description,
        "created_at": datetime.utcnow().isoformat(),
        "done": False,
        "todos": [],
    }
    tasks.append(task)
    _save_tasks(tasks)
    return task


def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    return next((task for task in _load_tasks() if task["id"] == task_id), None)


def list_all_tasks(include_completed: bool = False) -> List[Dict[str, Any]]:
    tasks = _load_tasks()
    if include_completed:
        return tasks
    return [task for task in tasks if not task.get("done")]


def list_open_tasks() -> List[Dict[str, Any]]:
    """Convenience function to get only open tasks."""
    return list_all_tasks(include_completed=False)


def add_todo(task_id: int, text: str) -> bool:
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return False
    task.setdefault("todos", []).append({"text": text, "done": False})
    _save_tasks(tasks)
    return True


def toggle_todo(task_id: int, todo_index: int) -> bool:
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task or not 0 <= todo_index < len(task.get("todos", [])):
        return False
    task["todos"][todo_index]["done"] = not task["todos"][todo_index]["done"]
    _save_tasks(tasks)
    return True


def mark_task_done(task_id: int) -> bool:
    tasks = _load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        return False
    task["done"] = True
    _save_tasks(tasks)
    return True


def hard_delete_task(task_id: int) -> bool:
    tasks = _load_tasks()
    original_len = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]
    if len(tasks) < original_len:
        _save_tasks(tasks)
        return True
    return False


def cleanup_completed_tasks(days_old: int = 30) -> int:
    """Remove completed tasks older than a certain number of days."""
    tasks = _load_tasks()
    cutoff = datetime.utcnow() - timedelta(days=days_old)
    tasks_to_keep = []
    for task in tasks:
        if not task.get("done"): # Keep all open tasks
            tasks_to_keep.append(task)
            continue
        
        completed_at_str = task.get("completed_at") # Assuming you add this field when marking done
        if completed_at_str:
            completed_at = datetime.fromisoformat(completed_at_str)
            if completed_at > cutoff:
                tasks_to_keep.append(task)
    
    if len(tasks_to_keep) < len(tasks):
        _save_tasks(tasks_to_keep)
    return len(tasks) - len(tasks_to_keep)


def get_task_details_string(task_id: int) -> str:
    """Return a formatted string with details of a specific task."""
    task = get_task(task_id)
    if not task:
        return f"No task found with ID: {task_id}"

    details = []
    status = "✅ Done" if task.get('done') else "🕒 In Progress"
    details.append(f"ID: {task['id']}")
    details.append(f"Description: {task['description']}")
    details.append(f"Status: {status}")
    details.append(f"Created At: {task.get('created_at', 'N/A')}")

    todos = task.get('todos', [])
    if todos:
        details.append("\nTODOs:")
        for i, todo in enumerate(todos):
            todo_status = "✅" if todo.get('done') else "🔲"
            details.append(f"  {i}. {todo_status} {todo['text']}")
    else:
        details.append("\nNo TODOs for this task.")

    return "\n".join(details)


# CLI for simple interactions
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TODO List Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List command
    list_parser = subparsers.add_parser("list", help="List all tasks")
    list_parser.add_argument("--all", action="store_true", help="Include completed tasks")

    # New command
    new_parser = subparsers.add_parser("new", help="Create a new task")
    new_parser.add_argument("description", type=str, help="The task description")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a TODO to a task")
    add_parser.add_argument("task_id", type=int, help="The ID of the task")
    add_parser.add_argument("text", type=str, help="The TODO item text")

    # Done command
    done_parser = subparsers.add_parser("done", help="Mark a TODO as done")
    done_parser.add_argument("task_id", type=int, help="The ID of the task")
    done_parser.add_argument("todo_index", type=int, help="The index of the TODO item")

    # Task done command
    task_done_parser = subparsers.add_parser("taskdone", help="Mark an entire task as done")
    task_done_parser.add_argument("task_id", type=int, help="The ID of the task")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("task_id", type=int, help="The ID of the task")

    # Detail command
    detail_parser = subparsers.add_parser("detail", help="Show details for a specific task")
    detail_parser.add_argument("task_id", type=int, help="The ID of the task")

    args = parser.parse_args()

    if args.command == "list":
        tasks = list_all_tasks(include_completed=args.all)
        if not tasks:
            print("No tasks found.")
        else:
            for task in tasks:
                status = "✅" if task.get('done') else "🕒"
                print(f"{status} {task['description']} (ID: {task['id']})")
                for todo in task.get('todos', []):
                    todo_status = "✅" if todo.get('done') else "🔲"
                    print(f"    {todo_status} {todo['text']}")
    elif args.command == "new":
        new_task(args.description)
        print(f"Task '{args.description}' created.")
    elif args.command == "add":
        if add_todo(args.task_id, args.text):
            print("TODO added.")
        else:
            print("Task not found.")
    elif args.command == "done":
        if toggle_todo(args.task_id, args.todo_index):
            print("TODO status toggled.")
        else:
            print("Task or TODO not found.")
    elif args.command == "taskdone":
        if mark_task_done(args.task_id):
            print("Task marked as done.")
        else:
            print("Task not found.")
    elif args.command == "delete":
        if hard_delete_task(args.task_id):
            print("Task deleted.")
        else:
            print("Task not found.")
    elif args.command == "detail":
        print(get_task_details_string(args.task_id))

```

---

## `workflow_memory_intelligence_fixed.py`

```python
from __future__ import annotations

import pprint
from typing import Any, Dict, List, Tuple

from auto_detect_chunker import AutoDetectChunker
from command_chunker import CommandChunker

# Optional imports for telemetry and memory
try:
    from memory_system.services import memory_provider
    from memory_system.services import telemetry
except ImportError:
    memory_provider = None
    telemetry = None


class TaskComplexityAnalyzer:
    """Analyzes task complexity to guide chunking and execution."""

    def analyze(self, task: Dict[str, Any]) -> Dict[str, Any]:
        num_todos = len(task.get("todos", []))
        description_len = len(task.get("description", ""))
        complexity_score = (num_todos * 10) + (description_len // 20)

        if complexity_score > 100:
            level = "HIGH"
        elif complexity_score > 40:
            level = "MEDIUM"
        else:
            level = "LOW"

        return {
            "complexity_score": complexity_score,
            "level": level,
            "num_todos": num_todos,
            "description_length": description_len,
        }


class IntelligentTaskChunker:
    """Breaks down tasks into actionable, memory-optimized chunks."""

    def __init__(self):
        self.analyzer = TaskComplexityAnalyzer()
        self.auto_chunker = AutoDetectChunker()
        self.command_chunker = CommandChunker()

    def chunk_task(self, task: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if telemetry:
            with telemetry.span("chunk_task.fixed", task_id=task.get("id")):
                return self._chunk_task_internal(task)
        else:
            return self._chunk_task_internal(task)

    def _chunk_task_internal(self, task: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        analysis = self.analyzer.analyze(task)
        full_text = task["description"] + "\n\n" + "\n".join(
            [f"- {td['text']}" for td in task.get("todos", [])]
        )

        # Use command chunker for shell-like tasks
        if task["description"].lower().startswith(("run:", "exec:", "shell:")):
            command = task["description"].split(":", 1)[1].strip()
            chunks, chunk_analysis = [command], {"num_chunks": 1}
            if len(command) > 200: # Simple heuristic
                chunks = self.command_chunker.chunk_command(command, strategy="auto")
                chunk_analysis = {"num_chunks": len(chunks), "strategy": "command_chunker"}
        else:
            chunks, chunk_analysis = self.auto_chunker.auto_chunk(full_text)

        action_items = self._extract_action_items(chunks, task)
        analysis.update(chunk_analysis)
        return action_items, analysis

    def _extract_action_items(self, chunks: List[str], task: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = []
        for i, chunk_text in enumerate(chunks):
            items.append(
                {
                    "task_id": task["id"],
                    "chunk_id": i,
                    "type": "informational_chunk",
                    "content": chunk_text,
                    "is_complete": False,
                }
            )
        return items


class SmartTaskExecutionManager:
    """Executes a sequence of task chunks with memory and context."""

    def __init__(self):
        self.memory = memory_provider.get_provider() if memory_provider else None

    def execute_task_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        if not chunks:
            return

        print(f"Starting execution of {len(chunks)} chunks.")
        for chunk in chunks:
            if telemetry:
                with telemetry.span("execute_chunk.fixed", chunk_id=chunk.get("chunk_id")):
                    self._execute_single_chunk(chunk)
            else:
                self._execute_single_chunk(chunk)

    def _execute_single_chunk(self, chunk: Dict[str, Any]) -> None:
        print(f"--- Executing Chunk {chunk['chunk_id']} ---")
        # In a real system, this would involve LLM calls, tool use, etc.
        # Here, we simulate by printing the content and searching memory.
        pprint.pprint(chunk["content"])

        if self.memory:
            # Simulate searching for related memories
            keywords = chunk["content"].split()[:5]  # Use first 5 words as keywords
            for keyword in keywords:
                results = self.memory.search(keyword)
                if results:
                    print(f"  [Memory] Found related info for '{keyword}': {results}")
                    break
        print("--- Chunk Complete ---\n")


# CLI for testing
if __name__ == "__main__":
    # Mock task for demonstration
    mock_task = {
        "id": 101,
        "description": "Analyze user feedback from the last sprint and create a summary report. The feedback is located in 'feedback.log'. Also, run the script 'generate_report.sh' which processes this log.",
        "todos": [
            {"text": "Read and parse feedback.log", "done": False},
            {"text": "Categorize feedback into bugs, features, and suggestions", "done": False},
            {"text": "Generate charts for each category", "done": False},
            {"text": "Write a 2-paragraph summary of key findings", "done": False},
            {"text": "Execute generate_report.sh to finalize", "done": False},
        ],
    }

    chunker = IntelligentTaskChunker()
    executor = SmartTaskExecutionManager()

    action_chunks, full_analysis = chunker.chunk_task(mock_task)

    print("=== TASK ANALYSIS ===")
    pprint.pprint(full_analysis)
    print("\n=== ACTION CHUNKS ===")
    pprint.pprint(action_chunks)
    print("\n=== EXECUTION ===")
    executor.execute_task_chunks(action_chunks)

```

---

## `workflow_memory_intelligence.py`

```python
from __future__ import annotations

import pprint
from typing import Any, Dict, List, Tuple

# This is the fallback/original version of the workflow intelligence system.
# It has a simpler structure and less sophisticated chunking.

# Optional imports for telemetry and memory
try:
    from memory_system.services import memory_provider
    from memory_system.services import telemetry
except ImportError:
    memory_provider = None
    telemetry = None


class TaskComplexityAnalyzer:
    """Analyzes task complexity (simpler version)."""

    def analyze(self, task: Dict[str, Any]) -> Dict[str, Any]:
        num_todos = len(task.get("todos", []))
        description_len = len(task.get("description", ""))
        # Simpler scoring
        complexity_score = num_todos + (description_len // 50)

        if complexity_score > 10:
            level = "COMPLEX"
        elif complexity_score > 3:
            level = "MODERATE"
        else:
            level = "SIMPLE"

        return {
            "complexity_score": complexity_score,
            "level": level,
        }


class IntelligentTaskChunker:
    """Breaks down tasks into simple, sequential chunks."""

    def __init__(self):
        self.analyzer = TaskComplexityAnalyzer()

    def chunk_task(self, task: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        if telemetry:
            with telemetry.span("chunk_task.fallback", task_id=task.get("id")):
                return self._chunk_task_internal(task)
        else:
            return self._chunk_task_internal(task)

    def _chunk_task_internal(self, task: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        analysis = self.analyzer.analyze(task)
        chunks = []

        # First chunk is always the main description
        chunks.append(task["description"])

        # Subsequent chunks are the TODO items
        for todo in task.get("todos", []):
            chunks.append(todo["text"])

        action_items = self._extract_action_items(chunks, task)
        analysis["num_chunks"] = len(action_items)
        return action_items, analysis

    def _extract_action_items(self, chunks: List[str], task: Dict[str, Any]) -> List[Dict[str, Any]]:
        items = []
        for i, chunk_text in enumerate(chunks):
            items.append(
                {
                    "task_id": task["id"],
                    "chunk_id": i,
                    "content": chunk_text,
                }
            )
        return items


class SmartTaskExecutionManager:
    """Executes a sequence of task chunks (simpler version)."""

    def __init__(self):
        self.memory = memory_provider.get_provider() if memory_provider else None

    def execute_task_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        if not chunks:
            return

        for chunk in chunks:
            if telemetry:
                with telemetry.span("execute_chunk.fallback", chunk_id=chunk.get("chunk_id")):
                    self._execute_single_chunk(chunk)
            else:
                self._execute_single_chunk(chunk)

    def _execute_single_chunk(self, chunk: Dict[str, Any]) -> None:
        print(f">>> Executing: {chunk['content']}")
        # Simulation of work
        if self.memory:
            results = self.memory.search(chunk['content'].split()[0]) # Search by first word
            if results:
                print(f"    -> Found memory: {results[0]}")


# CLI for testing
if __name__ == "__main__":
    mock_task = {
        "id": 202,
        "description": "Deploy the new model to staging.",
        "todos": [
            {"text": "Update the docker-compose file.", "done": False},
            {"text": "Run the build script.", "done": False},
            {"text": "Push the image to the registry.", "done": False},
            {"text": "Update the Kubernetes deployment config.", "done": False},
        ],
    }

    chunker = IntelligentTaskChunker()
    executor = SmartTaskExecutionManager()

    action_chunks, full_analysis = chunker.chunk_task(mock_task)

    print("=== FALLBACK ANALYSIS ===")
    pprint.pprint(full_analysis)
    print("\n=== FALLBACK EXECUTION ===")
    executor.execute_task_chunks(action_chunks)

```

---

## `auto_sync_manager.py`

```python
from __future__ import annotations

import json
import os
from typing import Any, Dict

# Import managers for state manipulation
import cursor_session_manager
import task_interruption_manager
import task_state_manager
import todo_manager


def auto_sync() -> None:
    """Sync all state files to ensure consistency with the source of truth (todo-tasks.json)."""
    # 1. Get the ground truth: the list of open tasks
    open_tasks = todo_manager.list_open_tasks()
    active_task_ids = {task['id'] for task in open_tasks}

    # 2. Sync Task Interruption State
    sync_task_interruption_state(active_task_ids)

    # 3. Sync Task State
    sync_task_state(open_tasks)

    # 4. Sync Cursor Session State
    sync_cursor_session(open_tasks)

    # 5. (Optional) Update human-readable markdown file
    try:
        from cursor_memory_bridge import dump_markdown
        dump_markdown()
    except ImportError:
        pass

    print("Auto-sync complete. All state files are consistent.")


def sync_task_interruption_state(active_task_ids: set[int]) -> None:
    """Ensure the interrupted tasks list is accurate."""
    manager = task_interruption_manager.TaskInterruptionManager()
    interrupted_tasks = manager.list_interrupted_tasks()
    
    # Remove any interrupted tasks that are no longer in the main todo list (i.e., deleted)
    cleaned_interrupted = [t for t in interrupted_tasks if t['task_id'] in active_task_ids]
    
    if len(cleaned_interrupted) != len(interrupted_tasks):
        manager._state['interrupted_tasks'] = cleaned_interrupted
        manager._save_state()

    # If the globally active task is no longer in the open list, clear it
    current_active_id = manager.get_current_task_id()
    if current_active_id and current_active_id not in active_task_ids:
        manager._state['active_task_id'] = None
        manager._save_state()


def sync_task_state(open_tasks: list[dict]) -> None:
    """Update task-state.json with the latest from the source of truth."""
    # This is a simple example; a real implementation might be more complex
    # For now, we just ensure the list of open tasks is present in the state file
    current_task_state = task_state_manager.load_task_state()
    current_task_state['open_tasks_snapshot'] = [
        {'id': t['id'], 'description': t['description']} for t in open_tasks
    ]
    task_state_manager.save_task_state(current_task_state)


def sync_cursor_session(open_tasks: list[dict]) -> None:
    """Ensure the cursor session reflects the current reality of tasks."""
    session = cursor_session_manager.session_manager
    state = session.get_state()
    cursor = state.get('cursor_session', {})
    current_task_desc = cursor.get('current_task')

    if not current_task_desc:
        return # Nothing to sync if no task is set

    # Check if the task in the cursor session is still an open task
    is_task_still_open = any(t['description'] == current_task_desc for t in open_tasks)

    if not is_task_still_open:
        # The task is completed or deleted, so clear it from the cursor session
        session.update(current_task=None, progress=None)


# CLI for manual sync
if __name__ == "__main__":
    print("Performing manual state synchronization...")
    auto_sync()

```

---

## `task_state_manager.py`

```python
from __future__ import annotations

"""Minimal task state manager with optional Cursor session awareness.

This module *replaces* the absent legacy implementation referenced in the prompt.
For broader projects already shipping a task_state_manager module you can safely
import the `save_task_state` and `load_task_state` helpers below – the public API
is intentionally tiny so integration is painless.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any

from cursor_session_manager import session_manager

STATE_FILE = os.path.join(os.getcwd(), "task-state.json")


# ------------------------------------------------------------------
# Core helpers ------------------------------------------------------
# ------------------------------------------------------------------

def load_task_state() -> Dict[str, Any]:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def save_task_state(extra_state: Dict[str, Any] | None = None) -> None:
    """Merge *extra_state* with the current session state and persist it."""
    state: Dict[str, Any] = load_task_state()
    state.update(extra_state or {})
    # Inject cursor session so everything is centralised.
    state["cursor_session"] = session_manager.get_state().get("cursor_session", {})
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as fp:
            json.dump(state, fp, indent=2, ensure_ascii=False)
    except OSError:
        pass


# ------------------------------------------------------------------
# Convenience API ---------------------------------------------------
# ------------------------------------------------------------------

def add_completed_task(description: str) -> None:
    """Append a completed task entry with timestamp into task history."""
    state = load_task_state()
    history = state.setdefault("task_history", [])
    history.append({"task": description, "completed": datetime.utcnow().isoformat()})
    save_task_state(state)


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser(description="Task state helper")
    parser.add_argument("--complete", dest="done_task", help="mark a task as completed")
    parser.add_argument("--show", action="store_true", help="display saved task state")
    args = parser.parse_args()

    if args.done_task:
        add_completed_task(args.done_task)
    if args.show or not any(vars(args).values()):
        pprint.pprint(load_task_state())

```

---

## `cursor_session_manager.py`

```python
import json
import os
import threading
import time
import atexit
from datetime import datetime
from typing import Any, Dict, Optional


class CursorSessionManager:
    """Light-weight utility that remembers the user's current Cursor context.

    The design principle is: *no dependencies, no network*, just drop-in and go.
    A single JSON file (``cursor_state.json`` at the project root) is used as the
    source-of-truth across sessions.  The manager keeps the file in sync every
    ``autosave_interval`` seconds and again on interpreter shutdown.
    """

    DEFAULT_STATE_FILE = os.path.join(os.getcwd(), "cursor_state.json")

    def __init__(self, state_file: str | None = None, autosave_interval: int = 30):
        self.state_file = state_file or self.DEFAULT_STATE_FILE
        self._state: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self.autosave_interval = autosave_interval
        self._stop_event = threading.Event()
        self._autosave_thread: Optional[threading.Thread] = None

        # Load persisted state (if any) so consumers can immediately resume.
        self._load_state_from_disk()

        # Start periodic persistence in a daemon thread.
        self._start_autosave()

        # Ensure graceful persistence on clean interpreter exit.
        atexit.register(self.end_session)

    # ---------------------------------------------------------------------
    # Public helper API ----------------------------------------------------
    # ---------------------------------------------------------------------
    def update(self,
               current_file: Optional[str] = None,
               cursor_line: Optional[int] = None,
               current_task: Optional[str] = None,
               progress: Optional[float] = None) -> None:
        """Update one or more fields in the in-memory state structure."""
        with self._lock:
            if current_file is not None:
                self._state.setdefault("cursor_session", {})["current_file"] = current_file
            if cursor_line is not None:
                self._state.setdefault("cursor_session", {})["cursor_line"] = cursor_line
            if current_task is not None:
                self._state.setdefault("cursor_session", {})["current_task"] = current_task
            if progress is not None:
                self._state.setdefault("cursor_session", {})["progress"] = float(progress)
            self._state.setdefault("cursor_session", {})["last_activity"] = (
                datetime.utcnow().isoformat()
            )

    def get_state(self) -> Dict[str, Any]:
        """Return a *copy* of the current session state."""
        with self._lock:
            return json.loads(json.dumps(self._state))  # deep-ish copy

    def resume_state(self) -> Dict[str, Any]:
        """Return the last persisted state (on disk). Useful at program boot."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    def _start_autosave(self) -> None:
        def _save_loop() -> None:
            while not self._stop_event.wait(self.autosave_interval):
                self._save_state_to_disk()
        self._autosave_thread = threading.Thread(
            target=_save_loop, name="CursorSessionAutosave", daemon=True
        )
        self._autosave_thread.start()

    def _load_state_from_disk(self) -> None:
        if os.path.isfile(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
            except (json.JSONDecodeError, OSError):
                # Corrupted or inaccessible state file – start fresh.
                self._state = {}
        else:
            self._state = {}

    def _save_state_to_disk(self) -> None:
        with self._lock:
            tmp_path = f"{self.state_file}.tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(self._state, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, self.state_file)

                # ALSO refresh human-readable markdown snapshot so Cursor
                # background agent always has up-to-date context without
                # manual --dump calls.
                try:
                    from cursor_memory_bridge import dump_markdown  # local import to avoid circular

                    dump_markdown()
                except Exception:
                    # Silently ignore to avoid recursion / startup import issues
                    pass
            except OSError:
                # Best effort – swallow errors so we never crash the main app.
                pass

    # ------------------------------------------------------------------
    # Lifecycle ---------------------------------------------------------
    # ------------------------------------------------------------------
    def end_session(self) -> None:
        """Mark a *disconnect* event and flush state to disk."""
        with self._lock:
            self._state.setdefault("cursor_session", {})["disconnected_at"] = (
                datetime.utcnow().isoformat()
            )
        self._save_state_to_disk()
        self._stop_event.set()


# Singleton pattern for convenience – most scripts will simply import this
# file and interact with the global ``session_manager`` instance.
session_manager = CursorSessionManager()


# ----------------------------------------------------------------------
# Optional: tiny CLI for quick inspection --------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser(description="Inspect or update cursor session state.")
    parser.add_argument("--file", dest="current_file", help="file you are currently editing")
    parser.add_argument("--line", dest="cursor_line", type=int, help="cursor line number")
    parser.add_argument("--task", dest="current_task", help="current task description")
    parser.add_argument("--progress", dest="progress", type=float, help="progress 0-1 range")
    parser.add_argument("--show", action="store_true", help="print the current state then exit")
    parser.add_argument("--summary", action="store_true", help="print short human summary then exit")

    args = parser.parse_args()

    if any([args.current_file, args.cursor_line, args.current_task, args.progress is not None]):
        session_manager.update(
            current_file=args.current_file,
            cursor_line=args.cursor_line,
            current_task=args.current_task,
            progress=args.progress,
        )
        # Give the autosave thread a brief moment to write to disk.
        time.sleep(0.1)
    if args.summary:
        state = session_manager.get_state().get("cursor_session", {})
        if state:
            print("📝 Cursor Session Summary:")
            print(f"   • File      : {state.get('current_file', '—')}")
            print(f"   • Line      : {state.get('cursor_line', '—')}")
            print(f"   • Task      : {state.get('current_task', '—')}")
            print(f"   • Progress  : {state.get('progress', '—')}")
        else:
            print("ℹ️  No session data recorded yet.")
    elif args.show or not any(vars(args).values()):
        pprint.pprint(session_manager.get_state())

```

---

## `auto_detect_chunker.py`

```python
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


class AutoDetectChunker:
    """Intelligently splits long text into memory-friendly chunks.

    The chunking logic uses a three-pass algorithm:

    1. A quick exit for short text that doesn't need chunking.
    2. A greedy paragraph merge that combines adjacent short paragraphs.
    3. A fallback to sentence-level adaptive chunking for very long paragraphs.

    The goal is to produce ≤ 10 chunks that are semantically coherent.
    """

    def __init__(self, max_chunks: int = 10, ideal_chunk_size: int = 1024):
        if not isinstance(max_chunks, int) or max_chunks < 1:
            raise ValueError("max_chunks must be a positive integer")
        if not isinstance(ideal_chunk_size, int) or ideal_chunk_size < 100:
            raise ValueError("ideal_chunk_size must be at least 100")

        self.max_chunks = max_chunks
        self.ideal_chunk_size = ideal_chunk_size
        # Regex to split text into paragraphs
        self.paragraph_splitter = re.compile(r"\n{2,}")
        # Regex to split paragraphs into sentences
        self.sentence_splitter = re.compile(r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s")

    def auto_chunk(self, text: str) -> Tuple[List[str], Dict[str, Any]]:
        """The main chunking entrypoint. Returns chunks and metadata."""
        if not isinstance(text, str):
            raise TypeError("text must be str")

        # Pass 1: Quick exit for short text
        if len(text) <= self.ideal_chunk_size:
            return [text], {"strategy": "single_chunk", "num_chunks": 1}

        # Initial paragraph split
        paragraphs = [p.strip() for p in self.paragraph_splitter.split(text) if p.strip()]
        if not paragraphs:
            return [], {"strategy": "empty_text", "num_chunks": 0}

        # Pass 2: Greedy paragraph merge
        merged_chunks = self._merge_paragraphs(paragraphs)

        # Pass 3: Sentence-level fallback for oversized chunks
        final_chunks = self._split_oversized_chunks(merged_chunks)

        # Final check to enforce max_chunks limit
        if len(final_chunks) > self.max_chunks:
            final_chunks = self._force_merge_to_limit(final_chunks)

        return final_chunks, {"strategy": "multi_level_chunking", "num_chunks": len(final_chunks)}

    def _merge_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """Merge small adjacent paragraphs into ideal-sized chunks."""
        chunks: List[str] = []
        current_chunk = ""
        for p in paragraphs:
            if not current_chunk:
                current_chunk = p
            elif len(current_chunk) + len(p) + 2 <= self.ideal_chunk_size:
                current_chunk += f"\n\n{p}"
            else:
                chunks.append(current_chunk)
                current_chunk = p
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def _split_oversized_chunks(self, chunks: List[str]) -> List[str]:
        """Split any chunk that still exceeds the ideal size into sentences."""
        refined_chunks: List[str] = []
        for chunk in chunks:
            if len(chunk) > self.ideal_chunk_size:
                # This chunk is too big, so split it by sentence
                sentences = [s.strip() for s in self.sentence_splitter.split(chunk) if s.strip()]
                if len(sentences) > 1:
                    refined_chunks.extend(self._merge_paragraphs(sentences))
                else:
                    # Cannot split further, so add as is
                    refined_chunks.append(chunk)
            else:
                refined_chunks.append(chunk)
        return refined_chunks

    def _force_merge_to_limit(self, chunks: List[str]) -> List[str]:
        """A final pass to ensure the number of chunks is under the limit."""
        while len(chunks) > self.max_chunks:
            # Find the two smallest adjacent chunks to merge
            smallest_merge_cost = float('inf')
            merge_idx = -1
            for i in range(len(chunks) - 1):
                cost = len(chunks[i]) + len(chunks[i+1])
                if cost < smallest_merge_cost:
                    smallest_merge_cost = cost
                    merge_idx = i

            if merge_idx != -1:
                chunks[merge_idx] += f"\n\n{chunks.pop(merge_idx + 1)}"
            else:
                # Should not happen, but as a safeguard
                break
        return chunks


# CLI for testing
if __name__ == "__main__":
    import pprint

    chunker = AutoDetectChunker()
    long_text = (
        "This is the first paragraph. It is relatively short.\n\n" 
        "This is a second, much longer paragraph designed to test the chunking algorithm. "
        "It contains multiple sentences. The first sentence is here. The second sentence follows. "
        "The third adds even more length. We need to see if the system can handle this gracefully. "
        "This paragraph will definitely exceed the ideal chunk size, forcing a sentence-level split. "
        "Let's add another sentence for good measure. And one more.\n\n" 
        "The third paragraph is also short. It should be merged with the first one if possible, "
        "but the long second paragraph is in the way.\n\n" 
        "Finally, a fourth paragraph to wrap things up."
    )

    chunks, metadata = chunker.auto_chunk(long_text)
    print("--- Chunking Results ---")
    pprint.pprint(metadata)
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} (length: {len(chunk)}) ---")
        print(chunk)

```

---

## `command_chunker.py`

```python
from __future__ import annotations

import argparse
import pprint
import shlex
from typing import Any, Dict, List, Tuple


class CommandChunker:
    """Splits long shell commands into logically coherent chunks.

    The chunker uses multiple strategies, applied in order:
    1.  **Operator-based splitting**: Splits commands by logical operators
        like `&&`, `||`, and `|`.
    2.  **Argument-based splitting**: For commands without operators, it tries
        to group the command with its essential arguments, then splits
        the remaining arguments into separate chunks.
    3.  **Size-based splitting**: As a last resort, it splits the command string
        by a fixed size.
    """

    # Operators that signify a logical break in a command sequence.
    OPERATOR_SPLITTERS = {"&&", "||", "|"}

    # For argument-based splitting, how many initial tokens to keep with the command.
    MIN_ARGS_TO_KEEP = 2

    # Fallback chunk size.
    FALLBACK_CHUNK_SIZE = 512

    def chunk_command(self, command: str) -> Tuple[List[str], Dict[str, Any]]:
        """Main entrypoint to chunk a command string."""
        if not isinstance(command, str) or not command.strip():
            return [], {"strategy": "empty_command", "num_chunks": 0}

        # Strategy 1: Operator-based splitting
        chunks = self._try_operator_split(command)
        if len(chunks) > 1:
            return chunks, {"strategy": "operator_split", "num_chunks": len(chunks)}

        # Strategy 2: Argument-based splitting
        chunks = self._try_argument_split(command)
        if len(chunks) > 1:
            return chunks, {"strategy": "argument_split", "num_chunks": len(chunks)}

        # Strategy 3: Fallback to size-based splitting
        chunks = self._fallback_size_split(command)
        return chunks, {"strategy": "size_split", "num_chunks": len(chunks)}

    def _try_operator_split(self, command: str) -> List[str]:
        """Splits the command by logical shell operators."""
        tokens = shlex.split(command)
        if not any(op in self.OPERATOR_SPLITTERS for op in tokens):
            return [command]  # No operators found, return original command

        chunks: List[str] = []
        current_chunk_tokens: List[str] = []

        for token in tokens:
            if token in self.OPERATOR_SPLITTERS:
                # When an operator is found, finalize the previous chunk.
                if current_chunk_tokens:
                    chunks.append(shlex.join(current_chunk_tokens))
                # The operator itself becomes a new, separate chunk.
                chunks.append(token)
                current_chunk_tokens = []
            else:
                current_chunk_tokens.append(token)

        # Add the last remaining chunk.
        if current_chunk_tokens:
            chunks.append(shlex.join(current_chunk_tokens))

        return chunks

    def _try_argument_split(self, command: str) -> List[str]:
        """Splits a single command into the core command + separate arguments."""
        try:
            tokens = shlex.split(command)
        except ValueError:
            # Unbalanced quotes, cannot parse reliably.
            return [command]

        if len(tokens) <= self.MIN_ARGS_TO_KEEP + 1:
            return [command]  # Not enough arguments to split

        chunks: List[str] = []
        # The first chunk is the command and its essential arguments.
        main_command_chunk = shlex.join(tokens[: self.MIN_ARGS_TO_KEEP])
        chunks.append(main_command_chunk)

        # The rest of the arguments are chunked individually or in small groups.
        # (Here, we chunk them individually for simplicity).
        for token in tokens[self.MIN_ARGS_TO_KEEP :]:
            chunks.append(token)

        return chunks

    def _fallback_size_split(self, command: str) -> List[str]:
        """A simple, brute-force split based on character length."""
        if len(command) <= self.FALLBACK_CHUNK_SIZE:
            return [command]

        return [
            command[i : i + self.FALLBACK_CHUNK_SIZE]
            for i in range(0, len(command), self.FALLBACK_CHUNK_SIZE)
        ]


def main():
    """CLI for interactive testing."""
    parser = argparse.ArgumentParser(description="Chunk a shell command for analysis.")
    parser.add_argument(
        "command",
        nargs="?",
        help="The shell command to chunk. If empty, runs interactive examples.",
    )
    args = parser.parse_args()

    chunker = CommandChunker()

    if args.command:
        commands_to_test = [args.command]
    else:
        # A list of examples to demonstrate different strategies.
        commands_to_test = [
            # Operator Split Example
            "echo 'Starting...' && ls -la /etc && cat /etc/hosts | grep 'localhost'",
            # Argument Split Example
            "find /usr/local/bin -type f -name '*python*' -exec ls -l {} + -print",
            # Size Split Example (a long, unbroken string)
            "echo 'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.'",
            # Simple command (no split)
            "docker ps -a",
        ]

    for cmd in commands_to_test:
        chunks, metadata = chunker.chunk_command(cmd)
        print(f'\n--- Testing Command ---')
        print(f'Original: "{cmd}"')
        print('\n--- Analysis ---')
        pprint.pprint(metadata)
        print('\n--- Generated Chunks ---')
        for i, chunk in enumerate(chunks):
            print(f'  Chunk {i+1}: "{chunk}"')
        print('-' * 25)


if __name__ == "__main__":
    main()

```

---

## `cursor_memory_bridge.py`

```python
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from typing import Any, Dict, List

# These are the primary sources of truth for the bridge.
import cursor_session_manager
import todo_manager

# The output directory for human-readable markdown files.
MEMORY_BANK_DIR = os.path.join(os.getcwd(), "memory-bank")


def get_command_context() -> Dict[str, Any]:
    """Aggregate state from all relevant managers into a single context dict."""
    session_state = cursor_session_manager.session_manager.get_state()
    tasks = todo_manager.load_tasks()
    return {
        "cursor_session": session_state.get("cursor_session", {}),
        "todo_tasks": tasks,
        "timestamp": datetime.utcnow().isoformat(),
    }


def dump_markdown() -> str:
    """Generate a human-readable markdown summary of the current session state.

    This function is the core of the bridge. It reads data from the primary
    managers and writes a formatted markdown file to the `memory-bank`
    directory. This file can be used by other agents or for human review.
    """
    context = get_command_context()
    session = context.get("cursor_session", {})
    tasks = context.get("todo_tasks", {})
    open_tasks = tasks.get("tasks", [])
    completed_tasks = tasks.get("completed_tasks", [])

    # Build the markdown content.
    md = []
    md.append("# 🧠 Cursor Session State")
    md.append(f"_Last updated: {context['timestamp']}_\n")

    # Current Activity Section
    md.append("## 🎯 Current Activity")
    md.append(f"- **File:** `{session.get('current_file', 'N/A')}`")
    md.append(f"- **Line:** `{session.get('cursor_line', 'N/A')}`")
    md.append(f"- **Task:** `{session.get('current_task', 'No active task')}`")
    md.append(f"- **Progress:** `{session.get('progress', 'N/A')}`")
    md.append(f"- **Last Activity:** `{session.get('last_activity', 'N/A')}`")
    if session.get("disconnected_at"):
        md.append(f"- **Disconnected:** `{session.get('disconnected_at')}`")
    md.append("\n")

    # Open Tasks Section
    md.append("## ✅ Open Tasks")
    if open_tasks:
        for task in open_tasks:
            md.append(f"- [ ] **Task {task['id']}**: {task['description']}")
            for todo in task.get('todos', []):
                status = "x" if todo.get('done') else " "
                md.append(f"  - [{status}] {todo['text']}")
    else:
        md.append("_No open tasks._")
    md.append("\n")

    # Completed Tasks Section
    md.append("## ✔️ Recently Completed")
    if completed_tasks:
        # Show the 5 most recent
        for task in reversed(completed_tasks[-5:]):
            md.append(f"- [x] ~~{task['description']}~~ (Completed on {task['completed_at']})")
    else:
        md.append("_No tasks completed recently._")

    # Ensure the output directory exists.
    os.makedirs(MEMORY_BANK_DIR, exist_ok=True)

    # Write the file.
    output_path = os.path.join(MEMORY_BANK_DIR, "current-session.md")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md))
        return output_path
    except OSError as e:
        print(f"Error writing to {output_path}: {e}")
        return ""


def handle_natural_language_command(command: str) -> str:
    """Provide a simple natural language interface for querying state."""
    command = command.lower().strip()
    context = get_command_context()
    session = context.get("cursor_session", {})
    tasks = context.get("todo_tasks", {}).get("tasks", [])

    if "what am i working on" in command or "current task" in command:
        return session.get("current_task", "I don't have a specific task recorded for you right now.")
    
    if "what should i do next" in command or "next task" in command:
        if not tasks:
            return "There are no open tasks. You're all clear!"
        # Find the first task that isn't the current one
        current_desc = session.get("current_task")
        for task in tasks:
            if task['description'] != current_desc:
                return f"The next task is: '{task['description']}' (ID: {task['id']})"
        return f"You are on the last task: '{current_desc}'. After this, you're done!"

    if "how many tasks" in command or "open tasks" in command:
        num_tasks = len(tasks)
        if num_tasks == 0:
            return "There are no open tasks."
        if num_tasks == 1:
            return "There is 1 open task."
        return f"There are {num_tasks} open tasks."

    return "I'm not sure how to answer that. Try asking 'what am I working on?' or 'what should I do next?'"


def main():
    """CLI for the bridge."""
    parser = argparse.ArgumentParser(
        description="A bridge between Cursor's state and other tools."
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump the current state to a human-readable markdown file.",
    )
    parser.add_argument(
        "--context", action="store_true", help="Print the raw JSON context and exit."
    )
    parser.add_argument(
        "--ask",
        dest="query",
        help="Ask a question in natural language about the current state.",
    )

    args = parser.parse_args()

    if args.context:
        print(json.dumps(get_command_context(), indent=2))
    elif args.dump:
        output_file = dump_markdown()
        if output_file:
            print(f"Successfully dumped state to: {output_file}")
    elif args.query:
        response = handle_natural_language_command(args.query)
        print(f"🤖 {response}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

```

---

## `memory_system/services/memory_provider.py`

```python
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any, List, Optional, Protocol

# Fallback if ChromaDB is not installed
try:
    import chromadb
    from chromadb.types import Collection
except ImportError:
    chromadb = None
    Collection = None  # type: ignore


# ------------------------------------------------------------------
# Interface and Factory --------------------------------------------
# ------------------------------------------------------------------

class MemoryProvider(Protocol):
    """A standard interface for agents to store and retrieve memories."""

    def search(self, keyword: str, limit: int = 10) -> List[Any]:
        ...

    def add(self, memory: str, metadata: Optional[dict] = None) -> None:
        ...


def get_provider(provider_type: str = "filesystem") -> MemoryProvider:
    """Factory function to get a specific memory provider instance."""
    if provider_type == "sqlite":
        return SQLiteMemoryProvider()
    if provider_type == "chromadb" and chromadb:
        return ChromaDBMemoryProvider()
    # Default to filesystem
    return FileSystemMemoryProvider()


# ------------------------------------------------------------------
# Implementations --------------------------------------------------
# ------------------------------------------------------------------

class FileSystemMemoryProvider:
    """Stores memories as simple markdown files in a directory.

    - **Search**: Case-insensitive regex search on file contents.
    - **Add**: Creates a new `.md` file in the `memory-bank` directory.
    """

    def __init__(self, directory: str = "memory-bank"):
        self._dir = Path(directory)
        self._dir.mkdir(exist_ok=True)

    def _iter_files(self):
        return self._dir.glob("*.md")

    def search(self, keyword: str, limit: int = 10) -> List[str]:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        results: List[str] = []
        for p in self._iter_files():
            try:
                if pattern.search(p.read_text(errors="ignore")):
                    results.append(str(p))
                    if len(results) >= limit:
                        break
            except Exception:
                continue
        return results

    def add(self, memory: str, metadata: Optional[dict] = None) -> None:
        # Use a simple counter for unique filenames
        i = 0
        while True:
            filename = self._dir / f"memory_{i}.md"
            if not filename.exists():
                filename.write_text(memory, encoding="utf-8")
                break
            i += 1


class SQLiteMemoryProvider:
    """Stores memories in a local SQLite database file.

    - **Search**: Uses `LIKE` query for simple substring matching.
    - **Add**: Inserts a new row into the `memories` table.
    """

    def __init__(self, db_path: str = "memory.db"):
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS memories (id INTEGER PRIMARY KEY, content TEXT)"
        )

    def search(self, keyword: str, limit: int = 10) -> List[str]:
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT content FROM memories WHERE content LIKE ? LIMIT ?",
            (f"%{keyword}%", limit),
        )
        return [row[0] for row in cursor.fetchall()]

    def add(self, memory: str, metadata: Optional[dict] = None) -> None:
        self._conn.execute("INSERT INTO memories (content) VALUES (?)", (memory,))
        self._conn.commit()


class ChromaDBMemoryProvider:
    """Uses ChromaDB for vector-based semantic search (STUBBED)."""

    def __init__(self):
        if not chromadb:
            raise ImportError("ChromaDB is not installed. pip install chromadb")
        self._client = chromadb.Client()
        self._collection: Collection = self._client.get_or_create_collection("agent_memories")
        self._counter = 0

    def search(self, keyword: str, limit: int = 10) -> List[str]:
        # In a real implementation, you'd embed the keyword and query Chroma.
        # This is a simplified placeholder.
        results = self._collection.query(query_texts=[keyword], n_results=limit)
        return results.get("documents", [[]])[0]

    def add(self, memory: str, metadata: Optional[dict] = None) -> None:
        # Each document needs a unique ID.
        doc_id = f"doc_{self._counter}"
        self._collection.add(documents=[memory], ids=[doc_id], metadatas=[metadata or {}])
        self._counter += 1


# CLI for simple testing
if __name__ == "__main__":
    import shutil

    print("--- Testing FileSystemMemoryProvider ---")
    fs_provider = FileSystemMemoryProvider()
    fs_provider.add("The user prefers Python for scripting.")
    fs_provider.add("The database schema is in schema.sql.")
    print("Search for 'python':", fs_provider.search("python"))
    shutil.rmtree("memory-bank")

    print("\n--- Testing SQLiteMemoryProvider ---")
    sql_provider = SQLiteMemoryProvider(db_path=":memory:")
    sql_provider.add("The API key for OpenAI is stored in an env var.")
    sql_provider.add("Remember to run tests before deploying.")
    print("Search for 'api':", sql_provider.search("api"))

    if chromadb:
        print("\n--- Testing ChromaDBMemoryProvider (stub) ---")
        # Note: This is an in-memory instance, will be lost on exit.
        chroma_provider = ChromaDBMemoryProvider()
        chroma_provider.add("The primary goal is to increase user engagement.")
        chroma_provider.add("The secondary goal is to reduce latency.")
        print("Search for 'goal':", chroma_provider.search("goal"))

```

---

## `memory_system/services/telemetry.py`

```python
from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, Optional


class TelemetryEmitter:
    """A simple, lightweight telemetry event emitter.

    Events are written as JSON lines to a specified file, making them easy to
    parse by other services (like Fluentd, Logstash, etc.).

    The emitter can be disabled globally by setting the `TELEMETRY_DISABLED`
    environment variable to `1`.
    """

    def __init__(self, output_file: str = "telemetry_events.jsonl"):
        self._disabled = os.environ.get("TELEMETRY_DISABLED") == "1"
        if self._disabled:
            self._file_handle = None
        else:
            # Open in append mode with line buffering (1)
            self._file_handle = open(output_file, "a", buffering=1, encoding="utf-8")

    def emit(self, event_name: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit a single telemetry event."""
        if self._disabled or not self._file_handle:
            return

        event_data = {
            "event": event_name,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {},
        }
        try:
            json.dump(event_data, self._file_handle)
            self._file_handle.write("\n")
        except (IOError, TypeError):
            # Fail silently if the file is closed or data is not serializable
            pass

    @contextmanager
    def span(self, span_name: str, data: Optional[Dict[str, Any]] = None) -> Generator[None, None, None]:
        """Context manager to measure the duration of an operation."""
        start_time = time.perf_counter()
        self.emit(f"{span_name}.start", data)
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            final_data = (data or {}).copy()
            final_data["duration_ms"] = duration_ms
            self.emit(f"{span_name}.end", final_data)

    def close(self) -> None:
        """Close the underlying file handle."""
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None


# Global singleton instance for easy use across the application
telemetry = TelemetryEmitter()


# Example usage
if __name__ == "__main__":
    print("Emitting sample telemetry events to 'telemetry_events.jsonl'")

    # Example 1: Simple event
    telemetry.emit("app.startup", {"version": "1.0.0"})

    # Example 2: Using the span context manager
    with telemetry.span("data.processing", {"dataset_id": "xyz-123"}):
        print("Simulating work inside a span...")
        time.sleep(0.5)

    telemetry.emit("app.shutdown")

    # Important to close the handle to ensure all buffered events are written
    telemetry.close()

    print("\nContents of 'telemetry_events.jsonl':")
    with open("telemetry_events.jsonl", "r") as f:
        for line in f:
            print(line.strip())
    
    # Clean up the file
    os.remove("telemetry_events.jsonl")

```

