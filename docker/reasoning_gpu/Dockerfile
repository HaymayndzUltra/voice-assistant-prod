# ---------- builder ----------
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-dev build-essential curl \
        && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip

COPY docker/reasoning_gpu/minimal-requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

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
COPY remote_api_adapter/ /app/remote_api_adapter/

WORKDIR /app

# Add health check for GPU reasoning services
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import zmq; c = zmq.Context(); s = c.socket(zmq.REQ); s.connect('tcp://localhost:5501'); s.send_string('ping'); s.recv_string(); s.close(); c.term()" || exit 1

CMD ["python3", "-m", "main_pc_code.agents.responder"]
