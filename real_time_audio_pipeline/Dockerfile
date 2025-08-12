# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for Real-Time Audio Pipeline

ARG BASE_IMAGE=ghcr.io/haymayndzultra/family-torch-cu121:20250810-9c99cc9
ARG MACHINE=mainpc

# Builder stage
FROM python:3.11-slim AS builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config curl git \
    libffi-dev libssl-dev portaudio19-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy common module and service code
COPY common/ /build/common/
COPY real_time_audio_pipeline/ /build/real_time_audio_pipeline/

# Install packages
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e /build/common && \
    pip install -e /build/real_time_audio_pipeline

# Runtime stage
FROM ${BASE_IMAGE} AS runtime

# Hardware-aware defaults
ARG MACHINE=mainpc
COPY real_time_audio_pipeline/config/machine-profiles/${MACHINE}.json /etc/machine-profile.json

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    AUDIO_BACKEND=${AUDIO_BACKEND:-default}

# Create non-root user (UID:GID 10001:10001)
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -d /app -s /sbin/nologin appuser
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy common module and service code
COPY common/ /app/common/
COPY real_time_audio_pipeline/ /app/real_time_audio_pipeline/

# Install packages in runtime
RUN pip install --no-deps /app/common && \
    pip install --no-deps /app/real_time_audio_pipeline

# Runtime utilities - audio libraries and tini
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl tini \
    portaudio19-dev alsa-utils pulseaudio-utils \
  && rm -rf /var/lib/apt/lists/* && \
  mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

# Add user to audio group for device access (if available)
RUN usermod -aG audio appuser || true

USER appuser

# Health check and ports (5557/6557)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:6557/health || exit 1
EXPOSE 5557 6557

# Metadata
LABEL org.opencontainers.image.title="Real-Time Audio Pipeline"
LABEL org.opencontainers.image.description="Real-time audio processing and streaming"
LABEL org.opencontainers.image.version="1.0.0"

# Use tini as PID 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "real_time_audio_pipeline.app"]
