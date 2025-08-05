# Multi-stage Docker build for utility_cpu service group
# Optimized for production deployment with minimal attack surface

# ====== BUILD STAGE ======
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY docker/utility_cpu/minimal-requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --user -r /tmp/requirements.txt

# ====== RUNTIME STAGE ======
FROM python:3.10-slim as runtime

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Set up application structure
WORKDIR /app

# Copy application code
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/

# Set environment variables
ENV PYTHONPATH=/app
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Health check for utility CPU services
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import zmq; c = zmq.Context(); s = c.socket(zmq.REQ); s.connect('tcp://localhost:5591'); s.send_string('ping'); s.recv_string(); s.close(); c.term()" || exit 1

# Default entrypoint - CodeGenerator agent
CMD ["python", "-m", "main_pc_code.agents.code_generator_agent"]
