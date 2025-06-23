# PC2 ONLY - Dockerfile for PC2 Components

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libzmq3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY docker/pc2/requirements.pc2.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/logs /app/cache /app/translation_models /app/certificates

# Copy the application code
COPY pc2_code /app/pc2_code
COPY config /app/config
COPY scripts /app/scripts

# Set environment variables
ENV PYTHONPATH=/app
ENV SECURE_ZMQ=1
ENV MACHINE_TYPE=PC2
ENV LOG_LEVEL=INFO

# Default command - will be overridden by docker-compose
CMD ["python", "-m", "pc2_code.agents.advanced_router"] 