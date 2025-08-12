#!/bin/bash
# Batch containerize foundation services

set -e

echo "================================================"
echo "🏗️ Batch Containerizing Foundation Services"
echo "================================================"

# Foundation services to containerize
SERVICES=(
    "ServiceRegistry:8200:main_pc_code/agents/service_registry.py"
    "SystemDigitalTwin:8220:main_pc_code/agents/system_digital_twin.py"
    "UnifiedSystemAgent:8201:main_pc_code/agents/unified_system_agent.py"
    "MemoryFusionHub:6713:memory_fusion_hub/app.py"
)

# Create Dockerfile template
create_dockerfile() {
    local service=$1
    local port=$2
    local script=$3
    local dir=$(dirname $script)
    
    cat > "$dir/Dockerfile" << EOF
# syntax=docker/dockerfile:1.7
# Auto-generated Dockerfile for $service

ARG BASE_IMAGE=ghcr.io/haymayndzultra/base-cpu-pydeps:20250810-9c99cc9
ARG MACHINE=mainpc

# Builder stage
FROM python:3.11-slim AS builder
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential pkg-config curl git \\
    libffi-dev libssl-dev \\
  && rm -rf /var/lib/apt/lists/*

# Copy common and service code
COPY common/ /build/common/
COPY $dir/ /build/$service/

# Install packages
RUN pip install --upgrade pip setuptools wheel && \\
    pip install -e /build/common && \\
    cd /build/$service && \\
    if [ ! -f pyproject.toml ]; then \\
        echo '[build-system]' > pyproject.toml && \\
        echo 'requires = ["setuptools>=61.0", "wheel"]' >> pyproject.toml && \\
        echo 'build-backend = "setuptools.build_meta"' >> pyproject.toml && \\
        echo '' >> pyproject.toml && \\
        echo '[project]' >> pyproject.toml && \\
        echo 'name = "$service"' >> pyproject.toml && \\
        echo 'version = "0.1.0"' >> pyproject.toml && \\
        echo 'requires-python = ">=3.11"' >> pyproject.toml; \\
    fi && \\
    pip install -e .

# Runtime stage
FROM \${BASE_IMAGE} AS runtime

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \\
    PYTHONPATH=/app:/workspace \\
    PORT_OFFSET=0

RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -d /app -s /sbin/nologin appuser
WORKDIR /app

# Copy installed packages
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy service code
COPY common/ /app/common/
COPY $dir/ /app/$service/

# Install runtime packages
RUN pip install --no-deps /app/common && \\
    pip install --no-deps /app/$service || true

# Runtime utilities
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \\
    curl procps tini \\
  && rm -rf /var/lib/apt/lists/* && \\
  mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
  CMD curl -f http://localhost:$port/health || exit 1

# Expose ports (gRPC and HTTP)
EXPOSE $((port - 1000)) $port

# Use tini as PID 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "$service.$(basename $script .py)"]
EOF
    
    echo "✅ Created Dockerfile for $service"
}

# Create pyproject.toml template
create_pyproject() {
    local service=$1
    local dir=$2
    
    cat > "$dir/pyproject.toml" << EOF
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "$service"
version = "0.1.0"
description = "$service for AI System"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "grpcio>=1.59.0",
    "pyzmq>=25.0.0",
    "redis>=4.5.0",
    "psutil>=5.9.0",
    "pydantic>=2.0.0",
    "prometheus-client>=0.18.0",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["*"]
EOF
    
    echo "✅ Created pyproject.toml for $service"
}

# Process each service
for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r service port script <<< "$service_info"
    dir=$(dirname $script)
    
    echo ""
    echo "Processing $service..."
    
    # Create pyproject.toml if it doesn't exist
    if [ ! -f "$dir/pyproject.toml" ]; then
        create_pyproject "$service" "$dir"
    fi
    
    # Create Dockerfile
    create_dockerfile "$service" "$port" "$script"
done

echo ""
echo "================================================"
echo "✅ Foundation Services Prepared for Containerization"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Review generated Dockerfiles in each service directory"
echo "2. Build with: bash rebuild_all_images.sh"
echo "3. Deploy with: bash deploy_native_linux.sh"
echo ""
echo "Services prepared:"
for service_info in "${SERVICES[@]}"; do
    IFS=':' read -r service port script <<< "$service_info"
    echo "  - $service (port $port)"
done