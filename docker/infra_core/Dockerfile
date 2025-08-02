# ─── Base image ──────────────────────────────────────────────────────────────
FROM python:3.10-slim

# ─── Metadata / labels ───────────────────────────────────────────────────────
LABEL maintainer="YOU <you@example.com>" \
      org.opencontainers.image.source="https://github.com/your-org/your-repo" \
      org.opencontainers.image.description="Infra-core agents (ServiceRegistry & SystemDigitalTwin)"

# ─── System-level deps ───────────────────────────────────────────────────────
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# ─── Python deps ─────────────────────────────────────────────────────────────
COPY docker/infra_core/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ─── App code ────────────────────────────────────────────────────────────────
# Copy the entire main_pc_code directory for correct import structure
COPY main_pc_code /app/main_pc_code

# Copy common dependencies
COPY common /app/common
COPY common_utils /app/common_utils

WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# ─── Entrypoint (overridden via docker-compose) ──────────────────────────────
CMD ["python", "-m", "main_pc_code.agents.service_registry_agent"]
