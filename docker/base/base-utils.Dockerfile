ARG ORG
ARG BASE_TAG
FROM ghcr.io/${ORG}/base-python:${BASE_TAG}

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gosu tzdata dumb-init gnupg \
    && rm -rf /var/lib/apt/lists/*

# Keep root for subsequent layers; runtime users are set in family images