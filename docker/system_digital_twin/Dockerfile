# Optimized Dockerfile - slim base image with pip cache disabled
FROM python:3.10-slim-bullseye
# -- common-req-layer
ARG COMMON_REQ=/workspace/requirements.common.txt
COPY ${COMMON_REQ} /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.common.txt
RUN apt-get update && apt-get install \
    && rm -rf /var/lib/apt/lists/* -y --no-install-recommends curl gcc build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/
RUN pip install --disable-pip-version-check --no-cache-dir -r /tmp/requirements.txt
COPY main_pc_code /app/main_pc_code
COPY common /app/common
COPY common_utils /app/common_utils
WORKDIR /app
ENV PYTHONPATH=/app
HEALTHCHECK CMD curl -f http://localhost:7220/health || exit 1
CMD ["python", "-m", "main_pc_code.agents.system_digital_twin"]
