# --- Stage 1: Builder ---
FROM python:3.11-slim as builder
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install core dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir numpy requests pyyaml pyzmq redis flask

# Install test dependencies
RUN pip install --no-cache-dir pytest pytest-cov pytest-mock

# --- Stage 2: Final Image ---
FROM python:3.11-slim
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Copy essential directories
COPY utils /app/utils/
COPY common /app/common/
COPY src /app/src/
COPY scripts /app/scripts/
COPY main_pc_code/agents /app/main_pc_code/agents/
COPY main_pc_code/FORMAINPC /app/main_pc_code/FORMAINPC/
COPY main_pc_code/services /app/main_pc_code/services/
COPY main_pc_code/config /app/main_pc_code/config/

# Make the run_group.sh script executable
RUN chmod +x /app/scripts/run_group.sh