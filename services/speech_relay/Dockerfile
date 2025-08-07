FROM python:3.10-slim-bullseye
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
WORKDIR /app
CMD ["python3","relay.py"]
