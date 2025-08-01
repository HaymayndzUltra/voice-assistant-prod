FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

# Install Python and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 \
        python3-pip \
        python3.10-dev \
        gcc \
        g++ \
        build-essential \
        wget \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Create symbolic link for python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

# Upgrade pip
RUN python -m pip install --upgrade pip

# Copy requirements and install dependencies
COPY docker/translation_services/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

# Copy application code
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# GPU environment variables
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# Default entrypoint = FixedStreamingTranslation
CMD ["python", "-m", "main_pc_code.agents.fixed_streaming_translation"]
