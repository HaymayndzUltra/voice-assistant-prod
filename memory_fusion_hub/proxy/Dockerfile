FROM python:3.11-slim

WORKDIR /app

# Copy requirements from parent directory during build
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the proxy server code
COPY proxy_server.py /app/proxy_server.py

# Set environment variables
ENV TARGET_MFH_HOST=mfh
ENV TARGET_MFH_PORT=5714
ENV CACHE_TTL_SEC=60
ENV PROXY_GRPC_PORT=5715
ENV PROXY_METRICS_PORT=8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8082/health', timeout=5)" || exit 1

EXPOSE 5715 8082

CMD ["python", "proxy_server.py"]

