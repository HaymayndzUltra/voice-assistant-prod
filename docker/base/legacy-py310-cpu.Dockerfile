# syntax=docker/dockerfile:1.7
FROM python:3.10-slim

ARG DEBIAN_FRONTEND=noninteractive
ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        tini ca-certificates \
    && python -m pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 10001 appuser && \
    useradd -m -u 10001 -g 10001 -s /usr/sbin/nologin appuser

ENTRYPOINT ["/usr/bin/tini","--"]
USER appuser