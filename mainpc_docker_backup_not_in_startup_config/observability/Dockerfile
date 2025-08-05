FROM python:3.10-slim

# System dependencies
RUN apt-get update && apt-get install -y \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Create symlink for python
RUN ln -s /usr/bin/python3 /usr/bin/python

# --- python deps -------------------------------------------------------------
COPY docker/observability/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# --- app code ----------------------------------------------------------------
COPY main_pc_code/            /app/main_pc_code/
COPY common/                  /app/common/
COPY common_utils/            /app/common_utils/
COPY phase1_implementation/   /app/phase1_implementation/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

CMD ["python","-m","phase1_implementation.consolidated_agents.observability_hub.backup_observability_hub.observability_hub"]
