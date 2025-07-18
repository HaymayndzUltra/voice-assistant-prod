#!/bin/bash

# Background Agents Startup Script for Cursor Ultra Plan
# This script starts background monitoring agents

echo "🚀 Starting Background Agents for Cursor Ultra Plan..."

# Set environment variables
export AI_SYSTEM_PATH="/home/haymayndz/AI_System_Monorepo"
export GITHUB_TOKEN="${GITHUB_TOKEN:-}"
export MONITORING_INTERVAL="30"
export ENABLE_BACKGROUND_MONITORING="true"

# Create logs directory
mkdir -p /home/haymayndz/AI_System_Monorepo/logs

# Start background agent manager
echo "📊 Starting System Monitor..."
nohup python3 /home/haymayndz/AI_System_Monorepo/scripts/background_agent_manager.py > /home/haymayndz/AI_System_Monorepo/logs/background_agents.log 2>&1 &

# Start AI system monitor
echo "🤖 Starting AI System Monitor..."
nohup python3 /home/haymayndz/AI_System_Monorepo/scripts/ai_system_monitor.py > /home/haymayndz/AI_System_Monorepo/logs/ai_monitor.log 2>&1 &

# Start agent health checker
echo "🏥 Starting Agent Health Checker..."
nohup python3 /home/haymayndz/AI_System_Monorepo/scripts/check_all_agents_health.py > /home/haymayndz/AI_System_Monorepo/logs/health_checker.log 2>&1 &

echo "✅ Background agents started!"
echo "📋 Logs available in: /home/haymayndz/AI_System_Monorepo/logs/"
echo ""
echo "🔍 Monitor background agents:"
echo "   tail -f /home/haymayndz/AI_System_Monorepo/logs/background_agents.log"
echo ""
echo "🛑 Stop background agents:"
echo "   pkill -f background_agent_manager.py"
echo "   pkill -f ai_system_monitor.py"
echo "   pkill -f check_all_agents_health.py" 