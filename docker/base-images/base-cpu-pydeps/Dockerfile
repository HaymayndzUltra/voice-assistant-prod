# syntax=docker/dockerfile:1.5
# Base CPU Python Dependencies
FROM ghcr.io/haymayndzultra/base-utils:20250812-latest

USER root

# Install common Python dependencies per plan.md
RUN pip install --no-cache-dir \
    numpy==1.24.3 \
    pydantic==2.5.3 \
    fastapi==0.109.0 \
    uvicorn==0.27.0 \
    redis==5.0.1 \
    psutil==5.9.8 \
    pyzmq==25.1.2 \
    httpx==0.26.0 \
    pyyaml==6.0.1 \
    python-dotenv==1.0.0 \
    asyncio==3.4.3 \
    aiofiles==23.2.1 \
    prometheus-client==0.19.0

USER appuser
WORKDIR /app


