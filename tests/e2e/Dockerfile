FROM python:3.11-slim

WORKDIR /app

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest==7.4.* \
    pytest-asyncio==0.21.* \
    pytest-timeout==2.1.* \
    requests==2.31.* \
    aiohttp==3.9.* \
    websockets==11.0.*

# Copy test files
COPY tests/ tests/
COPY scripts/ scripts/

# Set proper permissions
RUN chmod +x scripts/health_probe.py

CMD ["python", "-m", "pytest", "tests/e2e/", "-v"]