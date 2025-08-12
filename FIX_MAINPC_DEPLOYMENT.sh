#!/bin/bash
# FIX DEPLOYMENT - Proper container runs without overriding entrypoints

set -e

echo "================================================"
echo "🔧 FIXING DEPLOYMENT - Proper Way"
echo "================================================"

# Variables
export ORG='haymayndzultra'
export TAG='20250812-576dfae'  # Using your latest tag

# Step 1: Stop and remove broken containers
echo "🛑 Stopping broken containers..."
docker stop model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor central_error_bus 2>/dev/null || true
docker rm -f model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor central_error_bus 2>/dev/null || true

echo "⏳ Waiting for cleanup..."
sleep 5

# Step 2: Run containers PROPERLY (without overriding entrypoint/cmd)
echo ""
echo "🚀 Starting services the RIGHT way..."

# ModelOpsCoordinator
echo "Starting ModelOpsCoordinator..."
docker run -d \
  --name model_ops_coordinator \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e PYTHONPATH=/app:/workspace \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG
# Note: NO command override - uses the CMD from Dockerfile

# RealTimeAudioPipeline  
echo "Starting RealTimeAudioPipeline..."
docker run -d \
  --name real_time_audio_pipeline \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e PYTHONPATH=/app:/workspace \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  --device /dev/snd \
  ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG

# AffectiveProcessingCenter
echo "Starting AffectiveProcessingCenter..."
docker run -d \
  --name affective_processing_center \
  --gpus all \
  --restart unless-stopped \
  --network host \
  -e PYTHONPATH=/app:/workspace \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/affective_processing_center:$TAG

# UnifiedObservabilityCenter
echo "Starting UnifiedObservabilityCenter..."
docker run -d \
  --name unified_observability_center \
  --restart unless-stopped \
  --network host \
  -e PYTHONPATH=/app:/workspace \
  -e MACHINE=mainpc \
  -v /home/haymayndz/AI_System_Monorepo:/workspace:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/unified_observability_center:$TAG

# SelfHealingSupervisor (if not already running)
echo "Starting SelfHealingSupervisor..."
docker run -d \
  --name self_healing_supervisor \
  --restart unless-stopped \
  --network host \
  -e MACHINE=mainpc \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /etc/machine-profile.json:/etc/machine-profile.json:ro \
  ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG

# Step 3: Wait for services to start
echo ""
echo "⏳ Waiting 30 seconds for services to initialize..."
sleep 30

# Step 4: Check container status
echo ""
echo "📦 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(model_ops|real_time|affective|unified|self_healing)" || true

# Step 5: Check logs for errors
echo ""
echo "🔍 Checking for startup errors..."
for service in model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor; do
    echo ""
    echo "--- $service logs (last 5 lines) ---"
    docker logs --tail 5 $service 2>&1 || echo "No logs available"
done

# Step 6: Health checks
echo ""
echo "================================================"
echo "🏥 HEALTH CHECK RESULTS"
echo "================================================"

check_health() {
    local name=$1
    local port=$2
    if curl -sf "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $name (port $port): HEALTHY"
        return 0
    else
        echo "❌ $name (port $port): FAILED"
        # Show why it failed
        echo "   Checking container status..."
        docker ps -a --filter "name=$name" --format "   Status: {{.Status}}"
        return 1
    fi
}

check_health "model_ops_coordinator" 8212
check_health "real_time_audio_pipeline" 6557
check_health "affective_processing_center" 6560
check_health "unified_observability_center" 9110
check_health "self_healing_supervisor" 9008

echo ""
echo "================================================"

# Step 7: Debug info if services are failing
echo ""
echo "📋 Debug Commands (if needed):"
echo "  docker logs model_ops_coordinator"
echo "  docker exec model_ops_coordinator ls -la /app"
echo "  docker exec model_ops_coordinator python --version"
echo ""
echo "🔧 To restart a service:"
echo "  docker restart <service_name>"
echo ""
echo "🔄 To rebuild everything:"
echo "  bash AUTOMATED_MAINPC_CRON.sh"