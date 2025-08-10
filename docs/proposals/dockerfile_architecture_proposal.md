### Dockerfile Architecture Proposal (Dual-Machine: RTX 4090 + RTX 3060)

This proposal defines a unified, production-ready container architecture for all active services, covering consolidated hubs and legacy agents from:
- `main_pc_code/config/startup_config.yaml`
- `pc2_code/config/startup_config.yaml`

It is optimized for the hardware reality:
- MainPC: NVIDIA RTX 4090 (Ada 8.9), AMD Ryzen 9 7900
- PC2: NVIDIA RTX 3060 (Ampere 8.6), low-power CPU

The design enforces dependency hygiene, promotes shared layers where they demonstrably reduce size/build time, and keeps CPU-only services free of GPU stacks.

---

### A. High-level strategy & rationale

- Functional base families, not a single monolithic template
  - A single, heavily-parameterized Dockerfile would either bloat CPU-only services with GPU stacks or create complex branching that’s hard to audit and cache effectively. Functional families let us:
    - Keep each runtime minimal per service type
    - Reuse shared heavy layers (e.g., CUDA + torch) across GPU-bound services for fast builds
    - Avoid divergence by codifying the smallest viable set of base families

- Strict dependency hygiene
  - Per-service requirements are minimized (auto-generated for legacy agents when feasible; pinned otherwise).
  - Families include only ubiquitous dependencies for that group; optional extras stay per-service to avoid bloat.

- Multi-stage builds and venv handoff
  - Builder installs compilers and dev libs; runtime contains only what’s needed to run.
  - Virtualenv copied from builder → runtime to reduce size and ensure reproducibility.

- Security by default
  - Non-root users, minimal apt footprint, healthchecks, explicit port exposure, and CI-integrated CVE scanning.

- Hardware-aware defaults
  - MainPC tuned for maximum throughput; PC2 tuned for efficiency and safe fallback behavior.

---

### B. Base image hierarchy (families, tags, registries, CUDA strategy)

Proposed registry naming (confirm): `ghcr.io/<org>/<family>:<version>`
- Example tags include OS, Python, CUDA track, and date: `v1-py311-cu121-ubuntu22.04-2025q3`

CUDA strategy
- Default CUDA track: 12.1 (cu121) for both RTX 4090 and RTX 3060 to enable shared torch wheels.
- Optional MainPC-only track: 12.4 (cu124) if benchmarks justify it (opt-in per-service).
- NVIDIA runtime provided by host via NVIDIA Container Toolkit.

Families
- base.cpu-core
  - FROM `python:3.11-slim` (preferred)
  - For legacy services requiring py3.10, provide `base.cpu-core-py310` FROM `python:3.10-slim`
  - Minimal runtime: curl, ca-certificates for healthchecks
- base.cpu-web
  - FROM `base.cpu-core`
  - Adds `fastapi`, `uvicorn`, `prometheus-client` (and `httpx` where widely used)
- base.gpu-core-cu121
  - FROM `nvidia/cuda:12.1.1-runtime-ubuntu22.04`
  - Installs Python 3.11 (or 3.10 for legacy), venv, curl, ca-certificates
  - No ML libraries; just CUDA runtime + Python
- base.gpu-ml-cu121
  - FROM `base.gpu-core-cu121`
  - Adds torch via `--extra-index-url https://download.pytorch.org/whl/cu121`
  - Torch version pinned; no transformers by default
- base.gpu-onnx-cu121 (for ONNX/InsightFace/OpenCV)
  - FROM `base.gpu-core-cu121`
  - Adds `onnxruntime-gpu`, `opencv-python-headless` (pinned)
- Optional extras (evaluate per adoption):
  - base.cpu-audio-extras (webrtcvad, sounddevice, pvporcupine)
  - base.gpu-ml-audio-extras (extends gpu-ml-cu121 with audio libs)

Note: Prefer service-level extras initially to avoid premature bloat; move to extras families once ≥3 services share the exact pins.

---

### C. Optimization & standardization plan

- Image size reduction
  - Multi-stage builds with venv copy; builder includes compilers, runtime does not.
  - Combine apt operations, use `--no-install-recommends`, and clear apt lists.
  - `.dockerignore` already excludes models, logs, artifacts; ensure service directories add local ignores for tests/dev-only data.
  - Target reduction: 30–60% vs naïve single-stage images (range depends on service footprints and torch presence).

