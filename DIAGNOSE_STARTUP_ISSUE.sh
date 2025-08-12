#!/bin/bash
# DIAGNOSE - Why are containers failing to start?

echo "================================================"
echo "🔍 DIAGNOSING CONTAINER STARTUP FAILURES"
echo "================================================"

export ORG='haymayndzultra'
export TAG='20250812-576dfae'

# Function to check a container
check_container() {
    local name=$1
    local image="ghcr.io/$ORG/ai_system/$name:$TAG"
    
    echo ""
    echo "=== $name ==="
    
    # Check last logs
    echo "Last logs:"
    docker logs --tail 10 $name 2>&1 | sed 's/^/  /' || echo "  No logs"
    
    # Check what's in /app
    echo ""
    echo "Checking /app directory:"
    docker run --rm --entrypoint ls "$image" -la /app 2>&1 | head -5 | sed 's/^/  /'
    
    # Check if app.py exists
    echo ""
    echo "Looking for app.py or main startup:"
    docker run --rm --entrypoint find "$image" /app -name "*.py" -type f 2>&1 | head -10 | sed 's/^/  /'
    
    # Check actual CMD
    echo ""
    echo "Image CMD: $(docker inspect "$image" --format='{{.Config.Cmd}}')"
    echo "Image ENTRYPOINT: $(docker inspect "$image" --format='{{.Config.Entrypoint}}')"
}

# Check each failing service
for service in model_ops_coordinator real_time_audio_pipeline affective_processing_center unified_observability_center self_healing_supervisor; do
    check_container $service
done

echo ""
echo "================================================"
echo "🔧 LIKELY ISSUES:"
echo "================================================"
echo ""
echo "1. If 'app.py' doesn't exist:"
echo "   → The Dockerfiles didn't copy the right files"
echo "   → Need to rebuild with correct COPY commands"
echo ""
echo "2. If logs show 'ModuleNotFoundError':"
echo "   → Python dependencies missing"
echo "   → Need to rebuild with proper requirements.txt"
echo ""
echo "3. If logs show 'Permission denied':"
echo "   → User permission issue"
echo "   → Check if running as appuser correctly"
echo ""
echo "4. For audio device issue (WSL2):"
echo "   → Remove '--device /dev/snd' from RTAP"
echo "   → Use PulseAudio over network instead"