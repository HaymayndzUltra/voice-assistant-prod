#!/bin/bash
# Build base images locally first (no GHCR dependency)
# This allows testing before pushing to registry

set -e

echo "============================================================"
echo "🚀 BUILDING BASE IMAGES LOCALLY FIRST"
echo "============================================================"
echo "This builds everything locally without needing GHCR access"
echo ""

# Function to build locally
build_local() {
    local name=$1
    local context=$2
    local dockerfile=$3
    
    echo "Building ${name}..."
    docker build \
        -t ${name}:latest \
        -f ${dockerfile} \
        ${context}
    
    echo "✅ ${name} built locally"
    echo ""
}

# Phase 1: Build base images IN ORDER (dependencies matter!)
echo "============================================================"
echo "PHASE 1: BASE IMAGE HIERARCHY"
echo "============================================================"

# 1. Base Python (no dependencies)
build_local "base-python" "/workspace/docker/base-images/base-python" "Dockerfile"

# 2. Base Utils (depends on base-python - but we'll build from Docker Hub for now)
echo "Note: base-utils needs base-python. Building standalone for now..."
build_local "base-utils" "/workspace/docker/base-images/base-utils" "Dockerfile"

# 3. Base CPU Pydeps (depends on base-utils - standalone for now) 
build_local "base-cpu-pydeps" "/workspace/docker/base-images/base-cpu-pydeps" "Dockerfile"

# 4. Base GPU CUDA
build_local "base-gpu-cu121" "/workspace/docker/base-images/base-gpu-cu121" "Dockerfile"

# 5. Legacy Python 3.10
build_local "legacy-py310-cpu" "/workspace/docker/base-images/legacy-py310-cpu" "Dockerfile"

echo "============================================================"
echo "PHASE 2: FAMILY IMAGES (These need fixing!)"
echo "============================================================"
echo "⚠️  Family images reference ghcr.io/* which doesn't exist yet!"
echo "You need to either:"
echo "  1. Build and push base images to GHCR first, OR"
echo "  2. Modify family Dockerfiles to use local base images"
echo ""

# Temporarily modify family Dockerfiles to use local images
echo "Fixing family Dockerfiles to use local base images..."

# Fix family-web to use local base
sed -i 's|FROM ghcr.io/haymayndzultra/base-cpu-pydeps:.*|FROM base-cpu-pydeps:latest|' \
    /workspace/docker/base-images/family-web/Dockerfile

# Fix family-torch-cu121 to use local base
sed -i 's|FROM ghcr.io/haymayndzultra/base-gpu-cu121:.*|FROM base-gpu-cu121:latest|' \
    /workspace/docker/base-images/family-torch-cu121/Dockerfile

# Fix family-llm-cu121 to use local family-torch
sed -i 's|FROM ghcr.io/haymayndzultra/family-torch-cu121:.*|FROM family-torch-cu121:latest|' \
    /workspace/docker/base-images/family-llm-cu121/Dockerfile

# Fix family-vision-cu121 to use local base
sed -i 's|FROM ghcr.io/haymayndzultra/base-gpu-cu121:.*|FROM base-gpu-cu121:latest|' \
    /workspace/docker/base-images/family-vision-cu121/Dockerfile

echo "✅ Modified family Dockerfiles to use local images"
echo ""

# Now build family images
build_local "family-web" "/workspace/docker/base-images/family-web" "Dockerfile"
build_local "family-torch-cu121" "/workspace/docker/base-images/family-torch-cu121" "Dockerfile"
build_local "family-llm-cu121" "/workspace/docker/base-images/family-llm-cu121" "Dockerfile"
build_local "family-vision-cu121" "/workspace/docker/base-images/family-vision-cu121" "Dockerfile"

echo "============================================================"
echo "PHASE 3: CORE SERVICES (Need to fix these too!)"
echo "============================================================"
echo ""

# Fix service Dockerfiles to use local family images
echo "Fixing service Dockerfiles to use local family images..."

for dockerfile in \
    /workspace/model_ops_coordinator/Dockerfile.optimized \
    /workspace/real_time_audio_pipeline/Dockerfile.optimized \
    /workspace/affective_processing_center/Dockerfile.optimized \
    /workspace/unified_observability_center/Dockerfile.optimized \
    /workspace/memory_fusion_hub/Dockerfile.optimized \
    /workspace/services/self_healing_supervisor/Dockerfile.optimized \
    /workspace/services/central_error_bus/Dockerfile.optimized
do
    if [ -f "$dockerfile" ]; then
        # Replace ghcr.io references with local images
        sed -i 's|FROM ghcr.io/haymayndzultra/\([^:]*\):.*|FROM \1:latest|' "$dockerfile"
        echo "  ✅ Fixed $dockerfile"
    fi
done

echo ""
echo "Now you can build services:"
echo ""

# Build core services
echo "# ModelOpsCoordinator"
echo "docker build -f model_ops_coordinator/Dockerfile.optimized \\"
echo "  --build-arg MACHINE=mainpc \\"
echo "  -t model_ops_coordinator:latest ."
echo ""

echo "# RealTimeAudioPipeline"
echo "docker build -f real_time_audio_pipeline/Dockerfile.optimized \\"
echo "  --build-arg MACHINE=mainpc \\"
echo "  -t real_time_audio_pipeline:latest ."
echo ""

echo "# And so on for other services..."
echo ""

echo "============================================================"
echo "✅ PREPARATION COMPLETE!"
echo "============================================================"
echo ""
echo "NEXT STEPS:"
echo "1. Review the modified Dockerfiles"
echo "2. Build base images: ./BUILD_LOCAL_FIRST.sh"
echo "3. Build services with the commands above"
echo "4. Test locally before pushing to GHCR"
echo ""
echo "To restore GHCR references later:"
echo "  git checkout -- docker/base-images/*/Dockerfile"
echo "  git checkout -- */Dockerfile.optimized"