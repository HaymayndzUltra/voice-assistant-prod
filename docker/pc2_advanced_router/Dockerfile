FROM ghcr.io/haymayndzultra/pc2-base-dl:latest AS base
WORKDIR /app
COPY . /app
COPY requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
ENV PYTHONPATH=/app
HEALTHCHECK CMD curl -f http://localhost:8120/health || exit 1
CMD ["python", "-m", "pc2_code.agents.advanced_router"]
