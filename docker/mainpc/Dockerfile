FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Make python3 the default python
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create application directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY main_pc_code/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu121

# Install llama-cpp-python with CUDA support specifically for RTX 4090
RUN CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=89" pip install --no-cache-dir llama-cpp-python==0.2.23

# Copy application code
COPY . /app/

# Make scripts executable
RUN chmod +x /app/docker/mainpc/agent_starter.py \
    && chmod +x /app/main_pc_code/scripts/container_healthcheck.py

# Create necessary directories if they don't exist
RUN mkdir -p /app/logs /app/data /app/models /app/config

# Default command - will be overridden by docker-compose
ENTRYPOINT ["python", "/app/docker/mainpc/agent_starter.py"] 