- Build-time optimization
  - Layer ordering: COPY requirements → install deps → COPY source (maximize cache reuse).
  - Share families so torch/CUDA layers are cached across GPU services.
  - Use BuildKit + Buildx with registry cache export/import between CI jobs.
  - Prebuild and publish family images on version bumps only.

- Dependency minimization for legacy agents
  - Use `/workspace/scripts/extract_individual_requirements.py` in builder to emit minimal per-agent `requirements.txt` by static import scan; pip-install that file.
  - For dynamic imports or plugin loading, mark with “uncertain — ask” and optionally allow a safe manual allowlist.
  - Maintain service-specific `constraints.txt` for pins; adopt `pip-compile` workflow if needed.

- Standardization
  - Non-root `USER` in runtime stage
  - `ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1`
  - Healthchecks present for any HTTP/gRPC service; ZMQ ping fallback where applicable
  - Consistent `PYTHONPATH=/app`; repository layout standardized so `common/` is always available

- Security posture
  - Minimal packages, non-root runtime, small surface area
  - Add CI CVE scanning (e.g., Trivy or Grype) with policy gates (see Open Questions for tool/policy)

- Reproducibility
  - Pin exact versions in `requirements.txt`
  - For critical services, adopt `--require-hashes` (pip hash mode) managed via `pip-compile --generate-hashes`
  - Pin family bases by digest (e.g., `nvidia/cuda@sha256:...`) once finalized

---

### D. Hardware-aware defaults (MainPC vs PC2)

Set safe defaults via ENV; override per service with env vars or startup config.

MainPC (RTX 4090, high CPU)
- GPU env:
  - `NVIDIA_VISIBLE_DEVICES=all`
  - `NVIDIA_DRIVER_CAPABILITIES=compute,utility`
  - `CUDA_DEVICE_ORDER=PCI_BUS_ID`
  - `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb=64`
- Threads/workers:
  - `OMP_NUM_THREADS=8`, `MKL_NUM_THREADS=8`
  - For uvicorn apps: `UVICORN_WORKERS=4` (service-specific tuning allowed)

PC2 (RTX 3060, low-power CPU)
- GPU env:
  - Same visibility; prefer smaller batches and concurrency in the app
- Threads/workers:
  - `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`
  - `UVICORN_WORKERS=1`
- Fallbacks:
  - Prefer CPU fallback where feasible (e.g., STT Whisper cpp path already present).

GPU readiness checks (at startup and/or health)
- Torch services: probe `torch.cuda.is_available()` and log device names; fail-fast if `REQUIRED_GPU=true` and not available.
- Non-torch GPU users (NVML/ONNX): check NVML device count and/or ONNX GPU provider availability; log and degrade gracefully if allowed.

---

### E. Concrete EXAMPLE Dockerfiles (reference only; not to be committed)

These examples assume build context is the repo root (`/workspace`). They demonstrate multi-stage builds, minimal runtime layers, and correct COPY paths.

1) ModelOpsCoordinator (MainPC-optimized; CUDA 12.1, torch cu121)

```dockerfile
# syntax=docker/dockerfile:1.6

FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv python3-pip python3-distutils \
    curl ca-certificates build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app
COPY model_ops_coordinator/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cu121 -r /tmp/requirements.txt

# Copy only what is needed to run
COPY model_ops_coordinator/ /app/model_ops_coordinator/
COPY common/ /app/common/

WORKDIR /app/model_ops_coordinator
RUN python -m py_compile app.py

FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH="/app" \
    NVIDIA_VISIBLE_DEVICES="all" \
    NVIDIA_DRIVER_CAPABILITIES="compute,utility" \
    CUDA_DEVICE_ORDER="PCI_BUS_ID" \
    PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True,max_split_size_mb=64" \
    OMP_NUM_THREADS="8" \
    MKL_NUM_THREADS="8"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r moc && useradd -r -g moc -d /app -s /bin/bash moc
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app
RUN mkdir -p /app/data /app/logs /app/config && chown -R moc:moc /app
USER moc

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -sf http://localhost:8008/health || exit 1

EXPOSE 7211 7212 8008
WORKDIR /app/model_ops_coordinator
CMD ["python", "app.py"]
```

2) MemoryFusionHub (PC2-optimized; CPU-only)

