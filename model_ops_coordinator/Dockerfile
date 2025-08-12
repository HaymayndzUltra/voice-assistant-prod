# syntax=docker/dockerfile:1.7
# Optimized multi-stage Dockerfile for ModelOps Coordinator

ARG BASE_IMAGE=ghcr.io/haymayndzultra/family-llm-cu121:20250810-9c99cc9
ARG MACHINE=mainpc

# Builder stage – build and install packages
FROM python:3.11-slim AS builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config curl git \
    libffi-dev libssl-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy common module and service code
COPY common/ /build/common/
COPY model_ops_coordinator/ /build/model_ops_coordinator/

# Install packages in editable mode for builder
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e /build/common && \
    pip install -e /build/model_ops_coordinator

# Runtime stage
FROM ${BASE_IMAGE} AS runtime

# Hardware-aware defaults based on machine profile
ARG MACHINE=mainpc
COPY model_ops_coordinator/config/machine-profiles/${MACHINE}.json /etc/machine-profile.json

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

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy common module and service code for runtime
COPY common/ /app/common/
COPY model_ops_coordinator/ /app/model_ops_coordinator/

# Install packages in the runtime
RUN pip install --no-deps /app/common && \
    pip install --no-deps /app/model_ops_coordinator

# Minimal runtime utilities
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl procps tini \
  && rm -rf /var/lib/apt/lists/* && \
  mkdir -p /app/data /app/logs /app/config && chown -R appuser:appuser /app

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
CMD ["python", "-m", "model_ops_coordinator.app"]