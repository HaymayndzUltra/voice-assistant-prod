# syntax=docker/dockerfile:1.7

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ENV PORT=8000 \
    PYTHONUNBUFFERED=1

# Intentionally minimal; services add their own framework/runtime deps
WORKDIR /app

CMD ["bash", "-lc", "python --version && echo 'family-web base ready'"]