```dockerfile
# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app
COPY memory_fusion_hub/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY memory_fusion_hub/ /app/memory_fusion_hub/
COPY common/ /app/common/
RUN python -m py_compile /app/memory_fusion_hub/app.py

FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH="/app" \
    OMP_NUM_THREADS="1" \
    UVICORN_WORKERS="1"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r mfh && useradd -r -g mfh -d /app -s /bin/bash mfh
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app
RUN mkdir -p /app/logs /app/data /app/cache && chown -R mfh:mfh /app
USER mfh

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -sf http://localhost:8080/health || exit 1

EXPOSE 8080 50051 5555
WORKDIR /app/memory_fusion_hub
CMD ["python", "app.py", "--config", "/app/memory_fusion_hub/config/default.yaml", "--log-level", "INFO"]
```

3) Simple legacy agent (ServiceRegistry; CPU-only; auto-minimized deps)

```dockerfile
# syntax=docker/dockerfile:1.6

FROM python:3.10-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app
COPY scripts/extract_individual_requirements.py /app/scripts/extract_individual_requirements.py
COPY main_pc_code/agents/ /app/main_pc_code/agents/
COPY common/ /app/common/

RUN python /app/scripts/extract_individual_requirements.py service_registry_agent \
    --workspace /app \
    --output /tmp/requirements_agent.txt
RUN pip install --no-cache-dir -r /tmp/requirements_agent.txt

FROM python:3.10-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH="/app"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r svc && useradd -r -g svc -d /app -s /bin/bash svc
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/main_pc_code/ /app/main_pc_code/
COPY --from=builder /app/common/ /app/common/
USER svc

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -sf http://localhost:${HEALTH_PORT:-7200}/health || exit 1

CMD ["python", "main_pc_code/agents/service_registry_agent.py"]
```

---

### F. Fleet coverage table (100% of active agents)

Key to base families: `cpu-core`, `cpu-web`, `gpu-core-cu121`, `gpu-ml-cu121`, `gpu-onnx-cu121` (extras noted in “notes”). Where needs are uncertain, they’re marked and listed under Open Questions.

