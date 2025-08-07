FROM python:3.10-slim-bullseye
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
WORKDIR /app
VOLUME /var/run/docker.sock
CMD ["python3","supervisor.py"]
