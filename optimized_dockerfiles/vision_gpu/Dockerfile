# ---------- builder ----------
FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-dev build-essential \
        libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip

COPY docker/vision_gpu/minimal-requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

# ---------- runtime ----------
FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 libgl1-mesa-glx libglib2.0-0 \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO

COPY --from=builder /usr/local/lib/python3.*/site-packages /usr/local/lib/python3.*/site-packages
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/

WORKDIR /app
CMD ["python3", "-m", "main_pc_code.agents.face_recognition_agent"]
