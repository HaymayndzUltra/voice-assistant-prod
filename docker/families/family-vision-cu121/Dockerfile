# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# Add vision stack system libs for cv2 and image decoders
# Ensure running as root for apt-get (fix permission denied)
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxrender1 \
      libxext6 \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --no-cache-dir \
      numpy \
      pillow \
      opencv-python-headless

WORKDIR /app

CMD ["bash", "-lc", "python -c 'import numpy, PIL; print("vision base ready")'"]


