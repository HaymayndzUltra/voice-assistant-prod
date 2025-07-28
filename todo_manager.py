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


def _load() -> Dict[str, Any]:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text("utf-8"))
        except json.JSONDecodeError:
            pass
    return {"tasks": []}


def _save(data: Dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _timestamp() -> str:
    return datetime.utcnow().isoformat()


# ------------------------------------------------------------------
# CRUD helpers ------------------------------------------------------
# ------------------------------------------------------------------

def new_task(description: str) -> str:
    data = _load()
    task_id = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{description.replace(' ', '_')[:30]}"
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


def mark_done(task_id: str, index: int) -> None:
    data = _load()
    task = next((t for t in data["tasks"] if t["id"] == task_id), None)
    if task is None:
        print(f"❌ Task '{task_id}' not found.")
        return
    try:
        task["todos"][index]["done"] = True
        task["updated"] = _timestamp()
        _save(data)
    except IndexError:
        print(f"❌ TODO index {index} out of range.")


def list_open_tasks() -> List[Dict[str, Any]]:
    data = _load()
    return [t for t in data["tasks"] if t.get("status") != "completed"]


def set_task_status(task_id: str, status: str) -> None:
    data = _load()
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            t["updated"] = _timestamp()
            _save(data)
            return
    print(f"❌ Task '{task_id}' not found.")


# ------------------------------------------------------------------
# CLI ----------------------------------------------------------------
# ------------------------------------------------------------------

def _print_task(task: Dict[str, Any]) -> None:
    print(f"🗒️  {task['id']} — {task['description']} (status: {task['status']})")
    for i, todo in enumerate(task["todos"]):
        mark = "✔" if todo["done"] else "✗"
        print(f"    [{mark}] {i}. {todo['text']}")


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
    sub_done.add_argument("index", type=int)

    sub_list = sub.add_parser("list", help="list open tasks")

    args = parser.parse_args(argv)

    if args.cmd == "new":
        tid = new_task(args.description)
        print(f"✅ Created task {tid}")
    elif args.cmd == "add":
        add_todo(args.task_id, args.text)
    elif args.cmd == "done":
        mark_done(args.task_id, args.index)
    else:
        tasks = list_open_tasks()
        print(f"🔎 {len(tasks)} open tasks")
        for t in tasks:
            _print_task(t)


if __name__ == "__main__":
    main(sys.argv[1:])