# Base Dockerfile for PC2 agents
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libzmq3-dev \
    libopenblas-dev \
    gfortran \
    git \
    curl \
    wget \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and user
RUN useradd -m -s /bin/bash ai && \
    mkdir -p /app/logs /app/data /app/models /app/cache && \
    chown -R ai:ai /app

WORKDIR /app

# Copy requirements first for better caching
COPY requirements/pc2_requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy application code
COPY --chown=ai:ai common/ /app/common/
COPY --chown=ai:ai common_utils/ /app/common_utils/
COPY --chown=ai:ai pc2_code/ /app/pc2_code/

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER ai

# Default health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command
CMD ["python", "-m", "pc2_code.agents.base_agent"]