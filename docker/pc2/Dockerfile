FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04 as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-setuptools \
    python3-dev \
    build-essential \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Make python3 the default python
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

COPY requirements.base.txt /app/requirements.base.txt
COPY docker/pc2/requirements.pc2.txt /app/requirements.txt

# Install Python dependencies but optimize for size
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.base.txt && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir transformers[sentencepiece] sacremoses ctranslate2 && \
    pip install --no-cache-dir pyyaml requests psutil prometheus-client && \
    pip cache purge && \
    find /usr/local/lib/python3.10 -name __pycache__ | xargs rm -rf && \
    find /usr/local/lib/python3.10 -name "*.pyc" | xargs rm -rf

# Stage 2: Final image (smaller)
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set environment variables for memory optimization
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
ENV MALLOC_TRIM_THRESHOLD_=100000
ENV TZ=UTC
ENV LOG_LEVEL=INFO

# Install only required runtime packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    procps \
    htop \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Make python3 the default python
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only essential project files
# First copy just what we need for the health check
COPY pc2_code/scripts/container_healthcheck.py /app/pc2_code/scripts/
COPY pc2_code/config/container_groups.yaml /app/pc2_code/config/
COPY pc2_code/config/startup_config.yaml /app/pc2_code/config/

# Then copy the rest of the application code (no unnecessary files)
COPY common/core /app/common/core/
COPY common/utils /app/common/utils/
COPY config/network_config.yaml /app/config/
COPY src/core /app/src/core/
COPY pc2_code/agents /app/pc2_code/agents/
COPY pc2_code/config /app/pc2_code/config/
COPY pc2_code/scripts/container_healthcheck.py /app/pc2_code/scripts/
COPY utils/agent_health.py /app/utils/
COPY utils/agent_supervisor.py /app/utils/

# Set permissions on the healthcheck script
RUN chmod +x /app/pc2_code/scripts/container_healthcheck.py

# Create necessary directories with minimal structure
RUN mkdir -p /app/logs /app/models /app/data/redis /app/data/users /app/data/monitoring

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1
    
# Declare volumes for proper permissions
VOLUME ["/app/logs", "/app/data", "/app/models", "/app/cache"]

USER ai

CMD

# Add startup script to control memory usage
COPY docker/pc2/memory_monitor.sh /app/memory_monitor.sh
RUN chmod +x /app/memory_monitor.sh

# Set default command - will be overridden by docker-compose
CMD ["bash", "-c", "/app/memory_monitor.sh"] 
# Security and metadata labels
LABEL security_level="hardened" \
      user="non-root" \
      work_package="WP-02"

# Add group filtering
ENV ENABLED_GROUPS="core_services,memory_system,pc2_services,utility_services,language_processing"
