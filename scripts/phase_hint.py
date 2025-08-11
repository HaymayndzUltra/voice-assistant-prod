#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_tasks(repo_root: Path) -> List[Dict[str, Any]]:
    active = repo_root / "memory-bank" / "queue-system" / "tasks_active.json"
    try:
        data = json.loads(active.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "tasks" in data:
            data = data["tasks"]
        return data if isinstance(data, list) else []
    except Exception:
        return []


def first_unfinished(todos: List[Dict[str, Any]]) -> Tuple[int, Optional[Dict[str, Any]]]:
    for i, td in enumerate(todos or []):
        if not bool(td.get("done", False)):
            return i, td
    return -1, None


def title_of(markdown: str) -> str:
    return (markdown or "").strip().splitlines()[0] if markdown else ""


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    tasks = load_tasks(repo_root)
    task = next((t for t in tasks if t.get("status") == "in_progress"), tasks[0] if tasks else None)
    if not task:
        return

    task_id = str(task.get("id"))
    todos = task.get("todos", []) if isinstance(task.get("todos", []), list) else []
    idx, todo = first_unfinished(todos)
    if idx < 0:
        # All phases done; fall back to the last phase index for audit/re-run convenience
        idx = max(0, len(todos) - 1)
        todo = todos[idx] if todos else {}

    title = title_of((todo or {}).get("text", ""))
    gate_cmd = (
        f"PRINT_NEXT_SUMMARY=1 CONFIDENCE_THRESHOLD=90 python3 {repo_root}/phase_guard.py {task_id} {idx}"
    )

    print(f"[Phase Guard] Task {task_id} • Next {idx}: {title}")
    print(f"Run: {gate_cmd}")


if __name__ == "__main__":
    main()


