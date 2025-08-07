FROM python:3.10-slim-bullseye
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
WORKDIR /app
ENV OBS_HUB=http://localhost:9000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]
