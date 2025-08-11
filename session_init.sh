#!/bin/bash

# Session Initialization Script for AI System Monorepo (quiet by default)
# Set AI_SESSION_VERBOSE=1 to see logs

SESSION_MARKER="/tmp/ai_session_$(date +%Y%m%d)"
WORKSPACE_DIR="/home/haymayndz/AI_System_Monorepo"

VERBOSE=${AI_SESSION_VERBOSE:-0}

# Check if we're in the correct workspace (quiet)
if [ "$PWD" != "$WORKSPACE_DIR" ]; then
    exit 0
fi

# Check if session already initialized today (quiet)
if [ -f "$SESSION_MARKER" ]; then
    exit 0
fi

# Create session marker
touch "$SESSION_MARKER"

if [ "$VERBOSE" = "1" ]; then
  echo "🚀 Initializing new AI session..."
  echo "📍 Workspace: $WORKSPACE_DIR"
  echo "📅 Date: $(date)"
  echo ""
fi

# Run memory loading (quiet)
if [ -f "./auto_load_memory.sh" ]; then
    ./auto_load_memory.sh >/dev/null 2>&1 || true
fi

# Always print only the phase guard hint (minimal)
python3 "$WORKSPACE_DIR/scripts/phase_hint.py" 2>/dev/null || true