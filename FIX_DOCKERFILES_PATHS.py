#!/usr/bin/env python3
"""
Fix all Dockerfile paths based on ACTUAL directory structure
"""

import os
from pathlib import Path

# ACTUAL directory structure based on verification
ACTUAL_SERVICES = {
    # Core services in root
    "model_ops_coordinator": {
        "path": "/workspace/model_ops_coordinator",
        "entry": "app.py",
        "has_pyproject": True
    },
    "real_time_audio_pipeline": {
        "path": "/workspace/real_time_audio_pipeline", 
        "entry": "app.py",
        "has_pyproject": True
    },
    "affective_processing_center": {
        "path": "/workspace/affective_processing_center",
        "entry": "app.py", 
        "has_pyproject": True
    },
    "unified_observability_center": {
        "path": "/workspace/unified_observability_center",
        "entry": "app.py",
        "has_pyproject": True
    },
    "memory_fusion_hub": {
        "path": "/workspace/memory_fusion_hub",
        "entry": "app.py",
        "has_pyproject": True
    },
    
    # Services under /workspace/services/
    "self_healing_supervisor": {
        "path": "/workspace/services/self_healing_supervisor",
        "entry": "supervisor.py",  # NOT app.py!
        "has_pyproject": True
    },
    "central_error_bus": {
        "path": "/workspace/services/central_error_bus",
        "entry": "error_bus.py",  # NOT app.py!
        "has_pyproject": True
    },
}

def fix_core_dockerfiles():
    """Fix the 6 core service Dockerfiles with correct paths"""
    
    # 1. Fix model_ops_coordinator/Dockerfile.optimized
    dockerfile = f"""# syntax=docker/dockerfile:1.5
# ModelOpsCoordinator - GPU-heavy LLM service (MainPC/4090)
FROM ghcr.io/haymayndzultra/family-llm-cu121:20250812-latest AS base

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \\
    TORCH_CUDA_ARCH_LIST="8.9" \\
    GPU_VISIBLE_DEVICES=${{GPU_VISIBLE_DEVICES:-0}}

WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${{MACHINE}}.json /etc/machine-profile.json

# Builder stage
FROM base AS builder
COPY model_ops_coordinator/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY model_ops_coordinator/ ./model_ops_coordinator
COPY common/ ./common

USER appuser

# Health check on port 8212
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -sf http://localhost:8212/health || exit 1

# Expose service and health ports
EXPOSE 7212 8212

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "model_ops_coordinator.app"]
"""
    
    with open("/workspace/model_ops_coordinator/Dockerfile.optimized", "w") as f:
        f.write(dockerfile)
    print("✅ Fixed model_ops_coordinator/Dockerfile.optimized")
    
    # 2. Fix real_time_audio_pipeline/Dockerfile.optimized
    dockerfile = f"""# syntax=docker/dockerfile:1.5
# RealTimeAudioPipeline - GPU/Audio service (Both)
FROM ghcr.io/haymayndzultra/family-torch-cu121:20250812-latest AS base

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \\
    TORCH_CUDA_ARCH_LIST="8.9" \\
    GPU_VISIBLE_DEVICES=${{GPU_VISIBLE_DEVICES:-0}} \\
    PULSE_SERVER=/run/pulse/native \\
    AUDIO_BACKEND=${{AUDIO_BACKEND:-alsa}}

WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${{MACHINE}}.json /etc/machine-profile.json

# Builder stage
FROM base AS builder
COPY real_time_audio_pipeline/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY real_time_audio_pipeline/ ./real_time_audio_pipeline
COPY common/ ./common

USER appuser

# Health check on port 6557
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -sf http://localhost:6557/health || exit 1

# Expose service and health ports  
EXPOSE 5557 6557

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "real_time_audio_pipeline.app"]
"""
    
    with open("/workspace/real_time_audio_pipeline/Dockerfile.optimized", "w") as f:
        f.write(dockerfile)
    print("✅ Fixed real_time_audio_pipeline/Dockerfile.optimized")
    
    # 3. Fix affective_processing_center/Dockerfile.optimized
    dockerfile = f"""# syntax=docker/dockerfile:1.5
# AffectiveProcessingCenter - GPU service (MainPC/4090)
FROM ghcr.io/haymayndzultra/family-torch-cu121:20250812-latest AS base

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \\
    TORCH_CUDA_ARCH_LIST="8.9" \\
    GPU_VISIBLE_DEVICES=${{GPU_VISIBLE_DEVICES:-0}}

WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${{MACHINE}}.json /etc/machine-profile.json

# Builder stage
FROM base AS builder
COPY affective_processing_center/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY affective_processing_center/ ./affective_processing_center
COPY common/ ./common

USER appuser

# Health check on port 6560
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -sf http://localhost:6560/health || exit 1

# Expose service and health ports
EXPOSE 5560 6560

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "affective_processing_center.app"]
"""
    
    with open("/workspace/affective_processing_center/Dockerfile.optimized", "w") as f:
        f.write(dockerfile)
    print("✅ Fixed affective_processing_center/Dockerfile.optimized")
    
    # 4. Fix unified_observability_center/Dockerfile.optimized
    dockerfile = f"""# syntax=docker/dockerfile:1.5
# UnifiedObservabilityCenter - CPU/Web service (Both)
FROM ghcr.io/haymayndzultra/family-web:20250812-latest AS base

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${{MACHINE}}.json /etc/machine-profile.json

# Builder stage
FROM base AS builder
COPY unified_observability_center/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY unified_observability_center/ ./unified_observability_center
COPY common/ ./common

USER appuser

# Health check on port 9110
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -sf http://localhost:9110/health || exit 1

# Expose service and health ports
EXPOSE 9100 9110

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "unified_observability_center.app"]
"""
    
    with open("/workspace/unified_observability_center/Dockerfile.optimized", "w") as f:
        f.write(dockerfile)
    print("✅ Fixed unified_observability_center/Dockerfile.optimized")
    
    # 5. Fix services/self_healing_supervisor/Dockerfile.optimized
    dockerfile = f"""# syntax=docker/dockerfile:1.5
# SelfHealingSupervisor - CPU/Docker service (Both)
FROM ghcr.io/haymayndzultra/base-cpu-pydeps:20250812-latest AS base

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${{MACHINE}}.json /etc/machine-profile.json

# Builder stage
FROM base AS builder
COPY services/self_healing_supervisor/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY services/self_healing_supervisor/ ./self_healing_supervisor
COPY common/ ./common

USER appuser

# Health check on port 9008
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -sf http://localhost:9008/health || exit 1

# Expose service and health ports
EXPOSE 7009 9008

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "self_healing_supervisor/supervisor.py"]
"""
    
    with open("/workspace/services/self_healing_supervisor/Dockerfile.optimized", "w") as f:
        f.write(dockerfile)
    print("✅ Fixed services/self_healing_supervisor/Dockerfile.optimized")
    
    # 6. Fix services/central_error_bus/Dockerfile.optimized
    dockerfile = f"""# syntax=docker/dockerfile:1.5
# CentralErrorBus - CPU/Web service (PC2/3060)
FROM ghcr.io/haymayndzultra/family-web:20250812-latest AS base

ARG MACHINE=pc2
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${{MACHINE}}.json /etc/machine-profile.json

# Builder stage
FROM base AS builder
COPY services/central_error_bus/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY services/central_error_bus/ ./central_error_bus
COPY common/ ./common

USER appuser

# Health check on port 8150
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -sf http://localhost:8150/health || exit 1

# Expose service and health ports
EXPOSE 7150 8150

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "central_error_bus/error_bus.py"]
"""
    
    with open("/workspace/services/central_error_bus/Dockerfile.optimized", "w") as f:
        f.write(dockerfile)
    print("✅ Fixed services/central_error_bus/Dockerfile.optimized")
    
    # 7. Fix memory_fusion_hub/Dockerfile.optimized
    dockerfile = f"""# syntax=docker/dockerfile:1.5
# MemoryFusionHub - CPU (GPU-aware) service (Both)
FROM ghcr.io/haymayndzultra/base-cpu-pydeps:20250812-latest AS base

ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy machine profile
COPY config/machine-profiles/${{MACHINE}}.json /etc/machine-profile.json

# Builder stage
FROM base AS builder
COPY memory_fusion_hub/requirements.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --no-cache-dir -r requirements.txt || true

# Runtime stage
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY memory_fusion_hub/ ./memory_fusion_hub
COPY common/ ./common

USER appuser

# Health check on port 6713
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -sf http://localhost:6713/health || exit 1

# Expose service and health ports
EXPOSE 5713 6713

ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "-m", "memory_fusion_hub.app"]
"""
    
    with open("/workspace/memory_fusion_hub/Dockerfile.optimized", "w") as f:
        f.write(dockerfile)
    print("✅ Fixed memory_fusion_hub/Dockerfile.optimized")
    
