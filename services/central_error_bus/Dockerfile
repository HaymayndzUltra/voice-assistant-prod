# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for Central Error Bus

ARG BASE_IMAGE=ghcr.io/haymayndzultra/family-web:20250810-9c99cc9
ARG MACHINE=pc2

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
COPY services/central_error_bus/ /build/central_error_bus/

# Create pyproject.toml if not exists
RUN cd /build/central_error_bus && \
    if [ ! -f pyproject.toml ]; then \
        echo '[build-system]' > pyproject.toml && \
        echo 'requires = ["setuptools>=61.0", "wheel"]' >> pyproject.toml && \
        echo 'build-backend = "setuptools.build_meta"' >> pyproject.toml && \
        echo '' >> pyproject.toml && \
        echo '[project]' >> pyproject.toml && \
        echo 'name = "central_error_bus"' >> pyproject.toml && \
        echo 'version = "0.1.0"' >> pyproject.toml && \
        echo 'requires-python = ">=3.11"' >> pyproject.toml; \
    fi

# Install packages
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e /build/common && \
    pip install -e /build/central_error_bus

# Runtime stage
FROM ${BASE_IMAGE} AS runtime

# Hardware-aware defaults
ARG MACHINE=pc2
COPY services/central_error_bus/config/machine-profiles/${MACHINE}.json /etc/machine-profile.json 2>/dev/null || true

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/workspace

# Create non-root user (UID:GID 10001:10001)
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -d /app -s /sbin/nologin appuser
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy common module and service code
COPY common/ /app/common/
COPY services/central_error_bus/ /app/central_error_bus/

# Install packages in runtime
RUN pip install --no-deps /app/common && \
    pip install --no-deps /app/central_error_bus || true

# Runtime utilities
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl procps tini \
  && rm -rf /var/lib/apt/lists/* && \
  mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

USER appuser

# Health check and ports (7150/8150)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8150/health || exit 1
EXPOSE 7150 8150

# Metadata
LABEL org.opencontainers.image.title="Central Error Bus"
LABEL org.opencontainers.image.description="Centralized error handling and routing"
LABEL org.opencontainers.image.version="1.0.0"

# Use tini as PID 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "central_error_bus.app"]

