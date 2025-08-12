# syntax=docker/dockerfile:1.7
# Multi-stage Dockerfile for Self-Healing Supervisor

ARG BASE_IMAGE=ghcr.io/haymayndzultra/base-cpu-pydeps:20250810-9c99cc9
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
COPY services/self_healing_supervisor/ /build/self_healing_supervisor/

# Create pyproject.toml if not exists (for installability)
RUN cd /build/self_healing_supervisor && \
    if [ ! -f pyproject.toml ]; then \
        echo '[build-system]' > pyproject.toml && \
        echo 'requires = ["setuptools>=61.0", "wheel"]' >> pyproject.toml && \
        echo 'build-backend = "setuptools.build_meta"' >> pyproject.toml && \
        echo '' >> pyproject.toml && \
        echo '[project]' >> pyproject.toml && \
        echo 'name = "self_healing_supervisor"' >> pyproject.toml && \
        echo 'version = "0.1.0"' >> pyproject.toml && \
        echo 'requires-python = ">=3.11"' >> pyproject.toml; \
    fi

# Install packages
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e /build/common && \
    pip install -e /build/self_healing_supervisor

# Runtime stage
FROM ${BASE_IMAGE} AS runtime

# Hardware-aware defaults
ARG MACHINE=mainpc
COPY services/self_healing_supervisor/config/machine-profiles/${MACHINE}.json /etc/machine-profile.json 2>/dev/null || true

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/workspace

# Create non-root user (UID:GID 10001:10001)
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -d /app -s /sbin/nologin appuser
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copy common module and service code
COPY common/ /app/common/
COPY services/self_healing_supervisor/ /app/self_healing_supervisor/

# Install packages in runtime
RUN pip install --no-deps /app/common && \
    pip install --no-deps /app/self_healing_supervisor || true

# Runtime utilities
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl procps tini docker.io \
  && rm -rf /var/lib/apt/lists/* && \
  mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

# Add user to docker group for socket access (native Linux only)
RUN usermod -aG docker appuser || true

USER appuser

# Health check and ports (7009/9008)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:9008/health || exit 1
EXPOSE 7009 9008

# Metadata
LABEL org.opencontainers.image.title="Self-Healing Supervisor"
LABEL org.opencontainers.image.description="Container health monitoring and recovery"
LABEL org.opencontainers.image.version="1.0.0"

# Use tini as PID 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "self_healing_supervisor.supervisor"]
