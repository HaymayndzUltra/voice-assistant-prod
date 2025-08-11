# syntax=docker/dockerfile:1.7
# Affective Processing Center - Optimized per plan.md

ARG BASE_IMAGE
ARG MACHINE=mainpc

# Builder stage
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config curl git \
    libffi-dev libssl-dev \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip wheel setuptools && \
    pip wheel -w /wheels -r requirements.txt

# Runtime stage (family provides CUDA/Torch stack)
FROM ${BASE_IMAGE} AS runtime

# Hardware-aware defaults
ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \
    TORCH_CUDA_ARCH_LIST="8.9;8.6" \
    GPU_VISIBLE_DEVICES=${GPU_VISIBLE_DEVICES:-0}

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl tini \
    ffmpeg libsndfile1 \
  && rm -rf /var/lib/apt/lists/*

# Create non-root user per plan.md (UID:GID 10001:10001)
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -s /sbin/nologin appuser
WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${MACHINE}.json /etc/machine-profile.json

# Install Python deps from wheels (no venv needed with family image)
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy application code
COPY . .

# Set permissions
RUN mkdir -p /app/logs /app/data /app/models /app/config && \
    chown -R appuser:appuser /app && \
    chmod +x /usr/bin/tini

# Copy config
COPY config/default.yaml /app/config/

USER appuser

# Ports per plan.md line 118: 5560/6560
EXPOSE 5560 6560

# Health check per plan.md
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:6560/health || exit 1

# Production configuration
ENV APC_ENV=production \
    APC_LOG_LEVEL=INFO \
    APC_CONFIG_PATH=/app/config/default.yaml

# Use tini as PID 1 per plan.md
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "app.py"]