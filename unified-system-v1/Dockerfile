# Multi-stage build for optimized image
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt

# Runtime stage
FROM python:3.10-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 unified

# Copy Python packages from builder
COPY --from=builder /root/.local /home/unified/.local

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=unified:unified . .

# Create necessary directories
RUN mkdir -p logs data artifacts && \
    chown -R unified:unified /app

# Switch to non-root user
USER unified

# Add local bin to PATH
ENV PATH=/home/unified/.local/bin:$PATH

# Default environment
ENV PROFILE=core \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9000/health || exit 1

# Expose ports (base ports for core services)
EXPOSE 7200-7299 8200-8299 9000-9099

# Default command
CMD ["python", "main.py", "start"]