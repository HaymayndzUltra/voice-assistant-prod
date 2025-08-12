# syntax=docker/dockerfile:1.5
# Base GPU CUDA 12.1 - Foundation for GPU services
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Install Python 3.11 and essential tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    tini \
    curl \
    wget \
    git \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Upgrade pip
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Create non-root user safely (idempotent) and set up /app
RUN if ! getent group appuser >/dev/null; then groupadd -g 10001 appuser; fi \
 && if ! id -u appuser >/dev/null 2>&1; then useradd -r -u 10001 -g appuser -m -d /home/appuser -s /bin/bash appuser; fi \
 && mkdir -p /app && chown -R 10001:10001 /app

# Set Python and CUDA environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CUDA_HOME=/usr/local/cuda \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH \
    TORCH_CUDA_ARCH_LIST="8.9;8.6"

WORKDIR /app
USER appuser

ENTRYPOINT ["/usr/bin/tini", "--"]
