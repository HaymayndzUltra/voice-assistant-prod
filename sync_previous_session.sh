#!/bin/bash

# Previous Session Memory Sync Script
# Helps transfer context from old AI sessions

echo "🔄 Previous Session Memory Sync"
echo "================================="
echo ""

# Create sync directory if not exists
mkdir -p session_sync

echo "📝 Options for syncing previous session memory:"
echo ""
echo "1. 📋 Manual Summary (Recommended)"
echo "   - Tell AI about key accomplishments/decisions"
echo "   - Update memory-bank files with important changes"
echo "   - Quick and focused"
echo ""
echo "2. 💾 Export Chat/Terminal History"
echo "   - Copy terminal history: history > session_sync/terminal_history.txt"
echo "   - Copy chat history if available"
echo "   - AI can process and extract key information"
echo ""
echo "3. 🔍 Code Changes Review"
echo "   - git log --oneline --since='1 day ago' > session_sync/recent_changes.txt"
echo "   - git diff HEAD~10..HEAD > session_sync/recent_diff.txt"
echo "   - Focus on what actually changed in codebase"
echo ""
echo "4. 📊 Status Snapshot"
echo "   - Current project status"
echo "   - Outstanding issues/tasks"
echo "   - Next planned steps"
echo ""

# Generate some helpful commands
echo "🔧 Helpful sync commands:"
echo "------------------------"
echo ""

# Recent git activity
if [ -d ".git" ]; then
    echo "📈 Recent Git Activity (last 24 hours):"
    git log --oneline --since='1 day ago' | head -10
    echo ""
    
    echo "📁 Recently modified files:"
    git diff --name-only HEAD~5..HEAD | head -10
    echo ""
fi

# Check running processes related to the project
echo "🔍 Current project processes:"
ps aux | grep -E "(python|node|memory|agent)" | grep -v grep | head -5
echo ""

echo "💡 Recommendation:"
echo "  Start with Option 1 (Manual Summary) - just tell the AI:"
echo "  'In my previous session, I [accomplished/worked on/fixed]...'"
echo ""
echo "  Then update relevant memory-bank files if needed."
echo "" 