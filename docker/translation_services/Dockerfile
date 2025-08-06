# Optimized Dockerfile - slim base image with pip cache disabled
FROM python:3.10-slim-bullseye
# -- common-req-layer
ARG COMMON_REQ=/workspace/requirements.common.txt
COPY ${COMMON_REQ} /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.common.txt

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install \
    && rm -rf /var/lib/apt/lists/* -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --disable-pip-version-check --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"]