| service | machine(s) | needs (CPU/GPU/Web/Audio/Vision) | proposed base family | entrypoint | ports | healthcheck | notes |
|---|---|---|---|---|---|---|---|
| ServiceRegistry | MainPC | CPU | cpu-core | main_pc_code/agents/service_registry_agent.py | 7200/8200 | TCP/HTTP (uncertain — ask) | ZMQ-based; add HTTP /health or ZMQ ping |
| SystemDigitalTwin | MainPC | CPU | cpu-core | main_pc_code/agents/system_digital_twin.py | 7220/8220 | TCP/HTTP (uncertain — ask) | Uses Redis; no GPU |
| UnifiedSystemAgent | MainPC | CPU | cpu-core | main_pc_code/agents/unified_system_agent.py | 7201/8201 | TCP/HTTP (uncertain — ask) | Coordinator logic; no GPU libs |
| SelfHealingSupervisor | MainPC, PC2 | CPU | cpu-core | services/self_healing_supervisor/supervisor.py | 7009/9008 | HTTP (add /health) | Uses Docker SDK; CPU-only |
| MemoryFusionHub | MainPC, PC2 | CPU, gRPC | cpu-core | memory_fusion_hub/app.py | 5713/6713 (+8080 metrics) | HTTP 8080 | No GPU libs required |
| ModelOpsCoordinator | MainPC | GPU (torch), REST/gRPC | gpu-ml-cu121 | model_ops_coordinator/app.py | 7211,7212,8008 | HTTP 8008 | Torch cu121; RTX 4090 optimized |
| AffectiveProcessingCenter | MainPC | GPU (torch+audio) | gpu-ml-cu121 | affective_processing_center/app.py | 5560/6560 | HTTP/ZMQ (uncertain — ask) | requirements include torch/torchaudio |
| RealTimeAudioPipeline | MainPC, PC2 | GPU (torch), Audio | gpu-ml-cu121 | real_time_audio_pipeline/app.py | 5557/6557 | HTTP (uncertain — ask) | audio extras needed (webrtcvad, sounddevice) |
| CrossMachineGPUScheduler | MainPC | CPU + NVML | cpu-core | services/cross_gpu_scheduler/app.py | 7155/8155 | HTTP 8155 | Needs NVIDIA runtime for NVML access |
| FaceRecognitionAgent | MainPC | GPU (Vision, ONNX) | gpu-onnx-cu121 | main_pc_code/agents/face_recognition_agent.py | 5610/6610 | HTTP/ZMQ (uncertain — ask) | InsightFace + ONNX CUDA providers |
| LearningOpportunityDetector | MainPC | CPU (uncertain) | cpu-core | main_pc_code/agents/learning_opportunity_detector.py | 7202/8202 | TCP/HTTP (uncertain — ask) | Likely RPC into ModelOps |
| LearningManager | MainPC | GPU (uncertain) | gpu-ml-cu121 (uncertain) | main_pc_code/agents/learning_manager.py | 5580/6580 | TCP/HTTP (uncertain — ask) | May schedule GPU training slices |
| ActiveLearningMonitor | MainPC | CPU | cpu-core | main_pc_code/agents/active_learning_monitor.py | 5638/6638 | TCP/HTTP (uncertain — ask) | Monitoring/orchestration |
| IntentionValidatorAgent | MainPC | CPU | cpu-core | main_pc_code/agents/IntentionValidatorAgent.py | 5701/6701 | TCP/HTTP (uncertain — ask) | NLU pipeline client |
| NLUAgent | MainPC | CPU | cpu-core | main_pc_code/agents/nlu_agent.py | 5709/6709 | TCP/HTTP (uncertain — ask) | NLU client; RPC to models |
| AdvancedCommandHandler | MainPC | CPU | cpu-core | main_pc_code/agents/advanced_command_handler.py | 5710/6710 | TCP/HTTP (uncertain — ask) | Dialogue manager |
| ChitchatAgent | MainPC | CPU | cpu-core | main_pc_code/agents/chitchat_agent.py | 5711/6711 | TCP/HTTP (uncertain — ask) | Dialogue client |
| FeedbackHandler | MainPC | CPU | cpu-core | main_pc_code/agents/feedback_handler.py | 5636/6636 | TCP/HTTP (uncertain — ask) | Feedback processing |
| Responder | MainPC | CPU | cpu-core | main_pc_code/agents/responder.py | 5637/6637 | TCP/HTTP (uncertain — ask) | Integrates with TTS/STT; no torch |
| DynamicIdentityAgent | MainPC | CPU | cpu-core | main_pc_code/agents/DynamicIdentityAgent.py | 5802/6802 | TCP/HTTP (uncertain — ask) | Identity logic |
| EmotionSynthesisAgent | MainPC | CPU (uncertain) | cpu-core (uncertain) | main_pc_code/agents/emotion_synthesis_agent.py | 5706/6706 | TCP/HTTP (uncertain — ask) | Might rely on ModelOps; verify |
| STTService | MainPC | GPU (whisper via ModelOps) | gpu-ml-cu121 | main_pc_code/services/stt_service.py | 5800/6800 | TCP/HTTP (uncertain — ask) | Sends requests with device=cuda; torch via ModelOps |
| TTSService | MainPC | CPU (likely) | cpu-core | main_pc_code/services/tts_service.py | 5801/6801 | TCP/HTTP (uncertain — ask) | Uses sounddevice; GPU work delegated |
| AudioCapture | MainPC | CPU, Audio | cpu-core (audio extras) | main_pc_code/agents/streaming_audio_capture.py | 6550/7550 | TCP/HTTP (uncertain — ask) | RTAP gating via env |
| FusedAudioPreprocessor | MainPC | CPU, Audio | cpu-core (audio extras) | main_pc_code/agents/fused_audio_preprocessor.py | 6551/7551 | TCP/HTTP (uncertain — ask) | Audio DSP |
| StreamingInterruptHandler | MainPC | CPU | cpu-core | main_pc_code/agents/streaming_interrupt_handler.py | 5576/6576 | TCP/HTTP (uncertain — ask) | Control-plane |
| StreamingSpeechRecognition | MainPC | CPU (calls STT) | cpu-core | main_pc_code/agents/streaming_speech_recognition.py | 6553/7553 | TCP/HTTP (uncertain — ask) | Client to STTService |
| StreamingTTSAgent | MainPC | CPU | cpu-core | main_pc_code/agents/streaming_tts_agent.py | 5562/6562 | TCP/HTTP (uncertain — ask) | Client to TTSService |
| WakeWordDetector | MainPC | CPU, Audio | cpu-core (audio extras) | main_pc_code/agents/wake_word_detector.py | 6552/7552 | TCP/HTTP (uncertain — ask) | pvporcupine |
| StreamingLanguageAnalyzer | MainPC | CPU | cpu-core | main_pc_code/agents/streaming_language_analyzer.py | 5579/6579 | TCP/HTTP (uncertain — ask) | Analyzer client |
| ProactiveAgent | MainPC | CPU | cpu-core | main_pc_code/agents/ProactiveAgent.py | 5624/6624 | TCP/HTTP (uncertain — ask) | Proactivity logic |
| EmotionEngine | MainPC | CPU | cpu-core | main_pc_code/agents/emotion_engine.py | 5590/6590 | TCP/HTTP (uncertain — ask) | Emotion logic |
| MoodTrackerAgent | MainPC | CPU | cpu-core | main_pc_code/agents/mood_tracker_agent.py | 5704/6704 | TCP/HTTP (uncertain — ask) | Tracker |
| HumanAwarenessAgent | MainPC | CPU | cpu-core | main_pc_code/agents/human_awareness_agent.py | 5705/6705 | TCP/HTTP (uncertain — ask) | Awareness logic |
| ToneDetector | MainPC | CPU, Audio | cpu-core (audio extras) | main_pc_code/agents/tone_detector.py | 5625/6625 | TCP/HTTP (uncertain — ask) | Audio features |
| VoiceProfilingAgent | MainPC | CPU, Audio | cpu-core (audio extras) | main_pc_code/agents/voice_profiling_agent.py | 5708/6708 | TCP/HTTP (uncertain — ask) | Profiling |
| EmpathyAgent | MainPC | CPU | cpu-core | main_pc_code/agents/EmpathyAgent.py | 5703/6703 | TCP/HTTP (uncertain — ask) | Dialogue feature |
| CloudTranslationService | MainPC | CPU, HTTP client | cpu-core | main_pc_code/agents/cloud_translation_service.py | 5592/6592 | HTTP (add /health) | Calls external APIs |
| StreamingTranslationProxy | MainPC | CPU-Web, WS | cpu-web | services/streaming_translation_proxy/proxy.py | 5596/6596 (+9106 metrics) | HTTP /health | FastAPI + WS + Prom |
| ObservabilityDashboardAPI | MainPC | CPU-Web | cpu-web | services/obs_dashboard_api/server.py | 8001/9007 (+9107 metrics) | HTTP /health | FastAPI + Prom |
| UnifiedObservabilityCenter | MainPC, PC2 | CPU-Web | cpu-web | unified_observability_center/app.py | 9100/9110 | HTTP /health | Present in PC2 config; MainPC via groups (uncertain — ask) |
| CodeGenerator | MainPC | CPU | cpu-core | main_pc_code/agents/code_generator_agent.py | 5650/6650 | TCP/HTTP (uncertain — ask) | Utility |
| PredictiveHealthMonitor | MainPC | CPU | cpu-core | main_pc_code/agents/predictive_health_monitor.py | 5613/6613 | TCP/HTTP (uncertain — ask) | Utility |
| Executor | MainPC | CPU | cpu-core | main_pc_code/agents/executor.py | 5606/6606 | TCP/HTTP (uncertain — ask) | Utility |
| SmartHomeAgent | MainPC | CPU | cpu-core | main_pc_code/agents/smart_home_agent.py | 7125/8125 | TCP/HTTP (uncertain — ask) | Optional |
| ChainOfThoughtAgent | MainPC | CPU (GPU via RPC) | cpu-core | main_pc_code/FORMAINPC/chain_of_thought_agent.py | 5612/6612 | TCP/HTTP (uncertain — ask) | Reasoning, uses ModelOps |
| GoTToTAgent | MainPC | CPU (GPU via RPC) | cpu-core | main_pc_code/FORMAINPC/got_tot_agent.py | 5646/6646 | TCP/HTTP (uncertain — ask) | Optional |
| CognitiveModelAgent | MainPC | CPU (GPU via RPC) | cpu-core | main_pc_code/FORMAINPC/cognitive_model_agent.py | 5641/6641 | TCP/HTTP (uncertain — ask) | Optional |
| CentralErrorBus | PC2 | CPU | cpu-core | services/central_error_bus/error_bus.py | 7150/8150 | HTTP (add /health) | pyzmq + Prom |
| RealTimeAudioPipelinePC2 | PC2 | GPU (torch), Audio | gpu-ml-cu121 | real_time_audio_pipeline/app.py | 5557/6557 | HTTP (uncertain — ask) | audio extras needed |
| TieredResponder | PC2 | CPU | cpu-core | pc2_code/agents/tiered_responder.py | 7100/8100 | TCP/HTTP (uncertain — ask) | Async pipeline |
| AsyncProcessor | PC2 | CPU | cpu-core | pc2_code/agents/async_processor.py | 7101/8101 | TCP/HTTP (uncertain — ask) | Async pipeline |
| CacheManager | PC2 | CPU | cpu-core | pc2_code/agents/cache_manager.py | 7102/8102 | TCP/HTTP (uncertain — ask) | Cache/Memory |
| VisionProcessingAgent | PC2 | GPU (Vision) | gpu-onnx-cu121 (uncertain) | pc2_code/agents/VisionProcessingAgent.py | 7160/8160 | TCP/HTTP (uncertain — ask) | May use OpenCV/ONNX |
| DreamWorldAgent | PC2 | GPU (likely torch) | gpu-ml-cu121 (uncertain) | pc2_code/agents/DreamWorldAgent.py | 7104/8104 | TCP/HTTP (uncertain — ask) | Dream sim |
| ResourceManager | PC2 | CPU | cpu-core | pc2_code/agents/resource_manager.py | 7113/8113 | TCP/HTTP (uncertain — ask) | Infra core |
| TaskScheduler | PC2 | CPU | cpu-core | pc2_code/agents/task_scheduler.py | 7115/8115 | TCP/HTTP (uncertain — ask) | Infra core |
| AuthenticationAgent | PC2 | CPU | cpu-core | pc2_code/agents/ForPC2/AuthenticationAgent.py | 7116/8116 | TCP/HTTP (uncertain — ask) | Security |
| UnifiedUtilsAgent | PC2 | CPU | cpu-core | pc2_code/agents/ForPC2/unified_utils_agent.py | 7118/8118 | TCP/HTTP (uncertain — ask) | Utility |
| ProactiveContextMonitor | PC2 | CPU | cpu-core | pc2_code/agents/ForPC2/proactive_context_monitor.py | 7119/8119 | TCP/HTTP (uncertain — ask) | Memory context |
| AgentTrustScorer | PC2 | CPU | cpu-core | pc2_code/agents/AgentTrustScorer.py | 7122/8122 | TCP/HTTP (uncertain — ask) | Security scoring |
| FileSystemAssistantAgent | PC2 | CPU | cpu-core | pc2_code/agents/filesystem_assistant_agent.py | 7123/8123 | TCP/HTTP (uncertain — ask) | Filesystem ops |
| RemoteConnectorAgent | PC2 | CPU | cpu-core | pc2_code/agents/remote_connector_agent.py | 7124/8124 | TCP/HTTP (uncertain — ask) | Networking |
| UnifiedWebAgent | PC2 | CPU-Web | cpu-web | pc2_code/agents/unified_web_agent.py | 7126/8126 | HTTP /health (if present) | Web interface |
| DreamingModeAgent | PC2 | GPU (likely torch) | gpu-ml-cu121 (uncertain) | pc2_code/agents/DreamingModeAgent.py | 7127/8127 | TCP/HTTP (uncertain — ask) | Ties to DreamWorld |
| AdvancedRouter | PC2 | CPU | cpu-core | pc2_code/agents/advanced_router.py | 7129/8129 | TCP/HTTP (uncertain — ask) | Routing |
| TutoringServiceAgent | PC2 | CPU | cpu-core | pc2_code/agents/TutoringServiceAgent.py | 7108/8108 | TCP/HTTP (uncertain — ask) | Tutoring |
| SpeechRelayService | PC2 | CPU, gRPC | cpu-core | services/speech_relay/relay.py | 7130/8130 (+9109 metrics) | HTTP metrics only | gRPC server + ZMQ client |

