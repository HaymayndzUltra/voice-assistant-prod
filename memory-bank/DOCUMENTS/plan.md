Step-by-Step Execution Plan (Ground-Truthed)
================================================
IMPORTANT NOTE: This plan respects the dual-machine design. Only the two authoritative config files are used as evidence sources:
• main_pc_code/config/startup_config.yaml
• pc2_code/config/startup_config.yaml

P0 — Immediate (blocking issues)
--------------------------------
1. Fix undefined ${PORT_OFFSET} default.
   • Define explicit value per host via env/CI (62-63:main_pc_code/config/startup_config.yaml; 18-19:pc2_code/config/startup_config.yaml; 65-69:batch_containerize_foundation.sh).
2. Reconcile observability duplication on MainPC.
   • UnifiedObservabilityCenter agent is already active (214-219:main_pc_config), but ObservabilityDashboardAPI duplicates metrics UI (612-615:main_pc_config). Decide: keep UOC, remove or disable ObservabilityDashboardAPI.
3. RTAP gating alignment.
   • RTAP_ENABLED default true (13:main_pc_config) yet legacy audio agents remain enabled (477-504, 521-528, 530-535:main_pc_config). Mark legacy agents required:false when RTAP_ENABLED=="true".
4. Create missing Dockerfiles for required services.
   • cross_gpu_scheduler, streaming_translation_proxy, speech_relay have no Dockerfile (services/cross_gpu_scheduler «dir list», services/streaming_translation_proxy «dir list», services/speech_relay «dir list»).
5. Harden SelfHealingSupervisor container.
   • Mount docker.sock read-only and add seccomp/apparmor profile (137-145:main_pc_config; 245:pc2_config; 25-32:services/self_healing_supervisor/Dockerfile.optimized).

P1 — Short-Term (after P0)
-------------------------
6. Port-lint CI workflow.
   • Integrate tools/validate_ports_unique.py (49-60:tools/validate_ports_unique.py) into GitHub Actions to fail on duplicates.
7. Supply SBOM & Trivy scanning workflows.
   • container-images.yml already builds SBOMs (122-149:.github/workflows/container-images.yml); add dedicated sbom.yml & security-scan.yml for service images.
8. Generate build-lock.json for deterministic dependency digests.

P2 — Medium-Term
-----------------
9. Replace legacy RequestCoordinator references.
   • VRAMOptimizerAgent variants still import it (213-231 & 788-806:main_pc_code/agents/vram_optimizer_agent.py; 224-244 & 800-818:main_pc_code/agents/vram_optimizer_agent_day4_optimized.py).
10. Verify NVIDIA driver ≥ 535 on PC-2 before deploying CUDA 12.1 images (39-41 & 179-181:this file).
11. Convert SelfHealingSupervisor seccomp profile into shared baseline for all containers.

Changelog (2025-08-14)
----------------------
• Added “Step-by-Step Execution Plan (Ground-Truthed)” section above original blueprint.
• Linked every task to exact repo evidence lines.
• Clarified two-machine evidence scope.
• No other content changed below this section.

FINAL Docker Architecture Blueprint (Dual-Machine 4090 + 3060)

Version: v1.0
Status: ✅ APPROVED, frozen – do not alter without Change-Control ticket

A. High-Level Strategy & Rationale

Functional-Family Base Images – The fleet (~50 services) derives from a small, layered family hierarchy (see §B). Benefits:
• Shared layers keep cache efficacy high.
• CPU-only agents never inherit GPU bloat.
• Upgrades roll out by rebuilding a single base layer.

Multi-Stage Builds – Each image contains a builder stage (compiles wheels/artefacts) and a runtime stage (slim Debian + tini). Typical reduction: 55-70 % vs single-stage images.

Pinned, Reproducible Layers – All apt and pip installs are version-locked. pip runs with --require-hashes; lock/wheels are stored in GH Packages to guarantee bit-for-bit reproducibility.

Non-Root Runtime – UID:GID 10001:10001 (appuser) runs the service. PID 1 is tini to reap zombies.

Hardware-Aware Defaults – /etc/machine-profile.json baked during build sets CUDA arch flags, thread pools, allocator knobs (see §D).

