# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m pip install --upgrade pip setuptools wheel

WORKDIR /app

RUN groupadd -g 10001 appuser \
    && useradd -u 10001 -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R 10001:10001 /app

USER appuser

CMD ["bash", "-lc", "python --version && pip --version"]


