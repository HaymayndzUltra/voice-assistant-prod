#!/bin/bash

# Smart Session Detection and Auto-Loading
# This checks various conditions and auto-loads memory if needed

detect_new_session() {
    local session_file="/tmp/last_ai_session"
    local current_time=$(date +%s)
    local session_timeout=3600  # 1 hour
    
    if [ -f "$session_file" ]; then
        local last_session=$(cat "$session_file")
        local time_diff=$((current_time - last_session))
        
        if [ $time_diff -gt $session_timeout ]; then
            echo "New session detected (timeout: ${time_diff}s)"
            return 0
        else
            echo "Recent session (${time_diff}s ago)"
            return 1
        fi
    else
        echo "First session today"
        return 0
    fi
}

# Check if we're in AI workspace
if [ "$PWD" = "/home/haymayndz/AI_System_Monorepo" ]; then
    if detect_new_session; then
        echo "🤖 Auto-loading memory for new AI session..."
        ./auto_load_memory.sh
        echo $(date +%s) > /tmp/last_ai_session
    fi
fi
