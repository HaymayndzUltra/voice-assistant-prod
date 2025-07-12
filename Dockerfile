# --- Stage 1: Builder ---
# Use a full Python image to build dependencies
FROM python:3.11-slim as builder

# Set the working directory
WORKDIR /app

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only the requirements file to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies into the virtual environment
RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Final Image ---
# Use a slim image for the final application
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Set the PATH to use the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# --- FINAL & VERIFIED COPY LIST ---
# This list is based on the definitive dependency trace.
COPY utils/ /app/utils/
COPY common/ /app/common/
COPY common_utils/ /app/common_utils/
COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY main_pc_code/agents/ /app/main_pc_code/agents/
COPY main_pc_code/FORMAINPC/ /app/main_pc_code/FORMAINPC/
COPY main_pc_code/services/ /app/main_pc_code/services/
COPY main_pc_code/config/ /app/main_pc_code/config/

# Make the startup script executable
RUN chmod +x /app/scripts/run_group.sh 