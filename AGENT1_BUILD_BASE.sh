#!/bin/bash
# AGENT 1: Build Base Images
# Run this in Background Agent Session 1

set -e

echo "============================================================"
echo "🚀 AGENT 1: BUILDING BASE IMAGES"
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

# Clean space first
echo "Cleaning Docker space..."
docker system prune -a -f --volumes || true

cd /workspace

# Build base images IN ORDER (dependencies matter!)
echo "Building base-python..."
docker build -t ghcr.io/haymayndzultra/base-python:latest \
    docker/base-images/base-python/
docker push ghcr.io/haymayndzultra/base-python:latest
echo "✅ base-python pushed"

echo "Building base-utils..."
docker build -t ghcr.io/haymayndzultra/base-utils:latest \
    docker/base-images/base-utils/
docker push ghcr.io/haymayndzultra/base-utils:latest
echo "✅ base-utils pushed"

echo "Building base-cpu-pydeps..."
docker build -t ghcr.io/haymayndzultra/base-cpu-pydeps:latest \
    docker/base-images/base-cpu-pydeps/
docker push ghcr.io/haymayndzultra/base-cpu-pydeps:latest
echo "✅ base-cpu-pydeps pushed"

echo "Building base-gpu-cu121..."
docker build -t ghcr.io/haymayndzultra/base-gpu-cu121:latest \
    docker/base-images/base-gpu-cu121/
docker push ghcr.io/haymayndzultra/base-gpu-cu121:latest
echo "✅ base-gpu-cu121 pushed"

echo "Building legacy-py310-cpu..."
docker build -t ghcr.io/haymayndzultra/legacy-py310-cpu:latest \
    docker/base-images/legacy-py310-cpu/
docker push ghcr.io/haymayndzultra/legacy-py310-cpu:latest
echo "✅ legacy-py310-cpu pushed"

echo "============================================================"
echo "✅ AGENT 1 COMPLETE! Base images ready on GHCR"
echo "============================================================"
echo "Agent 2 can now start building family images"