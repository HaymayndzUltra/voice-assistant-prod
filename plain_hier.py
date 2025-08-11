#!/usr/bin/env python3
"""Read-only hierarchical plan viewer (path auto-detected)."""
import json, sys, re
from pathlib import Path

def _detect_repo_root() -> Path:
    cwd = Path.cwd()
    if (cwd / "memory-bank" / "queue-system" / "tasks_active.json").exists():
        return cwd
    env_root = Path(os.getenv("AI_System_Monorepo", "")) if os.getenv("AI_System_Monorepo") else None
    if env_root and (env_root / "memory-bank" / "queue-system" / "tasks_active.json").exists():
        return env_root
    mainpc = Path("/home/haymayndz/AI_System_Monorepo")
    if (mainpc / "memory-bank" / "queue-system" / "tasks_active.json").exists():
        return mainpc
    return cwd

REPO_ROOT = _detect_repo_root()
ACTIVE = REPO_ROOT / "memory-bank" / "queue-system" / "tasks_active.json"

def blocks(md: str):
    return re.findall(r"```(?:[\w+-]+)?\n([\s\S]*?)\n```", md or "", re.M)

def head(line: str) -> str:
    return (line or "").strip().splitlines()[0] if line else ""

def main():
    if len(sys.argv) != 2:
        print("usage: plan_hier.py <TASK_ID>"); sys.exit(2)
    task_id = sys.argv[1]
    data = json.loads(ACTIVE.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "tasks" in data:
        data = data["tasks"]
    task = next((t for t in data if t.get("id")==task_id), None)
    if not task:
        print(f"❌ Task not found: {task_id}"); sys.exit(2)

    todos = task.get("todos", [])
    done_count = sum(1 for td in todos if td.get("done"))
    print(f"🗒️ {task_id} — {done_count}/{len(todos)} done")
    for i, td in enumerate(todos):
        mark = "✔" if td.get("done") else "✗"
        title = head(td.get("text",""))
        print(f"  [{mark}] {i}. {title}")
        note_idx = td.get("text","").find("IMPORTANT NOTE:")
        if note_idx >= 0:
            snippet = td["text"][note_idx:note_idx+220].replace("\n"," ")
            print(f"     NOTE: {snippet}{'…' if len(td['text'])-note_idx>220 else ''}")
        code = blocks(td.get("text",""))
        if code:
            prev = "\n".join(code[0].splitlines()[:4])
            print("     cmds:")
            for ln in prev.splitlines():
                print(f"       {ln}")
    print("✅ read-only view complete")

if __name__ == "__main__":
    main()
