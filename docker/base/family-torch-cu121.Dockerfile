ARG ORG
ARG BASE_TAG
FROM ghcr.io/${ORG}/base-gpu-cu121:${BASE_TAG}

ENV TORCH_CUDA_ARCH_LIST="8.9;8.6"

# Use PyTorch CUDA 12.1 wheels
COPY docker/base/requirements.family-torch-cu121.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

USER appuser