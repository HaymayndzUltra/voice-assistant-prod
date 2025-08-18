#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def active_path(root: Path) -> Path:
    return root / "memory-bank" / "queue-system" / "tasks_active.json"


def output_path(root: Path) -> Path:
    return root / "goaltomakelikethis.md"


def load_tasks(path: Path) -> List[Dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "tasks" in data:
        data = data["tasks"]
    if not isinstance(data, list):
        raise SystemExit("❌ tasks_active.json must be a list of task objects")
    return data


def first_line(s: str) -> str:
    return (s or "").strip().splitlines()[0] if s else ""


def compile_markdown(tasks: List[Dict[str, Any]]) -> str:
    out: List[str] = []
    out.append("============================================================")
    out.append("🎮 TASK COMMAND & CONTROL CENTER")
    out.append("============================================================")
    out.append("")
    out.append("📋 ALL OPEN TASKS:")
    out.append("========================================")
    out.append("")

    for idx, task in enumerate(tasks, start=1):
        task_id = task.get("id", "")
        desc = task.get("description", "")
        status = task.get("status", "")
        created = task.get("created", "")
        todos: List[Dict[str, Any]] = task.get("todos", []) or []

        out.append(f"{idx}. 🗒️  {task_id}")
        out.append(f"   Description: {desc[:200]}{'…' if len(desc) > 200 else ''}")
        out.append(f"   Status: {status}")
        out.append(f"   Created: {created}")
        out.append(f"   TODO Items ({len(todos)}):")

        for phase_index, td in enumerate(todos):
            done = bool(td.get("done", False))
            mark = "✔" if done else "✗"
            text = td.get("text", "")
            lines = (text or "").splitlines()
            title = first_line(text)
            out.append(f"      [{mark}] {phase_index}. {title}")

            body_lines = lines[1:] if len(lines) > 1 else []
            if body_lines:
                out.append("")
                out.extend(body_lines)
            out.append("")

        out.append("")

    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    root = repo_root()
    active = active_path(root)
    if not active.exists():
        raise SystemExit(f"❌ Not found: {active}")
    tasks = load_tasks(active)
    md = compile_markdown(tasks)
    out = output_path(root)
    out.write_text(md, encoding="utf-8")
    print(f"✅ Wrote {out}")


if __name__ == "__main__":
    main()


