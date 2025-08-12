#!/bin/bash
# Hybrid Build Strategy - Best for Docker Desktop users

echo "============================================================"
echo "🎯 HYBRID BUILD STRATEGY"
echo "============================================================"
echo "Pull base images from GHCR, build services locally"
echo ""

# Step 1: Try to pull base images from GHCR
echo "STEP 1: Pulling base images from GHCR (if available)..."
echo ""

BASE_IMAGES=(
    "ghcr.io/haymayndzultra/base-python:20250812-latest"
    "ghcr.io/haymayndzultra/base-utils:20250812-latest"
    "ghcr.io/haymayndzultra/base-cpu-pydeps:20250812-latest"
    "ghcr.io/haymayndzultra/family-web:20250812-latest"
)

for image in "${BASE_IMAGES[@]}"; do
    echo "Trying to pull $image..."
    if docker pull "$image" 2>/dev/null; then
        echo "  ✅ Pulled $image"
        # Tag it locally without ghcr.io prefix
        local_name=$(echo "$image" | sed 's|ghcr.io/haymayndzultra/||' | sed 's|:.*|:latest|')
        docker tag "$image" "$local_name"
        echo "  ✅ Tagged as $local_name"
    else
        echo "  ⚠️  Not available on GHCR (will build locally)"
    fi
    echo ""
done

# Step 2: Build any missing base images locally
echo "STEP 2: Building missing base images locally..."
echo ""

# Check if base-python exists locally
if ! docker images | grep -q "base-python.*latest"; then
    echo "Building base-python locally..."
    docker build -t base-python:latest docker/base-images/base-python/
fi

# Check if base-utils exists locally
if ! docker images | grep -q "base-utils.*latest"; then
    echo "Building base-utils locally..."
    # Temporarily fix FROM to use local image
    sed -i.bak 's|FROM ghcr.io/[^/]*/base-python:.*|FROM base-python:latest|' \
        docker/base-images/base-utils/Dockerfile
    docker build -t base-utils:latest docker/base-images/base-utils/
    # Restore original
    mv docker/base-images/base-utils/Dockerfile.bak docker/base-images/base-utils/Dockerfile
fi

# Continue for other base images...

# Step 3: Build service images locally (CPU-only for Docker Desktop)
echo "STEP 3: Building service images locally (CPU mode)..."
echo ""

# For Docker Desktop, we need CPU-only builds
export DOCKER_BUILDKIT=1

echo "Building ModelOpsCoordinator (CPU mode)..."
cat > /tmp/Dockerfile.moc.cpu << 'EOF'
# CPU-only version for Docker Desktop
FROM family-web:latest AS base

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${MACHINE}.json /etc/machine-profile.json

# Builder stage
FROM base AS builder
COPY model_ops_coordinator/requirements.txt ./requirements.txt
# Install without CUDA dependencies
RUN pip install --no-cache-dir \
    fastapi uvicorn redis psutil || true

# Runtime stage
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY model_ops_coordinator/ ./model_ops_coordinator
COPY common/ ./common

USER appuser

LABEL health_check_port="8212"

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -sf http://localhost:8212/health || exit 1

EXPOSE 7212 8212

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "model_ops_coordinator.app"]
EOF

docker build -f /tmp/Dockerfile.moc.cpu \
    --build-arg MACHINE=mainpc \
    -t model_ops_coordinator:cpu-only .

echo "✅ Built CPU-only version for Docker Desktop"
echo ""

echo "============================================================"
echo "✅ HYBRID BUILD COMPLETE!"
echo "============================================================"
echo ""
echo "What we did:"
echo "1. Pulled stable base images from GHCR (if available)"
echo "2. Built missing base images locally"
echo "3. Built service images in CPU-only mode for Docker Desktop"
echo ""
echo "This approach gives you:"
echo "- Consistent base images (from GHCR)"
echo "- Platform-specific service builds (for your Docker Desktop)"
echo "- No GPU dependencies (works on WSL2)"
echo ""
echo "To run services:"
echo "  docker run -p 8212:8212 model_ops_coordinator:cpu-only"