# 🛑 Session End Workflow

## 📋 AUTO-TRIGGER ACTIONS ON SESSION END

### 1. Save Current Session State
```python
# Update cursor_state.json with final position
python3 -c "
import json
from datetime import datetime
try:
    with open('cursor_state.json', 'r') as f:
        state = json.load(f)
except:
    state = {}

state.update({
    'disconnected_at': datetime.now().isoformat(),
    'session_end': datetime.now().isoformat(),
    'last_activity': 'session_end'
})

with open('cursor_state.json', 'w') as f:
    json.dump(state, f, indent=2)
print('✅ Session state saved')
"
```

### 2. Update Memory Bank
```bash
# Append session summary to current-session.md
echo "### Session End: $(date)" >> memory-bank/current-session.md
echo "- Duration: Session completed" >> memory-bank/current-session.md
echo "- Last activity: $(cat cursor_state.json | grep last_activity || echo 'unknown')" >> memory-bank/current-session.md
echo "" >> memory-bank/current-session.md
```

### 3. Sync Memory System
```bash
# Store session summary in memory system
python3 memory_system/cli.py store --summary "Session completed on $(date)"
```

### 4. Clean Temporary Files
```bash
# Clean up temporary files
python3 memory_system/cli.py cleanup --dry-run
find . -name "*.tmp" -delete 2>/dev/null || true
```

### 5. Task State Preservation
```python
# Ensure task interruption state is saved
python3 -c "
import json
from datetime import datetime
try:
    with open('todo-tasks.json', 'r') as f:
        tasks = json.load(f)
    
    # Find active task
    active_task = None
    for task in tasks:
        if task.get('status') == 'active':
            active_task = task
            break
    
    if active_task:
        interruption_state = {
            'interrupted_task_id': active_task['id'],
            'interrupted_at': datetime.now().isoformat(),
            'reason': 'session_end',
            'progress': active_task.get('progress', 0),
            'current_step': active_task.get('current_step', 'unknown')
        }
        
        with open('task_interruption_state.json', 'w') as f:
            json.dump(interruption_state, f, indent=2)
        print('✅ Task interruption state saved')
    else:
        print('ℹ️ No active task to preserve')
except Exception as e:
    print(f'⚠️ Error saving interruption state: {e}')
"
```

---

## 🔄 RESUME PREPARATION

### For Next Session:
- ✅ cursor_state.json updated with disconnect time
- ✅ task_interruption_state.json preserved active task
- ✅ memory-bank/current-session.md updated
- ✅ MCP memory system synced
- ✅ Temporary files cleaned

### Resume Triggers:
- **Read** task_interruption_state.json to resume work
- **Load** cursor_state.json for last position
- **Check** todo-tasks.json for pending tasks
- **Sync** all state files to current reality
