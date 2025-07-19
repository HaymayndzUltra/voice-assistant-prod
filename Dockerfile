# --- Stage 1: Builder ---
FROM ai_system/base:1.0
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 2: Final Image ---
FROM ai_system/base:1.0
WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Project-specific utilities
COPY main_pc_code/utils/ /app/utils/
COPY common/ /app/common/
COPY scripts/ /app/scripts/
COPY main_pc_code/agents/ /app/main_pc_code/agents/
COPY main_pc_code/FORMAINPC/ /app/main_pc_code/FORMAINPC/
COPY main_pc_code/services/ /app/main_pc_code/services/
COPY main_pc_code/config/ /app/main_pc_code/config/
COPY main_pc_code/src/ /app/main_pc_code/src/

RUN chmod +x /app/scripts/run_group.sh

# Security and metadata labels
LABEL security_level="hardened" \
      user="non-root" \
      work_package="WP-02"
