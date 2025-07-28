#!/bin/bash
echo "🧠 Auto-loading memory context for new session..."

# Load memory-bank files
echo "📖 Loading memory-bank files:"
for file in memory-bank/*.md; do
    if [ -f "$file" ] && [ -s "$file" ]; then
        echo "  ✅ $(basename $file) ($(wc -l < "$file") lines)"
    else
        echo "  ⚠️  $(basename $file) (empty)"
    fi
done

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

echo "🚀 Memory loading complete!"
echo ""
echo "💡 To get started:"
echo "   - Use standard memory functions for conversation context"
echo "   - Memory-bank files contain project documentation"
echo "   - MCP Memory service is configured and ready"
echo ""
