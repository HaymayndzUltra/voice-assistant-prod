FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

# --- system deps -------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-dev \
        gcc g++ build-essential \
        wget curl git \
        libgl1-mesa-glx libglib2.0-0 \
        && rm -rf /var/lib/apt/lists/*

# Create symlink for python
RUN ln -s /usr/bin/python3 /usr/bin/python

# --- python deps -------------------------------------------------------------
COPY docker/coordination/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# --- app code ----------------------------------------------------------------
COPY main_pc_code/            /app/main_pc_code/
COPY common/                  /app/common/
COPY common_utils/            /app/common_utils/
COPY phase1_implementation/   /app/phase1_implementation/
COPY docker/coordination/     /app/docker/coordination/

WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV CUDA_VISIBLE_DEVICES=0

# Default CMD (can be overridden in docker-compose)
CMD ["python", "-m", "main_pc_code.agents.request_coordinator"]
