# syntax=docker/dockerfile:1.5
# Family Torch CUDA 12.1 - PyTorch GPU services
FROM ghcr.io/haymayndzultra/base-gpu-cu121:20250812-latest

USER root

# Install PyTorch 2.2.2+cu121 per plan.md
RUN pip install --no-cache-dir \
    torch==2.2.2+cu121 \
    torchvision==0.17.2+cu121 \
    torchaudio==2.2.2+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Install common ML dependencies
RUN pip install --no-cache-dir \
    numpy==1.24.3 \
    scipy==1.11.4 \
    pandas==2.1.4 \
    scikit-learn==1.3.2 \
    matplotlib==3.8.2 \
    tensorboard==2.15.1 \
    einops==0.7.0 \
    safetensors==0.4.1

# Set CUDA arch list for compilation
ENV TORCH_CUDA_ARCH_LIST="8.9;8.6" \
    CUDA_VISIBLE_DEVICES=0

USER appuser
WORKDIR /app