## Dockerfile Architecture Proposal (Dual-Machine 4090 + 3060)

- Author: Lead DevOps Architecture Draft
- Scope: Proposal only; no code/CI changes yet
- Confidence: 87%

### A. High-Level Strategy & Rationale

- **Objective**: Standardize all containers for consolidated hubs and legacy agents across two heterogeneous GPU hosts (MainPC RTX 4090, PC2 RTX 3060) while enforcing dependency hygiene and maximizing layer re-use.
- **Approach**: Use a small set of functional base families with parameterization rather than one monolithic Dockerfile. Each service gets a thin service Dockerfile that `FROM`s a family base and installs only its minimal requirements.
- **Families vs Single Template**:
  - **Families (recommended)**: Separate CPU, CPU-Web, GPU-Ada (4090), GPU-Ampere (3060), and optional audio/vision variants. Pros: lighter images, fewer conditional branches, clear GPU targeting, strong cache re-use. Cons: more base images to maintain.
  - **Single parameterized template**: Pros: one file. Cons: sprawling ARG/IF logic, higher build complexity, risk of pulling unnecessary GPU stacks for CPU-only agents, larger images, weaker cache locality.
- **Result**: Families deliver smaller images, faster rebuilds, and clear hardware-aware targeting. Each agent remains minimal and reproducible.

### B. Base Image Hierarchy (with tags, registries, CUDA strategy)

- **Registry pattern (proposed, confirm)**: `ghcr.io/<org>/ai-base:<family>-<version>`
- **Hierarchy**:
  - `ghcr.io/<org>/ai-base:cpu-py311-<date>`
    - FROM `python:3.11-slim` (Debian/Ubuntu base acceptable; slim footprint)
    - Non-root user `app`, `tini`, `ca-certificates`, timezone data
  - `ghcr.io/<org>/ai-base:cpu-web-py311-<date>`
    - Extends cpu-py311, adds `tini`, `curl`, `uvicorn[standard]`, `gunicorn`
  - `ghcr.io/<org>/ai-base:cpu-audio-py311-<date>`
    - Extends cpu-py311, adds `ffmpeg`, `libsndfile1`, `tini` (confirm audio stack)
  - `ghcr.io/<org>/ai-base:cuda12.3-runtime-py311-<date>`
    - FROM `nvidia/cuda:12.3.2-runtime-ubuntu22.04`, installs Python 3.11 stack
  - `ghcr.io/<org>/ai-base:cuda12.3-ada-py311-<date>` (MainPC)
    - Extends cuda12.3-runtime; sets `TORCH_CUDA_ARCH_LIST=8.9` and Ada-tuned flags
  - `ghcr.io/<org>/ai-base:cuda12.3-ampere-py311-<date>` (PC2)
    - Extends cuda12.3-runtime; sets `TORCH_CUDA_ARCH_LIST=8.6` and Ampere-tuned flags
  - Optional add-ons:
    - `*-gpu-vision`: adds `libgl1` for OpenCV wheels runtime
    - `*-gpu-audio`: adds `ffmpeg`, `libsndfile1` when GPU + audio required

- **CUDA strategy**:
  - Standardize on CUDA 12.3 runtime for both hosts to maximize wheel availability; pin PyTorch CUDA wheels accordingly (cu121/cu122 track to be confirmed).
  - Keep CPU families free of GPU libs; avoid fat-binaries.

### C. Optimization & Standardization Plan

- **Image size**:
  - Separate dependency layer (`pip install -r requirements.txt`) to maximize cache sharing.
  - Use slim bases; remove apt caches and `*.pyc`; avoid dev headers unless compiling.
  - Factor shared stacks (torch, transformers, opencv) into base family variants only where required.
  - Target: double-digit percentage reduction relative to a newly captured baseline, achieved by removing GPU libs from CPU images and deduplicating heavy wheels into family layers.

- **Build time**:
  - Multi-stage builds with "deps" layer; re-builds cheap when only app code changes.
  - Use `pip download` to pre-populate a versioned wheelhouse in base families for heavy libs (torch/transformers/opencv) to accelerate per-service installs.
  - Enable BuildKit with inline cache and registry cache export/import.

