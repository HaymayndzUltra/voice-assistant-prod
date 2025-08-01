# ObservabilityHub - Centralized telemetry, metrics, prediction & health
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and user
RUN useradd -m -u 1000 ai && mkdir -p /app && chown -R ai:ai /app
WORKDIR /app

# Copy requirements
COPY --chown=ai:ai requirements.base.txt ./
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.base.txt

# Copy application code
COPY --chown=ai:ai phase1_implementation/ ./phase1_implementation/

# Expose Prometheus metrics port
EXPOSE 9000

# Switch to non-root user
USER ai

# Run ObservabilityHub
CMD ["python", "phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py"] 