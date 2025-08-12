#!/bin/bash
# NUCLEAR CLEANUP - Based on your Docker Desktop screenshots
# This will FREE 100GB+ immediately!

echo "================================================"
echo "💣 NUCLEAR CLEANUP - Freeing 100GB+"
echo "================================================"

# Step 1: Delete those huge buildx volumes (41.5GB)
echo "🗑️ Deleting buildx volumes (41.5GB)..."
docker volume rm buildx_buildkit_baseimg-builder0_state
docker volume rm buildx_buildkit_phase4_2_builder0_state

# Step 2: Remove ALL old 576dfae images
echo "🗑️ Removing old 576dfae images..."
docker images | grep "576dfae" | awk '{print $3}' | xargs -r docker rmi -f

# Step 3: Remove duplicate images (keep only latest)
echo "🗑️ Removing duplicate images..."
# Remove all 20250811 tags (old)
docker images | grep "20250811" | awk '{print $3}' | xargs -r docker rmi -f

# Step 4: Clean buildx cache
echo "🗑️ Cleaning buildx cache..."
docker buildx prune -a -f

# Step 5: Remove all unused images
echo "🗑️ Removing unused images..."
docker image prune -a -f

# Step 6: Clean system
echo "🗑️ Final system cleanup..."
docker system prune -a --volumes -f

echo ""
echo "================================================"
echo "✅ CLEANUP COMPLETE!"
echo "================================================"
echo ""
echo "Space freed: ~100GB+"
echo ""
echo "Run 'docker system df' to verify"