- **CI integration sketch**:
  - Build matrix: (families × machine) with tags `:cpu`, `:cpu-web`, `:cpu-audio`, `:cuda12.3-ada`, `:cuda12.3-ampere`, plus optional `-vision`/`-audio` suffixes.
  - Export/import cache to registry; fail-fast gates for image size drift and CVE levels; publish only on green.
  - Parallel builds by family, then fast service builds using cached deps layer.

- **.dockerignore standardization**:
  - Reuse root `.dockerignore` and add per-service ignores where needed. Ensure models, data, logs, artifacts are excluded from build context.

- **Per-agent dependency minimization**:
  - Static import analysis (existing: `main_pc_code/scripts/dependency_resolver.py`, `main_pc_code/NEWMUSTFOLLOW/dependency_tracer.py`) per agent to compute minimal `requirements.generated.txt`.
  - Lock via `pip-compile --generate-hashes` to produce reproducible `requirements.lock` per agent.
  - Legacy-benefit set (examples): MainPC `{FeedbackHandler, ChitchatAgent, NLUAgent, AdvancedCommandHandler, Responder, SmartHomeAgent}`; PC2 `{TieredResponder, AsyncProcessor, CacheManager, TaskScheduler, AdvancedRouter, UnifiedUtilsAgent, FileSystemAssistantAgent, AuthenticationAgent}`.

- **Shared stacks to factor**:
  - GPU-heavy: `torch`, `torchvision`, `torchaudio`, `transformers`, `sentencepiece` (only in GPU families that need them)
  - Vision: `opencv-python-headless`, system `libgl1` (vision variants only)
  - Web: `fastapi`, `uvicorn[standard]`, `gunicorn` (web family)
  - Messaging/IO: `pyzmq`, `redis`, `grpcio`, `pydantic`, `orjson`

- **Security posture**:
  - Run as non-root; drop capabilities.
  - Minimal apt; verify GPG for repos; remove build tools in final stage.
  - HEALTHCHECKs; read-only FS where possible; mount models/data via volumes.
  - CI CVE scan step (scanner TBD; propose Trivy/Grype) with fail-on HIGH/CRITICAL policy (confirm thresholds).

- **Reproducibility**:
  - Pin base image digests; pin Python package versions with hashes; consistent timezone/locale.

- **GPU readiness**:
  - Health/startup probe: `nvidia-smi` and `python -c 'import torch; assert torch.cuda.is_available()'` with device capability check.

### D. Hardware-Aware Defaults (MainPC vs PC2)

- **MainPC (RTX 4090, Ryzen 9 7900)**:
  - Families: `cuda12.3-ada-py311`
  - Env: `TORCH_CUDA_ARCH_LIST=8.9`, `OMP_NUM_THREADS=8..16` (per service), `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`
  - Workers: higher defaults (e.g., ModelOpsCoordinator `max_workers=16`)
  - Fallback: if CUDA unavailable at runtime, fail fast for GPU-only services (observability will alert) and auto-route to cloud/local-CPU per hybrid policy.

- **PC2 (RTX 3060, low-power CPU)**:
  - Families: `cuda12.3-ampere-py311`
  - Env: `TORCH_CUDA_ARCH_LIST=8.6`, `OMP_NUM_THREADS=2`, `UVICORN_WORKERS=1`
  - Prefer CPU-path for auxiliary agents; keep GPU-bound services minimal; lower batch sizes.
  - Fallback: degrade to CPU path for non-critical GPU users (e.g., pipeline stages) or temporarily pause workloads; never overcommit VRAM.

### E. Concrete Example Dockerfiles (Reference Only)

- Note: These are examples; final families and versions will be set post-approval. HEALTHCHECKs included for readiness. Non-root user assumed created in base.

#### E.1 ModelOpsCoordinator (MainPC, RTX 4090)

