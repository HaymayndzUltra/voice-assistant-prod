# Docker Migration Actionable Plan
Version: 1.0
Status: READY FOR EXECUTION
Generated: 2025-01-12
Confidence: 85%

## Executive Summary
Migration of ~50 services across 8 consolidation hubs to optimized Docker architecture with 55-70% size reduction through proper base image hierarchy and multi-stage builds.

## Implementation Plan

### PHASE 0: SETUP & PROTOCOL (READ FIRST)

**Objective:** Establish foundation and validate prerequisites

**Steps:**
1. Verify GHCR authentication: `docker login ghcr.io -u haymayndzultra`
2. Install Docker buildx: `docker buildx install`
3. Create builder instance: `docker buildx create --name migration-builder --use`
4. Validate base image structure in `/docker/base-images/`
5. Create machine profiles for MainPC/PC2

**Concluding Step: Phase Completion Protocol**
```bash
python3 todo_manager.py show docker_migration_20250112
python3 todo_manager.py done docker_migration_20250112 0
```

IMPORTANT NOTE: This phase establishes critical infrastructure. All subsequent phases depend on successful GHCR authentication and buildx configuration. Failure here blocks all migration activities.

### PHASE 1: BUILD FOUNDATIONAL BASE IMAGES

**Objective:** Create hierarchical base image family

**Explanations:** Implement the base image hierarchy as defined in the Docker Architecture Blueprint. This creates the foundation for all service images with proper layer sharing.

**Steps:**
1. Build base-python:3.11-slim
```bash
cd /workspace/docker/base-images/base-python
docker buildx build --platform linux/amd64 \
  --cache-to type=registry,ref=ghcr.io/haymayndzultra/cache:base-python \
  --cache-from type=registry,ref=ghcr.io/haymayndzultra/cache:base-python \
  -t ghcr.io/haymayndzultra/base-python:3.11-slim-$(date +%Y%m%d) \
  --push .
```

2. Build base-utils layer
```bash
cd /workspace/docker/base-images/base-utils
docker buildx build --platform linux/amd64 \
  --cache-to type=registry,ref=ghcr.io/haymayndzultra/cache:base-utils \
  --cache-from type=registry,ref=ghcr.io/haymayndzultra/cache:base-utils \
  -t ghcr.io/haymayndzultra/base-utils:$(date +%Y%m%d) \
  --push .
```

3. Build CPU and GPU base variants
```bash
# CPU variant
cd /workspace/docker/base-images/base-cpu-pydeps
docker buildx build --platform linux/amd64 \
  -t ghcr.io/haymayndzultra/base-cpu-pydeps:$(date +%Y%m%d) \
  --push .

# GPU variant with CUDA 12.1
cd /workspace/docker/base-images/base-gpu-cu121
docker buildx build --platform linux/amd64 \
  --build-arg CUDA_VERSION=12.1.1 \
  -t ghcr.io/haymayndzultra/base-gpu-cu121:$(date +%Y%m%d) \
  --push .
```

**Concluding Step: Phase Completion Protocol**
```bash
python3 todo_manager.py show docker_migration_20250112
python3 todo_manager.py done docker_migration_20250112 1
```

IMPORTANT NOTE: Base images must be pushed to GHCR before any service migration begins. Verify all images are accessible via `docker pull ghcr.io/haymayndzultra/base-*` before proceeding.

### PHASE 2: MIGRATE CPU-ONLY SERVICES (MEMORY FUSION HUB)

**Objective:** Pilot migration with simplest CPU-only service

**Explanations:** Memory Fusion Hub is the ideal pilot service - CPU-only, well-structured, with existing optimized Dockerfile. This validates the migration process before tackling complex GPU services.

**Steps:**
1. Update memory_fusion_hub/Dockerfile.optimized
```dockerfile
FROM ghcr.io/haymayndzultra/base-cpu-pydeps:20250112 AS base
ARG MACHINE=pc2
ENV PYTHONUNBUFFERED=1
WORKDIR /app

FROM base AS builder
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --require-hashes -r requirements.txt

FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
USER appuser
HEALTHCHECK CMD curl -sf http://localhost:6713/health || exit 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["python", "app.py"]
```

2. Build and push to GHCR
```bash
cd /workspace/memory_fusion_hub
docker buildx build --platform linux/amd64 \
  --cache-to type=registry,ref=ghcr.io/haymayndzultra/cache:memory-fusion \
  --cache-from type=registry,ref=ghcr.io/haymayndzultra/cache:memory-fusion \
  -t ghcr.io/haymayndzultra/memory-fusion-hub:$(date +%Y%m%d)-$(git rev-parse --short HEAD) \
  --push -f Dockerfile.optimized .
```

3. Update docker-compose.yml to use GHCR image
4. Test deployment: `docker-compose up -d memory_fusion_hub`
5. Validate health: `curl http://localhost:6713/health`

**Concluding Step: Phase Completion Protocol**
```bash
python3 todo_manager.py show docker_migration_20250112
python3 todo_manager.py done docker_migration_20250112 2
```

