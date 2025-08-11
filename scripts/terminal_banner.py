#!/usr/bin/env python3
"""Prints a concise terminal banner with the current task/phase and key commands.

- Detects the active task from memory-bank/queue-system/tasks_active.json
- Finds the next unfinished phase index and title
- Prints the exact commands you typically need to run next
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_active_tasks(repo_root: Path) -> List[Dict[str, Any]]:
    active = repo_root / "memory-bank" / "queue-system" / "tasks_active.json"
    try:
        data = json.loads(active.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "tasks" in data:
            data = data["tasks"]
        if not isinstance(data, list):
            return []
        return data
    except Exception:
        return []


def first_unfinished(todos: List[Dict[str, Any]]) -> Tuple[int, Optional[Dict[str, Any]]]:
    for i, td in enumerate(todos):
        if not bool(td.get("done", False)):
            return i, td
    return -1, None


def title_line(markdown: str) -> str:
    return (markdown or "").strip().splitlines()[0] if markdown else ""


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    task_list = load_active_tasks(repo_root)

    # Pick the first in-progress task (or the first task if none tagged)
    task: Optional[Dict[str, Any]] = None
    for t in task_list:
        if t.get("status") == "in_progress":
            task = t
            break
    if task is None and task_list:
        task = task_list[0]

    print("\n🔔 Session Quick Guide — actions you can run now\n")

    if not task:
        print("No active task found.")
        return

    task_id = str(task.get("id"))
    todos = task.get("todos", []) if isinstance(task.get("todos", []), list) else []
    idx, todo = first_unfinished(todos)
    phase_title = title_line(todo.get("text", "")) if todo else "(All phases complete)"

    print(f"• Task: {task_id}")
    print(f"• Next phase: {idx if idx >= 0 else '-'} — {phase_title}")
    print("")

    # Key commands
    print("➡️  Core commands:")
    if idx >= 0:
        print(f"  PRINT_NEXT_SUMMARY=1 CONFIDENCE_THRESHOLD=90 python3 {repo_root}/phase_guard.py {task_id} {idx}")
        print(f"  python3 {repo_root}/todo_manager.py done {task_id} {idx}    # after gate OK")
    print(f"  python3 {repo_root}/todo_manager.py show {task_id}")
    print(f"  python3 {repo_root}/plan_next.py")
    print(f"  python3 {repo_root}/plain_hier.py {task_id}")
    print(f"  python3 {repo_root}/phase_auto_runner.py --task {task_id} --print-next --confidence 90   # auto-gate + mark done")
    print("")

    # Memory note quick save
    print("➡️  Save a quick memory note:")
    print(
        f"  python3 {repo_root}/memory_system/cli.py save \"<note>\" --task {task_id} --tag progress"
    )
    print("")

    # PC2 build sequence (run on PC2)
    print("➡️  PC2 build sequence (run on PC2):")
    print(f"  cd {repo_root}/docker/pc2_infra_core && docker compose up -d --build")
    print(f"  cd {repo_root}/docker/pc2_memory_stack && docker compose up -d --build")
    print(f"  cd {repo_root}/docker/pc2_async_pipeline && docker compose up -d --build")
    print(f"  cd {repo_root}/docker/pc2_tutoring_cpu && docker compose up -d --build")
    print(f"  cd {repo_root}/docker/pc2_utility_suite && docker compose up -d --build")
    print(f"  cd {repo_root}/docker/pc2_vision_dream_gpu && docker compose up -d --build   # if GPU available")
    print(f"  cd {repo_root}/docker/pc2_web_interface && docker compose up -d --build")
    print("")

    # Status / cleanup helpers
    print("➡️  Status & cleanup:")
    print("  docker ps | grep pc2")
    print("  docker logs pc2_observability_hub --tail 20")
    print("  docker system prune -f && docker volume prune -f   # careful")
    print("")


if __name__ == "__main__":
    main()


