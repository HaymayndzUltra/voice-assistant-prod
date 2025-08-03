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
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Create logs and data directories
RUN mkdir -p /app/logs /app/data /app/web_data /app/static /app/templates

# Health check script
COPY docker/pc2_web_interface/health_check.sh /health_check.sh
RUN chmod +x /health_check.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /health_check.sh

# Default command (will be overridden by docker-compose)
CMD ["python", "pc2_code/agents/unified_web_agent.py"]
