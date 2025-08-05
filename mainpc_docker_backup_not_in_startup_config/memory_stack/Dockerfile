FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY docker/memory_stack/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/

WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# default cmd = MemoryClient
CMD ["python","-m","main_pc_code.agents.memory_client"]
