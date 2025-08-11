# Real-Time Audio Pipeline (RTAP) - Optimized multi-stage image

ARG BASE_IMAGE
ARG MACHINE=mainpc

# Base runtime (family provides CUDA/Torch stack)
FROM ${BASE_IMAGE} AS base

# Builder stage: compile Python wheels with slim image
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config curl git \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements.runtime.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip wheel setuptools && \
    pip wheel -w /wheels -r requirements.txt

# Runtime stage: install only needed wheels on top of family base
FROM ${BASE_IMAGE}

# Hardware-aware defaults based on machine profile
ARG MACHINE=mainpc
COPY --from=base /workspace/model_ops_coordinator/config/machine-profiles/${MACHINE}.json /etc/machine-profile.json

# Metadata
LABEL maintainer="RTAP Team"
LABEL version="1.0"
LABEL description="Real-Time Audio Pipeline - Ultra-low-latency speech processing service"

# Env
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# System/audio deps (runtime only)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libasound2-dev alsa-utils pulseaudio pulseaudio-utils \
    curl wget ffmpeg htop procps netcat-openbsd \
  && rm -rf /var/lib/apt/lists/*

# Create non-root user and app dir (use standard UID:GID 10001:10001)
RUN groupadd -g 10001 rtap && useradd -u 10001 -g rtap -s /sbin/nologin rtap
WORKDIR /app

# Install Python deps from wheels
COPY --from=builder /wheels /wheels
COPY requirements.txt requirements.runtime.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.runtime.txt && \
    rm -rf /wheels

# Copy application code
COPY . .

# Prepare directories and permissions
RUN mkdir -p /app/logs /app/data /app/models && \
    chown -R rtap:rtap /app && \
    usermod -a -G audio rtap

# Health check and entrypoint scripts
RUN chmod +x /app/healthcheck.sh /app/entrypoint.sh || true

# Switch to non-root
USER rtap

# Expose ports
EXPOSE 6552 6553 5802 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD /app/healthcheck.sh

# Volumes
VOLUME ["/app/config", "/app/logs", "/app/data", "/app/models"]

# Entry
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python3", "app.py", "--log-level", "INFO"]
