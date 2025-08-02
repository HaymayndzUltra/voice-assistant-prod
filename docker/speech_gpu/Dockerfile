# Speech GPU Docker Image - Using Python slim base (same pattern as vision_gpu)
FROM python:3.10-slim

# Install system dependencies including audio processing requirements
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libasound2-dev \
    portaudio19-dev \
    libflac-dev \
    libvorbis-dev \
    libopus-dev \
    libmp3lame-dev \
    libffi-dev \
    libssl-dev \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set PYTHONPATH to include the application directory
ENV PYTHONPATH=/app

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY docker/speech_gpu/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

# Copy source code
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/
COPY remote_api_adapter/ /app/remote_api_adapter/

# Set working directory
WORKDIR /app
