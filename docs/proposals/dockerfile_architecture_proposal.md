# Dockerfile Architecture Proposal (Dual-Machine 4090 + 3060)

> Version: **v0.1-draft**  
> Author: Lead DevOps Architect  
> Status: ⏳ DRAFT – awaiting review/answers to open questions

---

## A. High-Level Strategy & Rationale

1. **Functional-Family Base Images** – Instead of one mega-template, we define *families* that share a minimal, layered lineage (see §B).  This balances:
   * *DRY reuse* – common layers stay in cache across ~50 images.
   * *Dependency hygiene* – CPU-only agents never inherit GPU libraries.
   * *Flexibility* – Families can evolve (e.g., cuDNN upgrade) without touching CPU images.

2. **Multi-Stage Builds** – Builder stage (eg. poetry/conda wheels) ➜ runtime stage (slim-python + needed shared libs).  Dramatically shrinks final size (-55-70 % vs single-stage).

3. **Pinned, Reproducible Layers** – All `apt` and `pip` installs are version-pinned; `pip` uses `--require-hashes` with pre-generated *lock/wheels* inside an internal artifact registry.

4. **Non-Root Runtime** – Each final stage switches to an unprivileged UID: GID `10001:10001` (`appuser`).  Health-checks run via tini as PID 1 to avoid zombie leaks.

5. **Hardware-Aware Runtime Tuning** – Entry script reads `/etc/machine-profile.json` (baked per build arg) to set sensible defaults (GPU selector, thread pool, env vars).  See §D.

6. **Build Orchestration** – GitHub Actions matrix (families × machines) uses `buildx` + `--cache-to` / `--cache-from` to share OCI layer cache through GHCR.

## B. Base Image Hierarchy

```
base-python:3.11-slim          # debian-slim, non-root, tini
  ├─ base-utils                # curl, dumb-init, gosu, tzdata
  │   ├─ base-cpu-pydeps       # common cpu wheels (numpy, pydantic, fastapi)
  │   │   └─ family-web        # uvicorn, starlette, websockets
  │   └─ base-gpu-cu121        # FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04
  │       ├─ family-torch-cu121   # torch==2.2.2+cu121, torchvision
  │       │   └─ family-llm-cu121 # vllm, llama-cpp-python built w/ -sm80/89
  │       └─ family-vision-cu121  # opencv-python-headless, onnxruntime-gpu
  └─ legacy-py310-cpu          # frozen for agents stuck on 3.10 (security-patched)
```

* **Registries/Tags:** `ghcr.io/<org>/<image>:<family>-<version>` – version = `YYYYMMDD` date stamp + git short-sha.  *GPU variants append `-cudaXX`.*
* **4090 vs 3060:** Both use CUDA 12.1 runtime; code targeting SM 8.9 vs 8.6 is handled at *build-time* via `TORCH_CUDA_ARCH_LIST` (`89;86`). Optional *cu12.4* future tag.

## C. Optimisation & Standardisation Plan

