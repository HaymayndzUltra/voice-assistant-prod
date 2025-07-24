#!/bin/bash
# =============================================================================
# MAINPC CORE PLATFORM STARTUP SCRIPT
# =============================================================================

set -e

echo "🚀 Starting MainPC Core Platform Container..."
echo "Container Role: ${CONTAINER_ROLE}"
echo "Machine Type: ${MACHINE_TYPE}"
echo "Port Offset: ${PORT_OFFSET}"

# Create log directories
mkdir -p /app/logs/core-platform

# Function to start agent in background
start_agent() {
    local agent_name=$1
    local agent_script=$2
    local port=$3
    
    echo "🔧 Starting ${agent_name} on port ${port}..."
    cd /app
    python3 -m "${agent_script}" --port "${port}" \
        > "/app/logs/core-platform/${agent_name}.log" 2>&1 &
    
    # Store PID for later management
    echo $! > "/app/logs/core-platform/${agent_name}.pid"
    
    # Wait a moment for startup
    sleep 2
    
    # Check if process is still running
    if kill -0 $(cat "/app/logs/core-platform/${agent_name}.pid") 2>/dev/null; then
        echo "✅ ${agent_name} started successfully (PID: $(cat "/app/logs/core-platform/${agent_name}.pid"))"
    else
        echo "❌ ${agent_name} failed to start"
        return 1
    fi
}

# Start core services in order
echo "📡 Starting Core Platform Agents..."

# 1. ServiceRegistry (foundational service)
start_agent "ServiceRegistry" "main_pc_code.agents.service_registry_agent" "7200"

# 2. SystemDigitalTwin (system monitoring)
start_agent "SystemDigitalTwin" "main_pc_code.agents.system_digital_twin" "7220"

# 3. RequestCoordinator (request routing)
start_agent "RequestCoordinator" "main_pc_code.agents.request_coordinator" "26002"

# 4. ObservabilityHub (metrics and health)
start_agent "ObservabilityHub" "phase1_implementation.consolidated_agents.observability_hub.backup_observability_hub.observability_hub" "9000"

echo "🎉 All Core Platform agents started successfully!"

# Function to handle shutdown gracefully
shutdown() {
    echo "🛑 Shutting down Core Platform agents..."
    
    # Kill all agents gracefully
    for pidfile in /app/logs/core-platform/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            agent_name=$(basename "$pidfile" .pid)
            
            echo "🔄 Stopping ${agent_name} (PID: ${pid})..."
            
            # Try graceful shutdown first
            kill -TERM "$pid" 2>/dev/null || true
            
            # Wait up to 10 seconds for graceful shutdown
            for i in {1..10}; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    echo "✅ ${agent_name} stopped gracefully"
                    break
                fi
                sleep 1
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                echo "⚠️ Force killing ${agent_name}..."
                kill -KILL "$pid" 2>/dev/null || true
            fi
            
            rm -f "$pidfile"
        fi
    done
    
    echo "🏁 Core Platform shutdown complete"
    exit 0
}

# Set up signal handlers
trap shutdown SIGTERM SIGINT

# Keep container running and monitor agents
echo "📊 Core Platform running. Monitoring agents..."

while true; do
    # Check if all agents are still running
    all_running=true
    
    for pidfile in /app/logs/core-platform/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            agent_name=$(basename "$pidfile" .pid)
            
            if ! kill -0 "$pid" 2>/dev/null; then
                echo "💥 ${agent_name} has crashed! Attempting restart..."
                rm -f "$pidfile"
                
                # Restart based on agent name
                case "$agent_name" in
                    "ServiceRegistry")
                        start_agent "ServiceRegistry" "main_pc_code.agents.service_registry_agent" "7200" || all_running=false
                        ;;
                    "SystemDigitalTwin")
                        start_agent "SystemDigitalTwin" "main_pc_code.agents.system_digital_twin" "7220" || all_running=false
                        ;;
                    "RequestCoordinator")
                        start_agent "RequestCoordinator" "main_pc_code.agents.request_coordinator" "26002" || all_running=false
                        ;;
                    "ObservabilityHub")
                        start_agent "ObservabilityHub" "main_pc_code.agents.observability_hub" "9000" || all_running=false
                        ;;
                esac
            fi
        fi
    done
    
    # If critical agents keep failing, exit
    if [ "$all_running" = false ]; then
        echo "❌ Critical agents failed to restart. Exiting..."
        shutdown
    fi
    
    # Check every 30 seconds
    sleep 30
done 