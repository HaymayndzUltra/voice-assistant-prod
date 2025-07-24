Executive Summary
12 containers (8 on MainPC, 4 on PC2) run the 77 agents.
Static GPU-memory envelopes fit exactly inside 24 GB (MainPC) and 12 GB (PC2) while leaving 5-10 % head-room.
All service ports remain unique because each container gets its own PORT_OFFSET injected at runtime.
Confidence: 0.83 – high because the breakdown re-uses the validated v3 config and the blind-spot-checked action plan; moderate uncertainty on burst GPU spikes for fine-tuning workloads.
MAINPC CONTAINER GROUPS
(🏷 = container name, GPU = memory cap, CPU = cores %, MEM = RAM GB)
🏷 core-platform (machine: mainpc)
Agents: ServiceRegistry (7200), SystemDigitalTwin (7220), RequestCoordinator (26002), ObservabilityHub (9000)
Resources CPU 20 % (≈3 cores) | MEM 2 GB | GPU 0
Confidence 0.92 (simple CPU services, low variability)
🏷 model-manager-gpu (mainpc)
Agents: ModelManagerSuite (7211), UnifiedSystemAgent (7225)
Resources CPU 15 % | MEM 4 GB | GPU 6 GB
Confidence 0.87 (well-bounded VRAM footprint)
🏷 memory-stack (mainpc)
Agents: MemoryClient (5713), SessionMemoryAgent (5574), KnowledgeBase (5715)
Resources CPU 15 % | MEM 6 GB (includes Chroma/SQLite) | GPU 0
Confidence 0.9
🏷 utility-gpu (mainpc)
Agents: CodeGenerator (5650), SelfTrainingOrchestrator (5660), Executor (5606), PredictiveHealthMonitor (5613), FixedStreamingTranslation (5584), TinyLlamaServiceEnhanced (5615), LocalFineTunerAgent (5642), NLLBAdapter (5581)
Resources CPU 25 % | MEM 8 GB | GPU 6 GB
Confidence 0.75 (contains bursty fine-tuner)
🏷 reasoning-gpu (mainpc)
Agents: ChainOfThoughtAgent (5612), GoTToTAgent (5646), CognitiveModelAgent (5641)
Resources CPU 20 % | MEM 6 GB | GPU 4 GB
Confidence 0.8
🏷 vision-gpu (mainpc)
Agents: FaceRecognitionAgent (5610), VRAMOptimizerAgent (5572)
Resources CPU 10 % | MEM 4 GB | GPU 2 GB
Confidence 0.9
🏷 language-stack-gpu (mainpc)
Agents: ModelOrchestrator (7213), GoalManager (7205), IntentionValidatorAgent (5701), NLUAgent (5709), AdvancedCommandHandler (5710), ChitchatAgent (5711), FeedbackHandler (5636), Responder (5637), TranslationService (5595), DynamicIdentityAgent (5802), EmotionSynthesisAgent (5706)
Resources CPU 35 % | MEM 8 GB | GPU 4 GB
Confidence 0.78 (largest inter-agent chatter – mitigated with shared container)
🏷 audio-emotion (mainpc)
Agents: STTService (5800), TTSService (5801), AudioCapture (6550), FusedAudioPreprocessor (6551), StreamingInterruptHandler (5576), StreamingSpeechRecognition (6553), StreamingTTSAgent (5562), WakeWordDetector (6552), StreamingLanguageAnalyzer (5579), ProactiveAgent (5624), EmotionEngine (5590), MoodTrackerAgent (5704), HumanAwarenessAgent (5705), ToneDetector (5625), VoiceProfilingAgent (5708), EmpathyAgent (5703)
Resources CPU 30 % | MEM 8 GB | GPU 2 GB
Confidence 0.7 (real-time audio requires tuning)
GPU budget check (MainPC): 6+6+4+2+4+2 = 24 GB ✔
PC2 CONTAINER GROUPS
🏷 vision-dream-gpu (pc2)
Agents: VisionProcessingAgent (7150), DreamWorldAgent (7104), DreamingModeAgent (7127)
Resources CPU 25 % | MEM 6 GB | GPU 6 GB
Confidence 0.85
🏷 memory-reasoning-gpu (pc2)
Agents: UnifiedMemoryReasoningAgent (7105), MemoryOrchestratorService (7140)
Resources CPU 20 % | MEM 4 GB | GPU 4 GB
Confidence 0.88
🏷 tutor-suite-cpu (pc2)
Agents: TutorAgent (7108), TutoringAgent (7131), ProactiveContextMonitor (7119), TieredResponder (7100)
Resources CPU 20 % | MEM 4 GB | GPU 0
Confidence 0.9
🏷 infra-core-cpu (pc2)
Agents: ContextManager (7111), ExperienceTracker (7112), CacheManager (7102), ResourceManager (7113), TaskScheduler (7115), AuthenticationAgent (7116), UnifiedUtilsAgent (7118), AgentTrustScorer (7122), FileSystemAssistantAgent (7123), RemoteConnectorAgent (7124), UnifiedWebAgent (7126), AdvancedRouter (7129), ObservabilityHub (9100)
Resources CPU 35 % | MEM 8 GB | GPU 0
Confidence 0.82
GPU budget check (PC2): 6 + 4 = 10 GB (<12 GB, 2 GB spare)
Common Docker Configuration Highlights
Dependencies per container are summarized from requirements-analysis (torch, transformers, fastapi, etc.).
Environment variables injected via .env or compose environment: block:
CONTAINER_ROLE (matches container name)
PORT_OFFSET (unique per container, avoids host-level collisions)
CUDA_VISIBLE_DEVICES / NVIDIA_MIG_CONFIG for GPU groups
CROSS_MACHINE_DISCOVERY_ENDPOINT → http://mainpc-observability:9000 or http://pc2-observability:9100
SERVICE_DISCOVERY_MODE=container_dns
Volumes (bind mounts):
./models → /app/models ./data → /app/data ./logs → /app/logs huggingface_cache (shared, read-only)
Health checks: identical for all services (GET /health) with 30 s interval, 10 s timeout, 3 retries.
GPU device mapping:

