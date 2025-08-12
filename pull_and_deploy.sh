#!/bin/bash
# Pull and deploy pre-built images from GHCR
# Run this AFTER GitHub Actions completes

set -e

echo "============================================================"
echo "🚀 PULLING PRE-BUILT IMAGES FROM GHCR"
echo "============================================================"

# Get the latest SHA or use provided one
SHA=${1:-latest}

if [ "$SHA" == "latest" ]; then
    echo "Using 'latest' tag. For specific version, run: $0 <git-sha>"
else
    echo "Using SHA: $SHA"
fi

echo ""
echo "📦 Pulling service images..."

# Core services
SERVICES=(
    "model_ops_coordinator"
    "real_time_audio_pipeline"
    "affective_processing_center"
    "unified_observability_center"
    "memory_fusion_hub"
    "self_healing_supervisor"
    "central_error_bus"
)

for service in "${SERVICES[@]}"; do
    echo "Pulling $service..."
    docker pull ghcr.io/haymayndzultra/ai_system/${service}:${SHA} || {
        echo "❌ Failed to pull $service. Has it been built yet?"
        echo "Check: https://github.com/HaymayndzUltra/voice-assistant-prod/actions"
        exit 1
    }
    
    # Tag as latest for easy reference
    docker tag ghcr.io/haymayndzultra/ai_system/${service}:${SHA} ${service}:latest
    echo "✅ $service ready"
done

echo ""
echo "============================================================"
echo "✅ ALL IMAGES PULLED SUCCESSFULLY!"
echo "============================================================"
echo ""
echo "To run services (Docker Desktop):"
echo "  ./deploy_docker_desktop.sh"
echo ""
echo "To run services (Native Linux):"
echo "  ./deploy_native_linux.sh"
echo ""
echo "To check health:"
echo "  ./validate_fleet.sh"