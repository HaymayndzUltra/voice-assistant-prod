# Memory Fusion Hub (MFH) - Production Dockerfile
# Multi-stage build for optimal production deployment

# Build stage
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create non-root user for security
RUN groupadd -r mfh && useradd -r -g mfh -d /app -s /bin/bash mfh

# Create application directory
WORKDIR /app

# Copy application code
COPY --chown=mfh:mfh . /app/

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/cache && \
    chown -R mfh:mfh /app

# Switch to non-root user
USER mfh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Expose ports
EXPOSE 8080 50051 5555

# Production configuration
ENV MFH_ENV=production
ENV MFH_LOG_LEVEL=INFO
ENV MFH_CONFIG_PATH=/app/config/default.yaml

# Run application
CMD ["python", "app.py", "--config", "/app/config/default.yaml", "--log-level", "INFO"]

# Labels for container metadata
LABEL maintainer="MFH Team <mfh-team@company.com>"
LABEL version="1.0.0"
LABEL description="Memory Fusion Hub - Unified memory management and fusion service"
LABEL service.type="memory-processing"
LABEL service.ports="8080,50051,5555"