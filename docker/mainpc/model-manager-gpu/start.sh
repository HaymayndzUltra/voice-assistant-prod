#!/bin/bash
# =============================================================================
# MAINPC MODEL MANAGER GPU STARTUP SCRIPT
# =============================================================================

set -e

echo "🚀 Starting MainPC Model Manager GPU Container..."
echo "Container Role: ${CONTAINER_ROLE}"
echo "CUDA Devices: ${CUDA_VISIBLE_DEVICES}"

# Check GPU availability
echo "🔍 Checking GPU availability..."
nvidia-smi || echo "⚠️ nvidia-smi not available"

# Create log directories
mkdir -p /app/logs/model-manager-gpu

# Function to start agent in background
start_agent() {
    local agent_name=$1
    local agent_script=$2
    local port=$3
    
    echo "🔧 Starting ${agent_name} on port ${port}..."
    cd /app
    python3 -m "${agent_script}" --port="${port}" --machine="${MACHINE_TYPE}" \
        > "/app/logs/model-manager-gpu/${agent_name}.log" 2>&1 &
    
    # Store PID for later management
    echo $! > "/app/logs/model-manager-gpu/${agent_name}.pid"
    
    # Wait for startup (longer for GPU services)
    sleep 10
    
    # Check if process is still running
    if kill -0 $(cat "/app/logs/model-manager-gpu/${agent_name}.pid") 2>/dev/null; then
        echo "✅ ${agent_name} started successfully (PID: $(cat "/app/logs/model-manager-gpu/${agent_name}.pid"))"
    else
        echo "❌ ${agent_name} failed to start"
        return 1
    fi
}

# Check available models
echo "📊 Checking available models..."
if [ -d "/app/models/gguf" ]; then
    echo "Found GGUF models:"
    ls -la /app/models/gguf/
else
    echo "⚠️ No GGUF models directory found"
fi

# Start model management services
echo "🧠 Starting Model Manager GPU Agents..."

# 1. ModelManagerSuite (primary model management)
start_agent "ModelManagerSuite" "main_pc_code.model_manager_suite" "7211"

# 2. UnifiedSystemAgent (system integration)
start_agent "UnifiedSystemAgent" "main_pc_code.agents.unified_system_agent" "7225"

echo "🎉 All Model Manager GPU agents started successfully!"

# Health check endpoint for the container
echo "🏥 Starting health check server on port 8211..."
python3 -c "
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            # Check if all services are running
            import os
            import subprocess
            
            status = {'status': 'healthy', 'services': {}}
            
            for service in ['ModelManagerSuite', 'UnifiedSystemAgent']:
                pidfile = f'/app/logs/model-manager-gpu/{service}.pid'
                if os.path.exists(pidfile):
                    with open(pidfile, 'r') as f:
                        pid = int(f.read().strip())
                    try:
                        os.kill(pid, 0)  # Check if process exists
                        status['services'][service] = 'running'
                    except OSError:
                        status['services'][service] = 'stopped'
                        status['status'] = 'unhealthy'
                else:
                    status['services'][service] = 'not_started'
                    status['status'] = 'unhealthy'
            
            self.send_response(200 if status['status'] == 'healthy' else 503)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(404)
            self.end_headers()

def run_health_server():
    server = HTTPServer(('0.0.0.0', 8211), HealthCheckHandler)
    server.serve_forever()

health_thread = threading.Thread(target=run_health_server)
health_thread.daemon = True
health_thread.start()

# Keep main thread alive
while True:
    time.sleep(1)
" &

# Function to handle shutdown gracefully
shutdown() {
    echo "🛑 Shutting down Model Manager GPU agents..."
    
    # Kill all agents gracefully
    for pidfile in /app/logs/model-manager-gpu/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            agent_name=$(basename "$pidfile" .pid)
            
            echo "🔄 Stopping ${agent_name} (PID: ${pid})..."
            
            # Try graceful shutdown first
            kill -TERM "$pid" 2>/dev/null || true
            
            # Wait up to 15 seconds for graceful shutdown (longer for GPU services)
            for i in {1..15}; do
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
    
    echo "🏁 Model Manager GPU shutdown complete"
    exit 0
}

# Set up signal handlers
trap shutdown SIGTERM SIGINT

# Keep container running and monitor agents
echo "📊 Model Manager GPU running. Monitoring agents..."

while true; do
    # Monitor GPU memory usage
    if command -v nvidia-smi >/dev/null 2>&1; then
        gpu_memory=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -n1)
        echo "📈 GPU Memory Usage: ${gpu_memory}MB"
    fi
    
    # Check if all agents are still running
    all_running=true
    
    for pidfile in /app/logs/model-manager-gpu/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            agent_name=$(basename "$pidfile" .pid)
            
            if ! kill -0 "$pid" 2>/dev/null; then
                echo "💥 ${agent_name} has crashed! Attempting restart..."
                rm -f "$pidfile"
                
                # Restart based on agent name
                case "$agent_name" in
                    "ModelManagerSuite")
                        start_agent "ModelManagerSuite" "main_pc_code.model_manager_suite" "7211" || all_running=false
                        ;;
                    "UnifiedSystemAgent")
                        start_agent "UnifiedSystemAgent" "main_pc_code.agents.unified_system_agent" "7225" || all_running=false
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
    
    # Check every 60 seconds (less frequent for GPU services)
    sleep 60
done 