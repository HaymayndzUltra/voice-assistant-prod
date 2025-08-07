# Real-Time Audio Pipeline (RTAP) - Production Docker Image
# Optimized for ultra-low-latency audio processing with ≤150ms p95 target

FROM python:3.11-slim-bullseye

# Metadata
LABEL maintainer="RTAP Team"
LABEL version="1.0"
LABEL description="Real-Time Audio Pipeline - Ultra-low-latency speech processing service"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Audio and system dependencies
RUN apt-get update && apt-get install -y \
    # Audio system dependencies
    libasound2-dev \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils \
    # System utilities
    curl \
    wget \
    git \
    # Build dependencies for Python packages
    build-essential \
    pkg-config \
    # FFmpeg for audio processing
    ffmpeg \
    # System monitoring
    htop \
    procps \
    # Network utilities
    netcat-openbsd \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r rtap && useradd -r -g rtap -s /bin/bash rtap

# Create application directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/models && \
    chown -R rtap:rtap /app

# Copy configuration files
COPY config/ /app/config/

# Audio device permissions and setup
RUN usermod -a -G audio rtap

# Health check script
COPY docker/healthcheck.sh /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh

# Create entrypoint script
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER rtap

# Expose ports
# 6552: ZMQ Events
# 6553: ZMQ Transcripts (primary output)
# 5802: WebSocket Server
# 8080: Health check endpoint
EXPOSE 6552 6553 5802 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/healthcheck.sh

# Volume mounts for configuration and data
VOLUME ["/app/config", "/app/logs", "/app/data", "/app/models"]

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python3", "app.py", "--log-level", "INFO"]
