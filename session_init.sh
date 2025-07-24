#!/bin/bash

# Session Initialization Script for AI System Monorepo
# This script runs automatically when a new AI session is detected

SESSION_MARKER="/tmp/ai_session_$(date +%Y%m%d)"
WORKSPACE_DIR="/home/haymayndz/AI_System_Monorepo"

# Check if we're in the correct workspace
if [ "$PWD" != "$WORKSPACE_DIR" ]; then
    echo "Not in AI System workspace, skipping auto-load..."
    exit 0
fi

# Check if session already initialized today
if [ -f "$SESSION_MARKER" ]; then
    echo "Session already initialized today, skipping..."
    exit 0
fi

# Create session marker
touch "$SESSION_MARKER"

echo "🚀 Initializing new AI session..."
echo "📍 Workspace: $WORKSPACE_DIR"
echo "📅 Date: $(date)"
echo ""

# Run memory loading
if [ -f "./auto_load_memory.sh" ]; then
    ./auto_load_memory.sh
else
    echo "❌ auto_load_memory.sh not found!"
    exit 1
fi

echo ""
echo "✅ Session initialization complete!"
echo "💡 Ready for AI collaboration!" 