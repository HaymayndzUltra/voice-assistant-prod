# Optimized Dockerfile - slim base image with pip cache disabled
FROM python:3.10-slim-bullseye

WORKDIR /app

# Copy shared libraries
COPY . .

# Install any Python dependencies if requirements.txt exists
RUN if [ -f requirements.txt ]; then pip install --disable-pip-version-check --no-cache-dir -r requirements.txt; fi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD echo "Shared libraries container healthy" || exit 1

# Default command for shared library container
CMD ["python", "-c", "print('Shared libraries container running')"]