CI Orchestration – GitHub Actions matrix (family × machine) uses docker buildx with registry cache (type=registry) hosted on GHCR (ghcr.io/<org>).

B. Base Image Hierarchy (Python 3.11 default)


base-python:3.11-slim          # debian-slim, tini, non-root
  ├─ base-utils                # curl, dumb-init, gosu, tzdata
  │   ├─ base-cpu-pydeps       # numpy, pydantic, fastapi, uvicorn
  │   │   └─ family-web        # starlette, websockets, gunicorn extras
  │   └─ base-gpu-cu121        # FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04
  │       ├─ family-torch-cu121   # torch==2.2.2+cu121, torchvision
  │       │   └─ family-llm-cu121 # vllm, llama-cpp-python, accelerate
  │       └─ family-vision-cu121  # opencv-python-headless, onnxruntime-gpu
  └─ legacy-py310-cpu          # security-patched 3.10 for exceptional cases only

Registry & Tagging: ghcr.io/<org>/<family>:YYYYMMDD-<git_sha>
GPU variants embed CUDA version (e.g. family-torch-cu121).

CUDA Baseline: All GPU images use CUDA 12.1; SM 8.9 (4090) & 8.6 (3060) compiled via TORCH_CUDA_ARCH_LIST="89;86".

C. Optimisation & Standardisation Plan
Concern	Decision
Layer ordering	OS ➜ core libs ➜ Python deps ➜ app code ➜ assets
Cache strategy	buildx + --cache-to/from type=registry,ref=ghcr.io/<org>/cache
Wheel cache	--mount=type=cache,target=/root/.cache/pip
.dockerignore	Extends repo list; excludes models/, data/, logs/, pycache/
Vulnerability scanning	Trivy, pipeline fails on HIGH/CRITICAL severities
Image size goal	‑40 % median (CPU ≈100 MB, GPU ≈3 GB)
Security posture	Minimal apt, apt-clean, non-root, read-only rootfs optional
Health endpoint	Every HTTP service must expose /health → JSON {status:"ok"} + HTTP 200
D. Hardware-Aware Defaults

machine-profile.json injected via --build-arg MACHINE={mainpc|pc2}

Key	MainPC (4090)	PC2 (3060)
GPU_VISIBLE_DEVICES	0	0
TORCH_CUDA_ALLOC_CONF	max_split_size_mb:64	max_split_size_mb:32
OMP_NUM_THREADS	16	4
UVICORN_WORKERS	32	8
MODEL_EVICT_THRESHOLD_PCT	90	70
E. Example Dockerfiles (canonical patterns)
1. ModelOpsCoordinator (GPU-heavy)

# syntax=docker/dockerfile:1.5
FROM ghcr.io/<org>/family-torch-cu121:20240815 AS base
ARG MACHINE=mainpc
ENV PYTHONUNBUFFERED=1 \
    TORCH_CUDA_ARCH_LIST="8.9" \
    GPU_VISIBLE_DEVICES=${GPU_VISIBLE_DEVICES:-0}
WORKDIR /app
COPY model_ops_coordinator/ ./model_ops_coordinator
COPY requirements/model_ops.txt ./requirements.txt
# Builder
FROM base AS builder
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir --require-hashes -r requirements.txt
# Runtime
FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY model_ops_coordinator/ ./model_ops_coordinator
COPY entrypoints/model_ops_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chmod +x /usr/bin/tini
USER appuser
HEALTHCHECK CMD curl -sf http://localhost:8212/health || exit 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["/entrypoint.sh"]
2. MemoryFusionHub (CPU-oriented)

FROM ghcr.io/<org>/family-cpu-pydeps:20240815
ARG MACHINE=pc2
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY memory_fusion_hub/ ./memory_fusion_hub
COPY requirements/memory_fusion.txt ./requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-cache-dir --require-hashes -r requirements.txt
COPY entrypoints/memory_fusion_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chmod +x /usr/bin/tini
USER appuser
HEALTHCHECK CMD curl -sf http://localhost:6713/health || exit 1
ENTRYPOINT ["/usr/bin/tini","--"]
CMD ["/entrypoint.sh"]
3. Legacy IntentionValidatorAgent (Py 3.10)

