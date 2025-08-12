#!/bin/bash
echo "================================================"
echo "🧹 PROPER IMAGE CLEANUP"
echo "================================================"

# First, show what we have
echo "Current images:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}"

echo ""
echo "Cleaning duplicate service images..."

# Delete old affective_processing_center versions (keep only 20250812-576dfae)
for tag in 20250811-576dfae 20250811-230be7a 20250811-0596b99; do
    echo "Deleting ghcr.io/haymayndzultra/ai_system/affective_processing_center:$tag"
    docker rmi "ghcr.io/haymayndzultra/ai_system/affective_processing_center:$tag" 2>/dev/null
done

# Delete old real_time_audio_pipeline versions
for tag in 20250811-576dfae 20250811-230be7a 20250811-0596b99; do
    echo "Deleting ghcr.io/haymayndzultra/ai_system/real_time_audio_pipeline:$tag"
    docker rmi "ghcr.io/haymayndzultra/ai_system/real_time_audio_pipeline:$tag" 2>/dev/null
done

# Delete old model_ops_coordinator versions
for tag in 20250811-576dfae 20250811-230be7a 20250811-0596b99 20250811-07f77df; do
    echo "Deleting ghcr.io/haymayndzultra/ai_system/model_ops_coordinator:$tag"
    docker rmi "ghcr.io/haymayndzultra/ai_system/model_ops_coordinator:$tag" 2>/dev/null
done
docker rmi "ai_system/model_ops_coordinator:20250811-07f77df" 2>/dev/null

# Delete old self_healing_supervisor
docker rmi "ghcr.io/haymayndzultra/ai_system/self_healing_supervisor:20250811-576dfae" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/self_healing_supervisor:20250810-9c99cc9" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/self_healing_supervisor:20250810-07f77df" 2>/dev/null

# Delete old unified_observability_center
docker rmi "ghcr.io/haymayndzultra/unified_observability_center:20250810-07f77df" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/unified_observability_center:20250811-07f77df" 2>/dev/null

# Delete old central_error_bus
docker rmi "ghcr.io/haymayndzultra/central_error_bus:20250810-9c99cc9" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/central_error_bus:20250810-07f77df" 2>/dev/null

# Delete other old services
docker rmi "ghcr.io/haymayndzultra/system_digital_twin:20250811-07f77df" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/system_digital_twin:20250810-07f77df" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/unified_system_agent:20250811-07f77df" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/unified_system_agent:20250810-07f77df" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/service_registry:20250811-07f77df" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/service_registry:20250810-07f77df" 2>/dev/null

# Delete duplicate base images
docker rmi "family-llm-cu121:20250810-9c99cc9" 2>/dev/null
docker rmi "family-torch-cu121:20250810-9c99cc9" 2>/dev/null
docker rmi "family-vision-cu121:20250810-9c99cc9" 2>/dev/null
docker rmi "base-gpu-cu121:20250810-9c99cc9" 2>/dev/null
docker rmi "family-web:20250810-9c99cc9" 2>/dev/null
docker rmi "base-utils:20250810-9c99cc9" 2>/dev/null
docker rmi "base-cpu-pydeps:20250810-9c99cc9" 2>/dev/null
docker rmi "base-python:20250810-9c99cc9" 2>/dev/null
docker rmi "legacy-py310-cpu:20250810-9c99cc9" 2>/dev/null

# Delete pc2 images (not needed on MainPC)
docker rmi "ghcr.io/haymayndzultra/pc2-base-cache_redis:latest" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/pc2-base-minimal:latest" 2>/dev/null
docker rmi "ghcr.io/haymayndzultra/pc2-base-dl:latest" 2>/dev/null

# Clean all <none> images
docker images -f "dangling=true" -q | xargs docker rmi 2>/dev/null

echo ""
echo "Cleaning build cache..."
docker builder prune -a -f

echo ""
echo "Final aggressive cleanup..."
docker image prune -a -f

echo ""
echo "================================================"
echo "✅ CLEANUP COMPLETE!"
echo "================================================"
docker system df
