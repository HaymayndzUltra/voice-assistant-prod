# AUTONOMOUS WORKFLOW SYSTEM - PRACTICAL BACKGROUND AGENT PROMPT

## 🎯 **GOAL**: Build Simple Session Continuity System for Cursor

**CONTEXT**: Need simple system na maalala ang ginagawa mo sa cursor across sessions, at maging proactive sa pag-suggest ng next steps.

---

## 🚀 **SIMPLIFIED BACKGROUND AGENT PROMPT**

```
/agent
BUILD SIMPLE SESSION CONTINUITY SYSTEM FOR CURSOR:

## OBJECTIVE:
Create simple system na maalala ang current task, progress, at context across cursor sessions.

## ANALYZE EXISTING FILES:
- task_automation_hub.py - current task management
- task_state_manager.py - state persistence  
- session_action_logger.py - session tracking
- task-state.json - current state
- memory-bank/ - existing memory system

## CREATE THESE SIMPLE FILES:

1. **cursor_session_manager.py** (NEW)
   - Save current task every 30 seconds
   - Detect when cursor session ends/disconnects
   - Auto-resume from last state when reconnected
   - Store: current file, cursor position, task description

2. **cursor_memory_bridge.py** (NEW) 
   - Connect cursor state to memory-bank/
   - Save task progress to memory-bank/current-session.md
   - Load previous session on startup
   - Simple natural language commands

3. **ENHANCE EXISTING**:
   - task_state_manager.py: Add cursor session tracking
   - session_action_logger.py: Add disconnection detection
   - auto_load_memory.sh: Load cursor session state

## NATURAL LANGUAGE COMMANDS:
- "anong susunod na task" → Show next task from memory
- "ipagpatuloy muna" → Resume from last cursor position
- "kung saan ako natigil" → Show last known state
- "tumingin ka sa memory hub folder" → Analyze memory context

## SIMPLE STATE STRUCTURE:
```json
{
  "cursor_session": {
    "current_file": "file.py",
    "cursor_line": 42,
    "current_task": "fixing import error",
    "progress": 0.75,
    "last_activity": "2024-01-01 10:30:00"
  },
  "task_history": [
    {"task": "fixed syntax error", "completed": "2024-01-01 10:25:00"}
  ]
}
```

## SUCCESS CRITERIA:
- Cursor remembers current task across sessions
- Natural language commands work
- Simple and lightweight
- Integrates with existing memory-bank/

COMMIT: "CURSOR SESSION CONTINUITY: Simple system for remembering tasks across cursor sessions"
```

---

## 🎯 **WHAT THIS DOES:**

1. **Simple Session Memory** - Remembers current file, cursor position, task
2. **Auto-Resume** - Continues from where you left off
3. **Natural Commands** - "anong susunod na task", "ipagpatuloy muna"
4. **Lightweight** - No complex architecture, just practical functionality

**Much better na ba?** 😅 