FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY docker/language_stack/requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt

# Install PyTorch CPU-only for ModelManagerAgent
RUN pip install --no-cache-dir torch==2.2.0+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html

# Install build dependencies for llama-cpp-python
RUN pip install --no-cache-dir scikit-build-core[pyproject]

# Install llama-cpp-python for GGUF model support (Phase 5 fix)
RUN pip install --no-cache-dir "llama-cpp-python==0.2.58" \
    && python -c "import llama_cpp; print('llama-cpp-python installed successfully')"

# Copy source code
COPY main_pc_code/  /app/main_pc_code/
COPY common/        /app/common/
COPY common_utils/  /app/common_utils/
COPY remote_api_adapter/ /app/remote_api_adapter/

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

# Default command (will be overridden by docker-compose)
CMD ["python", "-m", "main_pc_code.agents.nlu_agent"]
