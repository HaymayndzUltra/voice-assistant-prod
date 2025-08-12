# syntax=docker/dockerfile:1.7
# UnifiedObservabilityCenter - Per plan.md line 120

ARG BASE_IMAGE=ghcr.io/haymayndzultra/family-web:20250810-9c99cc9
ARG MACHINE=mainpc

# Builder stage
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config curl git \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip wheel setuptools && \
    pip wheel -w /wheels -r requirements.txt

# Runtime stage
FROM ${BASE_IMAGE} AS runtime

# Hardware-aware defaults
ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UVICORN_WORKERS=1

# Runtime dependencies
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl tini ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Create non-root user per plan.md (UID:GID 10001:10001)
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -s /sbin/nologin appuser
WORKDIR /app

# Copy machine profile (optional for observability)
COPY config/machine-profiles/${MACHINE}.json /etc/machine-profile.json

# Install Python deps from wheels
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy application code
COPY . .

# Set permissions
RUN mkdir -p /app/logs /app/data && \
    chown -R appuser:appuser /app && \
    chmod +x /usr/bin/tini

USER appuser

# Ports per plan.md line 120: 9100/9110
EXPOSE 9100 9110

# Health check per plan.md
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9110/health || exit 1

ENV PYTHONPATH=/app

# Use tini as PID 1 per plan.md
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "unified_observability_center.app"]

