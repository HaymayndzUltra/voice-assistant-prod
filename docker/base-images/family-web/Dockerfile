# syntax=docker/dockerfile:1.5
# Family Web - For web/API services
FROM ghcr.io/haymayndzultra/base-cpu-pydeps:20250812-latest

USER root

# Install web-specific dependencies
RUN pip install --no-cache-dir \
    starlette==0.35.1 \
    websockets==12.0 \
    gunicorn==21.2.0 \
    uvloop==0.19.0 \
    httptools==0.6.1 \
    python-multipart==0.0.6 \
    jinja2==3.1.3 \
    aioredis==2.0.1 \
    sse-starlette==2.0.0 \
    fastapi-utils==0.2.1

USER appuser
WORKDIR /app