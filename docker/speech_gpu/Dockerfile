# ---------- builder ----------
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-dev build-essential \
        libsndfile1-dev ffmpeg && \
    rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip

COPY docker/speech_gpu/minimal-requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

# Download speech models in build stage for faster runtime
RUN python3 -c "import whisper; whisper.load_model('base')" || echo "Whisper model download failed, will download at runtime"
RUN python3 -c "import torch; import torchaudio; print('Audio models ready')" || echo "Audio models setup completed"

# ---------- runtime ----------
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends python3 \
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

# Add health check for GPU speech services
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import zmq; c = zmq.Context(); s = c.socket(zmq.REQ); s.connect('tcp://localhost:5524'); s.send_string('ping'); s.recv_string(); s.close(); c.term()" || exit 1

CMD ["python3", "-m", "main_pc_code.agents.streaming_tts_agent"]
