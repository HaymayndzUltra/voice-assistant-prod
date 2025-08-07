# PC2 Base Image: cache_redis
# Cache and memory management with Redis
# Agents: 3 (CacheManager, ProactiveContextMonitor, ObservabilityHub)

FROM python:3.10-slim-bullseye AS pc2_base_cache_redis

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        build-essential \
        curl \
        wget \
        && rm -rf /var/lib/apt/lists/*

# Install base dependencies
COPY docker/base/requirements_cache_redis.txt /tmp/base_deps.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/base_deps.txt && \
    rm /tmp/base_deps.txt

# Common workspace setup
WORKDIR /app

# Labels
LABEL maintainer="Haymayndz Ultra"
LABEL base_type="cache_redis"
LABEL agent_count="3"
LABEL registry="ghcr.io/haymayndzultra"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python --version || exit 1
RUN apt-get update && apt-get install -y git
