FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3.10-dev \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create symlink for python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set NVIDIA environment variables for GPU access
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Create logs and data directories
RUN mkdir -p /app/logs /app/data /app/vision_data /app/dream_data

# Health check script
COPY docker/pc2_vision_dream_gpu/health_check.sh /health_check.sh
RUN chmod +x /health_check.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /health_check.sh

# Default command (will be overridden by docker-compose)
CMD ["python", "pc2_code/agents/VisionProcessingAgent.py"]
