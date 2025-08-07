# PC2 Base Image: ml_heavy
# Machine learning with GPU support
# Agents: 2 (TieredResponder, AsyncProcessor)

FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS pc2_base_ml_heavy

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        wget \
        && rm -rf /var/lib/apt/lists/*
# Install Python on CUDA base
ARG PYTHON_VERSION=3.10
RUN apt-get update && \
    apt-get install -y python${PYTHON_VERSION} python3-pip && \
    ln -sf /usr/bin/python${PYTHON_VERSION} /usr/local/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Install base dependencies
COPY docker/base/requirements_ml_heavy.txt /tmp/base_deps.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/base_deps.txt && \
    rm /tmp/base_deps.txt

# Common workspace setup
WORKDIR /app

# Labels
LABEL maintainer="Haymayndz Ultra"
LABEL base_type="ml_heavy"
LABEL agent_count="2"
LABEL registry="ghcr.io/haymayndzultra"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python --version || exit 1
