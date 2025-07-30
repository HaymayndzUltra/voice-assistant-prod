# 🚀 Session Start Workflow - ENHANCED WITH AUTO-SYNC

## ⚡ CRITICAL: AUTOMATIC STATE SYNCHRONIZATION

### 0. Immediate State Validation & Sync
```bash
# AUTOMATIC: Validate and sync all state files on session start
python3 auto_state_sync_hook.py --validate
```

```bash
# AUTO-FIX: Sync states if inconsistencies detected
python3 session_continuity_manager.py --sync-all
```

## 📋 AUTO-TRIGGER ACTIONS ON SESSION START

### 1. Memory System Initialization
```bash
# Load all memory contexts
python3 memory_system/cli.py sync
python3 memory_system/cli.py search "current session" --limit 10
```

### 2. State Files Synchronization
```python
# Enforce state consistency
python3 session_continuity_manager.py --sync-all
```

### 3. Load Memory Bank Context
```bash
# Read all memory-bank/*.md files for context
find memory-bank/ -name "*.md" -exec echo "=== {} ===" \; -exec cat {} \;
```

### 4. Current Session Status Check
```python
# Check current tasks and cursor state
python3 todo_manager.py list
cat cursor_state.json 2>/dev/null || echo "No cursor state"
cat task-state.json 2>/dev/null || echo "No task state"
```

### 5. Auto-Update State Files
```python
# Update current session info
python3 -c "
import json
from datetime import datetime
cursor_state = {
    'session_start': datetime.now().isoformat(),
    'last_activity': 'session_start',
    'current_task': 'loading...',
    'current_file': '',
    'cursor_line': 0
}
with open('cursor_state.json', 'w') as f:
    json.dump(cursor_state, f, indent=2)
print('✅ Session state initialized')
"
```

---

## 🎯 EXPECTED CONTEXT LOADING

### Memory Sources:
- ✅ MCP memory server data
- ✅ memory-bank/*.md files
- ✅ cursor_state.json
- ✅ task-state.json  
- ✅ todo-tasks.json
- ✅ task_interruption_state.json

### Auto-Responses:
- **"anong memory mo ngayon"** → Show current session context
- **"anong susunod na gagawin"** → Show active tasks from todo-tasks.json
- **"nasaan tayo"** → Show cursor position and current file

---

## 🔄 STATE SYNCHRONIZATION RULES

### On Session Start:
1. **READ** todo-tasks.json as source of truth
2. **UPDATE** cursor_state.json with current session
3. **SYNC** task-state.json with active tasks
4. **ENSURE** task_interruption_state.json consistency
5. **UPDATE** memory-bank/current-session.md

### Prevent Duplicates:
- Check existing tasks before creating new ones
- Use existing task IDs when resuming work
- Maintain timestamp consistency across files
