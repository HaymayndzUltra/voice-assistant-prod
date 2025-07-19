# Temporarily using Python base - will add CUDA support later
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3-pip \
    python3-setuptools \
    python3-dev \
    build-essential \
    curl \
    git \
    libportaudio2 \
    libsndfile1 \
    portaudio19-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    wget \
    gnupg \
    software-properties-common \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Make python3 the default python
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create non-root user
RUN groupadd -r ai && useradd -r -g ai ai

# Create application directory
WORKDIR /app

# Upgrade pip and install basic packages
RUN pip install --no-cache-dir -U pip setuptools wheel

# Install PyTorch with CUDA support
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install common Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install additional GPU-optimized packages
RUN pip install --no-cache-dir \
    transformers>=4.30.0 \
    accelerate>=0.20.0 \
    bitsandbytes>=0.39.0 \
    xformers>=0.0.20 \
    triton>=2.0.0

# Install llama-cpp-python without CUDA (since using python:3.11-slim base)
RUN pip install --no-cache-dir llama-cpp-python

# Copy application code
COPY --chown=ai:ai . /app

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/models /app/config /app/cache && \
    chown -R ai:ai /app

# Declare volumes for proper permissions
VOLUME ["/app/logs", "/app/data", "/app/models", "/app/cache"]

# Switch to non-root user
USER ai

# Health check script
COPY --chown=ai:ai scripts/health_check.py /app/scripts/health_check.py
RUN chmod +x /app/scripts/health_check.py

# Default command
CMD ["python", "/app/main_pc_code/scripts/start_system.py"]

# Security and metadata labels
LABEL security_level="hardened" \
      user="non-root" \
      work_package="WP-02" \
      gpu_support="cuda-11.8" \
      optimized_for="RTX-4090,RTX-3060" 