# 🔧 After Code Change Workflow

## 📋 AUTO-TRIGGER ACTIONS AFTER SIGNIFICANT CHANGES

### 1. AUTOMATIC STATE SYNC (CRITICAL)
```bash
# AUTO-SYNC: Update all state files with current progress
python3 auto_state_sync_hook.py "[task_name]" "in_progress"
```

### 2. Memory System Update
```bash
# Store summary of changes in memory system
python3 memory_system/cli.py store --summary "Code changes completed: $(date)"
```

### 3. State Files Synchronization
```python
# Update all state files to maintain consistency
python3 -c "
import json
from datetime import datetime

# Update cursor_state.json
try:
    with open('cursor_state.json', 'r') as f:
        cursor_state = json.load(f)
except:
    cursor_state = {}

cursor_state.update({
    'last_activity': datetime.now().isoformat(),
    'last_change': datetime.now().isoformat()
})

with open('cursor_state.json', 'w') as f:
    json.dump(cursor_state, f, indent=2)

# Update task-state.json if it exists
try:
    with open('task-state.json', 'r') as f:
        task_state = json.load(f)
    
    task_state.update({
        'last_updated': datetime.now().isoformat(),
        'progress_updated': datetime.now().isoformat()
    })
    
    with open('task-state.json', 'w') as f:
        json.dump(task_state, f, indent=2)
except:
    pass

print('✅ State files synchronized')
"
```

### 3. Update Memory Bank
```bash
# Append change summary to current-session.md
echo "### Code Change: $(date)" >> memory-bank/current-session.md
echo "- Files modified: [auto-detected]" >> memory-bank/current-session.md
echo "- Change type: Implementation/Bug fix/Enhancement" >> memory-bank/current-session.md
echo "" >> memory-bank/current-session.md
```

### 4. Task Progress Update
```python
# Update current task progress if applicable
python3 -c "
import json
from datetime import datetime

try:
    # Read current tasks
    with open('todo-tasks.json', 'r') as f:
        tasks = json.load(f)
    
    # Find active task and update progress
    updated = False
    for task in tasks:
        if task.get('status') == 'active':
            task['last_updated'] = datetime.now().isoformat()
            task['progress'] = min(100, task.get('progress', 0) + 10)  # Increment progress
            updated = True
            break
    
    if updated:
        with open('todo-tasks.json', 'w') as f:
            json.dump(tasks, f, indent=2)
        print('✅ Active task progress updated')
    else:
        print('ℹ️ No active task to update')

except Exception as e:
    print(f'⚠️ Error updating task progress: {e}')
"
```

### 5. Auto-Sync Trigger
```bash
# Trigger auto-sync if available
python3 auto_sync_manager.py --trigger-change-event 2>/dev/null || echo "Auto-sync not available"
```

---

## 🎯 CONSISTENCY ENFORCEMENT

### Mandatory Updates:
- ✅ cursor_state.json last_activity timestamp
- ✅ task-state.json progress timestamp  
- ✅ memory-bank/current-session.md activity log
- ✅ MCP memory system change summary

### Validation Checks:
- **Timestamp consistency** across all state files
- **Active task progress** increment
- **Memory system** change storage
- **Auto-sync** trigger if available

### Prevent Issues:
- **No duplicate tasks** created
- **Consistent timestamps** across files
- **Valid JSON** structure maintained
- **Memory continuity** preserved