Notes:
- Metrics ports for some services (e.g., 9106/9107/9109) are included where code shows Prometheus exporters.
- For rows with “HTTP (uncertain — ask)”, add a uniform `/health` route or provide a lightweight gRPC/ZMQ health RPC where applicable.

---

### G. Risk register & rollback considerations

- Risk: CUDA/toolchain mismatches across machines
  - Mitigation: Single default track (cu121) for both; optional cu124 only when validated. Pin family base by digest.
- Risk: Image bloat from shared families
  - Mitigation: Families contain only truly shared deps; extras remain per-service until ≥3 adopters.
- Risk: Legacy agent hidden dynamic deps
  - Mitigation: Use extractor-generated requirements; add explicit allowlist when dynamic imports are detected. Build smoke tests to validate imports.
- Risk: GPU not available at runtime (driver/runtime issues)
  - Mitigation: Startup GPU probe; if `REQUIRED_GPU=true`, fail fast with clear logs; otherwise degrade to CPU when possible (PC2 safety).
- Risk: CI runtime without GPU for GPU images
  - Mitigation: Build-only in CPU CI runners; run smoke tests that don’t require device; run device tests on dedicated GPU runners nightly.
- Rollback
  - Keep legacy Dockerfiles and images tagged for one minor release window; ability to revert to service-level images while base families stabilize.

