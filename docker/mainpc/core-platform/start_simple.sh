#!/bin/bash
# =============================================================================
# MAINPC CORE PLATFORM SIMPLE STARTUP SCRIPT
# =============================================================================

set -e

echo "🚀 Starting MainPC Core Platform Container (SIMPLE)..."
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

echo "📡 Starting ServiceRegistry only..."

# Start ServiceRegistry
cd /app
echo "🔧 Starting ServiceRegistry on port 7200..."
python3 main_pc_code/agents/service_registry_agent.py --port 7200 &
SERVICE_REGISTRY_PID=$!

# Wait for startup
sleep 5

# Check if process is still running
if kill -0 $SERVICE_REGISTRY_PID 2>/dev/null; then
    echo "✅ ServiceRegistry started successfully (PID: $SERVICE_REGISTRY_PID)"
    
    # Test health endpoint
    sleep 3
    if curl -f "http://localhost:7201/health" >/dev/null 2>&1; then
        echo "✅ ServiceRegistry health check passed"
    else
        echo "⚠️ ServiceRegistry health check not responding yet"
    fi
else
    echo "❌ ServiceRegistry failed to start"
    exit 1
fi

echo "🎉 ServiceRegistry is running successfully!"

# Keep container running
echo "📊 Container running. Press Ctrl+C to stop..."
trap "echo '🛑 Shutting down...'; kill $SERVICE_REGISTRY_PID; exit 0" SIGTERM SIGINT

while kill -0 $SERVICE_REGISTRY_PID 2>/dev/null; do
    sleep 10
done

echo "💥 ServiceRegistry has stopped"
exit 1 