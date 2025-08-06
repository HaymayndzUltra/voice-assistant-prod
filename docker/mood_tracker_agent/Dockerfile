# Optimized Dockerfile - slim base image with pip cache disabled
FROM python:3.10-slim-bullseye

WORKDIR /app

RUN apt-get update && apt-get install \
    && rm -rf /var/lib/apt/lists/* -y curl && rm -rf /var/lib/apt/lists/*

COPY docker/mood_tracker_agent/requirements.txt .
RUN pip install --disable-pip-version-check --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

RUN mkdir -p logs data

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${HEALTH_PORT:-6705}/health || exit 1

EXPOSE 5705 6705

CMD ["python", "main_pc_code/agents/mood_tracker_agent.py"]
