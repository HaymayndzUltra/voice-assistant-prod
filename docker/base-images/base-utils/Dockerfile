# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       git \
        build-essential \
        pkg-config \
        curl \
        wget \
        ca-certificates \
        tzdata \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN groupadd -g 10001 appuser \
    && useradd -u 10001 -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R 10001:10001 /app

USER appuser

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash", "-lc", "python --version && pip --version"]


