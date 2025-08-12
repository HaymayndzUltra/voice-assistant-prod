# syntax=docker/dockerfile:1.5
# Family LLM CUDA 12.1 - For LLM/language model services
FROM ghcr.io/haymayndzultra/family-torch-cu121:20250812-latest

USER root

# Install LLM-specific dependencies (with pip cache mount)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir \
        transformers==4.36.2 \
        accelerate==0.25.0 \
        bitsandbytes==0.41.3 \
        sentencepiece==0.1.99 \
        tokenizers==0.15.0 \
        peft==0.7.1 \
        datasets==2.16.1 \
        evaluate==0.4.1 \
        langchain==0.1.0 \
        openai==1.6.1 \
        anthropic==0.8.1 \
        tiktoken==0.5.2

# Install vLLM for optimized inference (optional; with cache mount)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir vllm==0.2.7 || echo "vLLM installation optional"

# Install llama-cpp-python as binary-only and optional to avoid toolchain
# (no CMAKE_ARGS to prevent source builds)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --only-binary=:all: llama-cpp-python==0.2.28 || echo "llama-cpp optional"

USER appuser
WORKDIR /app
