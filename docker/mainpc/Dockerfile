FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install system dependencies with better error handling
RUN apt-get update -y && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends --fix-missing \
    python3.10 \
    python3-pip \
    python3-setuptools \
    python3-dev \
    python3-venv \
    build-essential \
    curl \
    wget \
    git \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install media and audio libraries separately to handle potential conflicts
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
    libsndfile1 \
    portaudio19-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libasound2-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Make python3 the default python
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create application directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.base.txt /app/requirements.base.txt
COPY main_pc_code/requirements.txt /app/requirements.txt

# 1. install common libs (cached across multiple images)
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.base.txt

# 2. install main-pc specific extras (smaller delta)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121

# Install llama-cpp-python with CUDA support for RTX 4090 (architecture 86)
RUN CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=86" pip install --no-cache-dir llama-cpp-python==0.2.23

# Install missing dependencies for error_bus (system-wide installation)
RUN pip install --no-cache-dir nats-py asyncio-nats-client aiofiles

# Copy application code
COPY . /app/

# Make scripts executable
RUN chmod +x /app/docker/mainpc/agent_starter.py \
    && chmod +x /app/main_pc_code/scripts/container_healthcheck.py

# Create necessary directories if they don't exist
RUN mkdir -p /app/logs /app/data /app/models /app/config

# Create non-root user for security
RUN groupadd -r ai && useradd -r -g ai -m -s /bin/bash ai && \
    chown -R ai:ai /app && \
    chmod -R 755 /app

# Default command - will be overridden by docker-compose

# Declare volumes for proper permissions  
VOLUME ["/app/logs", "/app/data", "/app/models", "/app/cache"]

USER ai

# Security and metadata labels
LABEL security_level="hardened" \
      user="non-root" \
      work_package="WP-02"
