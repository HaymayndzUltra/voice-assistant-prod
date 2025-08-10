ARG ORG=haymayndzultra
ARG BASE_TAG=latest
FROM ghcr.io/${ORG}/family-torch-cu121:${BASE_TAG}

# We need elevated permissions for build-time compiles and file cleanup
USER root

# Optional: include llama-cpp build (heavy). Control via build-arg.
ARG INCLUDE_LLAMA_CPP=0

COPY docker/base/requirements.family-llm-cu121.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    if [ "$INCLUDE_LLAMA_CPP" = "1" ]; then \
        apt-get update && apt-get install -y --no-install-recommends cmake g++ && \
        CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install --no-binary=:all: llama-cpp-python==0.2.86 && \
        apt-get purge -y --auto-remove cmake g++ && rm -rf /var/lib/apt/lists/*; \
    fi && \
    rm -f /tmp/requirements.txt || true

# Drop privileges for runtime
USER appuser