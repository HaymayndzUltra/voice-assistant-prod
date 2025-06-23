# MAINPC ONLY - Dockerfile for MainPC Voice Pipeline Components

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libzmq3-dev \
    portaudio19-dev \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY docker/mainpc/requirements.mainpc.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/logs /app/cache /app/models /app/voice_samples /app/certificates

# Copy the application code
COPY main_pc_code /app/main_pc_code
COPY config /app/config
COPY scripts /app/scripts

# Set environment variables
ENV PYTHONPATH=/app
ENV SECURE_ZMQ=1
ENV MACHINE_TYPE=MAINPC
ENV LOG_LEVEL=INFO

# Default command - will be overridden by docker-compose
CMD ["python", "-m", "main_pc_code.src.core.task_router"] 