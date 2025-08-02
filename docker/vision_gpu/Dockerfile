# Vision GPU Docker Image - Using Python slim base (same as emotion_system)
FROM python:3.10-slim

# Install system dependencies including OpenCV requirements
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set PYTHONPATH to include the application directory
ENV PYTHONPATH=/app

# Copy requirements and install Python dependencies
COPY docker/vision_gpu/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

# Copy source code
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/
COPY remote_api_adapter/ /app/remote_api_adapter/

# Set working directory
WORKDIR /app

# Default command (will be overridden by docker-compose)
CMD ["python", "-m", "main_pc_code.agents.face_recognition_agent"]
