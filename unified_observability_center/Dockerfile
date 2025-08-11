ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UVICORN_WORKERS=1

WORKDIR /app

# family-web/base-cpu already provides a slim runtime; keep minimal apt
RUN apt-get update -y && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install -r /app/requirements.txt

# App code
COPY . /app

EXPOSE 9100

ENV PYTHONPATH=/app

CMD ["python", "-m", "unified_observability_center.app"]

