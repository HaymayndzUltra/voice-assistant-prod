FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent source code
COPY pc2_code /app/pc2_code

# Copy the rest of the project
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Create logs directory
RUN mkdir -p /app/logs

# Health check script
COPY docker/pc2_async_pipeline/health_check.sh /health_check.sh
RUN chmod +x /health_check.sh

# Default command (will be overridden by docker-compose)
CMD ["python", "pc2_code/agents/async_processor.py"]

# Health check as required by endorsement document
HEALTHCHECK CMD curl -f http://localhost:${HEALTH_PORT}/health || exit 1
