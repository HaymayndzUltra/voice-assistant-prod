FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY docker/emotion_system/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/
WORKDIR /app
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# default entrypoint = EmotionEngine
CMD ["python","-m","main_pc_code.agents.emotion_engine"]
