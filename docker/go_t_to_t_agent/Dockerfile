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
COPY docker/go_t_to_t_agent/requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create logs directory
RUN mkdir -p logs data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${HEALTH_PORT:-6646}/health || exit 1

# Expose ports
EXPOSE 5646 6646

# Run the agent
CMD ["python", "main_pc_code/FORMAINPC/go_t_to_t_agent.py"]
