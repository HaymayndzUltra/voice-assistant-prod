# Optimized Dockerfile - slim base image with pip cache disabled
FROM python:3.10-slim-bullseye
# -- common-req-layer
ARG COMMON_REQ=./requirements.common.lock.txt
COPY ${COMMON_REQ} /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.common.lock.txt
RUN apt-get update && apt-get install -y --no-install-recommends curl gcc build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/
RUN pip install --disable-pip-version-check --no-cache-dir -r /tmp/requirements.txt
COPY ./pc2_code /app/pc2_code
COPY ./common /app/common
WORKDIR /app
ENV PYTHONPATH=/app
HEALTHCHECK CMD curl -f http://localhost:8101/health || exit 1
CMD ["python", "-m", "pc2_code.agents.async_processor"]