---

### H. Open questions (blocking/clarifying)

1) Registry and naming: Confirm registry (e.g., GHCR) and final naming pattern `ghcr.io/<org>/<family>:<tag>` and digest pinning policy.
2) Python targets: Default new hubs to Python 3.11, allow py3.10 for legacy agents. Acceptable?
3) CUDA track: Adopt cu12.1 by default now and offer cu12.4 variant for MainPC where beneficial? OK?
4) Vulnerability scanner: Preference (Trivy vs Grype) and gating policy (fail on HIGH/CRITICAL?).
5) Healthchecks: For non-web agents, standardize on HTTP `/health`, gRPC health, or ZMQ ping? Which is preferred?
6) Audio/Vision extras: Which agents require mandatory `sounddevice`, `webrtcvad`, `pvporcupine`, `opencv-python-headless`, `onnxruntime-gpu` in-base vs per-service?
7) CI constraints: Availability of GPU runners, registry-cache capacity limits, and artifact retention requirements?
8) UnifiedObservabilityCenter on MainPC: It appears in groups but not explicitly listed as an agent. Should it run on MainPC as well? If yes, confirm ports/env.
9) torch pinning: For services with torch requirements outside ModelOps (e.g., RTAP, AffectiveProcessingCenter), confirm exact versions and whether they must match ModelOpsCoordinator.

