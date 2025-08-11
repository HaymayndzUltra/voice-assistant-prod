# syntax=docker/dockerfile:1.7

FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Ensure running as root for apt-get (fix permission denied)
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       software-properties-common \
       ca-certificates \
       curl \
       git \
       build-essential \
       pkg-config \
       libssl-dev \
       libffi-dev \
       tzdata \
       tini \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
       python3.11 python3.11-venv python3.11-dev \
    && curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py \
    && python3.11 /tmp/get-pip.py \
    && ln -sf /usr/bin/python3.11 /usr/local/bin/python \
    && ln -sf /usr/local/bin/pip3.11 /usr/local/bin/pip \
    && rm -rf /var/lib/apt/lists/* /tmp/get-pip.py

WORKDIR /app

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["bash", "-lc", "python --version && pip --version"]


