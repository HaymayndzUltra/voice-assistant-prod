# PC2 Base Image: minimal
# Minimal Python base with basic utilities
# Agents: 18 (MemoryOrchestratorService, VisionProcessingAgent, DreamWorldAgent...)

FROM python:3.10-slim-bullseye AS pc2_base_minimal

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        curl \
        wget \
        && rm -rf /var/lib/apt/lists/*

# Install base dependencies
COPY docker/base/requirements_minimal.txt /tmp/base_deps.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/base_deps.txt && \
    rm /tmp/base_deps.txt

# Common workspace setup
WORKDIR /app

# Labels
LABEL maintainer="Haymayndz Ultra"
LABEL base_type="minimal"
LABEL agent_count="18"
LABEL registry="ghcr.io/haymayndzultra"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python --version || exit 1
