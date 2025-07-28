#!/bin/bash
echo "🧠 Auto-loading memory context for new session..."

# Load memory-bank files
echo "📖 Loading memory-bank files:"
# Count markdown docs instead of listing each one
count=$(ls memory-bank/*.md 2>/dev/null | wc -l | tr -d ' ')
echo "  ✅ $count markdown documents loaded"

# Check MCP services
echo "🔗 Checking MCP services:"
if source .env 2>/dev/null && [ ! -z "$MEMORY_API_KEY" ]; then
    echo "  ✅ Environment variables loaded"
    if curl -s --connect-timeout 3 "https://memory-mcp.hpkv.io/health" > /dev/null; then
        echo "  ✅ MCP Memory Service: Online"
    else
        echo "  ⚠️  MCP Memory Service: Connection timeout"
    fi
else
    echo "  ❌ Environment variables not loaded"
fi

# Check local memory system  
echo "🖥️  Local Memory System:"
if pgrep -f "memory_orchestrator" > /dev/null; then
    echo "  ✅ MemoryOrchestratorService: Running"
else
    echo "  ⚠️  MemoryOrchestratorService: Not detected"
fi

# NEW ➜ Show last Cursor session state (if available)
echo "📝 Last Cursor Session State:"
# shellcheck disable=SC2016
python3 cursor_session_manager.py --summary 2>/dev/null || echo "  ℹ️  No session summary available"

# Show count of open tasks (todo_manager)
if python3 - <<'PY' 2>/dev/null; then
import json, pathlib, os, sys
fp = pathlib.Path(os.getcwd()) / 'todo-tasks.json'
if fp.exists():
    data = json.loads(fp.read_text())
    open_tasks = [t for t in data.get('tasks', []) if t.get('status') != 'completed']
    print(f"📋 Open Tasks: {len(open_tasks)}")
else:
    print("📋 Open Tasks: 0 (no todo-tasks.json)")
PY
fi

echo "🚀 Memory loading complete!"
echo ""
echo "💡 To get started:"
echo "   - Use standard memory functions for conversation context"
echo "   - Memory-bank files contain project documentation"
echo "   - MCP Memory service is configured and ready"
echo ""