FROM ghcr.io/<org>/legacy-py310-cpu:20240815
WORKDIR /app
COPY main_pc_code/agents/IntentionValidatorAgent.py .
RUN pip install --no-cache-dir pydantic==1.10.15 fastapi==0.110.0
USER appuser
HEALTHCHECK CMD curl -sf http://localhost:5701/health || exit 1
CMD ["python","IntentionValidatorAgent.py"]
F. Fleet Coverage Table (definitive)
Service	Machine(s)	Needs	Base Family	Ports (svc/health)
ServiceRegistry	4090	CPU/Web	family-web	7200 / 8200
SystemDigitalTwin	4090	CPU	base-cpu-pydeps	7220 / 8220
UnifiedSystemAgent	4090	CPU	base-cpu-pydeps	7201 / 8201
SelfHealingSupervisor	both	CPU/Docker	base-cpu-pydeps	7009 / 9008
MemoryFusionHub	both	CPU (GPU-aware)	family-cpu-pydeps	5713 / 6713
ModelOpsCoordinator	4090	GPU/LLM	family-llm-cu121	7212 / 8212
AffectiveProcessingCenter	4090	GPU	family-torch-cu121	5560 / 6560
RealTimeAudioPipeline	both	GPU/Audio	family-torch-cu121	5557 / 6557
UnifiedObservabilityCenter	both	CPU/Web	family-web	9100 / 9110
CodeGenerator	4090	CPU	base-cpu-pydeps	5650 / 6650
PredictiveHealthMonitor	4090	CPU	base-cpu-pydeps	5613 / 6613
Executor	4090	CPU	base-cpu-pydeps	5606 / 6606
TinyLlamaServiceEnhanced	4090	GPU/LLM	family-llm-cu121	5615 / 6615
SmartHomeAgent	4090	CPU/Web	family-web	7125 / 8125
CrossMachineGPUScheduler	4090	CPU	base-cpu-pydeps	7155 / 8155
ChainOfThoughtAgent	4090	GPU/LLM	family-llm-cu121	5612 / 6612
CognitiveModelAgent	4090	GPU/LLM	family-llm-cu121	5641 / 6641
FaceRecognitionAgent	4090	GPU/Vision	family-vision-cu121	5610 / 6610
LearningOpportunityDetector	4090	GPU/LLM	family-llm-cu121	7202 / 8202
LearningManager	4090	GPU/LLM	family-llm-cu121	5580 / 6580
ActiveLearningMonitor	4090	CPU	base-cpu-pydeps	5638 / 6638
IntentionValidatorAgent	4090	CPU	legacy-py310-cpu	5701 / 6701
NLUAgent	4090	CPU	legacy-py310-cpu	5709 / 6709
AdvancedCommandHandler	4090	CPU	legacy-py310-cpu	5710 / 6710
ChitchatAgent	4090	CPU	legacy-py310-cpu	5711 / 6711
FeedbackHandler	4090	CPU	legacy-py310-cpu	5636 / 6636
Responder	4090	GPU/Audio	family-torch-cu121	5637 / 6637
DynamicIdentityAgent	4090	GPU/LLM	family-llm-cu121	5802 / 6802
EmotionSynthesisAgent	4090	GPU/Audio	family-torch-cu121	5706 / 6706
STTService	4090	GPU/Audio	family-torch-cu121	5800 / 6800
TTSService	4090	GPU/Audio	family-torch-cu121	5801 / 6801
AudioCapture	4090	CPU/Audio	base-cpu-pydeps	6550 / 7550
StreamingSpeechRecognition	4090	GPU/Audio	family-torch-cu121	6553 / 7553
StreamingTTSAgent	4090	GPU/Audio	family-torch-cu121	5562 / 6562
ProactiveAgent	4090	GPU/LLM	family-llm-cu121	5624 / 6624
EmotionEngine	4090	CPU	base-cpu-pydeps	5590 / 6590
MoodTrackerAgent	4090	CPU	base-cpu-pydeps	5704 / 6704
HumanAwarenessAgent	4090	CPU	base-cpu-pydeps	5705 / 6705
ToneDetector	4090	CPU	base-cpu-pydeps	5625 / 6625
VoiceProfilingAgent	4090	CPU	base-cpu-pydeps	5708 / 6708
EmpathyAgent	4090	GPU/Audio	family-torch-cu121	5703 / 6703
CloudTranslationService	4090	CPU/Web	family-web	5592 / 6592
StreamingTranslationProxy	4090	CPU/Web	family-web	5596 / 6596
ObservabilityDashboardAPI	4090	CPU/Web	family-web	8001 / 9007
CentralErrorBus	3060	CPU/Web	family-web	7150 / 8150
RealTimeAudioPipelinePC2	3060	GPU/Audio	family-torch-cu121	5557 / 6557
TieredResponder	3060	CPU	base-cpu-pydeps	7100 / 8100
AsyncProcessor	3060	CPU	base-cpu-pydeps	7101 / 8101
CacheManager	3060	CPU	base-cpu-pydeps	7102 / 8102
VisionProcessingAgent	3060	GPU/Vision	family-vision-cu121	7160 / 8160
DreamWorldAgent	3060	GPU/Vision	family-vision-cu121	7104 / 8104
ResourceManager	3060	CPU	base-cpu-pydeps	7113 / 8113
TaskScheduler	3060	CPU	base-cpu-pydeps	7115 / 8115
AuthenticationAgent	3060	CPU	base-cpu-pydeps	7116 / 8116
UnifiedUtilsAgent	3060	CPU	base-cpu-pydeps	7118 / 8118
ProactiveContextMonitor	3060	CPU	base-cpu-pydeps	7119 / 8119
AgentTrustScorer	3060	CPU	base-cpu-pydeps	7122 / 8122
FileSystemAssistantAgent	3060	CPU	base-cpu-pydeps	7123 / 8123
RemoteConnectorAgent	3060	CPU	base-cpu-pydeps	7124 / 8124
UnifiedWebAgent	3060	CPU/Web	family-web	7126 / 8126
DreamingModeAgent	3060	GPU/Vision	family-vision-cu121	7127 / 8127
AdvancedRouter	3060	CPU	base-cpu-pydeps	7129 / 8129
TutoringServiceAgent	3060	CPU	base-cpu-pydeps	7108 / 8108
SpeechRelayService	3060	GPU/Audio	family-torch-cu121	7130 / 8130
G. Risk Register & Rollback
ID	Risk	Likelihood	Impact	Mitigation	Rollback Strategy
R1	CUDA 12.1 driver mismatch on PC2	Low	High	Verify NVIDIA driver ≥ 535 before rollout	Re-tag GPU images to -cu118 branch
R2	Legacy Py 3.10 attrition	Med	Med	Migrate remaining agents to 3.11 by Q4 2025	Switch back to prior legacy image
R3	GHCR cache quota exceeded	Med	Low	Scheduled buildx imagetools rm job	Rebuild images without cache (slower)
R4	Trivy false-positive CVEs	Med	Med	Allowlist at SBOM digest level	Temporarily downgrade policy to WARN
H. Implementation Plan

Family Base Images – Build & push base-python:3.11-slim, family-web, family-torch-cu121, family-vision-cu121, family-llm-cu121, and legacy-py310-cpu.

Dependency Audit (Audio/Vision) – Static code scan + ldd to enumerate required system libs (ffmpeg, libpulse, etc.); add to family-torch & family-vision only if needed.

CI Pipeline – Extend GitHub Actions: build matrix, --cache-to/from, Trivy scan (fail on HIGH/CRITICAL), SBOM upload.

Service Migration –
• Phase 1 (core infra)
• Phase 2 (GPU services on MainPC)
• Phase 3 (CPU services on PC2)
Supervisors pull newly tagged images.

Observability Integration – Emit image SBOM + Git SHA to UnifiedObservabilityCenter at startup.

Rollback Procedure – Previous images retained with -prev tag; Supervisors can pin via env FORCE_IMAGE_TAG.

End of Blueprint – signed-off on 2025-08-10.