```Dockerfile
# Family base for Ada (4090)
FROM ghcr.io/<org>/ai-base:cuda12.3-ada-py311-<date> AS base

# Dedicated dependency layer (shared cache between services)
FROM base AS deps
WORKDIR /opt/app
COPY model_ops_coordinator/requirements.txt /opt/app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /opt/app/requirements.txt

# Final image
FROM base AS runtime
ENV PYTHONUNBUFFERED=1 \
    TORCH_CUDA_ARCH_LIST=8.9 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility
WORKDIR /app
COPY --from=deps /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY model_ops_coordinator/ /app/model_ops_coordinator/
COPY model_ops_coordinator/config/ /app/model_ops_coordinator/config/

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import torch,sys; sys.exit(0 if torch.cuda.is_available() else 1)" && \
      python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 8008)); s.close()" || exit 1

EXPOSE 8008 7212 7211
CMD ["python", "-m", "model_ops_coordinator.app"]
```

#### E.2 MemoryFusionHub (PC2-optimized)

```Dockerfile
# PC2 uses Ampere base; low CPU concurrency; no heavy GPU deps by default
FROM ghcr.io/<org>/ai-base:cuda12.3-ampere-py311-<date> AS base

FROM base AS deps
WORKDIR /opt/app
COPY memory_fusion_hub/requirements.txt /opt/app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /opt/app/requirements.txt

FROM base AS runtime
ENV PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=2 \
    UVICORN_WORKERS=1
WORKDIR /app
COPY --from=deps /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY memory_fusion_hub/ /app/memory_fusion_hub/
COPY memory_fusion_hub/config/ /app/memory_fusion_hub/config/

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1', 8080)); s.close()" || exit 1

EXPOSE 5713 5714 8080
CMD ["python", "-m", "memory_fusion_hub.app"]
```

#### E.3 Simple Legacy Agent (CPU-only)

```Dockerfile
FROM ghcr.io/<org>/ai-base:cpu-py311-<date> AS base

FROM base AS deps
WORKDIR /opt/app
COPY legacy_agents/simple_agent/requirements.txt /opt/app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /opt/app/requirements.txt

FROM base AS runtime
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=deps /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY legacy_agents/simple_agent/ /app/legacy_agents/simple_agent/

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 CMD python - <<'PY' || exit 1
import socket,sys
s=socket.socket(); s.settimeout(2)
try:
    s.connect(("127.0.0.1", 7110))  # example health port
    s.close(); sys.exit(0)
except Exception:
    sys.exit(1)
PY

EXPOSE 7110
CMD ["python", "-m", "legacy_agents.simple_agent.app"]
```

### F. Fleet Coverage Table (100% of Active Agents)

Notes:
- Ports use `${PORT_OFFSET}+<port>` where configured. Health ports included where specified.
- Needs are inferred via names/config; entries marked “(uncertain — ask)” require confirmation.
- Base family keys: `cpu`, `cpu-web`, `cpu-audio`, `gpu-ada`, `gpu-ampere`, `gpu-ada-vision`, `gpu-ampere-vision`.

