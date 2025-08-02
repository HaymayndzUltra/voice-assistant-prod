# Learning GPU Docker Image - Using Python slim base (same pattern as other GPU groups)
FROM python:3.10-slim

# Install system dependencies for ML training and GPU support
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set PYTHONPATH to include the application directory
ENV PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY docker/learning_gpu/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

# Copy source code
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/
COPY remote_api_adapter/ /app/remote_api_adapter/

# Set working directory
WORKDIR /app
