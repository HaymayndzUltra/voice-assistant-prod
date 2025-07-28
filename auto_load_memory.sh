#!/bin/bash

# Enhanced Auto-Load Memory Script for AI Session Continuity
# Loads memory bank context + task state + pending tasks with explanations

MEMORY_BANK_DIR="./memory-bank"
LOAD_LOG="/tmp/memory_load_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 AI SYSTEM SESSION STARTUP" | tee -a "$LOAD_LOG"
echo "==========================================" | tee -a "$LOAD_LOG"
echo "" | tee -a "$LOAD_LOG"

# 1. LOAD TASK STATE AND PENDING TASKS
echo "📋 Loading task state and continuity context..." | tee -a "$LOAD_LOG"

if command -v python3 >/dev/null 2>&1; then
    # Generate session summary using TaskStateManager
    SESSION_SUMMARY=$(python3 -c "
from task_state_manager import TaskStateManager
import sys
try:
    tsm = TaskStateManager()
    print(tsm.get_session_summary())
except Exception as e:
    print('⚠️  Task state system not available:', str(e))
    sys.exit(1)
" 2>/dev/null)

    if [ $? -eq 0 ]; then
        echo "$SESSION_SUMMARY" | tee -a "$LOAD_LOG"
    else
        echo "⚠️  Task state system not initialized yet" | tee -a "$LOAD_LOG"
    fi
else
    echo "⚠️  Python3 not available for task state management" | tee -a "$LOAD_LOG"
fi

echo "" | tee -a "$LOAD_LOG"

# 2. LOAD MEMORY BANK CONTEXT
echo "🧠 Loading memory bank context files..." | tee -a "$LOAD_LOG"

# Check if memory-bank directory exists
if [ ! -d "$MEMORY_BANK_DIR" ]; then
    echo "❌ Memory bank directory not found: $MEMORY_BANK_DIR" | tee -a "$LOAD_LOG"
    exit 1
fi

# Count memory files
MEMORY_FILES=$(find "$MEMORY_BANK_DIR" -name "*.md" -type f)
FILE_COUNT=$(echo "$MEMORY_FILES" | wc -l)

if [ $FILE_COUNT -eq 0 ]; then
    echo "⚠️  No memory files found in $MEMORY_BANK_DIR" | tee -a "$LOAD_LOG"
else
    echo "📊 Found $FILE_COUNT memory files:" | tee -a "$LOAD_LOG"
    
    # List memory files with sizes
    while IFS= read -r file; do
        if [ -f "$file" ]; then
            SIZE=$(wc -l < "$file")
            BASENAME=$(basename "$file")
            echo "  ✓ $BASENAME ($SIZE lines)" | tee -a "$LOAD_LOG"
        fi
    done <<< "$MEMORY_FILES"
    
    # Special highlight for Background Agent capabilities
    if [ -f "$MEMORY_BANK_DIR/background-agent-escalation-guide.md" ]; then
        echo "" | tee -a "$LOAD_LOG"
        echo "🎯 BACKGROUND AGENT ESCALATION READY:" | tee -a "$LOAD_LOG"
        echo "  • When user says 'gamitin si background agent' → Use efficient problem reporting" | tee -a "$LOAD_LOG"
        echo "  • Provide: CURRENT PROBLEM + WHAT I TRIED + OUTPUT/RESULT" | tee -a "$LOAD_LOG"
        echo "  • Smart scoping via @startup_config.yaml (54 MainPC, 23 PC2 agents)" | tee -a "$LOAD_LOG"
        echo "  • Expected: FULL SUMMARY REPORT with STEP-BY-STEP ACTION PLAN" | tee -a "$LOAD_LOG"
        echo "  • Cost-optimize: Start narrow, expand if needed" | tee -a "$LOAD_LOG"
    fi
fi

echo "" | tee -a "$LOAD_LOG"

# 3. CHECK FOR INTERRUPTED SESSIONS
echo "🔍 Checking for interrupted sessions..." | tee -a "$LOAD_LOG"

if [ -f "session-progress.json" ]; then
    STATUS=$(jq -r '.status // "unknown"' session-progress.json 2>/dev/null)
    if [ "$STATUS" = "in_progress" ]; then
        echo "⚠️  INTERRUPTED SESSION DETECTED!" | tee -a "$LOAD_LOG"
        TASK_ID=$(jq -r '.task_id // "unknown"' session-progress.json 2>/dev/null)
        LAST_ACTION=$(jq -r '.last_action_time // "unknown"' session-progress.json 2>/dev/null)
        echo "  📋 Task: $TASK_ID" | tee -a "$LOAD_LOG"
        echo "  🕒 Last action: $LAST_ACTION" | tee -a "$LOAD_LOG"
        echo "  💡 Recovery context available for continuation" | tee -a "$LOAD_LOG"
    else
        echo "✅ No interrupted sessions found" | tee -a "$LOAD_LOG"
    fi
else
    echo "✅ No session recovery needed" | tee -a "$LOAD_LOG"
fi

echo "" | tee -a "$LOAD_LOG"

# 4. SYSTEM HEALTH CHECK
echo "🔧 System Health Check..." | tee -a "$LOAD_LOG"

# Check if key files exist
HEALTH_ISSUES=0

if [ ! -f "main_pc_code/config/startup_config.yaml" ]; then
    echo "  ❌ MainPC SOT config missing" | tee -a "$LOAD_LOG"
    HEALTH_ISSUES=$((HEALTH_ISSUES + 1))
fi

if [ ! -f "pc2_code/config/startup_config.yaml" ]; then
    echo "  ❌ PC2 SOT config missing" | tee -a "$LOAD_LOG"
    HEALTH_ISSUES=$((HEALTH_ISSUES + 1))
fi

# Check available tools
AVAILABLE_TOOLS=0
for tool in docker-cleanup-script.sh wsl-shrink-script.ps1 docker-daemon-config.json; do
    if [ -f "$tool" ]; then
        echo "  ✅ Tool available: $tool" | tee -a "$LOAD_LOG"
        AVAILABLE_TOOLS=$((AVAILABLE_TOOLS + 1))
    fi
done

if [ $HEALTH_ISSUES -eq 0 ]; then
    echo "✅ System health check passed" | tee -a "$LOAD_LOG"
else
    echo "⚠️  $HEALTH_ISSUES health issues detected" | tee -a "$LOAD_LOG"
fi

echo "" | tee -a "$LOAD_LOG"

# 5. FINAL SESSION SUMMARY
echo "📋 SESSION INITIALIZATION COMPLETE" | tee -a "$LOAD_LOG"
echo "==========================================" | tee -a "$LOAD_LOG"
echo "🗓️  Session: $(date)" | tee -a "$LOAD_LOG"
echo "📝 Log saved to: $LOAD_LOG" | tee -a "$LOAD_LOG"
echo "" | tee -a "$LOAD_LOG"

echo "💡 QUICK ACTIONS AVAILABLE:" | tee -a "$LOAD_LOG"
echo "  • Run './docker-cleanup-script.sh' for Docker maintenance" | tee -a "$LOAD_LOG" 
echo "  • Check 'task-state.json' for detailed task history" | tee -a "$LOAD_LOG"
echo "  • Use Python: 'from task_state_manager import TaskStateManager' for task operations" | tee -a "$LOAD_LOG"
echo "" | tee -a "$LOAD_LOG"

echo "🎯 Ready for new tasks! All context and continuity loaded." | tee -a "$LOAD_LOG"
