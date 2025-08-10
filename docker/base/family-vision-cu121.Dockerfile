# syntax=docker/dockerfile:1.7
ARG ORG
ARG BASE_TAG
FROM ghcr.io/${ORG}/base-gpu-cu121:${BASE_TAG}

COPY docker/base/requirements.family-vision-cu121.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

USER appuser