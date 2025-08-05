FROM python:3.10-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl gcc build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY pc2_code /app/pc2_code
COPY common /app/common
COPY common_utils /app/common_utils
WORKDIR /app
ENV PYTHONPATH=/app
HEALTHCHECK CMD curl -f http://localhost:8115/health || exit 1
CMD ["python", "-m", "pc2_code.agents.task_scheduler"]