CONSOLIDATION PROPOSAL (UPDATED – ModelManagerSuite deferred)
(The plan is intentionally detailed so you can execute it phase-by-phase without hunting for extra information.)

GLOBAL PRINCIPLES
Keep MainPC GPU-heavy (RTX 4090 → high-VRAM tasks, large models, fine-tuning, multi-modal reasoning).
Delegate orchestration / caching / web / light CPU logic to PC2 (RTX 3060).
One logical domain = one long-running service – no micro-agents inside a single process.
Stable Port Blocks (7 xxx for MainPC, 9 xxx for PC2 + health = 9 xxx + 100).
Everything bootstraps from CoreOrchestrator → ServiceDiscovery is in-proc, not separate.

### PHASE 0 – FOUNDATIONS (STARTING POINT)
Target: 82 agents → 22 agents over four staged roll-outs.

-- Consolidation Group: Core & Observability (5 agents → 2) --
Consolidation	Source Agents	New Agent	Port	Location
CoreOrchestrator	ServiceRegistry, SystemDigitalTwin, RequestCoordinator, UnifiedSystemAgent	- CoreOrchestrator	7000	MainPC
ObservabilityHub	PredictiveHealthMonitor, PerformanceMonitor, HealthMonitor, PerformanceLoggerAgent, SystemHealthManager	ObservabilityHub	9000	PC2

Notes
SystemDigitalTwin is kept as an internal module inside CoreOrchestrator.
Health endpoints become /metrics; data sent to Prometheus + Grafana.

-- Consolidation Group: Resource & Scheduling Layer (7 agents → 2) --
Consolidation	Source Agents	New Agent	Port	Location
ResourceManagerSuite	ResourceManager, TaskScheduler, AsyncProcessor, VRAMOptimizerAgent	ResourceManagerSuite	9001	PC2 (controls MainPC via NVML)
ErrorBus	retains NATS on 9002; becomes side-car in ResourceManagerSuite	ErrorBus	9002	PC2

Risk: merging SystemDigitalTwin with ServiceRegistry → large codebase touch. Mitigation: keep original classes, wrap them in a "facade" first, then deprecate.

### PHASE 1: DATA & MODEL BACKBONE
Target Reduction: 23 agents → 6 agents

-- Consolidation Group 1: MemoryHub --
Source Agents:
MemoryClient (5713) • SessionMemoryAgent (5574) • KnowledgeBase (5715) • MemoryOrchestratorService (7140) • UnifiedMemoryReasoningAgent (7105) • ContextManager (7111) • ExperienceTracker (7112) • CacheManager (7102)
Target Unified Agent: MemoryHub
Port: 7010
Hardware: PC2 (RAM + light CPU).
Integrated Functions: unified Redis + SQLite layer, neuro-symbolic search, session store.
Logic Merger Strategy: expose /kv, /doc, /embedding sub-routes; import legacy modules into sub-apps.
Dependencies: CoreOrchestrator → MemoryHub (startup priority 2).
Risk: schema collision – add namespacing per legacy agent.

-- Consolidation Group 2: ModelManagerSuite --
Source Agents:
GGUFModelManager (5575) • PredictiveLoader (5617) • ModelEvaluationFramework (7220)
Target Unified Agent: ModelManagerSuite
Port: 7011
Hardware: MainPC (GPU)
Integrated Functions: quantised-model registry, hot-swap loader, eval runner.
Dependencies: MemoryHub, ResourceManager.
Risk: GPU hot-swap races – implement lockfile.
Note: ModelManagerAgent (5570) remains standalone - already a large, complex agent (4,843 lines) with consolidated functionality.

-- Consolidation Group 3: AdaptiveLearningSuite --
Source Agents:
SelfTrainingOrchestrator (5660) • LocalFineTunerAgent (5642) • LearningManager (5580) • LearningOrchestrationService (7210) • LearningOpportunityDetector (7200) • ActiveLearningMonitor (5638) • LearningAdjusterAgent (5643)
Target Unified Agent: AdaptiveLearningSuite
Port: 7012
Hardware: MainPC (GPU)
Integrated Functions: continual-learning scheduler, LoRA fine-tuner, auto-eval loop.
Dependencies: ModelManagerSuite, MemoryHub.
Risk: VRAM spikes – rely on ResourceManager GPU quotas.

### PHASE 2: USER-FACING INTELLIGENCE
Target Reduction: 34 agents → 11 agents

