#!/bin/bash
# SMART CLEANUP - Handles edge cases

echo "================================================"
echo "🧹 SMART DOCKER CLEANUP - Starting..."
echo "================================================"

# Step 1: Stop and remove containers (if any exist)
echo ""
echo "1️⃣ Stopping containers..."
CONTAINERS=$(docker ps -aq)
if [ ! -z "$CONTAINERS" ]; then
    docker stop $CONTAINERS
    docker rm $CONTAINERS
else
    echo "   No containers to remove"
fi

# Step 2: Remove old image versions (keep only latest)
echo ""
echo "2️⃣ Removing duplicate/old images..."

# Remove 20250811 tags
echo "   Removing 20250811 tags..."
for img in $(docker images --format "{{.ID}}:{{.Repository}}:{{.Tag}}" | grep "20250811" | cut -d: -f1); do
    docker rmi -f $img 2>/dev/null && echo "   Deleted: $img"
done

# Remove 20250810 tags (old base images)
echo "   Removing 20250810 tags..."
for img in $(docker images --format "{{.ID}}:{{.Repository}}:{{.Tag}}" | grep "20250810" | cut -d: -f1); do
    docker rmi -f $img 2>/dev/null && echo "   Deleted: $img"
done

# Remove other old tags
echo "   Removing other old tags..."
for tag in "230be7a" "0596b99" "07f77df"; do
    for img in $(docker images --format "{{.ID}}:{{.Repository}}:{{.Tag}}" | grep "$tag" | cut -d: -f1); do
        docker rmi -f $img 2>/dev/null && echo "   Deleted: $img ($tag)"
    done
done

# Step 3: Remove buildx stuff
echo ""
echo "3️⃣ Cleaning buildx..."

# Stop buildx containers
docker stop buildx_buildkit_phase4_2_builder0 2>/dev/null
docker rm buildx_buildkit_phase4_2_builder0 2>/dev/null

# Remove buildx volumes
docker volume rm buildx_buildkit_baseimg-builder0_state 2>/dev/null
docker volume rm buildx_buildkit_phase4_2_builder0_state 2>/dev/null

# Prune buildx
docker buildx prune -a -f 2>/dev/null || echo "   No buildx cache to clean"

# Step 4: Remove dangling images
echo ""
echo "4️⃣ Removing dangling images..."
DANGLING=$(docker images -f "dangling=true" -q)
if [ ! -z "$DANGLING" ]; then
    docker rmi $DANGLING -f
else
    echo "   No dangling images"
fi

# Step 5: System prune
echo ""
echo "5️⃣ Final system cleanup..."
docker system prune -a -f --volumes

# Step 6: Show results
echo ""
echo "================================================"
echo "✅ CLEANUP COMPLETE!"
echo "================================================"
echo ""
docker system df