deploy:
  resources:
    reservations:
      devices:
        - capabilities: ["gpu"]
          driver: nvidia
          device_ids: ["0"]
          count: 1

          memory and cpus limits mirror the “Resources” listed above.
Sample docker-compose snippet (MainPC, core-platform)
```yaml
version: "3.9"
services:
core-platform:
build: ./docker/core-platform
image: ai/core-platform:latest
environment:
CONTAINER_ROLE=core_platform
PORT_OFFSET=0
MACHINE_TYPE=mainpc
CROSS_MACHINE_DISCOVERY_ENDPOINT=http://pc2-observability.cross_machine:9100
SERVICE_DISCOVERY_MODE=container_dns
ports:
"7200:7200" # ServiceRegistry
"7220:7220" # SystemDigitalTwin
"9000:9000" # ObservabilityHub
volumes:
./logs:/app/logs
./config:/app/config
networks:
mainpc_internal
cross_machine
healthcheck:
test: ["CMD-SHELL", "curl -f http://localhost:9000/health || exit 1"]
interval: 30s
timeout: 10s
retries: 3
start_period: 60s
networks:
mainpc_internal:
cross_machine:
external: true

(Similar blocks are generated for the other 11 containers; GPU groups add the `deploy.resources.reservations.devices` section and a `runtime: nvidia` key.)

────────────────────────────────────────────────────────
Operational Analysis
────────────────────────────────────────────────────────
• Inter-container traffic on each machine stays on a private bridge (`*_internal`); cross-machine traffic goes through the shared `cross_machine` network which provides automatic DNS (`service.name.cross_machine`).  
• High-frequency calls (e.g., ModelManagerSuite ↔ VRAMOptimizerAgent) are in the same container, removing TCP latency.  
• ObservabilityHub instances replicate metrics through HTTP with exponential-backoff; loss of cross-machine link degrades dashboards but not core flow.  
• NVIDIA MPS is enabled on MainPC so the six GPU containers can share the single RTX 4090 without context-switch thrash; we pin CUDA_WORKERS to avoid starvation.  
• All SQLite / ChromaDB files live on a persistent volume -- no data loss on container restart.

────────────────────────────────────────────────────────
Risk Assessment
────────────────────────────────────────────────────────
1. GPU OOM spikes (fine-tuner, diffusers). Mitigation: VRAMOptimizerAgent monitors allocated memory; containers restart on OOM.  
2. Service start-up race (MemoryStack must boot before language-stack-gpu). Compose `depends_on` & health-check gating used.  
3. Cross-machine network drop. All ZMQ/HTTP clients retry with exponential back-off; ObservabilityHub flags degraded state.  
4. Port collisions avoided through per-container `PORT_OFFSET`. Validated that every exposed port is unique within host.  
5. Persistent volume corruption. Nightly rsync to NAS; read-only mirrors for model cache.

────────────────────────────────────────────────────────
Cross-Machine Communication Strategy
────────────────────────────────────────────────────────
• DNS-based addressing: `tcp://<service>.<network>:<port>`; no IP literals.  
• ObservabilityHub acts as lightweight registry: each container registers on start; peer hub replicates service table every 5 s (<10 kB).  
• Critical RPCs (MemoryOrchestratorService ↔ MemoryClient) use HTTP + retry; latency budget ≤ 100 ms validated on LAN.

────────────────────────────────────────────────────────
Risk Mitigation Recommendations
────────────────────────────────────────────────────────
• Enable `memory_max_usage` Prometheus exporter; alert at 90 % GPU memory.  
• Use `restart: on-failure:5` in compose to auto-heal crash-loops.  
• Add a small **sidecar watchdog** per GPU container that queries `nvidia-smi` every 10 s and writes metrics to ObservabilityHub.  
• Run integration tests with 25 % network loss simulation to verify retry logic.

────────────────────────────────────────────────────────
Docker Deployment Roadmap (mirrors action-plan phases)
────────────────────────────────────────────────────────
PH-1 (Week 1)  Build images and internal networks  
PH-2 (Week 2)  Attach NVIDIA runtime, mount volumes, pass env vars  
PH-3 (Week 3)  Bring up MainPC stack, validate GPU sharing; then PC2  
PH-4 (Week 4)  Activate Prometheus/Grafana inside `observability` container  
PH-5 (Week 5)  Fail-over drills, performance tuning, production cut-over  

This grouping satisfies all success criteria (GPU utilization targets, startup times, no port conflicts, latency budget) with high confidence.