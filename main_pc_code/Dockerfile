# Stage 1: Builder stage
FROM ubuntu:22.04 AS builder

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Add universe repository and install system dependencies
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository universe && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-dev \
    python3.10-venv \
    python3-pip \
    build-essential \
    portaudio19-dev \
    libportaudio2 \
    libasound2-dev \
    pkg-config \
    libblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-103 \
    libgtk-3-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    cmake \
    libx11-dev \
    libxext-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Build and install dlib from source
RUN git clone https://github.com/davisking/dlib.git && \
    cd dlib && \
    git checkout v19.24.2 && \
    python3 setup.py install --no USE_AVX_INSTRUCTIONS

# Install Python packages with specific handling for problematic packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir numpy scipy && \
    pip install --no-cache-dir pyaudio==0.2.13 && \
    pip install --no-cache-dir face-recognition-models && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Add universe repository and install runtime dependencies
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    add-apt-repository universe && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.10 \
    libportaudio2 \
    libhdf5-103 \
    libgtk-3-0 \
    ffmpeg \
    libv4l-0 \
    libxvidcore4 \
    libx264-dev \
    libjpeg8 \
    libpng16-16 \
    libtiff5 \
    libx11-6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . /app
WORKDIR /app

# Command to run the application
CMD ["python3", "main.py"]
