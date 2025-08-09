# Multi-stage Dockerfile for ModelOps Coordinator
# Production-ready container with optimized size and security

# Build stage - Install dependencies and compile
FROM python:3.10-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --upgrade pip wheel setuptools
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Validate Python syntax and basic imports
RUN python -m py_compile app.py
RUN python -c "import sys; sys.path.insert(0, '.'); from core.kernel import Kernel; print('✅ Import validation successful')"

# Production stage - Minimal runtime environment
FROM python:3.10-slim as production

# Create non-root user for security
RUN groupadd -r moc && useradd -r -g moc moc

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --from=builder /build .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data /app/logs /app/config && \
    chown -R moc:moc /app

# Copy default configuration
COPY config/default.yaml /app/config/

# Switch to non-root user
USER moc

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

# Expose ports
EXPOSE 7211 7212 8008

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MOC_LOG_LEVEL=INFO
ENV MOC_CONFIG_DIR=/app/config

# Labels for metadata
LABEL org.opencontainers.image.title="ModelOps Coordinator"
LABEL org.opencontainers.image.description="Unified model lifecycle, inference, and resource management"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="ModelOps Team"
LABEL org.opencontainers.image.source="https://github.com/company/model-ops-coordinator"

# Default command
CMD ["python", "app.py"]

# Development stage - Includes dev tools and test dependencies
FROM production as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    ruff \
    mypy \
    black

# Install additional dev tools
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    strace \
    && rm -rf /var/lib/apt/lists/*

# Copy test files
COPY tests/ /app/tests/

# Switch back to moc user
USER moc

# Override command for development
CMD ["python", "app.py", "--dev"]

# Debug stage - For troubleshooting and debugging
FROM development as debug

USER root

# Install debug tools
RUN pip install --no-cache-dir \
    ipdb \
    memory-profiler \
    py-spy

# Install system debug tools
RUN apt-get update && apt-get install -y \
    gdb \
    valgrind \
    net-tools \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

USER moc

# Set debug environment
ENV MOC_LOG_LEVEL=DEBUG
ENV PYTHONDEBUG=1

CMD ["python", "-X", "dev", "app.py"]

# Test stage - For running tests in CI/CD
FROM development as test

USER root

# Copy all test files; conditionally include pytest.ini if present
COPY tests/ /app/tests/
# Use a build arg to optionally include pytest.ini without causing build failures when absent
ARG INCLUDE_PYTEST_INI=false
COPY pytest.ini /app/ 
RUN if [ "$INCLUDE_PYTEST_INI" = "false" ]; then rm -f /app/pytest.ini 2>/dev/null || true; fi

USER moc

# Run tests by default
CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]