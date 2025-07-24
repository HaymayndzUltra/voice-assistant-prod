# =============================================================================
# MAINPC MODEL MANAGER GPU CONTAINER
# Agents: ModelManagerSuite, UnifiedSystemAgent
# Resources: CPU 15%, RAM 4GB, GPU 6GB
# Models: phi-3-mini-4k-instruct-q4_K_M.gguf, mistral-7b-instruct-v0.2-q4_K_M.gguf
# =============================================================================
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    CONTAINER_ROLE=model_manager_gpu

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-pip \
    python3.11-dev \
    build-essential \
    curl \
    git \
    gcc \
    g++ \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Make python3 the default python
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Create non-root user
RUN groupadd --gid 1000 aiuser && \
    useradd --uid 1000 --gid aiuser --shell /bin/bash --create-home aiuser

# Create application directory
WORKDIR /app

# Copy requirements
COPY docker/mainpc/model-manager-gpu/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install llama-cpp-python with CUDA support for GGUF models
RUN CMAKE_ARGS="-DLLAMA_CUBLAS=on -DCMAKE_CUDA_ARCHITECTURES=89" \
    pip install --no-cache-dir llama-cpp-python==0.2.23

# Copy application code
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/{logs,data,config,cache,models} && \
    chown -R aiuser:aiuser /app

# Copy startup script
COPY docker/mainpc/model-manager-gpu/start.sh /app/start.sh
RUN chmod +x /app/start.sh && chown aiuser:aiuser /app/start.sh

# Copy model configuration
COPY docker/mainpc/model-manager-gpu/model_config.yaml /app/config/model_config.yaml

# Switch to non-root user
USER aiuser

# Expose ports
EXPOSE 7211 7225 8211

# Health check
HEALTHCHECK --interval=30s --timeout=15s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8211/health || exit 1

# Start script
CMD ["/app/start.sh"] 