IMPORTANT NOTE: This phase proves the migration pattern. Success metrics: image size < 200MB, health check passing, layer cache hit rate > 70%. Document any issues for GPU service migration.

### PHASE 3: IMPLEMENT MACHINE PROFILES

**Objective:** Configure hardware-aware defaults for MainPC/PC2

**Explanations:** Machine profiles enable optimal resource allocation based on hardware capabilities (4090 vs 3060), ensuring services run efficiently on their target machines.

**Steps:**
1. Create /workspace/docker/machine-profiles/mainpc.json
```json
{
  "GPU_VISIBLE_DEVICES": "0",
  "TORCH_CUDA_ALLOC_CONF": "max_split_size_mb:64",
  "OMP_NUM_THREADS": "16",
  "UVICORN_WORKERS": "32",
  "MODEL_EVICT_THRESHOLD_PCT": "90",
  "CUDA_ARCH": "8.9"
}
```

2. Create /workspace/docker/machine-profiles/pc2.json
```json
{
  "GPU_VISIBLE_DEVICES": "0",
  "TORCH_CUDA_ALLOC_CONF": "max_split_size_mb:32",
  "OMP_NUM_THREADS": "4",
  "UVICORN_WORKERS": "8",
  "MODEL_EVICT_THRESHOLD_PCT": "70",
  "CUDA_ARCH": "8.6"
}
```

3. Update build scripts to inject profiles
```bash
#!/bin/bash
MACHINE=${1:-mainpc}
docker buildx build --build-arg MACHINE=$MACHINE \
  --build-arg MACHINE_PROFILE=$(cat /workspace/docker/machine-profiles/$MACHINE.json) \
  ...
```

**Concluding Step: Phase Completion Protocol**
```bash
python3 todo_manager.py show docker_migration_20250112
python3 todo_manager.py done docker_migration_20250112 3
```

IMPORTANT NOTE: Machine profiles are critical for GPU services. Each GPU service MUST specify target machine during build. Incorrect profiles cause OOM errors or underutilization.

### PHASE 4: MIGRATE GPU SERVICES (MODEL OPS COORDINATOR)

**Objective:** Migrate primary GPU service with CUDA optimization

**Explanations:** Model Ops Coordinator is the most complex GPU service. Successful migration validates GPU layer sharing, CUDA compatibility, and hardware-aware optimization.

**Steps:**
1. Build GPU family images
```bash
# Torch family for ML models
cd /workspace/docker/families/family-torch-cu121
docker buildx build --platform linux/amd64 \
  --build-arg TORCH_CUDA_ARCH_LIST="8.9;8.6" \
  -t ghcr.io/haymayndzultra/family-torch-cu121:$(date +%Y%m%d) \
  --push .
```

2. Update model_ops_coordinator/Dockerfile.optimized
```dockerfile
FROM ghcr.io/haymayndzultra/family-torch-cu121:20250112 AS base
ARG MACHINE=mainpc
ARG MACHINE_PROFILE
ENV MACHINE_PROFILE=$MACHINE_PROFILE
# Parse and set environment from profile
RUN echo "$MACHINE_PROFILE" | python -c "import json,sys,os; \
    d=json.load(sys.stdin); \
    [print(f'export {k}={v}') for k,v in d.items()]" > /env.sh && \
    chmod +x /env.sh
```

3. Build with machine-specific optimization
```bash
cd /workspace/model_ops_coordinator
# For MainPC (4090)
docker buildx build --platform linux/amd64 \
  --build-arg MACHINE=mainpc \
  --build-arg MACHINE_PROFILE="$(cat /workspace/docker/machine-profiles/mainpc.json)" \
  -t ghcr.io/haymayndzultra/model-ops-mainpc:$(date +%Y%m%d)-$(git rev-parse --short HEAD) \
  --push -f Dockerfile.optimized .
```

4. Validate GPU access
```bash
docker run --rm --gpus all ghcr.io/haymayndzultra/model-ops-mainpc:latest \
  python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

**Concluding Step: Phase Completion Protocol**
```bash
python3 todo_manager.py show docker_migration_20250112
python3 todo_manager.py done docker_migration_20250112 4
```

IMPORTANT NOTE: GPU service migration requires NVIDIA Container Toolkit. Verify CUDA versions match (12.1). Monitor VRAM usage during first deployment. Rollback if OOM occurs.

### PHASE 5: SETUP CI/CD AUTOMATION

**Objective:** Automate build and deployment pipeline

**Explanations:** GitHub Actions matrix builds ensure consistent, reproducible deployments across all services and machines, eliminating manual build processes.

**Steps:**
1. Create .github/workflows/docker-build.yml
```yaml
name: Docker Build Matrix
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [memory_fusion_hub, model_ops_coordinator, affective_processing_center]
        machine: [mainpc, pc2]
    steps:
      - uses: actions/checkout@v3
      - uses: docker/setup-buildx-action@v2
      - uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: haymayndzultra
          password: ${{ secrets.GHCR_TOKEN }}
      - name: Build and push
        run: |
          docker buildx build \
            --platform linux/amd64 \
            --build-arg MACHINE=${{ matrix.machine }} \
            --cache-to type=registry,ref=ghcr.io/haymayndzultra/cache:${{ matrix.service }} \
            --cache-from type=registry,ref=ghcr.io/haymayndzultra/cache:${{ matrix.service }} \
            -t ghcr.io/haymayndzultra/${{ matrix.service }}-${{ matrix.machine }}:$(date +%Y%m%d)-${{ github.sha }} \
            -t ghcr.io/haymayndzultra/${{ matrix.service }}-${{ matrix.machine }}:latest \
            --push \
            -f ${{ matrix.service }}/Dockerfile.optimized \
            ${{ matrix.service }}
