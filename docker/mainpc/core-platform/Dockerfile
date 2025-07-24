# =============================================================================
# MAINPC CORE PLATFORM CONTAINER
# Agents: ServiceRegistry, SystemDigitalTwin, RequestCoordinator, ObservabilityHub
# Resources: CPU 20%, RAM 2GB, GPU 0GB
# =============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    CONTAINER_ROLE=core_platform

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 aiuser && \
    useradd --uid 1000 --gid aiuser --shell /bin/bash --create-home aiuser

# Create application directory
WORKDIR /app

# Create shared directory and copy shared requirements first
RUN mkdir -p /app/shared
COPY docker/shared/requirements.base.txt /app/shared/requirements.base.txt

# Copy requirements
COPY docker/mainpc/core-platform/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/{logs,data,config,cache} && \
    chown -R aiuser:aiuser /app

# Copy startup script
COPY docker/mainpc/core-platform/start.sh /app/start.sh
RUN chmod +x /app/start.sh && chown aiuser:aiuser /app/start.sh

# Switch to non-root user  
USER aiuser

# Expose ports
EXPOSE 7200 7220 26002 9000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Start script
CMD ["/app/start.sh"] 