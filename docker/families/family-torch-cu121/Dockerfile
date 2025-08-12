# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ENV TORCH_CUDA_ARCH_LIST="8.6;8.9;9.0+PTX" \
    CUDA_HOME=/usr/local/cuda \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

# Add minimal audio tooling needed by common torch audio stacks
# Ensure running as root for apt-get (fix permission denied)
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       libsndfile1 \
       libasound2 \
       libpulse0 \
       libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir \
        torch==2.2.2+cu121 \
        torchvision==0.17.2+cu121 \
        torchaudio==2.2.2+cu121 \
        --extra-index-url https://download.pytorch.org/whl/cu121

WORKDIR /app

USER appuser
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash", "-lc", "python - <<'PY'\nimport torch; print('torch', torch.__version__); print('cuda', torch.version.cuda)\nPY"]


