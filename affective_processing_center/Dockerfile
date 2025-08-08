# Affective Processing Center (APC) - Production Dockerfile
# Multi-stage build for optimal production deployment

# Build stage
FROM nvidia/cuda:12.1-devel-ubuntu22.04 AS builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    libasound2-dev \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Production stage
FROM nvidia/cuda:12.1-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

# GPU sharing configuration for multi-service deployment
ENV CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=25
ENV CUDA_VISIBLE_DEVICES=0
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    python3 \
    python3-distutils \
    ffmpeg \
    libsndfile1 \
    libasound2 \
    portaudio19-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r apc && useradd -r -g apc -d /app -s /bin/bash apc

# Create application directory
WORKDIR /app

# Copy application code
COPY --chown=apc:apc . /app/

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/models /app/cache && \
    chown -R apc:apc /app

# Switch to non-root user
USER apc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8008/health', timeout=5)" || exit 1

# Expose ports
EXPOSE 5591 5706 8008

# Production configuration
ENV APC_ENV=production
ENV APC_LOG_LEVEL=INFO
ENV APC_CONFIG_PATH=/app/config/default.yaml

# Run application
CMD ["python3", "app.py", "--config", "/app/config/default.yaml", "--log-level", "INFO"]

# Labels for container metadata
LABEL maintainer="APC Team <apc-team@company.com>"
LABEL version="1.0.0"
LABEL description="Affective Processing Center - Real-time emotional context analysis"
LABEL gpu.required="true"
LABEL gpu.memory="4GB"
LABEL service.type="emotion-processing"
LABEL service.ports="5591,5706,8008"