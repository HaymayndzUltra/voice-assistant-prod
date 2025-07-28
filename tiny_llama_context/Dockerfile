# TinyLlama Service Container
# Placeholder Dockerfile - replace with actual TinyLlama implementation

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN addgroup --system llama && adduser --system --ingroup llama llama
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch transformers

# Copy placeholder service
COPY . /app/

# Use non-root user
USER llama

# Health check endpoint
EXPOSE 8080

# Simple health check server
CMD ["python", "-c", "import http.server; import socketserver; handler = http.server.SimpleHTTPRequestHandler; handler.extensions_map.update({'.js': 'application/javascript', '.html': 'text/html'}); httpd = socketserver.TCPServer(('', 8080), handler); print('TinyLlama service running on port 8080'); httpd.serve_forever()"] 