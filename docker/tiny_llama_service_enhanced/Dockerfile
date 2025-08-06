FROM nvidia/cuda:11.8-devel-ubuntu22.04
# -- common-req-layer
ARG COMMON_REQ=/workspace/requirements.common.txt
COPY ${COMMON_REQ} /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.common.txt

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
RUN update-alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1

WORKDIR /app

# Copy requirements and install Python dependencies
COPY docker/tiny_llama_service_enhanced/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# Create logs directory
RUN mkdir -p logs data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${HEALTH_PORT:-6615}/health || exit 1

# Expose ports
EXPOSE 5615 6615

# Run the agent
CMD ["python3", "main_pc_code/FORMAINPC/tiny_llama_service_enhanced.py"]
