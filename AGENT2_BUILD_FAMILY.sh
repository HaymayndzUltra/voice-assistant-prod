#!/bin/bash
# AGENT 2: Build Family Images
# Run this in Background Agent Session 2 (after Agent 1 finishes)

set -e

echo "============================================================"
echo "🚀 AGENT 2: BUILDING FAMILY IMAGES"
echo "============================================================"

# Setup Docker
echo "Setting up Docker daemon..."
sudo -n nohup dockerd -H unix:///var/run/docker.sock \
    --storage-driver=vfs \
    --iptables=false \
    --bridge=none > /dev/null 2>&1 &
sleep 5

# Login to GHCR
echo "Logging in to GHCR..."
export GHCR_TOKEN="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"
echo $GHCR_TOKEN | docker login ghcr.io -u haymayndzultra --password-stdin

# Wait for base images to be ready
echo "Checking if base images are ready..."
while ! docker pull ghcr.io/haymayndzultra/base-gpu-cu121:latest; do
    echo "Waiting for base images to complete..."
    sleep 30
done
echo "✅ Base images ready!"

cd /workspace

# Build family images
echo "Building family-web..."
docker build -t ghcr.io/haymayndzultra/family-web:latest \
    docker/base-images/family-web/
docker push ghcr.io/haymayndzultra/family-web:latest
echo "✅ family-web pushed"

echo "Building family-torch-cu121..."
docker build -t ghcr.io/haymayndzultra/family-torch-cu121:latest \
    docker/base-images/family-torch-cu121/
docker push ghcr.io/haymayndzultra/family-torch-cu121:latest
echo "✅ family-torch-cu121 pushed"

echo "Building family-llm-cu121..."
docker build -t ghcr.io/haymayndzultra/family-llm-cu121:latest \
    docker/base-images/family-llm-cu121/
docker push ghcr.io/haymayndzultra/family-llm-cu121:latest
echo "✅ family-llm-cu121 pushed"

echo "Building family-vision-cu121..."
docker build -t ghcr.io/haymayndzultra/family-vision-cu121:latest \
    docker/base-images/family-vision-cu121/
docker push ghcr.io/haymayndzultra/family-vision-cu121:latest
echo "✅ family-vision-cu121 pushed"

echo "============================================================"
echo "✅ AGENT 2 COMPLETE! Family images ready on GHCR"
echo "============================================================"
echo "Agents 3 & 4 can now start building services"