---

### Evidence & quality gates (how this proposal meets them)

- Image size reduction plan
  - Multi-stage builder+runtime; families for shared heavy layers; no GPU libs in CPU images.
  - Target reduction: 30–60% vs naïve single-stage baselines.
- Build-time optimization
  - Cache-friendly layer ordering, shared family layers, Buildx cache export/import.
  - Optional prebuilt family images to avoid repeated torch/CUDA installs.
- Security posture
  - Non-root, minimal apt packages, explicit healthchecks, CVE scanning in CI (tool TBD).
- Reproducibility
  - Pin versions; encourage `--require-hashes` for critical services; pin base images by digest; avoid implicit latest.
- GPU readiness
  - Startup probes using torch/NVML; configurable fail-fast vs graceful fallback.
- PC2 safety
  - Conservative threads/workers and CPU fallbacks; no unnecessary GPU stacks in CPU services.
- CI integration sketch
  - Build matrix: families × machines; publish family bases on version bump; re-use registry cache.
  - Fail-fast on lint/import checks; optional nightly GPU device tests.

---

### Implementation Plan (post-approval)

1) Confirm registry, naming, and CUDA track choices (see Open Questions 1–3).
2) Build and publish family base images:
   - base.cpu-core and base.cpu-web (py311; py310 variants for legacy)
   - base.gpu-core-cu121, base.gpu-ml-cu121, base.gpu-onnx-cu121
3) Select 3–5 representative services per family and prototype Dockerfiles; measure size/time improvements; adjust pins.
4) Introduce standardized healthcheck helpers (HTTP/gRPC/ZMQ) and add to CPU-only agents.
5) CI integration:
   - Buildx with cache import/export; CVE scanning; optional GPU smoke tests on dedicated runners.
   - Adopt `pip-compile` and `--require-hashes` for critical services.
6) Gradual rollout: migrate hubs first (ModelOpsCoordinator, MemoryFusionHub, UOC), then GPU-heavy services, then remaining legacy agents with auto-minimized deps.
7) Observability: compare image sizes and build times; aim for 30–60% reduction; publish before/after metrics.

---

Confidence: 88%