# Optimized Dockerfile - slim base image with pip cache disabled
FROM python:3.10-slim-bullseye

WORKDIR /app

# Install basic utilities
RUN apt-get update && apt-get install \
    && rm -rf /var/lib/apt/lists/* -y \
    curl \
    git \
    jq \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Copy scripts
COPY . .

# Make scripts executable
RUN find . -name "*.sh" -exec chmod +x {} \;

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD echo "Scripts container healthy" || exit 1

CMD ["bash"]