| service | machine(s) | needs (CPU/GPU/Web/Audio/Vision) | proposed base family | entrypoint | ports | healthcheck | notes |
|---|---|---|---|---|---|---|---|
| ServiceRegistry | MainPC | CPU, Redis client | cpu | main_pc_code/agents/service_registry_agent.py | 7200 | 8200 | Uses Redis URL env |
| SystemDigitalTwin | MainPC | CPU | cpu | main_pc_code/agents/system_digital_twin.py | 7220 | 8220 | SQLite + Redis config |
| UnifiedSystemAgent | MainPC | CPU | cpu | main_pc_code/agents/unified_system_agent.py | 7201 | 8201 | Orchestration |
| SelfHealingSupervisor | MainPC, PC2 | CPU, Docker sock | cpu | services/self_healing_supervisor/supervisor.py | 7009 | 9008 | Needs `/var/run/docker.sock` |
| MemoryFusionHub | MainPC, PC2 | CPU, storage | cpu (PC2 may use gpu-ampere if kernels needed) | memory_fusion_hub/app.py | 5713, 5714, 8080 | 6713 | No GPU by default |
| ModelOpsCoordinator | MainPC | GPU (Ada) | gpu-ada | model_ops_coordinator/app.py | 7211, 7212, 8008 | 8212 | Heavy PyTorch/transformers |
| AffectiveProcessingCenter | MainPC | CPU (uncertain GPU) | cpu (uncertain — ask) | affective_processing_center/app.py | 5560, 5561 | 6560 | ZMQ pub/synth |
| RealTimeAudioPipeline | MainPC | Audio, GPU | gpu-ada (audio) | real_time_audio_pipeline/app.py | 5557, 5558 | 6557 | Uses CUDA device |
| CodeGenerator | MainPC | CPU | cpu | main_pc_code/agents/code_generator_agent.py | 5650 | 6650 |  |
| PredictiveHealthMonitor | MainPC | CPU | cpu | main_pc_code/agents/predictive_health_monitor.py | 5613 | 6613 |  |
| Executor | MainPC | CPU | cpu | main_pc_code/agents/executor.py | 5606 | 6606 |  |
| TinyLlamaServiceEnhanced | MainPC | GPU | gpu-ada | main_pc_code/FORMAINPC/tiny_llama_service_enhanced.py | 5615 | 6615 |  |
| SmartHomeAgent | MainPC | CPU, Web? | cpu | main_pc_code/agents/smart_home_agent.py | 7125 | 8125 | (uncertain — ask) |
| CrossMachineGPUScheduler | MainPC | CPU | cpu | services/cross_gpu_scheduler/app.py | 7155 | 8155 |  |
| ChainOfThoughtAgent | MainPC | GPU | gpu-ada | main_pc_code/FORMAINPC/chain_of_thought_agent.py | 5612 | 6612 |  |
| GoTToTAgent | MainPC | CPU/GPU (uncertain) | cpu | main_pc_code/FORMAINPC/got_tot_agent.py | 5646 | 6646 | Depends on CoT |
| CognitiveModelAgent | MainPC | GPU | gpu-ada | main_pc_code/FORMAINPC/cognitive_model_agent.py | 5641 | 6641 |  |
| FaceRecognitionAgent | MainPC | GPU, Vision | gpu-ada-vision | main_pc_code/agents/face_recognition_agent.py | 5610 | 6610 | `libgl1` for OpenCV |
| LearningOpportunityDetector | MainPC | CPU (uncertain GPU) | cpu | main_pc_code/agents/learning_opportunity_detector.py | 7202 | 8202 |  |
| LearningManager | MainPC | CPU | cpu | main_pc_code/agents/learning_manager.py | 5580 | 6580 |  |
| ActiveLearningMonitor | MainPC | CPU | cpu | main_pc_code/agents/active_learning_monitor.py | 5638 | 6638 |  |
| IntentionValidatorAgent | MainPC | CPU | cpu | main_pc_code/agents/IntentionValidatorAgent.py | 5701 | 6701 |  |
| NLUAgent | MainPC | CPU | cpu | main_pc_code/agents/nlu_agent.py | 5709 | 6709 |  |
| AdvancedCommandHandler | MainPC | CPU | cpu | main_pc_code/agents/advanced_command_handler.py | 5710 | 6710 |  |
| ChitchatAgent | MainPC | CPU | cpu | main_pc_code/agents/chitchat_agent.py | 5711 | 6711 |  |
| FeedbackHandler | MainPC | CPU | cpu | main_pc_code/agents/feedback_handler.py | 5636 | 6636 |  |
| Responder | MainPC | CPU | cpu | main_pc_code/agents/responder.py | 5637 | 6637 | Multi-dependency |
| DynamicIdentityAgent | MainPC | CPU | cpu | main_pc_code/agents/DynamicIdentityAgent.py | 5802 | 6802 |  |
| EmotionSynthesisAgent | MainPC | CPU (uncertain GPU) | cpu | main_pc_code/agents/emotion_synthesis_agent.py | 5706 | 6706 |  |
| STTService | MainPC | GPU, Audio | gpu-ada (audio) | main_pc_code/services/stt_service.py | 5800 | 6800 |  |
| TTSService | MainPC | GPU, Audio | gpu-ada (audio) | main_pc_code/services/tts_service.py | 5801 | 6801 |  |
| AudioCapture | MainPC | CPU, Audio | cpu-audio | main_pc_code/agents/streaming_audio_capture.py | 6550 | 7550 |  |
| FusedAudioPreprocessor | MainPC | CPU, Audio | cpu-audio | main_pc_code/agents/fused_audio_preprocessor.py | 6551 | 7551 |  |
| StreamingInterruptHandler | MainPC | CPU | cpu | main_pc_code/agents/streaming_interrupt_handler.py | 5576 | 6576 |  |
| StreamingSpeechRecognition | MainPC | CPU (calls STTService) | cpu | main_pc_code/agents/streaming_speech_recognition.py | 6553 | 7553 |  |
| StreamingTTSAgent | MainPC | CPU (calls TTSService) | cpu | main_pc_code/agents/streaming_tts_agent.py | 5562 | 6562 |  |
| WakeWordDetector | MainPC | CPU, Audio | cpu-audio | main_pc_code/agents/wake_word_detector.py | 6552 | 7552 |  |
| StreamingLanguageAnalyzer | MainPC | CPU | cpu | main_pc_code/agents/streaming_language_analyzer.py | 5579 | 6579 |  |
| ProactiveAgent | MainPC | CPU | cpu | main_pc_code/agents/ProactiveAgent.py | 5624 | 6624 |  |
| EmotionEngine | MainPC | CPU | cpu | main_pc_code/agents/emotion_engine.py | 5590 | 6590 |  |
| MoodTrackerAgent | MainPC | CPU | cpu | main_pc_code/agents/mood_tracker_agent.py | 5704 | 6704 |  |
| HumanAwarenessAgent | MainPC | CPU | cpu | main_pc_code/agents/human_awareness_agent.py | 5705 | 6705 |  |
| ToneDetector | MainPC | CPU | cpu | main_pc_code/agents/tone_detector.py | 5625 | 6625 |  |
| VoiceProfilingAgent | MainPC | CPU | cpu | main_pc_code/agents/voice_profiling_agent.py | 5708 | 6708 |  |
| EmpathyAgent | MainPC | CPU | cpu | main_pc_code/agents/EmpathyAgent.py | 5703 | 6703 |  |
| CloudTranslationService | MainPC | CPU | cpu | main_pc_code/agents/cloud_translation_service.py | 5592 | 6592 |  |
| StreamingTranslationProxy | MainPC | CPU, Web | cpu-web | services/streaming_translation_proxy/proxy.py | 5596 | 6596 | WebSocket proxy |
| ObservabilityDashboardAPI | MainPC | CPU, Web | cpu-web | services/obs_dashboard_api/server.py | 8001 | 9007 |  |
| UnifiedObservabilityCenter | MainPC, PC2 | CPU, Web | cpu-web | unified_observability_center/app.py | 9100 | 9110 | MainPC ports (uncertain — ask) |
| CentralErrorBus | PC2 | CPU, ZMQ | cpu | services/central_error_bus/error_bus.py | 7150 | 8150 |  |
| RealTimeAudioPipelinePC2 | PC2 | Audio, (GPU optional) | gpu-ampere (audio) | real_time_audio_pipeline/app.py | 5557, 5558 | 6557 |  |
| TieredResponder | PC2 | CPU | cpu | pc2_code/agents/tiered_responder.py | 7100 | 8100 |  |
| AsyncProcessor | PC2 | CPU | cpu | pc2_code/agents/async_processor.py | 7101 | 8101 |  |
| CacheManager | PC2 | CPU | cpu | pc2_code/agents/cache_manager.py | 7102 | 8102 |  |
| VisionProcessingAgent | PC2 | GPU, Vision | gpu-ampere-vision | pc2_code/agents/VisionProcessingAgent.py | 7160 | 8160 |  |
| DreamWorldAgent | PC2 | GPU | gpu-ampere | pc2_code/agents/DreamWorldAgent.py | 7104 | 8104 |  |
| ResourceManager | PC2 | CPU | cpu | pc2_code/agents/resource_manager.py | 7113 | 8113 |  |
| TaskScheduler | PC2 | CPU | cpu | pc2_code/agents/task_scheduler.py | 7115 | 8115 |  |
| AuthenticationAgent | PC2 | CPU | cpu | pc2_code/agents/ForPC2/AuthenticationAgent.py | 7116 | 8116 |  |
| UnifiedUtilsAgent | PC2 | CPU | cpu | pc2_code/agents/ForPC2/unified_utils_agent.py | 7118 | 8118 |  |
| ProactiveContextMonitor | PC2 | CPU | cpu | pc2_code/agents/ForPC2/proactive_context_monitor.py | 7119 | 8119 |  |
| AgentTrustScorer | PC2 | CPU | cpu | pc2_code/agents/AgentTrustScorer.py | 7122 | 8122 |  |
| FileSystemAssistantAgent | PC2 | CPU | cpu | pc2_code/agents/filesystem_assistant_agent.py | 7123 | 8123 |  |
| RemoteConnectorAgent | PC2 | CPU | cpu | pc2_code/agents/remote_connector_agent.py | 7124 | 8124 |  |
| UnifiedWebAgent | PC2 | CPU, Web | cpu-web | pc2_code/agents/unified_web_agent.py | 7126 | 8126 |  |
| DreamingModeAgent | PC2 | GPU | gpu-ampere | pc2_code/agents/DreamingModeAgent.py | 7127 | 8127 |  |
| AdvancedRouter | PC2 | CPU | cpu | pc2_code/agents/advanced_router.py | 7129 | 8129 |  |
| TutoringServiceAgent | PC2 | CPU | cpu | pc2_code/agents/TutoringServiceAgent.py | 7108 | 8108 |  |
| SpeechRelayService | PC2 | CPU, Audio | cpu-audio | services/speech_relay/relay.py | 7130 | 8130 | Depends on TTS/vision |

