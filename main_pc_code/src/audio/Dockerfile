FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for audio processing and security
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    portaudio19-dev \
    python3-dev \
    gcc \
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
CMD ["python", "-u", "src/audio/fused_audio_preprocessor.py"] 