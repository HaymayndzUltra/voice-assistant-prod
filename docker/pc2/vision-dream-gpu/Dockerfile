# =============================================================================
# PC2 VISION DREAM GPU CONTAINER
# Agents: VisionProcessingAgent, DreamWorldAgent, DreamingModeAgent
# Resources: CPU 25%, RAM 6GB, GPU 6GB
# =============================================================================
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    CONTAINER_ROLE=vision_dream_gpu

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-pip \
    python3.11-dev \
    build-essential \
    curl \
    git \
    gcc \
    g++ \
    cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Make python3 the default python
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create non-root user
RUN groupadd --gid 1000 aiuser && \
    useradd --uid 1000 --gid aiuser --shell /bin/bash --create-home aiuser

# Create application directory
WORKDIR /app

# Copy requirements
COPY docker/pc2/vision-dream-gpu/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/{logs,data,config,cache,models} && \
    chown -R aiuser:aiuser /app

# Copy startup script
COPY docker/pc2/vision-dream-gpu/start.sh /app/start.sh
RUN chmod +x /app/start.sh && chown aiuser:aiuser /app/start.sh

# Switch to non-root user
USER aiuser

# Expose ports
EXPOSE 7150 7104 7127

# Health check
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=3 \
    CMD python /app/scripts/health_check.py || exit 1

# Start script
CMD ["/app/start.sh"] 