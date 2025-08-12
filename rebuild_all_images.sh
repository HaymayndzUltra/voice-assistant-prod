#!/bin/bash
# Rebuild all images with fixed Dockerfiles

set -e

echo "================================================"
echo "🔨 Rebuilding All Images with Fixes"
echo "================================================"

export ORG='haymayndzultra'
export DATE=$(date -u +%Y%m%d)
export SHA=$(git rev-parse --short HEAD)
export TAG="${DATE}-${SHA}"
export GHCR_PAT='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'

echo "📋 Configuration:"
echo "  Organization: $ORG"
echo "  Tag: $TAG"
echo ""

# Login to GHCR
echo "🔐 Logging into GHCR..."
echo "$GHCR_PAT" | docker login ghcr.io -u "$ORG" --password-stdin

# Build function with retries
build_and_push() {
    local service=$1
    local dockerfile=$2
    local base_image=$3
    local machine=$4
    local context=$5
    
    echo ""
    echo "🔨 Building $service..."
    
    # Try to build
    if docker build \
        -f "$dockerfile" \
        --build-arg BASE_IMAGE="$base_image" \
        --build-arg MACHINE="$machine" \
        -t "ghcr.io/$ORG/ai_system/$service:$TAG" \
        .; then
        echo "✅ Built $service successfully"
        
        # Push to GHCR
        echo "📤 Pushing $service to GHCR..."
        if docker push "ghcr.io/$ORG/ai_system/$service:$TAG"; then
            echo "✅ Pushed $service"
        else
            echo "❌ Failed to push $service"
            return 1
        fi
    else
        echo "❌ Failed to build $service"
        return 1
    fi
}

# Build all services
echo ""
echo "📦 Building services..."

# ModelOpsCoordinator
build_and_push \
    "model_ops_coordinator" \
    "model_ops_coordinator/Dockerfile" \
    "ghcr.io/$ORG/family-llm-cu121:20250810-9c99cc9" \
    "mainpc" \
    "."

# RealTimeAudioPipeline
build_and_push \
    "real_time_audio_pipeline" \
    "real_time_audio_pipeline/Dockerfile" \
    "ghcr.io/$ORG/family-torch-cu121:20250810-9c99cc9" \
    "mainpc" \
    "."

# AffectiveProcessingCenter
build_and_push \
    "affective_processing_center" \
    "affective_processing_center/Dockerfile" \
    "ghcr.io/$ORG/family-torch-cu121:20250810-9c99cc9" \
    "mainpc" \
    "."

# UnifiedObservabilityCenter
build_and_push \
    "unified_observability_center" \
    "unified_observability_center/Dockerfile" \
    "ghcr.io/$ORG/family-web:20250810-9c99cc9" \
    "mainpc" \
    "."

# SelfHealingSupervisor
build_and_push \
    "self_healing_supervisor" \
    "services/self_healing_supervisor/Dockerfile" \
    "ghcr.io/$ORG/base-cpu-pydeps:20250810-9c99cc9" \
    "mainpc" \
    "."

# CentralErrorBus
build_and_push \
    "central_error_bus" \
    "services/central_error_bus/Dockerfile" \
    "ghcr.io/$ORG/family-web:20250810-9c99cc9" \
    "pc2" \
    "."

echo ""
echo "================================================"
echo "✅ Build Complete!"
echo "================================================"
echo ""
echo "Images built and pushed with tag: $TAG"
echo ""
echo "To deploy:"
echo "  - Docker Desktop: bash deploy_docker_desktop.sh"
echo "  - Native Linux: bash deploy_native_linux.sh"
echo ""
echo "To verify images:"
echo "  docker images | grep $TAG"