FROM python:3.10-slim-bullseye
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
COPY . /app
WORKDIR /app
ENV PORT=5596
CMD ["uvicorn", "proxy:app", "--host", "0.0.0.0", "--port", "5596"]
