# Remote API Adapter Container
# Lightweight image with OpenAI & AWS SDK support

FROM python:3.11-slim AS base

# Install minimal OS deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential ca-certificates curl git && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN addgroup --system adapter && adduser --system --ingroup adapter adapter
WORKDIR /app

# Copy source
COPY remote_api_adapter /app/remote_api_adapter

# Install Python deps – keep layers clean
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir openai boto3

# Use non-root user
USER adapter

# Healthcheck command by default
CMD ["python", "-m", "remote_api_adapter.adapter", "health_check"]
