#!/bin/bash
# EMERGENCY DOCKER CLEANUP - Free up space immediately!

echo "================================================"
echo "🚨 EMERGENCY DOCKER CLEANUP"
echo "================================================"

# Show current usage
echo "📊 Current Docker Storage Usage:"
docker system df
echo ""

# Step 1: Remove all stopped containers
echo "🗑️ Removing stopped containers..."
docker container prune -f

# Step 2: Remove unused images
echo "🗑️ Removing unused images..."
docker image prune -a -f

# Step 3: Remove build cache
echo "🗑️ Removing build cache..."
docker builder prune -a -f

# Step 4: Remove unused volumes
echo "🗑️ Removing unused volumes..."
docker volume prune -f

# Step 5: Remove unused networks
echo "🗑️ Removing unused networks..."
docker network prune -f

# Step 6: NUCLEAR OPTION - Remove everything except running containers
echo ""
echo "⚠️ NUCLEAR CLEANUP (removes ALL images/cache)?"
echo "This will delete ALL Docker data except running containers!"
read -p "Type 'yes' to proceed: " confirm

if [ "$confirm" = "yes" ]; then
    echo "💣 Performing nuclear cleanup..."
    docker system prune -a --volumes -f
fi

# Show results
echo ""
echo "✅ Cleanup Complete!"
echo ""
echo "📊 New Docker Storage Usage:"
docker system df

# Show disk space
echo ""
echo "💾 Disk Space:"
df -h /