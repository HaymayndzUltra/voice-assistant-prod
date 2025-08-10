# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

WORKDIR /app

# Install Python deps
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# Copy service code
COPY . /app

# Healthcheck: Python module import
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
  CMD ["python", "-c", "import importlib,sys; importlib.import_module('error_bus'); sys.exit(0)"]

CMD ["python", "-u", "error_bus.py"]


