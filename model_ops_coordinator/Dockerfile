# syntax=docker/dockerfile:1.7
# Optimized multi-stage Dockerfile for ModelOps Coordinator

ARG BASE_IMAGE
ARG MACHINE=mainpc

# Base stage from family image provides CUDA/LLM stack
FROM ${BASE_IMAGE} AS base

# Builder stage – build wheels using slim Python, cache pip to speed up builds
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config curl git \
    libffi-dev libssl-dev \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip wheel setuptools && \
    pip wheel -w /wheels -r requirements.txt

# Runtime stage – install only needed wheels on top of family base
FROM ${BASE_IMAGE} AS runtime

# Hardware-aware defaults based on machine profile
ARG MACHINE=mainpc
COPY config/machine-profiles/${MACHINE}.json /etc/machine-profile.json

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Set machine-specific environment variables from profile
RUN if [ "$MACHINE" = "mainpc" ]; then \
      export GPU_VISIBLE_DEVICES=0 && \
      export TORCH_CUDA_ALLOC_CONF="max_split_size_mb:64" && \
      export OMP_NUM_THREADS=16 && \
      export UVICORN_WORKERS=32 && \
      export MODEL_EVICT_THRESHOLD_PCT=90; \
    elif [ "$MACHINE" = "pc2" ]; then \
      export GPU_VISIBLE_DEVICES=0 && \
      export TORCH_CUDA_ALLOC_CONF="max_split_size_mb:32" && \
      export OMP_NUM_THREADS=4 && \
      export UVICORN_WORKERS=8 && \
      export MODEL_EVICT_THRESHOLD_PCT=70; \
    fi

# Create non-root user matching plan defaults (UID:GID 10001:10001)
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -d /app -s /sbin/nologin appuser
WORKDIR /app

# Copy wheels and install requirements using family-provided Python stack
COPY --from=builder /wheels /wheels
COPY requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy application code (avoid venv duplication)
COPY . .

# Minimal runtime utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl procps \
  && rm -rf /var/lib/apt/lists/* && \
  mkdir -p /app/data /app/logs /app/config && chown -R appuser:appuser /app
COPY config/default.yaml /app/config/

USER appuser

# Health check and ports (per plan.md line 117: 7212/8212)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8212/health || exit 1
EXPOSE 7212 8212

# Metadata
LABEL org.opencontainers.image.title="ModelOps Coordinator"
LABEL org.opencontainers.image.description="Unified model lifecycle, inference, and resource management"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="ModelOps Team"

# Use tini as PID 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "app.py"]