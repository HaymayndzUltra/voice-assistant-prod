# syntax=docker/dockerfile:1.5
FROM ghcr.io/haymayndzultra/base-gpu-cu121:20250812-latest

USER root

# System deps + full toolchain for dlib build
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 \
    libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 \
    build-essential cmake ninja-build pkg-config \
    python3-dev libboost-all-dev \
    libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev \
 && rm -rf /var/lib/apt/lists/*

# Prefer apt cmake over any pip cmake inside build isolation
ENV PATH="/usr/bin:${PATH}"
ENV TORCH_CUDA_ARCH_LIST="8.9;8.6"
ENV CMAKE_BUILD_PARALLEL_LEVEL="8"
# Force CPU-only dlib to avoid needing CUDA toolkits in runtime base
ENV DLIB_USE_CUDA="0" \
    DLIB_NO_GUI_SUPPORT="1" \
    CMAKE_ARGS="-DDLIB_USE_CUDA=0 -DDLIB_NO_GUI_SUPPORT=1 -DUSE_AVX_INSTRUCTIONS=1"

# Pin Torch GPU stack first
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
      torch==2.2.2+cu121 torchvision==0.17.2+cu121 torchaudio==2.2.2+cu121 \
      --index-url https://download.pytorch.org/whl/cu121

# Vision deps (force using system toolchain; avoid build isolation for dlib)
RUN --mount=type=cache,target=/root/.cache/pip \
    PIP_NO_BUILD_ISOLATION=1 pip install --no-cache-dir \
      opencv-python-headless==4.9.0.80 \
      pillow==10.2.0 \
      scikit-image==0.22.0 \
      albumentations==1.3.1 \
      mediapipe==0.10.9 \
      dlib==19.24.2 \
      face-recognition==1.3.0 \
      pytesseract==0.3.10 \
      onnx==1.15.0 \
      onnxruntime-gpu==1.16.3

# Avoid ultralytics pulling a different torch
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --no-deps ultralytics==8.0.238

USER appuser
WORKDIR /app