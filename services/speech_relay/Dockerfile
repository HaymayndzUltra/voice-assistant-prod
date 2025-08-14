# syntax=docker/dockerfile:1.7
# SpeechRelayService - gRPC + Prometheus (PC2)
FROM ghcr.io/haymayndzultra/family-web:20250812-latest AS base

ARG MACHINE=pc2
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT_OFFSET=0

WORKDIR /app

COPY services/speech_relay/ ./speech_relay
COPY common/ ./common

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r speech_relay/requirements.txt || true && \
    pip install --no-cache-dir grpcio grpcio-tools prometheus-client pyzmq

USER appuser

LABEL health_check_port="8130"
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -sf http://localhost:8130/metrics || exit 1

EXPOSE 7130 8130

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "speech_relay.relay"]


