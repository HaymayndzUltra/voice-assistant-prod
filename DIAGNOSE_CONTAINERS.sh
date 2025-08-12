#!/bin/bash
# DIAGNOSE - Check what's actually in the containers

echo "================================================"
echo "🔍 CONTAINER DIAGNOSTICS"
echo "================================================"

export ORG='haymayndzultra'
export TAG='20250812-576dfae'

echo ""
echo "📋 Checking what's inside the images..."
echo ""

# Function to inspect an image
inspect_image() {
    local service=$1
    local image="ghcr.io/$ORG/ai_system/$service:$TAG"
    
    echo "--- $service ---"
    
    # Check if image exists
    if docker image inspect "$image" >/dev/null 2>&1; then
        echo "✅ Image exists: $image"
        
        # Check entrypoint and cmd
        echo "ENTRYPOINT: $(docker inspect "$image" --format='{{.Config.Entrypoint}}')"
        echo "CMD: $(docker inspect "$image" --format='{{.Config.Cmd}}')"
        echo "WORKDIR: $(docker inspect "$image" --format='{{.Config.WorkingDir}}')"
        echo "USER: $(docker inspect "$image" --format='{{.Config.User}}')"
        
        # Try to list app directory
        echo "Checking /app contents:"
        docker run --rm --entrypoint ls "$image" -la /app 2>&1 | head -5 || echo "  Failed to list /app"
        
        # Check Python
        echo "Python version:"
        docker run --rm --entrypoint python "$image" --version 2>&1 || echo "  Failed to get Python version"
        
    else
        echo "❌ Image NOT found: $image"
        echo "   Need to pull or rebuild!"
    fi
    echo ""
}

# Check all services
for service in model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor; do
    inspect_image $service
done

echo "================================================"
echo "🐋 Current Container Status:"
echo "================================================"
docker ps -a --filter "name=model_ops_coordinator" --filter "name=real_time_audio_pipeline" --filter "name=affective_processing_center" --filter "name=unified_observability_center" --filter "name=self_healing_supervisor" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

echo ""
echo "================================================"
echo "📝 Recommendations:"
echo "================================================"

# Check if images exist
MISSING_IMAGES=0
for service in model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor; do
    if ! docker image inspect "ghcr.io/$ORG/ai_system/$service:$TAG" >/dev/null 2>&1; then
        echo "❌ Missing image: $service"
        MISSING_IMAGES=$((MISSING_IMAGES + 1))
    fi
done

if [ $MISSING_IMAGES -gt 0 ]; then
    echo ""
    echo "🔧 FIX: Pull missing images first:"
    echo "   docker pull ghcr.io/$ORG/ai_system/model_ops_coordinator:$TAG"
    echo "   docker pull ghcr.io/$ORG/ai_system/real_time_audio_pipeline:$TAG"
    echo "   docker pull ghcr.io/$ORG/ai_system/affective_processing_center:$TAG"
    echo "   docker pull ghcr.io/$ORG/ai_system/unified_observability_center:$TAG"
    echo "   docker pull ghcr.io/$ORG/ai_system/self_healing_supervisor:$TAG"
    echo ""
    echo "OR rebuild everything:"
    echo "   bash AUTOMATED_MAINPC_CRON.sh"
else
    echo "✅ All images exist locally"
    echo ""
    echo "🔧 Next step: Run the fix script:"
    echo "   bash FIX_MAINPC_DEPLOYMENT.sh"
fi