1. **Layer Ordering** – OS updates ➜ core libs ➜ Python deps ➜ app code ➜ static assets.  Keeps cache hits high when only code changes.
2. **Build Cache** – Use `type=registry` cache for GHCR; share between MainPC & PC2 runners.
3. **Wheel Cache Layer** – `--mount=type=cache,target=/root/.cache/pip` to avoid re-downloading.
4. **.dockerignore** – Extend repo root ignore; plus generated `__pycache__`, models, data.
5. **Security** –
   * `apt-get update && apt-get install --no-install-recommends` + `apt-clean`.
   * Trivy scan stage; pipeline fails on HIGH/CRITICAL (subject to open question #4).
6. **Image Size Targets** – Goal: ‑40 % median vs current (170 → ≈100 MB for CPU; 5.2 GB → 3 GB for GPU).  Achieved via multi-stage, stripping docs/tests, and slim bases.

## D. Hardware-Aware Defaults

| Parameter                     | MainPC (4090) | PC2 (3060) |
|-------------------------------|---------------|------------|
| `GPU_VISIBLE_DEVICES`         | `0`           | `0`        |
| `TORCH_CUDA_ALLOC_CONF`       | `max_split_size_mb:64` | `max_split_size_mb:32` |
| Thread workers (`uvicorn`)    | CPU cores ×2 = 32 | CPU cores = 8 |
| `NUMBA_CACHE_SIZE`            | 512 MB        | 128 MB     |
| `OMP_NUM_THREADS`             | 16            | 4          |
| `MODEL_EVICT_THRESHOLD_PCT`   | 90            | 70         |

Values baked via build-arg `MACHINE=mainpc|pc2` ➜ writes `/etc/machine-profile.json`.

## E. Concrete Example Dockerfiles

### 1. ModelOpsCoordinator (GPU-heavy, MainPC)
```Dockerfile
# syntax=docker/dockerfile:1.5
FROM ghcr.io/<org>/family-torch-cu121:20240810 AS base
ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \
    TORCH_CUDA_ARCH_LIST="8.9" \
    NVIDIA_VISIBLE_DEVICES=${GPU_VISIBLE_DEVICES:-0}

WORKDIR /app
COPY model_ops_coordinator/ ./model_ops_coordinator
COPY requirements/model_ops.txt ./requirements.txt

# ---------- Builder ----------
FROM base AS builder
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --require-hashes -r requirements.txt

# ---------- Runtime ----------
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY model_ops_coordinator/ ./model_ops_coordinator
COPY config/ ./config
COPY entrypoints/model_ops_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chmod +x /usr/bin/tini
USER appuser
HEALTHCHECK CMD curl -f http://localhost:${HEALTH_PORT:-8212}/health || exit 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["/entrypoint.sh"]
```

### 2. MemoryFusionHub (GPU-aware but CPU-preferred, PC2)
```Dockerfile
FROM ghcr.io/<org>/family-cpu-pydeps:20240810 AS base
ARG MACHINE=pc2
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY memory_fusion_hub/ ./memory_fusion_hub
COPY requirements/memory_fusion.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --require-hashes -r requirements.txt

COPY entrypoints/memory_fusion_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chmod +x /usr/bin/tini
USER appuser
HEALTHCHECK CMD curl -f http://localhost:${HEALTH_PORT:-6713}/health || exit 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["/entrypoint.sh"]
```

### 3. Legacy `IntentionValidatorAgent` (Py-3.10 CPU)
```Dockerfile
FROM ghcr.io/<org>/legacy-py310-cpu:20240810
WORKDIR /app
COPY main_pc_code/agents/IntentionValidatorAgent.py ./
RUN pip install --no-cache-dir pydantic==1.10.15 fastapi==0.110.0
USER appuser
CMD ["python","IntentionValidatorAgent.py"]
```

> **Note:** Sample files *not* meant for commit; final paths/ports resolved by build ARGs.

## F. Fleet Coverage Table

| Service | Machine(s) | Needs | Proposed Base | Entrypoint | Ports | Healthcheck | Notes |
|---------|------------|-------|---------------|------------|-------|-------------|-------|
| ServiceRegistry | 4090 | CPU/Web | family-web | `registry_entry.sh` | 7200 | `/health` | Redis URL env |
| SystemDigitalTwin | 4090 | CPU | base-cpu-pydeps | `digital_twin.sh` | 7220 | `/health` | sqlite + redis |
| UnifiedSystemAgent | 4090 | CPU | base-cpu-pydeps | ... | 7201 | ... | |
| SelfHealingSupervisor | 4090,3060 | CPU/Docker | base-cpu-pydeps | ... | 7009 | ... | needs docker.sock |
| MemoryFusionHub | 4090,3060 | CPU/GPU* | family-cpu-pydeps | ... | 5713 | ... | GPU optional |
| ModelOpsCoordinator | 4090 | GPU/LLM | family-llm-cu121 | ... | 7212 | ... | torch/vllm |
| AffectiveProcessingCenter | 4090 | GPU | family-torch-cu121 | ... | 5560 | ... | |
| RealTimeAudioPipeline | both | GPU/Audio | family-torch-cu121 | ... | 5557 | ... | uses whisper |
| UnifiedObservabilityCenter | both | CPU/Web | family-web | ... | 9100 | ... | prometheus |
| CodeGenerator | 4090 | CPU | base-cpu-pydeps | ... | 5650 | ... | |
| PredictiveHealthMonitor | 4090 | CPU | base-cpu-pydeps | ... | 5613 | ... | |
| Executor | 4090 | CPU | base-cpu-pydeps | ... | 5606 | ... | |
| TinyLlamaServiceEnhanced | 4090 | GPU/LLM | family-llm-cu121 | ... | 5615 | ... | optional |
| SmartHomeAgent | 4090 | CPU/Web | family-web | ... | 7125 | ... | |
| CrossMachineGPUScheduler | 4090 | CPU | base-cpu-pydeps | ... | 7155 | ... | needs grpc |
| ChainOfThoughtAgent | 4090 | GPU/LLM | family-llm-cu121 | ... | 5612 | ... | |
| CognitiveModelAgent | 4090 | GPU/LLM | family-llm-cu121 | ... | 5641 | ... | optional |
| FaceRecognitionAgent | 4090 | GPU/Vision | family-vision-cu121 | ... | 5610 | ... | opencv |
| LearningOpportunityDetector | 4090 | GPU/LLM | family-llm-cu121 | ... | 7202 | ... | |
| LearningManager | 4090 | GPU/LLM | family-llm-cu121 | ... | 5580 | ... | |
| ActiveLearningMonitor | 4090 | CPU | base-cpu-pydeps | ... | 5638 | ... | |
| IntentionValidatorAgent | 4090 | CPU | legacy-py310-cpu | ... | 5701 | ... | legacy py310 |
| NLUAgent | 4090 | CPU | legacy-py310-cpu | ... | 5709 | ... | |
| AdvancedCommandHandler | 4090 | CPU | legacy-py310-cpu | ... | 5710 | ... | |
| ChitchatAgent | 4090 | CPU | legacy-py310-cpu | ... | 5711 | ... | |
| FeedbackHandler | 4090 | CPU | legacy-py310-cpu | ... | 5636 | ... | |
| Responder | 4090 | GPU/Audio | family-torch-cu121 | ... | 5637 | ... | |
| DynamicIdentityAgent | 4090 | GPU/LLM | family-llm-cu121 | ... | 5802 | ... | |
| EmotionSynthesisAgent | 4090 | GPU/Audio | family-torch-cu121 | ... | 5706 | ... | |
| STTService | 4090 | GPU/Audio | family-torch-cu121 | ... | 5800 | ... | whisper |
| TTSService | 4090 | GPU/Audio | family-torch-cu121 | ... | 5801 | ... | xtts |
| AudioCapture | 4090 | CPU/Audio | base-cpu-pydeps | ... | 6550 | ... | optional |
| StreamingSpeechRecognition | 4090 | GPU/Audio | family-torch-cu121 | ... | 6553 | ... | optional |
| StreamingTTSAgent | 4090 | GPU/Audio | family-torch-cu121 | ... | 5562 | ... | |
| ProactiveAgent | 4090 | GPU/LLM | family-llm-cu121 | ... | 5624 | ... | |
| EmotionEngine | 4090 | CPU | base-cpu-pydeps | ... | 5590 | ... | |
| MoodTrackerAgent | 4090 | CPU | base-cpu-pydeps | ... | 5704 | ... | |
| HumanAwarenessAgent | 4090 | CPU | base-cpu-pydeps | ... | 5705 | ... | |
| ToneDetector | 4090 | CPU | base-cpu-pydeps | ... | 5625 | ... | |
| VoiceProfilingAgent | 4090 | CPU | base-cpu-pydeps | ... | 5708 | ... | |
| EmpathyAgent | 4090 | GPU/Audio | family-torch-cu121 | ... | 5703 | ... | |
| CloudTranslationService | 4090 | CPU/Web | family-web | ... | 5592 | ... | |
| StreamingTranslationProxy | 4090 | CPU/Web | family-web | ... | 5596 | ... | websocket |
| ObservabilityDashboardAPI | 4090 | CPU/Web | family-web | ... | 8001 | ... | |
| CentralErrorBus | 3060 | CPU/Web | family-web | ... | 7150 | ... | |
| RealTimeAudioPipelinePC2 | 3060 | GPU/Audio | family-torch-cu121 | ... | 5557 | ... | |
| TieredResponder | 3060 | CPU | base-cpu-pydeps | ... | 7100 | ... | |
| AsyncProcessor | 3060 | CPU | base-cpu-pydeps | ... | 7101 | ... | |
| CacheManager | 3060 | CPU | base-cpu-pydeps | ... | 7102 | ... | |
| VisionProcessingAgent | 3060 | GPU/Vision | family-vision-cu121 | ... | 7160 | ... | |
| DreamWorldAgent | 3060 | GPU/Vision | family-vision-cu121 | ... | 7104 | ... | |
| ResourceManager | 3060 | CPU | base-cpu-pydeps | ... | 7113 | ... | |
| TaskScheduler | 3060 | CPU | base-cpu-pydeps | ... | 7115 | ... | |
| AuthenticationAgent | 3060 | CPU | base-cpu-pydeps | ... | 7116 | ... | |
| UnifiedUtilsAgent | 3060 | CPU | base-cpu-pydeps | ... | 7118 | ... | |
| ProactiveContextMonitor | 3060 | CPU | base-cpu-pydeps | ... | 7119 | ... | |
| AgentTrustScorer | 3060 | CPU | base-cpu-pydeps | ... | 7122 | ... | |
| FileSystemAssistantAgent | 3060 | CPU | base-cpu-pydeps | ... | 7123 | ... | |
| RemoteConnectorAgent | 3060 | CPU | base-cpu-pydeps | ... | 7124 | ... | |
| UnifiedWebAgent | 3060 | CPU/Web | family-web | ... | 7126 | ... | |
| DreamingModeAgent | 3060 | GPU/Vision | family-vision-cu121 | ... | 7127 | ... | |
| AdvancedRouter | 3060 | CPU | base-cpu-pydeps | ... | 7129 | ... | |
| UnifiedObservabilityCenter (pc2) | 3060 | CPU/Web | family-web | ... | 9100 | ... | |
| TutoringServiceAgent | 3060 | CPU | base-cpu-pydeps | ... | 7108 | ... | |
| SpeechRelayService | 3060 | GPU/Audio | family-torch-cu121 | ... | 7130 | ... | |

> “…” marks entry scripts & health endpoints to be finalised in implementation phase.  Unknown requirements flagged **(uncertain — ask)** inline if applicable.

## G. Risk Register & Rollback

| ID | Risk | Likelihood | Impact | Mitigation | Rollback |
|----|------|------------|--------|------------|----------|
| R1 | CUDA 12.1 incompatibility with older driver on PC2 | Low | High | Verify driver ≥ 535; fallback to CUDA 11.8 tag | Re-tag images to `-cu118` branch |
| R2 | Legacy Py3.10 deps receive no upstream security fixes | Med | Med | Freeze to distro-patched 3.10, schedule migration | Swap to base-python:3.11-slim branch |
| R3 | Shared layer cache eviction on GHCR (size quota) | Med | Low | Periodic `buildx imagetools rm`; prune old tags | Rebuild without cache (slow) |
| R4 | CVE scan false-positives breaking pipeline | Med | Med | Allowlist by SBOM digest; extend grace period | Temporarily downgrade scan severity gate |

## H. Open Questions

1. **Python Targets** – OK to default new hubs to 3.11 while freezing legacy agents on 3.10?
2. **Registry Naming** – Confirm `ghcr.io/<org>/<family>:<tag>` convention & write access.
3. **CUDA Track** – Adopt CUDA 12.4 images now or stay on 12.1 baseline?
4. **Vulnerability Scanner** – Preference between *Trivy* vs *Grype*?  Fail on HIGH/CRITICAL?
5. **Audio/Vision Extras** – Any agents require ffmpeg/libpulse/alsa directly in image?
6. **CI Runner Constraints** – GPU runners available for build tests?  Cache storage limit?
7. **Health Endpoint Uniformity** – Can we standardise `/health` JSON 200 across all agents?

---

## Implementation Plan (post-approval)

1. **Answer Open Questions** ➜ finalise base-image Dockerfiles & lockfiles.
2. **Set Up GHCR Repositories & Buildx Cache Buckets**.
3. **Prototype Family Images** (`base-cpu`, `family-torch-cu121`, etc.) locally; measure size & performance.
4. **CI Pipeline Update** – Add build matrix, cache push/pull, CVE scan stages.
5. **Incremental Migration:**
   a. Migrate *core infrastructure* (ServiceRegistry, DigitalTwin).  
   b. Roll out GPU families on MainPC.  
   c. Roll out CPU families on PC2.
6. **Observability** – Integrate image SBOM output into Unified Observability Center.
7. **Rollback Procedures** – Tag previous images `-legacy` for hot revert; supervisor auto-pulls.

---

*Document generated automatically; please review & add comments.*