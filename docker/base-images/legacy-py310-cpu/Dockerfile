# syntax=docker/dockerfile:1.5
# Legacy Python 3.10 CPU - For exceptional cases only
FROM python:3.14.0rc2-slim-trixie

# Security updates and essential tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    tini \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip setuptools wheel

# Create non-root user with specific UID:GID per plan.md
RUN groupadd -g 10001 appuser && \
    useradd -r -u 10001 -g appuser -m -d /home/appuser -s /bin/bash appuser

# Install basic dependencies for legacy agents
RUN pip install --no-cache-dir \
    pydantic==1.10.15 \
    fastapi==0.110.0 \
    uvicorn==0.27.0 \
    redis==4.5.5 \
    psutil==5.9.8 \
    httpx==0.24.1

# Set Python environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

USER appuser
WORKDIR /app

ENTRYPOINT ["/usr/bin/tini", "--"]