def remove_duplicate_dockerfiles():
    """Remove Dockerfiles from wrong directories"""
    
    duplicates = [
        "/workspace/modelops_coordinator/Dockerfile.optimized",
        "/workspace/realtimeaudio_pipeline/Dockerfile.optimized", 
        "/workspace/affectiveprocessing_center/Dockerfile.optimized",
        "/workspace/services/selfhealing_supervisor/Dockerfile.optimized",
        "/workspace/services/centralerror_bus/Dockerfile.optimized",
        "/workspace/services/unifiedobservability_center/Dockerfile.optimized"
    ]
    
    for path in duplicates:
        if os.path.exists(path):
            os.remove(path)
            print(f"❌ Removed duplicate: {path}")

if __name__ == "__main__":
    print("=" * 60)
    print("FIXING DOCKERFILES WITH CORRECT PATHS")
    print("=" * 60)
    
    # Fix core Dockerfiles
    fix_core_dockerfiles()
    
    # Remove duplicates
    remove_duplicate_dockerfiles()
    
    print("\n" + "=" * 60)
    print("✅ DOCKERFILES FIXED!")
    print("=" * 60)
    print("\nCorrect locations:")
    print("  - /workspace/model_ops_coordinator/Dockerfile.optimized")
    print("  - /workspace/real_time_audio_pipeline/Dockerfile.optimized")
    print("  - /workspace/affective_processing_center/Dockerfile.optimized")
    print("  - /workspace/unified_observability_center/Dockerfile.optimized")
    print("  - /workspace/memory_fusion_hub/Dockerfile.optimized")
    print("  - /workspace/services/self_healing_supervisor/Dockerfile.optimized")
    print("  - /workspace/services/central_error_bus/Dockerfile.optimized")
    print("\nCorrect entry points:")
    print("  - model_ops_coordinator.app")
    print("  - real_time_audio_pipeline.app")
    print("  - affective_processing_center.app")
    print("  - unified_observability_center.app")
    print("  - memory_fusion_hub.app")
    print("  - self_healing_supervisor/supervisor.py")
    print("  - central_error_bus/error_bus.py")