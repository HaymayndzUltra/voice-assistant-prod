# syntax=docker/dockerfile:1.5
# Family Vision CUDA 12.1 - For computer vision services
FROM ghcr.io/haymayndzultra/base-gpu-cu121:20250812-latest

USER root

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install vision-specific Python dependencies
RUN pip install --no-cache-dir \
    opencv-python-headless==4.9.0.80 \
    pillow==10.2.0 \
    scikit-image==0.22.0 \
    albumentations==1.3.1 \
    ultralytics==8.0.238 \
    mediapipe==0.10.9 \
    face-recognition==1.3.0 \
    dlib==19.24.2 \
    pytesseract==0.3.10 \
    onnx==1.15.0 \
    onnxruntime-gpu==1.16.3

# Install PyTorch for vision models
RUN pip install --no-cache-dir \
    torch==2.2.2+cu121 \
    torchvision==0.17.2+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

ENV TORCH_CUDA_ARCH_LIST="8.9;8.6"

USER appuser
WORKDIR /app