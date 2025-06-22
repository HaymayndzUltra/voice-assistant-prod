FROM python:3.10

# Install system dependencies in a separate layer
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libportaudio2 \
    portaudio19-dev \
    python3-pyaudio \
    libasound-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt --verbose

# Copy application code
COPY . .

# Command to run the application
CMD ["python", "main.py"] 