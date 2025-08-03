# PC2 Infrastructure Core Services Dockerfile
# ObservabilityHub + ResourceManager
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy PC2 specific requirements
COPY docker/pc2_infra_core/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire codebase
COPY . .

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Environment variables for PC2
ENV PC2_SUBSYSTEM=true
ENV REDIS_URL=redis://redis_pc2_infra:6379/0
ENV NATS_SERVERS=nats://nats_pc2_infra:4222
ENV LOG_LEVEL=INFO

# Health check script
RUN echo '#!/bin/bash\ncurl -f http://localhost:${HEALTH_PORT:-8113}/health || exit 1' > /health_check.sh && \
    chmod +x /health_check.sh

# Expose default ports (will be overridden by compose)
EXPOSE 9100 9110 7113 8113

# Default command (will be overridden by docker-compose)
CMD ["python", "pc2_code/agents/resource_manager.py"]
