# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for Unified Observability Center

ARG BASE_IMAGE=ghcr.io/haymayndzultra/family-web:20250810-9c99cc9
ARG MACHINE=mainpc

# Builder stage
FROM python:3.11-slim AS builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config curl git \
    libffi-dev libssl-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy common module and service code
COPY common/ /build/common/
COPY unified_observability_center/ /build/unified_observability_center/

# Install packages
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e /build/common && \
    pip install -e /build/unified_observability_center

# Runtime stage
FROM ${BASE_IMAGE} AS runtime

# Hardware-aware defaults
ARG MACHINE=mainpc
COPY unified_observability_center/config/machine-profiles/${MACHINE}.json /etc/machine-profile.json

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Create non-root user (UID:GID 10001:10001)
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -d /app -s /sbin/nologin appuser
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy common module and service code
COPY common/ /app/common/
COPY unified_observability_center/ /app/unified_observability_center/

# Install packages in runtime
RUN pip install --no-deps /app/common && \
    pip install --no-deps /app/unified_observability_center

# Runtime utilities
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl procps tini \
  && rm -rf /var/lib/apt/lists/* && \
  mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

USER appuser

# Health check and ports (9100/9110)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:9110/health || exit 1
EXPOSE 9100 9110

# Metadata
LABEL org.opencontainers.image.title="Unified Observability Center"
LABEL org.opencontainers.image.description="Centralized monitoring and observability"
LABEL org.opencontainers.image.version="1.0.0"

# Use tini as PID 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "unified_observability_center.app"]

