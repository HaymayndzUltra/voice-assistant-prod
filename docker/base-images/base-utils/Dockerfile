# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive

# Ensure running as root for apt-get (fix permission denied)
USER root
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

# Create non-root user per plan.md (UID:GID 10001:10001)
RUN groupadd -g 10001 appuser && useradd -u 10001 -g appuser -s /sbin/nologin appuser

WORKDIR /app
RUN chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash", "-lc", "python --version && pip --version"]


