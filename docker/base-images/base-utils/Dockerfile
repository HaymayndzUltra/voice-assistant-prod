# syntax=docker/dockerfile:1.5
# Base Utils - adds essential system utilities
FROM ghcr.io/haymayndzultra/base-python:20250812-latest

USER root

# Add essential utilities per plan.md
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    dumb-init \
    gosu \
    tzdata \
    git \
    jq \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=UTC

USER appuser
WORKDIR /app


