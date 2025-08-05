FROM python:3.10-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl gcc build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY main_pc_code /app/main_pc_code
COPY common /app/common
COPY common_utils /app/common_utils
WORKDIR /app
ENV PYTHONPATH=/app
HEALTHCHECK CMD curl -f http://localhost:6596/health || exit 1
CMD ["python", "-m", "main_pc_code.agents.face_recognition_agent"]