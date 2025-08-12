#!/bin/bash
# Show all Docker resources para mapili ang tamang images

echo "================================================"
echo "📊 COMPLETE DOCKER INVENTORY"
echo "================================================"

echo ""
echo "1️⃣ DISK USAGE SUMMARY:"
echo "------------------------"
docker system df
echo ""

echo "2️⃣ ALL IMAGES (sorted by size):"
echo "---------------------------------"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}" | head -1
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}" | tail -n +2 | sort -k5 -hr
echo ""

echo "3️⃣ RUNNING CONTAINERS:"
echo "----------------------"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "4️⃣ ALL CONTAINERS (including stopped):"
echo "---------------------------------------"
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
echo ""

echo "5️⃣ DOCKER VOLUMES:"
echo "------------------"
docker volume ls
echo "Volume sizes:"
for vol in $(docker volume ls -q); do
    size=$(docker run --rm -v $vol:/data alpine du -sh /data 2>/dev/null | cut -f1)
    echo "  $vol: $size"
done
echo ""

echo "6️⃣ BUILDX BUILDERS:"
echo "-------------------"
docker buildx ls
echo ""

echo "7️⃣ DUPLICATE IMAGES (same repo, different tags):"
echo "-------------------------------------------------"
docker images --format "{{.Repository}}" | sort | uniq -c | sort -rn | head -10
echo ""

echo "8️⃣ IMAGES BY DATE (newest first):"
echo "----------------------------------"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}" | head -20
echo ""

echo "================================================"
echo "💡 RECOMMENDATIONS:"
echo "================================================"
echo ""
echo "KEEP these images:"
echo "  - Latest tag (newest date)"
echo "  - Currently running containers"
echo "  - ghcr.io/haymayndzultra/ai_system/* with latest date"
echo ""
echo "DELETE these:"
echo "  - Old tags (576dfae)"
echo "  - Duplicate IDs"
echo "  - <none> tagged images"
echo "  - buildx cache volumes"
echo ""
echo "To see specific image details:"
echo "  docker inspect <IMAGE_ID>"
echo ""
echo "To check what's using an image:"
echo "  docker ps -a --filter ancestor=<IMAGE_ID>"