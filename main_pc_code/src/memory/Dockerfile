FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for PostgreSQL and security
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libpq-dev \
    libsodium-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Default command
CMD ["python", "-u", "src/memory/memory_orchestrator.py"] 