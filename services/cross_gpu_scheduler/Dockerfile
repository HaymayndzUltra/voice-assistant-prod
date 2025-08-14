# syntax=docker/dockerfile:1.7
# CrossMachineGPUScheduler - gRPC + Prometheus
FROM ghcr.io/haymayndzultra/family-gpu-cu121:20250812-latest AS base

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT_OFFSET=0

WORKDIR /app

COPY services/cross_gpu_scheduler/ ./cross_gpu_scheduler
COPY common/ ./common

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r cross_gpu_scheduler/requirements.txt || true && \
    pip install --no-cache-dir grpcio grpcio-tools prometheus-client pynvml

USER appuser

LABEL health_check_port="8155"
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -sf http://localhost:8155/metrics || exit 1

EXPOSE 7155 8155

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "cross_gpu_scheduler.app"]


