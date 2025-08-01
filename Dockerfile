# Multi-stage Docker build for AI System Monorepo
# Optimized for production deployment with security and performance

# =============================================================================
# Base image with Python and system dependencies
# =============================================================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 aiuser && \
    useradd --uid 1000 --gid aiuser --shell /bin/bash --create-home aiuser

# =============================================================================
# Builder stage for dependencies
# =============================================================================
FROM base as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./
COPY requirements*.txt ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install hatch && \
    pip install -e .[all]

# =============================================================================
# Development stage
# =============================================================================
FROM builder as development

# Install development tools
RUN pip install -e .[dev,security,performance]

# Copy source code
COPY --chown=aiuser:aiuser . .

# Switch to non-root user
USER aiuser

# Expose ports
EXPOSE 8000 8001 8002

# Default command for development
CMD ["python", "-m", "main_pc_code.cli"]

# =============================================================================
# Production base
# =============================================================================
FROM base as production-base

# Install only production dependencies
WORKDIR /app

# Copy requirements from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# =============================================================================
# Production stage
# =============================================================================
FROM production-base as production

# Copy application code
COPY --chown=aiuser:aiuser main_pc_code/ ./main_pc_code/
COPY --chown=aiuser:aiuser pc2_code/ ./pc2_code/
COPY --chown=aiuser:aiuser common/ ./common/
COPY --chown=aiuser:aiuser common_utils/ ./common_utils/
COPY --chown=aiuser:aiuser events/ ./events/
COPY --chown=aiuser:aiuser pyproject.toml ./
COPY --chown=aiuser:aiuser config/startup_config.yaml ./

# Create necessary directories
RUN mkdir -p logs data backups && \
    chown -R aiuser:aiuser logs data backups

# Switch to non-root user
USER aiuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose ports
EXPOSE 8000 8001 8002

# Set resource limits
ENV PYTHONMALLOC=malloc \
    MALLOC_ARENA_MAX=2

# Default production command
CMD ["python", "-m", "main_pc_code.cli", "--mode", "production"]

# =============================================================================
# GPU-enabled stage for ML workloads
# =============================================================================
FROM nvidia/cuda:12.1-runtime-ubuntu22.04 as gpu-production

# Install Python
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Link python
RUN ln -s /usr/bin/python3.11 /usr/bin/python

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CUDA_VISIBLE_DEVICES=0

# Create user
RUN groupadd --gid 1000 aiuser && \
    useradd --uid 1000 --gid aiuser --shell /bin/bash --create-home aiuser

# Set working directory
WORKDIR /app

# Install Python dependencies with GPU support
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .[gpu,performance,monitoring]

# Copy application code
COPY --chown=aiuser:aiuser main_pc_code/ ./main_pc_code/
COPY --chown=aiuser:aiuser pc2_code/ ./pc2_code/
COPY --chown=aiuser:aiuser common/ ./common/
COPY --chown=aiuser:aiuser common_utils/ ./common_utils/
COPY --chown=aiuser:aiuser events/ ./events/
COPY --chown=aiuser:aiuser config/startup_config.yaml ./

# Create directories
RUN mkdir -p logs data backups && \
    chown -R aiuser:aiuser logs data backups

# Switch to non-root user
USER aiuser

# GPU health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import torch; assert torch.cuda.is_available()" || exit 1

# Expose ports
EXPOSE 8000 8001 8002

# GPU-optimized command
CMD ["python", "-m", "main_pc_code.cli", "--mode", "gpu-production"]

# =============================================================================
# Security scanning stage
# =============================================================================
FROM production as security-scan

# Install security tools
USER root
RUN pip install bandit safety semgrep

# Copy security configuration
COPY .bandit ./
COPY pyproject.toml ./

# Run security scans
RUN bandit -r main_pc_code pc2_code common -f json -o security-report.json || true
RUN safety check --json --output safety-report.json || true

# Switch back to aiuser
USER aiuser

# =============================================================================
# Testing stage
# =============================================================================
FROM development as testing

# Install test dependencies
RUN pip install -e .[dev,all]

# Copy test files
COPY --chown=aiuser:aiuser tests/ ./tests/

# Run tests
RUN python -m pytest tests/ --cov=main_pc_code --cov=pc2_code --cov=common --cov=events \
    --cov-report=html --cov-report=xml --cov-report=term

# =============================================================================
# Documentation stage
# =============================================================================
FROM base as docs

# Install documentation dependencies
RUN pip install -e .[docs]

# Copy source and docs
COPY --chown=aiuser:aiuser . .

# Switch to non-root user
USER aiuser

# Build documentation
RUN mkdocs build

# Expose documentation port
EXPOSE 8080

# Serve documentation
CMD ["mkdocs", "serve", "--dev-addr=0.0.0.0:8080"] 