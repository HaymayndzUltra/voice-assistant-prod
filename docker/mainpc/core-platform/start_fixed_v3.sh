#!/bin/bash
# =============================================================================
# MAINPC CORE PLATFORM FIXED STARTUP SCRIPT V3
# =============================================================================

set -e

echo "🚀 Starting MainPC Core Platform Container (FIXED V3)..."
echo "Container Role: ${CONTAINER_ROLE}"
echo "Machine Type: ${MACHINE_TYPE}"

# Create log directories
mkdir -p /app/logs/core-platform

# Set proper environment variables for container networking
export NATS_URL=${NATS_URL:-"nats://nats-server:4222"}
export REDIS_URL=${REDIS_URL:-"redis://redis-server:6379"}
export PYTHONPATH="/app:/app/main_pc_code:/app/common_utils:/app/common"

# Set container-specific service discovery
export SERVICE_DISCOVERY_MODE="container_dns"
export ENABLE_CROSS_MACHINE_DISCOVERY="true"

# Set proper hostnames for container communication
export NATS_HOST="nats-server"
export REDIS_HOST="redis-server"
export NATS_PORT="4222"
export REDIS_PORT="6379"

# Set specific health ports for each agent (matching their default expectations)
export SERVICE_REGISTRY_HEALTH_PORT="7201"
export SYSTEM_DIGITAL_TWIN_HEALTH_PORT="8220"  # Agent expects 8220
export REQUEST_COORDINATOR_HEALTH_PORT="26003"

# Function to start agent in background with proper environment and NATS configuration
start_agent() {
    local agent_name=$1
    local agent_script=$2
    local port=$3
    local health_port=$4
    
    echo "🔧 Starting ${agent_name} on port ${port} (health: ${health_port})..."
    
    # Set agent-specific environment variables
    export AGENT_NAME="${agent_name}"
    export AGENT_PORT="${port}"
    export HEALTH_PORT="${health_port}"
    
    # Set NATS and Redis configuration for the agent
    export NATS_SERVERS="[\"${NATS_URL}\"]"
    export REDIS_HOST="${REDIS_HOST}"
    export REDIS_PORT="${REDIS_PORT}"
    
    cd /app
    
    # Start the agent with proper NATS configuration
    python3 "${agent_script}" \
        --port "${port}" \
        --nats-servers "${NATS_URL}" \
        --redis-host "${REDIS_HOST}" \
        --redis-port "${REDIS_PORT}" \
        > "/app/logs/core-platform/${agent_name}.log" 2>&1 &
    
    # Store PID for later management
    echo $! > "/app/logs/core-platform/${agent_name}.pid"
    
    # Wait a moment for startup
    sleep 8
    
    # Check if process is still running
    if kill -0 $(cat "/app/logs/core-platform/${agent_name}.pid") 2>/dev/null; then
        echo "✅ ${agent_name} started successfully (PID: $(cat "/app/logs/core-platform/${agent_name}.pid"))"
        
        # Test health endpoint if available
        if [ -n "${health_port}" ]; then
            sleep 3
            if curl -f "http://localhost:${health_port}/health" >/dev/null 2>&1; then
                echo "✅ ${agent_name} health check passed"
            else
                echo "⚠️ ${agent_name} health check not responding yet (port ${health_port})"
            fi
        fi
    else
        echo "❌ ${agent_name} failed to start"
        echo "=== ${agent_name} LOG ==="
        cat "/app/logs/core-platform/${agent_name}.log"
        echo "=== END LOG ==="
        return 1
    fi
}

# Start core services in order with proper port allocation
echo "📡 Starting Core Platform Agents..."

# 1. ServiceRegistry (foundational service)
start_agent "ServiceRegistry" "main_pc_code/agents/service_registry_agent.py" "7200" "7201"

# Wait a bit for ServiceRegistry to fully initialize
sleep 5

# 2. SystemDigitalTwin (system monitoring) - using expected health port 8220
start_agent "SystemDigitalTwin" "main_pc_code/agents/system_digital_twin.py" "7220" "8220"

# Wait a bit for SystemDigitalTwin to fully initialize
sleep 5

# 3. RequestCoordinator (request routing) - using expected health port 26003
start_agent "RequestCoordinator" "main_pc_code/agents/request_coordinator.py" "26002" "26003"

echo "🎉 Core Platform agents started successfully!"

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
                        start_agent "ServiceRegistry" "main_pc_code/agents/service_registry_agent.py" "7200" "7201" || all_running=false
                        ;;
                    "SystemDigitalTwin")
                        start_agent "SystemDigitalTwin" "main_pc_code/agents/system_digital_twin.py" "7220" "8220" || all_running=false
                        ;;
                    "RequestCoordinator")
                        start_agent "RequestCoordinator" "main_pc_code/agents/request_coordinator.py" "26002" "26003" || all_running=false
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