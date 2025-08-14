# syntax=docker/dockerfile:1.7
# StreamingTranslationProxy - CPU/Web service (MainPC)
FROM ghcr.io/haymayndzultra/family-web:20250812-latest AS base

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT_OFFSET=0

WORKDIR /app

# Copy service code
COPY services/streaming_translation_proxy/ ./streaming_translation_proxy
COPY common/ ./common

# Install requirements
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r streaming_translation_proxy/requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn[standard] httpx prometheus-client

USER appuser

LABEL health_check_port="6596"

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -sf http://localhost:6596/health || exit 1

# service 5596, health 6596
EXPOSE 5596 6596

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "streaming_translation_proxy.proxy"]