```

2. Configure repository secrets
3. Test workflow with manual trigger
4. Setup deployment webhooks

**Concluding Step: Phase Completion Protocol**
```bash
python3 todo_manager.py show docker_migration_20250112
python3 todo_manager.py done docker_migration_20250112 5
```

IMPORTANT NOTE: CI/CD automation is critical for maintainability. All merges to main must trigger builds. Failed builds block deployments. Monitor registry storage quotas.

### PHASE 6: COMPLETE REMAINING SERVICES

**Objective:** Migrate all remaining consolidation hubs

**Explanations:** With patterns established, migrate remaining services in parallel. Each hub follows the proven migration pattern from earlier phases.

**Parallel Migration Tasks:**
1. Affective Processing Center (CPU-heavy, some GPU)
2. Real-Time Audio Pipeline (Mixed CPU/GPU)
3. Unified Observability Center (CPU-only)
4. Main PC services (70+ agents)
5. PC2 services (40+ agents)

**Per-Service Steps:**
1. Identify base image family (CPU vs GPU)
2. Convert to multi-stage build
3. Add health checks and non-root user
4. Build and push to GHCR
5. Update docker-compose references
6. Test deployment
7. Monitor for 24 hours

**Concluding Step: Phase Completion Protocol**
```bash
python3 todo_manager.py show docker_migration_20250112
python3 todo_manager.py done docker_migration_20250112 6
```

IMPORTANT NOTE: Parallel migration requires coordination. Use feature branches per service. Merge only after 24-hour stability. Maintain rollback tags for all services.

### PHASE 7: VALIDATION & OPTIMIZATION

**Objective:** Verify migration success and optimize

**Explanations:** Post-migration validation ensures all services are running optimally with expected size reductions and performance improvements.

**Validation Checklist:**
1. Image size reduction: Target 55-70% reduction achieved?
2. Layer cache effectiveness: Hit rate > 70%?
3. Build times: Under 5 minutes per service?
4. Registry bandwidth: Within acceptable limits?
5. Service health: All health checks passing?
6. GPU utilization: Optimal for workload?
7. Memory usage: No OOM errors?

**Optimization Tasks:**
1. Analyze layer sharing with `docker history`
2. Identify redundant layers
3. Optimize package installation order
4. Implement distroless images where possible
5. Setup vulnerability scanning with Trivy
6. Configure auto-pruning of old images

**Concluding Step: Phase Completion Protocol**
```bash
python3 todo_manager.py show docker_migration_20250112
python3 todo_manager.py done docker_migration_20250112 7
```

IMPORTANT NOTE: Validation must be data-driven. Collect metrics before and after migration. Document all optimizations. Share learnings with team.

## Risk Mitigation

### Rollback Procedures
1. **Image Level:** All previous images tagged with dates, can revert docker-compose
2. **Service Level:** Feature flags to switch between local/registry builds
3. **Full System:** Backup of all original Dockerfiles in `/backups/docker-pre-migration/`

### Failure Scenarios
1. **GHCR Outage:** Fallback to local builds with cached base images
2. **GPU Incompatibility:** Maintain CUDA 11.8 variants as fallback
3. **Network Issues:** Local registry mirror on each machine
4. **Size Explosion:** Revert to single-stage for problematic services

## Success Metrics
- ✅ All services migrated to GHCR
- ✅ 55-70% average size reduction
- ✅ Build time < 5 min per service
- ✅ Zero-downtime migration
- ✅ Automated CI/CD pipeline
- ✅ Hardware-optimized deployments

## Timeline
- Week 1: Phases 0-2 (Foundation + CPU pilot)
- Week 2: Phases 3-4 (Machine profiles + GPU services)
- Week 3: Phases 5-6 (CI/CD + Remaining services)
- Week 4: Phase 7 (Validation + Optimization)

## Dependencies
- GHCR access with sufficient storage quota
- Docker buildx on all build machines
- NVIDIA Container Toolkit for GPU nodes
- GitHub Actions for CI/CD
- Monitoring infrastructure (Prometheus/Grafana)

---
END OF PLAN
Confidence Score: 85%
Risk Level: Medium (mitigated by phased approach)
Estimated Completion: 4 weeks