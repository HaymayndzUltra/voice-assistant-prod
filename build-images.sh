#!/usr/bin/env bash
set -euo pipefail

# Build script for modular AI System Docker images
echo "Starting modular Docker image build process..."

# Array of image specifications (tag:dockerfile_path)
images=(
    # MainPC Services
    ai_system/infra_core:main_pc_code/Dockerfile.infra_core
    ai_system/coordination:main_pc_code/Dockerfile.coordination
    ai_system/observability_hub:phase1_implementation/consolidated_agents/observability_hub/Dockerfile
    ai_system/memory_stack:main_pc_code/Dockerfile.memory_stack
    ai_system/vision_suite:main_pc_code/Dockerfile.vision_suite
    ai_system/speech_pipeline:main_pc_code/Dockerfile.speech_pipeline
    ai_system/learning_pipeline:main_pc_code/Dockerfile.learning_pipeline
    ai_system/reasoning_suite:main_pc_code/Dockerfile.reasoning_suite
    ai_system/language_stack:main_pc_code/Dockerfile.language_stack
    ai_system/utility_suite:main_pc_code/Dockerfile.utility_suite
    ai_system/emotion_system:main_pc_code/Dockerfile.emotion_system
    # PC2 Services
    ai_system_pc2/infra_core:pc2_code/Dockerfile.infra_core
    ai_system_pc2/memory_stack:pc2_code/Dockerfile.memory_stack
    ai_system_pc2/async_pipeline:pc2_code/Dockerfile.async_pipeline
    ai_system_pc2/tutoring_suite:pc2_code/Dockerfile.tutoring_suite
    ai_system_pc2/vision_dream_suite:pc2_code/Dockerfile.vision_dream_suite
    ai_system_pc2/utility_suite:pc2_code/Dockerfile.utility_suite
    ai_system_pc2/web_interface:pc2_code/Dockerfile.web_interface
)

# Track build results
SUCCESS_COUNT=0
FAILED_COUNT=0
FAILED_IMAGES=()

# Build each image
for spec in "${images[@]}"; do
    IFS=: read tag file <<<"$spec"
    echo ""
    echo "============================================"
    echo "### BUILDING $tag (file: $file)"
    echo "============================================"
    
    if [ ! -f "$file" ]; then
        echo "ERROR: Dockerfile not found: $file"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_IMAGES+=("$tag (missing dockerfile)")
        continue
    fi
    
    if docker buildx build --progress=plain -f "$file" -t "$tag" .; then
        echo "✅ Successfully built: $tag"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "❌ Failed to build: $tag"
        FAILED_COUNT=$((FAILED_COUNT + 1))
        FAILED_IMAGES+=("$tag")
    fi
done

# Summary report
echo ""
echo "============================================"
echo "BUILD SUMMARY"
echo "============================================"
echo "✅ Successful builds: $SUCCESS_COUNT"
echo "❌ Failed builds: $FAILED_COUNT"

if [ $FAILED_COUNT -gt 0 ]; then
    echo ""
    echo "Failed images:"
    for img in "${FAILED_IMAGES[@]}"; do
        echo "  - $img"
    done
    exit 1
fi

echo ""
echo "All images built successfully!"
echo ""
echo "To push images to registry, run:"
echo "  ./push-images.sh" 