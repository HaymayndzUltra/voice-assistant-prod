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

# Configure pip for better network resilience
RUN pip config set global.timeout 300
RUN pip config set global.retries 5

# Install core dependencies first (lighter packages)
RUN pip install --no-cache-dir \
    redis==5.0.1 \
    nats-py==2.7.2 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    pydantic==2.5.1 \
    python-dotenv==1.0.0 \
    prometheus-client==0.19.0 \
    psutil==5.9.6 \
    aiohttp==3.9.1 \
    asyncio-mqtt==0.13.0 \
    httpx==0.25.2 \
    aiofiles==23.2.1 \
    websockets==12.0 \
    requests==2.31.0 \
    PyJWT==2.8.0 \
    pyzmq==25.1.2 \
    PyYAML==6.0.1 \
    sqlalchemy==2.0.25 \
    joblib==1.3.2 \
    pandas==2.1.3 \
    diskcache==5.6.3 \
    python-memcached==1.62

# Install basic ML dependencies only (lightweight)
RUN pip install --no-cache-dir \
    numpy==1.24.4 \
    pandas==2.1.3

# Copy only necessary files (not entire project)
COPY pc2_code/ ./pc2_code/
COPY common/ ./common/
COPY phase1_implementation/ ./phase1_implementation/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Create logs directory
RUN mkdir -p /app/logs

# Health check script
COPY docker/pc2_memory_stack/health_check.sh /health_check.sh
RUN chmod +x /health_check.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /health_check.sh

# Default command (will be overridden by docker-compose)
CMD ["python", "pc2_code/agents/memory_orchestrator_service.py"]
