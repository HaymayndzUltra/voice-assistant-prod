FROM python:3.10-slim

WORKDIR /app

COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY .. /app/memory_fusion_hub
WORKDIR /app/memory_fusion_hub/proxy

ENV TARGET_MFH_HOST=mfh
ENV TARGET_MFH_PORT=5714
ENV CACHE_TTL_SEC=60
ENV PROXY_GRPC_PORT=5715
ENV PROXY_METRICS_PORT=8082

EXPOSE 5715 8082

CMD ["python", "proxy_server.py"]