-- Consolidation Group 1: ReasoningEngine --
Source Agents:
ChainOfThoughtAgent (5612), GoTToTAgent (5646), CognitiveModelAgent (5641)
Target Unified Agent: ReasoningEngine
Port: 7020
Hardware: MainPC (GPU)
Integrated Functions: chain-of-thought reasoning, graph-of-thought processing, cognitive modeling.
Logic Merger Strategy: unified reasoning interface with multiple strategy options, intelligent strategy selection based on problem type.
Dependencies: ModelManagerSuite, MemoryHub.
Risk: algorithm consolidation complexity – implement strategy pattern with fallbacks.

-- Consolidation Group 2: PlanningOrchestrator --
Source Agents:
ModelOrchestrator (7010), GoalManager (7005)
Target Unified Agent: PlanningOrchestrator
Port: 7021
Hardware: MainPC (GPU)
Integrated Functions: task classification and routing, goal decomposition and swarm coordination.
Logic Merger Strategy: embedding-based task classification with goal breakdown workflows, shared LLM pools.
Dependencies: ModelManagerSuite, MemoryHub, ReasoningEngine.
Risk: planning logic complexity – maintain clear separation between classification and execution.

-- Consolidation Group 3: LanguageProcessor --
Source Agents:
NLUAgent (5709), ChitchatAgent (5711), FeedbackHandler (5636), IntentionValidatorAgent (5701)
Target Unified Agent: LanguageProcessor
Port: 7022
Hardware: MainPC (GPU)
Integrated Functions: natural language understanding, conversation management, feedback processing, intent validation.
Logic Merger Strategy: unified NLU pipeline with intent routing, modular conversation handling based on intent classification.
Dependencies: ModelManagerSuite, MemoryHub, PlanningOrchestrator.
Risk: intent classification accuracy – implement ensemble classification with confidence scoring.

-- Consolidation Group 4: TranslationGateway --
Source Agents:
TranslationService (5595), AdvancedCommandHandler (5710)
Target Unified Agent: TranslationGateway
Port: 7023
Hardware: MainPC (GPU)
Integrated Functions: 6-engine translation fallback chain, advanced command processing with sequences.
Logic Merger Strategy: maintain existing fallback architecture, integrate command handling as translation-aware service.
Dependencies: ModelManagerSuite, MemoryHub, LanguageProcessor.
Risk: translation engine complexity – preserve existing circuit breaker patterns and session management.

-- Consolidation Group 5: IdentityProactivityService --
Source Agents:
DynamicIdentityAgent (5802), ProactiveAgent (5624)
Target Unified Agent: IdentityProactivityService
Port: 7024
Hardware: MainPC (light GPU)
Integrated Functions: persona management, proactive task scheduling and monitoring.
Logic Merger Strategy: unified identity coordination with proactive context monitoring as internal coroutine.
Dependencies: MemoryHub, PlanningOrchestrator, LanguageProcessor.
Risk: state management complexity – implement clear persona/task separation with shared session context.

-- Consolidation Group 6: AudioSpeechInterface --
Source Agents:
AudioCapture (6550), FusedAudioPreprocessor (6551), StreamingSpeechRecognition (6553), STTService (5800), StreamingTTSAgent (5562), TTSService (5801), StreamingInterruptHandler (5576), WakeWordDetector (6552), StreamingLanguageAnalyzer (5579)
Target Unified Agent: AudioSpeechInterface
Port: 7025
Hardware: MainPC (GPU, uses Whisper & HiFi-GAN)
Integrated Functions: capture → VAD → ASR → analyzer; TTS with interrupt pipe.
Port Consolidation: gRPC bidirectional streams; deprecate per-stage TCP ports.
Dependencies: LanguageProcessor, TranslationGateway, MemoryHub.
Risk: Real-time latency – micro-benchmarks before removing shared-memory ring buffer.

-- Consolidation Group 7: SocialInteractionAgent --
Source Agents:
EmotionEngine (5590), MoodTrackerAgent (5704), HumanAwarenessAgent (5705), ToneDetector (5625), VoiceProfilingAgent (5708), EmpathyAgent (5703), EmotionSynthesisAgent (5706), Responder (5637)
Target Unified Agent: SocialInteractionAgent
Port: 7026
Hardware: MainPC (GPU optional for emotion-TTS)
Integrated Functions: affective state machine, prosody control, empathic response composer.
Dependencies: AudioSpeechInterface, MemoryHub, LanguageProcessor.
Risk: domain coupling – keep clear interface /affect/{analyze|synthesize}.