### G. Risk Register & Rollback Considerations

- **GPU driver/CUDA mismatch**: Early failure via startup probe; rollback by pinning previous base digest.
- **Wheel incompatibility**: Maintain wheelhouse per family; fallback to CPU path if GPU wheel absent.
- **Image bloat regression**: CI threshold check on image size; block merges if exceeding baseline ± tolerance.
- **Runtime perf regressions**: UOC telemetry watch; can toggle batch/threads via env; promote previous tag.
- **Security**: CVE scan gate; if fail, auto-rebuild with patched base or pin previous.

### H. Open Questions (Blocking/Design-Affecting)

1) Python baseline: default 3.11 for all; any legacy requiring 3.10?
2) Registry: confirm `ghcr.io/<org>` naming and retention policy; who owns org?
3) CUDA track: unify on CUDA 12.3; confirm PyTorch wheels variant (cu121 vs cu122/12.3). Do we need CUDA 12.4 soon for 4090?
4) Vulnerability scanning: Trivy vs Grype; policy thresholds (fail on HIGH/CRITICAL?).
5) Audio deps: exact packages required for RealTimeAudioPipeline, STT/TTS, SpeechRelay (e.g., `ffmpeg`, `libsndfile1`, `portaudio`?).
6) Vision deps: confirm need for `libgl1` only, or additional (e.g., `libglib2.0-0`) for OpenCV in production.
7) UnifiedObservabilityCenter on MainPC: confirm ports (proposed 9100/9110) and whether it runs on both machines concurrently.
8) Wheelhouse strategy: central shared cache vs per-family image baked wheels; storage constraints on CI runner.
9) Non-root UID/GID mapping: desired numeric IDs for volume permissions?
10) Healthcheck endpoints: standardize HTTP endpoints vs TCP port checks for all agents?

### Implementation Plan (Post-Approval)

- Define and publish base families (cpu, cpu-web, cpu-audio, cuda12.3-ada, cuda12.3-ampere, optional vision/audio variants) with pinned digests.
- Introduce per-agent thin Dockerfiles that `FROM` a family and install minimal `requirements.generated.txt`.
- CI: Build matrix by family×machine; enable BuildKit cache; add image-size and CVE gates; publish to registry.
- Add dependency extractor job to write `requirements.generated.txt` and lock (`--generate-hashes`).
- Add runtime health probes and thread/cuda env defaults per machine in compose/helm values.
- Baseline metrics (image size, cold-start latency), then iterate.