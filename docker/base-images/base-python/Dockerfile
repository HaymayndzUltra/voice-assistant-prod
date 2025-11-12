# syntax=docker/dockerfile:1.5
# Base Python image - Foundation for all services
FROM python:3.13.9-slim-bookworm

# Security updates and essential tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip setuptools wheel

# Create non-root user with specific UID:GID per plan.md
RUN groupadd -g 10001 appuser && \
    useradd -r -u 10001 -g appuser -m -d /home/appuser -s /bin/bash appuser

# Set Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Switch to non-root user
USER appuser
WORKDIR /app

# Tini will be the entrypoint for child images
ENTRYPOINT ["/usr/bin/tini", "--"]