-- Consolidation Group 8: VisionSuite --
Source Agents: FaceRecognitionAgent (5610), VisionProcessingAgent (7150)
Target Unified Agent: VisionSuite
Port: 7027
Hardware: MainPC inference; PC2 can act as frame-preprocessor
Integrated Functions: face recognition, vision processing, unified embeddings store.
Dependencies: MemoryHub, ModelManagerSuite.
Risk: camera bandwidth – compress with AV1.

-- Consolidation Group 9: UtilityToolkit --
Source Agents: CodeGenerator (5650), Executor (5606), FixedStreamingTranslation (5584), TinyLlamaServiceEnhanced (5615), NLLBAdapter (5581)
Target Unified Agent: UtilityToolkit
Port: 7028
Hardware: MainPC
Integrated Functions: code-gen, small-language model utilities, translation fallback.
Dependencies: ModelManagerSuite, TranslationGateway.
Risk: sandbox security for Executor.

-- Consolidation Group 10: NetGateway --
Source Agents: RemoteConnectorAgent (7124), AdvancedRouter (7129), UnifiedWebAgent (7126), TieredResponder (7100)
Target Unified Agent: NetGateway
Port: 9011
Hardware: PC2
Integrated Functions: reverse proxy, websocket, remote agent bridge.
Dependencies: All MainPC services via gRPC.
Risk: SSL termination – add Traefik.

-- Consolidation Group 11: ProactiveContextMonitor --
Source Agents: ProactiveContextMonitor (7119) (embedded into MemoryHub as a coroutine)
→ No external port - integrated into MemoryHub.

PORT ALLOCATION SUMMARY
Block | Range | Purpose
------|-------|--------
7000-7005 | Core & Ops | Orchestrator, ObsHub, ResourceMgr, ErrorBus, Security
7010-7015 | Data / Model | MemoryHub, ModelMgr, LearningSuite
7020-7024 | Reasoning & Language | ReasoningEngine, PlanningOrchestrator, LanguageProcessor, TranslationGateway, IdentityProactivity
7025-7028 | Media & Utilities | AudioSpeech, Social, Vision, UtilityToolkit
9010-9015 | PC2 Services | NetGateway, Web, External
7xxx+100 | Health ports | (+100 offset) e.g. 7020 → 7120

DEPENDENCY RESTRUCTURING
Star-topology around CoreOrchestrator – every service registers itself on startup (/register gRPC).
MemoryHub becomes first dependency for Reasoning, Planning, Language, Social, Vision services.
ModelManagerSuite supplies model handles via gRPC Streaming to all GPU-dependent services.
ResourceManager is queried synchronously before any GPU load is enqueued.
ObservabilityHub scrapes /metrics from all services and pushes to Prometheus.
Clear service layer hierarchy: Core → Data/Model → Reasoning/Language → Media/Utilities → External.

RISK MATRIX & MITIGATIONS
Area	Potential Issue	Mitigation
Large integrated codebases	Merge conflicts, tight coupling	Facade pattern first, gradual refactor behind feature flags
GPU over-commit	OOM on RTX 4090 under concurrent infer/fine-tune	ResourceManager enforces semaphore; VRAMOptimizer thread inside ModelManagerSuite
Real-time audio latency	Larger single-proc may increase processing chain delay	Keep audio DSP stages in asyncio sub-tasks with shared ring buffer; measure before removal
Memory schema collisions	Different agents expect different table layouts	Namespace tables (session_, longterm_, kb_) and add view layer
Security regression	JWT mis-config after merge	SecurityGateway holds auth middleware imported by every FastAPI app

ROLLOUT CHECKLIST
Stand-up CoreOrchestrator & ObservabilityHub in parallel with legacy agents (canary).
Migrate stateless agents first (VisionSuite, NetGateway) – validate via integration tests.
Swap MemoryHub behind feature flag; back-fill data nightly.
Cut over ModelManagerSuite; monitor VRAM & latency dashboards.
Deploy AdaptiveLearningSuite only after models are stably served.
Freeze legacy agents → remove containers → decommission ports.

EXPECTED METRICS IMPROVEMENT
Agent count: 82 → 26 (68% reduction)
Inter-agent TCP links: ~350 → <80 (77% reduction)
Average GPU utilisation per task: +15% on MainPC (fewer idle waits, better resource pooling)
Mean end-to-end latency (speech → response): -25% (fewer hops, optimized service chains)
Operational dashboards: single Grafana & Prometheus targets.
VRAM efficiency: +20% through shared model pools and intelligent loading.
Service startup time: -40% through reduced dependency chains.
This phased consolidation retains all existing functionality while delivering a dramatically cleaner, easier-to-manage architecture optimized for your dual-GPU hardware.
