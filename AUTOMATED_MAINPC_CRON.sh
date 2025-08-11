#!/bin/bash
# FULLY AUTOMATED BUILD - Run and Rest!
# Just start this on MainPC and walk away

set -e
LOG_FILE="/home/haymayndz/deployment_$(date +%Y%m%d_%H%M%S).log"

# Redirect all output to log file
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "=========================================="
echo "🤖 AUTOMATED DEPLOYMENT STARTING"
echo "📝 Logging to: $LOG_FILE"
echo "⏰ Started at: $(date)"
echo "💤 GO REST! This will take ~20 minutes"
echo "=========================================="

# Auto-answer yes to any prompts
export DEBIAN_FRONTEND=noninteractive
export DOCKER_BUILDKIT=1

# Step 1: Setup
cd /home/haymayndz/AI_System_Monorepo || exit 1

# Step 2: Git update (force to avoid conflicts)
git fetch origin
git checkout -f cursor/build-and-deploy-ai-system-services-0e14
git reset --hard origin/cursor/build-and-deploy-ai-system-services-0e14

# Step 3: Auto-login to GHCR
echo "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" | docker login ghcr.io -u haymayndzultra --password-stdin

# Step 4: Clean up space first
echo "🧹 Cleaning Docker space..."
docker system prune -af --volumes || true

# Step 5: Build with retries
export DATE=$(date -u +%Y%m%d)
export SHA=$(git rev-parse --short HEAD)
export TAG="${DATE}-${SHA}"

build_with_retry() {
    local service=$1
    local dockerfile=$2
    local base=$3
    local machine=$4
    local context=$5
    
    for i in {1..3}; do
        echo "🔨 Building $service (attempt $i/3)..."
        if docker build -f "$dockerfile" \
            --build-arg BASE_IMAGE="$base" \
            --build-arg MACHINE="$machine" \
            -t "ghcr.io/haymayndzultra/ai_system/$service:$TAG" \
            "$context" 2>&1; then
            echo "✅ $service built successfully"
            return 0
        else
            echo "⚠️  Retry $i failed for $service"
            sleep 5
        fi
    done
    echo "❌ Failed to build $service after 3 attempts"
    return 1
}

# Build all services
build_with_retry "model_ops_coordinator" \
    "model_ops_coordinator/Dockerfile" \
    "ghcr.io/haymayndzultra/family-llm-cu121:20250810-9c99cc9" \
    "mainpc" \
    "model_ops_coordinator"

build_with_retry "real_time_audio_pipeline" \
    "real_time_audio_pipeline/Dockerfile" \
    "ghcr.io/haymayndzultra/family-torch-cu121:20250810-9c99cc9" \
    "mainpc" \
    "real_time_audio_pipeline"

build_with_retry "affective_processing_center" \
    "affective_processing_center/Dockerfile" \
    "ghcr.io/haymayndzultra/family-torch-cu121:20250810-9c99cc9" \
    "mainpc" \
    "affective_processing_center"

build_with_retry "self_healing_supervisor" \
    "services/self_healing_supervisor/Dockerfile" \
    "ghcr.io/haymayndzultra/base-cpu-pydeps:20250810-9c99cc9" \
    "mainpc" \
    "services/self_healing_supervisor"

build_with_retry "central_error_bus" \
    "services/central_error_bus/Dockerfile" \
    "ghcr.io/haymayndzultra/family-web:20250810-9c99cc9" \
    "pc2" \
    "services/central_error_bus"

build_with_retry "unified_observability_center" \
    "unified_observability_center/Dockerfile" \
    "ghcr.io/haymayndzultra/family-web:20250810-9c99cc9" \
    "mainpc" \
    "unified_observability_center"

# Step 6: Push all (with retries)
echo "📤 Pushing to GHCR..."
for service in model_ops_coordinator real_time_audio_pipeline affective_processing_center \
              self_healing_supervisor central_error_bus unified_observability_center; do
    for i in {1..3}; do
        if docker push "ghcr.io/haymayndzultra/ai_system/$service:$TAG" 2>&1; then
            echo "✅ Pushed $service"
            break
        else
            echo "⚠️  Push retry $i for $service"
            sleep 5
        fi
    done
done

# Step 7: Deploy locally
echo "🚀 Deploying services..."
export FORCE_IMAGE_TAG=$TAG
sudo systemctl reload supervisor || true

# Step 8: Wait and test
echo "⏳ Waiting 60 seconds for services..."
sleep 60

# Step 9: Health checks with notifications
echo ""
echo "=========================================="
echo "🏥 HEALTH CHECK RESULTS"
echo "=========================================="

FAILED=0
check_health() {
    local name=$1
    local port=$2
    if curl -sf "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $name (port $port): HEALTHY"
    else
        echo "❌ $name (port $port): FAILED"
        FAILED=$((FAILED + 1))
    fi
}

check_health "ModelOpsCoordinator" 8212
check_health "RealTimeAudioPipeline" 6557
check_health "AffectiveProcessingCenter" 6560
check_health "UnifiedObservabilityCenter" 9110

echo ""
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo "🎉 DEPLOYMENT SUCCESSFUL!"
    echo "✅ All services healthy"
    
    # Optional: Send notification
    # notify-send "Deployment Complete" "All services deployed successfully"
else
    echo "⚠️  DEPLOYMENT COMPLETED WITH $FAILED FAILURES"
    echo "Check logs: docker logs <container_name>"
fi
echo "=========================================="
echo "⏰ Completed at: $(date)"
echo "📝 Full log saved to: $LOG_FILE"
echo ""
echo "Next: Run PC2_EXECUTE_NOW.sh on PC2"