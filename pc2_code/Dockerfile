FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser

# Set working directory
WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data/memory /app/cache /app/models

# Set permissions
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Default command (can be overridden in docker-compose)
CMD ["echo", "PC2 Container started. Specify a command in docker-compose to run an agent."] 