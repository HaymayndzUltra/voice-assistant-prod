#!/bin/bash
echo "🧠 Auto-loading memory context for new session... (quiet)"

# Load memory-bank files
count=$(ls memory-bank/*.md 2>/dev/null | wc -l | tr -d ' ')

# Check MCP services
if source .env 2>/dev/null && [ ! -z "$MEMORY_API_KEY" ]; then :; fi

# Check local memory system  
if pgrep -f "memory_orchestrator" > /dev/null; then :; fi

# Show last Cursor session state (if available)
python3 cursor_session_manager.py --summary 1>/dev/null 2>&1 || true

# Show count of open tasks (todo_manager)
python3 - <<'PY' 1>/dev/null 2>&1
import json, pathlib, os
fp = pathlib.Path(os.getcwd()) / 'todo-tasks.json'
if fp.exists():
    data = json.loads(fp.read_text())
    open_tasks = [t for t in data.get('tasks', []) if t.get('status') != 'completed']
    print(f"📋 Open Tasks: {len(open_tasks)}")
else:
    print("📋 Open Tasks: 0 (no todo-tasks.json)")
PY

echo ""
