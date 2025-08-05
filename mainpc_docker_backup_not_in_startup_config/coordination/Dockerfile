# ------------ builder ------------
FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04 AS builder

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-dev \
        && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --upgrade pip

COPY docker/coordination/minimal-requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
# Explicitly ensure pyzmq is installed and verify
RUN pip install --no-cache-dir pyzmq==26.0.3
RUN python3 -c "import zmq; print('ZMQ version:', zmq.zmq_version())"

# ------------ runtime ------------
FROM nvidia/cuda:12.3.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends python3 \
    && ln -s /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    LOG_LEVEL=INFO

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/

WORKDIR /app
CMD ["python3", "-m", "main_pc_code.agents.request_coordinator"]
