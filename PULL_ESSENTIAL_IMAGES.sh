#!/bin/bash
# Pull only the essential, latest images from GHCR

echo "================================================"
echo "📥 PULLING ESSENTIAL IMAGES FROM GHCR"
echo "================================================"

ORG="ghcr.io/haymayndzultra"
TAG="20250812-576dfae"

echo ""
echo "1️⃣ Pulling 6 core services (latest fixed versions)..."
echo "---------------------------------------------------"

# Core services with fixes
services=(
    "ai_system/model_ops_coordinator"
    "ai_system/real_time_audio_pipeline"
    "ai_system/affective_processing_center"
    "ai_system/self_healing_supervisor"
    "ai_system/central_error_bus"
    "ai_system/unified_observability_center"
)

for service in "${services[@]}"; do
    echo "Pulling $service:$TAG..."
    docker pull "$ORG/$service:$TAG"
done

echo ""
echo "2️⃣ Pulling essential base images..."
echo "------------------------------------"

# Only pull base images if you need to rebuild
echo "Pulling base-python..."
docker pull "$ORG/base-python:20250810-9c99cc9"

echo ""
echo "================================================"
echo "✅ DONE! Essential images pulled"
echo "================================================"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
echo ""
echo "Total disk usage:"
docker system df
