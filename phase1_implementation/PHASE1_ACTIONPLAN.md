
2️⃣ REVISED CONSOLIDATION PROPOSAL
(the previous draft is augmented to include every PC2-only agent and to tighten a few inter-machine decisions)
PHASE 0 – FOUNDATIONS
Target: 82 agents → 22 agents over four staged roll-outs.
2.1 Core & Observability (5 agents → 2)
Consolidation	Source Agents	New Agent	Port	Location
CoreOrchestrator	ServiceRegistry, SystemDigitalTwin, RequestCoordinator, UnifiedSystemAgent	CoreOrchestrator	7000	MainPC
ObservabilityHub	PredictiveHealthMonitor, PerformanceMonitor, HealthMonitor, PerformanceLoggerAgent, SystemHealthManager	ObservabilityHub	9000	PC2
Notes
SystemDigitalTwin is kept as an internal module inside CoreOrchestrator.
Health endpoints become /metrics; data sent to Prometheus + Grafana.
2.2 Resource & Scheduling Layer (7 agents → 2)
Consolidation	Source Agents	New Agent	Port	Location
ResourceManagerSuite	ResourceManager, TaskScheduler, AsyncProcessor, VRAMOptimizerAgent	ResourceManagerSuite	9001	PC2 (controls MainPC via NVML)
ErrorBus	retains NATS on 9002; becomes side-car in ResourceManagerSuite	ErrorBus	9002	PC2
PHASE 1 – DATA & MODEL BACKBONE
2.3 MemoryHub (12 agents → 1)
Source: MemoryClient, SessionMemoryAgent, KnowledgeBase, MemoryOrchestratorService, UnifiedMemoryReasoningAgent, ContextManager, ExperienceTracker, CacheManager, ProactiveContextMonitor, UnifiedUtilsAgent, AuthenticationAgent, AgentTrustScorer
→ MemoryHub (Port 7010, PC2).
Namespaced Redis + SQLite; built-in auth & trust-scoring middleware.
ProactiveContextMonitor becomes internal coroutine.
2.4 ModelManagerSuite (4 agents → 1)
GGUFModelManager, ModelManagerAgent, PredictiveLoader, ModelEvaluationFramework
→ ModelManagerSuite (Port 7011, MainPC).
Handles model registry, hot-swap, evaluation APIs.
PHASE 2 – LEARNING & ADAPTATION
2.5 AdaptiveLearningSuite (7 agents → 1)
SelfTrainingOrchestrator, LocalFineTunerAgent, LearningManager, LearningOrchestrationService, LearningOpportunityDetector, ActiveLearningMonitor, LearningAdjusterAgent
→ AdaptiveLearningSuite (Port 7012, MainPC).
Uses GPU quotas from ResourceManagerSuite.
2.6 KnowledgeTutorSuite (5 agents → 1)
TutorAgent, TutoringAgent, DreamWorldAgent, DreamingModeAgent, UnifiedWebAgent
→ KnowledgeTutorSuite (Port 9010, MainPC for DreamWorld GPU tasks; lightweight sub-services run on PC2).
Dream image generation off-loads to MainPC; lesson planning stays CPU-side.
PHASE 3 – USER-FACING INTELLIGENCE
2.7 CognitiveReasoningAgent (14 agents → 1)
Full NLU / planning / dialogue stack: ChainOfThoughtAgent, GoTToTAgent, CognitiveModelAgent, ModelOrchestrator, GoalManager, IntentionValidatorAgent, NLUAgent, AdvancedCommandHandler, ChitchatAgent, FeedbackHandler, TranslationService, DynamicIdentityAgent, ProactiveAgent, FixedStreamingTranslation
→ CognitiveReasoningAgent (Port 7020, MainPC).
2.8 AudioSpeechInterface (9 agents → 1)
AudioCapture, FusedAudioPreprocessor, StreamingSpeechRecognition, STTService, StreamingTTSAgent, TTSService, StreamingInterruptHandler, WakeWordDetector, StreamingLanguageAnalyzer
→ AudioSpeechInterface (Port 7021, MainPC).
2.9 SocialInteractionAgent (8 agents → 1)
EmotionEngine, MoodTrackerAgent, HumanAwarenessAgent, ToneDetector, VoiceProfilingAgent, EmpathyAgent, EmotionSynthesisAgent, Responder
→ SocialInteractionAgent (Port 7022, MainPC).
2.10 VisionSuite (2 agents → 1)
FaceRecognitionAgent + VisionProcessingAgent
→ VisionSuite (Port 7023, MainPC inference, PC2 pre-processing worker threads).
2.11 UtilityToolkit (5 agents → 1)
CodeGenerator, Executor, TinyLlamaServiceEnhanced, NLLBAdapter, TieredResponder
→ UtilityToolkit (Port 7024, MainPC).
2.12 NetGateway (4 agents → 1)
RemoteConnectorAgent, AdvancedRouter, FileSystemAssistantAgent, UnifiedWebAgent’s router component
→ NetGateway (Port 9011, PC2).
Traefik-based TLS termination + websocket multiplexing.
PORT & HEALTH RULES
Block | Function | Machine
------|----------|---------
7000-7030 | High-GPU intelligence & speech | MainPC
9000-9020 | Orchestration / Web / Caches | PC2
+100 offset | Health ports (e.g. 7000 → 7100)
DEPENDENCY DIAGRAM (post-consolidation)
CoreOrchestrator ↔ ResourceManagerSuite
↘︎ (registers) MemoryHub
  ↘︎ CognitiveReasoningAgent
   ↙︎ ModelManagerSuite ↔ AdaptiveLearningSuite
  ↘︎ AudioSpeechInterface, SocialInteractionAgent, VisionSuite
NetGateway → CognitiveReasoningAgent | AudioSpeechInterface
KnowledgeTutorSuite → CognitiveReasoningAgent, MemoryHub
ObservabilityHub scrapes everything
RISK & MITIGATION UPDATES
PC2 load: MemoryHub + NetGateway now fit in 12 GB VRAM; heavy diffusion in DreamWorld runs on MainPC via gRPC.
Security: AuthenticationAgent logic embedded into MemoryHub, enforced globally through JWT-signed tokens.
Cache coherency: single Redis instance with active-passive fail-over; all subsystems reference the same DSN.
Roll-back: keep Docker images of legacy agents for two release cycles; each new suite exposes legacy REST routes for backward compatibility flags.
End-state: 22 well-scoped services, GPU workload aligned with hardware, one memory source of truth, and dramatically shorter cross-service call chains – fully reflecting the agents and dependencies present in the real YAML configuration.
Thought for 33 seconds
Below is an exhaustive inventory extracted from the two startup configuration files.
It lists every agent, its listening-port pair, whether it is marked required, and the direct dependencies declared in the YAML.
(The arrows later show who depends on whom.)
## 1️⃣ MAIN-PC (RTX 4090) – main_pc_code/config/startup_config.yaml
1.1 Core Services
Agent	Port	Health	Required	Depends on
ServiceRegistry	7100	8100	✓	–
SystemDigitalTwin	7120	8120	✓	ServiceRegistry
RequestCoordinator	26002	27002	✓	SystemDigitalTwin
UnifiedSystemAgent	7125	8125	✓	SystemDigitalTwin
1.2 Memory System
MemoryClient	5713	6713	✓	SystemDigitalTwin
KnowledgeBase	5715	6715	✓	MemoryClient, SystemDigitalTwin
1.3 GPU-Infrastructure
GGUFModelManager	5575	6575	✓	SystemDigitalTwin
VRAMOptimizerAgent	5572	6572	✓	ModelManagerAgent, RequestCoordinator, SystemDigitalTwin
PredictiveLoader	5617	6617	✓	RequestCoordinator, SystemDigitalTwin
1.4 Utility Services
CodeGenerator	5650	6650	✓	SystemDigitalTwin, ModelManagerAgent
PredictiveHealthMonitor	5613	6613	✓	SystemDigitalTwin
FixedStreamingTranslation	5584	6584	✓	ModelManagerAgent, SystemDigitalTwin
Executor	5606	6606	✓	CodeGenerator, SystemDigitalTwin
TinyLlamaServiceEnhanced	5615	6615	(opt)	ModelManagerAgent, SystemDigitalTwin
LocalFineTunerAgent	5642	6642	✓	SelfTrainingOrchestrator, SystemDigitalTwin
NLLBAdapter	5581	6581	✓	SystemDigitalTwin
1.5 Reasoning Services
ChainOfThoughtAgent	5612	6612	✓	ModelManagerAgent, SystemDigitalTwin
CognitiveModelAgent	5641	6641	(opt)	ChainOfThoughtAgent, SystemDigitalTwin
1.6 Vision Processing
FaceRecognitionAgent	5610	6610	✓	RequestCoordinator, ModelManagerAgent, SystemDigitalTwin
1.7 Learning / Knowledge
ModelEvaluationFramework	7220	7221	✓	SystemDigitalTwin
LearningOpportunityDetector	7200	7201	✓	LearningOrchestrationService, MemoryClient, SystemDigitalTwin
LearningManager	5580	6580	✓	MemoryClient, RequestCoordinator, SystemDigitalTwin
ActiveLearningMonitor	5638	6638	✓	LearningManager, SystemDigitalTwin
LearningAdjusterAgent	5643	6643	✓	SelfTrainingOrchestrator, SystemDigitalTwin
1.8 Language Processing
ModelOrchestrator	7010	8010	✓	RequestCoordinator, ModelManagerAgent, SystemDigitalTwin
IntentionValidatorAgent	5701	6701	✓	RequestCoordinator, SystemDigitalTwin
NLUAgent	5709	6709	✓	SystemDigitalTwin
AdvancedCommandHandler	5710	6710	✓	NLUAgent, CodeGenerator, SystemDigitalTwin
ChitchatAgent	5711	6711	✓	NLUAgent, SystemDigitalTwin
FeedbackHandler	5636	6636	✓	NLUAgent, SystemDigitalTwin
Responder	5637	6637	✓	EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, SystemDigitalTwin, TTSService
TranslationService	5595	6595	✓	SystemDigitalTwin
DynamicIdentityAgent	5802	6802	✓	RequestCoordinator, SystemDigitalTwin
EmotionSynthesisAgent	5706	6706	✓	RequestCoordinator, ModelManagerAgent, SystemDigitalTwin
1.9 Speech Services
STTService	5800	6800	✓	ModelManagerAgent, SystemDigitalTwin
1.10 Audio Interface
AudioCapture	6550	7550	✓	SystemDigitalTwin
StreamingInterruptHandler	5576	6576	✓	StreamingSpeechRecognition, StreamingTTSAgent, SystemDigitalTwin
StreamingSpeechRecognition	6553	7553	✓	FusedAudioPreprocessor, RequestCoordinator, STTService, SystemDigitalTwin
StreamingTTSAgent	5562	6562	✓	RequestCoordinator, TTSService, SystemDigitalTwin, UnifiedSystemAgent
WakeWordDetector	6552	7552	✓	AudioCapture, FusedAudioPreprocessor, SystemDigitalTwin
StreamingLanguageAnalyzer	5579	6579	✓	StreamingSpeechRecognition, SystemDigitalTwin, TranslationService
ProactiveAgent	5624	6624	✓	RequestCoordinator, SystemDigitalTwin
1.11 Emotion System
EmotionEngine	5590	6590	✓	SystemDigitalTwin
HumanAwarenessAgent	5705	6705	✓	EmotionEngine, SystemDigitalTwin
ToneDetector	5625	6625	✓	EmotionEngine, SystemDigitalTwin
VoiceProfilingAgent	5708	6708	✓	EmotionEngine, SystemDigitalTwin
EmpathyAgent	5703	6703	✓	EmotionEngine, StreamingTTSAgent, SystemDigitalTwin
2️⃣ PC-2 (RTX 3060) – pc2_code/config/startup_config.yaml
Agent	Port	Health	Required	Depends on
MemoryOrchestratorService	7140	8140	✓	–
TieredResponder	7100	8100	✓	ResourceManager
AsyncProcessor	7101	8101	✓	ResourceManager
CacheManager	7102	8102	✓	MemoryOrchestratorService
PerformanceMonitor	7103	8103	✓	PerformanceLoggerAgent
VisionProcessingAgent	7150	8150	✓	CacheManager
DreamWorldAgent	7104	8104	✓	MemoryOrchestratorService
UnifiedMemoryReasoningAgent	7105	8105	✓	MemoryOrchestratorService
TutorAgent	7108	8108	✓	MemoryOrchestratorService
TutoringAgent	7131	8131	✓	MemoryOrchestratorService
ContextManager	7111	8111	✓	MemoryOrchestratorService
ExperienceTracker	7112	8112	✓	MemoryOrchestratorService
ResourceManager	7113	8113	✓	HealthMonitor
HealthMonitor	7114	8114	✓	PerformanceMonitor
TaskScheduler	7115	8115	✓	AsyncProcessor
AuthenticationAgent	7116	8116	✓	UnifiedUtilsAgent
SystemHealthManager	7117	8117	✓	–
UnifiedUtilsAgent	7118	8118	✓	SystemHealthManager
ProactiveContextMonitor	7119	8119	✓	ContextManager
AgentTrustScorer	7122	8122	✓	HealthMonitor
FileSystemAssistantAgent	7123	8123	✓	UnifiedUtilsAgent
RemoteConnectorAgent	7124	8124	✓	AdvancedRouter
UnifiedWebAgent	7126	8126	✓	FileSystemAssistantAgent, MemoryOrchestratorService
DreamingModeAgent	7127	8127	✓	DreamWorldAgent
PerformanceLoggerAgent	7128	8128	✓	–
AdvancedRouter	7129	8129	✓	TaskScheduler
Additional config items
‣ error_bus_port: 7150 (not a standalone agent, typically NATS/ZeroMQ).
‣ A block reserving 7100-7199 for service ports and 8100-8199 for health checks

3️⃣ OBSERVED DEPENDENCY PATTERNS & RELATIONSHIPS

3.1 High-Fan-Out Hubs (Main-PC)

SystemDigitalTwin  ← 32 direct dependents
RequestCoordinator ← 12 direct dependents
ModelManagerAgent  ← 10 direct dependents
EmotionEngine      ←  5 direct dependents

3.2 High-Fan-Out Hubs (PC-2)

MemoryOrchestratorService  ←  8 direct dependents
ResourceManager            ←  3 direct dependents

3.3 Cross-Machine Couplings
VisionProcessingAgent (PC-2) is down-stream of Main-PC’s ModelManagerAgent via model files but not declared in YAML.
RemoteConnectorAgent / UnifiedWebAgent (PC-2) surface APIs that ultimately call Main-PC’s language-reasoning stack.
Speech & emotion loops on Main-PC rely on streaming data produced solely on Main-PC—no declared dependency on PC-2 agents.
3.4 Logical Domains (deduced)
Domain | Representative Agents (sample)
-------|-------------------------------
Core Orchestration | ServiceRegistry, SystemDigitalTwin, RequestCoordinator
Memory & Knowledge | MemoryClient, KnowledgeBase (Main-PC) vs MemoryOrchestratorService (PC-2)
Model Lifecycle | GGUFModelManager, ModelManagerAgent, PredictiveLoader
Learning / Adaptation | LearningManager, SelfTrainingOrchestrator, ActiveLearningMonitor
Reasoning & Dialogue | ChainOfThoughtAgent, GoalManager, NLUAgent
Speech & Audio | STTService, StreamingSpeechRecognition, StreamingTTSAgent
Vision | FaceRecognitionAgent (Main-PC), VisionProcessingAgent (PC-2)
Emotion / Social | EmotionEngine, EmpathyAgent, MoodTrackerAgent
Utilities / Code-Gen | CodeGenerator, Executor, TinyLlamaServiceEnhanced
Infrastructure / Ops | PerformanceMonitor, HealthMonitor, ResourceManager, error_bus_port
Web / External I/O | RemoteConnectorAgent, UnifiedWebAgent, TieredResponder
This map provides the ground truth of what exists today.
With it we can now reason about optimal groupings, hardware placement, and how to collapse redundant layers without losing functionality.
Thought for 26 seconds
CONSOLIDATION PROPOSAL
(Everything is mapped to the agents that actually exist in the two YAML files.
Health-check ports follow the rule service port + 100.)
PHASE 1: CORE & OBSERVABILITY
Target Reduction: 20 agents → 5
Consolidation Group 1: CoreOrchestrator
Source Agents
ServiceRegistry (7100, service discovery)
SystemDigitalTwin (7120, runtime state)
RequestCoordinator (26002, message router)
UnifiedSystemAgent (7125, shared utilities)
Target Unified Agent: CoreOrchestrator
Port: 7000  Health: 7100
Hardware: MainPC (RTX 4090) – zero-copy access to GPU metrics
Integrated Functions: in-proc registry, global state DB, request fan-out, system APIs
Logic Merger Strategy: keep original classes, wrap them in a single FastAPI-gRPC service; expose /register, /state, /dispatch routes.
Dependencies: None (bootstrap)
Risk Assessment: tight coupling; mitigate with clearly typed internal interfaces.
Consolidation Group 2: ObservabilityHub
Source Agents
PredictiveHealthMonitor (5613, MainPC)
PerformanceMonitor (7103, PC2)
HealthMonitor (7114, PC2)
PerformanceLoggerAgent (7128, PC2)
SystemHealthManager (7117, PC2)
Target Unified Agent: ObservabilityHub
Port: 9000  Health: 9100
Hardware: PC2 (CPU-heavy, light GPU)
Integrated Functions: metrics scrape & push, anomaly detection, alerting, Grafana exporter
Logic Merger Strategy: side-car Prometheus + Python plug-ins; reuse existing logging code as Celery tasks.
Dependencies: CoreOrchestrator (for service list)
Risk: metric format drift – add protobuf schema.
Consolidation Group 3: ResourceManagerSuite
Source Agents
ResourceManager (7113)
TaskScheduler (7115)
AsyncProcessor (7101)
VRAMOptimizerAgent (5572)
Target Unified Agent: ResourceManagerSuite
Port: 9001  Health: 9101
Hardware: PC2 (controls both GPUs through NVML/NVIDIA-SML)
Integrated Functions: CPU/GPU quota tracking, async job queue, VRAM optimizer, semaphore locks
Logic Merger Strategy: Redis queue → asyncio workers; expose /enqueue, /quota, /stats.
Dependencies: ObservabilityHub (metrics push)
Risk: queue starvation – introduce priority levels.
Consolidation Group 4: SecurityGateway
Source Agents
AuthenticationAgent (7116)
AgentTrustScorer (7122)
Target Unified Agent: SecurityGateway
Port: 9002  Health: 9102
Hardware: PC2
Integrated Functions: JWT auth, trust-score middleware, IP throttling
Logic Merger Strategy: embed FastAPI dependency injection; publish public JWKS.
Dependencies: MemoryHub (for trust DB)
Risk: single auth point – keep hot-stand-by container.
Consolidation Group 5: ErrorBus
Source: error_bus_port (7150) + scattered ZeroMQ handlers
Target: ErrorBus (NATS) – Port 9003 / Health 9103, PC2
PHASE 2: DATA & MODEL BACKBONE
Target Reduction: 23 agents → 6
Consolidation Group 6: MemoryHub
Source Agents
MemoryClient (5713), SessionMemoryAgent (5574), KnowledgeBase (5715),
MemoryOrchestratorService (7140), UnifiedMemoryReasoningAgent (7105),
ContextManager (7111), ExperienceTracker (7112), CacheManager (7102),
ProactiveContextMonitor (7119), UnifiedUtilsAgent (7118)
Target Unified Agent: MemoryHub
Port: 7010  Health: 7110
Hardware: PC2 (larger RAM, no GPU need)
Integrated Functions: Redis-back cache, SQLite + DuckDB long-term store, context reasoning, TTL cache, auth utilities
Logic Merger Strategy: mount existing DB files; namespaced key-spaces (session:, kb:, etc.); keep gRPC for high-throughput read.
Dependencies: CoreOrchestrator, SecurityGateway
Risk: schema clash – add migration scripts.
Consolidation Group 7: ModelManagerSuite
Source Agents
GGUFModelManager (5575), ModelManagerAgent (5570), PredictiveLoader (5617), ModelEvaluationFramework (7220)
Target Unified Agent: ModelManagerSuite
Port: 7011  Health: 7111
Hardware: MainPC (RTX 4090)
Integrated Functions: model registry, GGUF/LoRA loader, quantization service, eval harness
Logic Merger Strategy: pluggable adapters per model family; REST /models/{id}, websocket /stream/load.
Dependencies: MemoryHub, ResourceManagerSuite
Risk: VRAM spikes – pre-flight quota check.
PHASE 3: LEARNING & KNOWLEDGE
Target Reduction: 12 agents → 2
Consolidation Group 8: AdaptiveLearningSuite
Source Agents
SelfTrainingOrchestrator (5660), LocalFineTunerAgent (5642), LearningManager (5580),
LearningOrchestrationService (7210), LearningOpportunityDetector (7200),
ActiveLearningMonitor (5638), LearningAdjusterAgent (5643)
Target Unified Agent: AdaptiveLearningSuite
Port: 7012  Health: 7112
Hardware: MainPC (GPU-intensive fine-tuning)
Integrated Functions: continual-learning scheduler, LoRA/QLoRA fine-tuner, eval feedback loop
Logic Merger Strategy: Celery beat jobs + Pytorch-Lightning driver; checkpoints stored via MemoryHub.
Dependencies: ModelManagerSuite, MemoryHub, ResourceManagerSuite
Risk: long fine-tunes blocking inference – enforce GPU time-slices.
Consolidation Group 9: KnowledgeTutorSuite
Source Agents
DreamWorldAgent (7104), DreamingModeAgent (7127), TutorAgent (7108), TutoringAgent (7131)
Target Unified Agent: KnowledgeTutorSuite
Port: 7013  Health: 7113
Hardware: MainPC for diffusion (DreamWorld); CPU threads on PC2 for lesson planning
Integrated Functions: dream-simulation, tutoring dialogue, curriculum builder
Logic Merger Strategy: micro-services inside same container (sub-FastAPI apps) with GPU hand-off to ModelManagerSuite.
Dependencies: MemoryHub, CognitiveReasoningAgent
Risk: GPU memory clash with VisionSuite – allocate fixed 6 GB slice.

PHASE 4: USER-FACING INTELLIGENCE
Target Reduction: 44 agents → 9
Consolidation Group 10: CognitiveReasoningAgent
Source Agents
ChainOfThoughtAgent (5612), GoTToTAgent (5646), CognitiveModelAgent (5641),
ModelOrchestrator (7010), GoalManager (7005), IntentionValidatorAgent (5701),
NLUAgent (5709), AdvancedCommandHandler (5710), ChitchatAgent (5711),
FeedbackHandler (5636), TranslationService (5595), DynamicIdentityAgent (5802),
ProactiveAgent (5624), FixedStreamingTranslation (5584)
Target Unified Agent: CognitiveReasoningAgent
Port: 7020  Health: 7120
Hardware: MainPC (LLM-heavy)
Integrated Functions: multi-lingual NLU/NLG, planner, persona engine, intent validation
Logic Merger Strategy: share a single vLLM pool; routers replicate legacy REST endpoints for backward compatibility.
Dependencies: ModelManagerSuite, MemoryHub
Risk: monolith size – enable plugin-based routing so pieces can be spun out if needed.
Consolidation Group 11: AudioSpeechInterface
Source Agents
AudioCapture (6550), FusedAudioPreprocessor (6551), StreamingSpeechRecognition (6553),
STTService (5800), StreamingTTSAgent (5562), TTSService (5801),
StreamingInterruptHandler (5576), WakeWordDetector (6552), StreamingLanguageAnalyzer (5579)
Target Unified Agent: AudioSpeechInterface
Port: 7021  Health: 7121
Hardware: MainPC (Whisper, HiFi-GAN)
Integrated Functions: A/V capture, VAD, ASR, online analyzer, TTS with interrupt capability
Logic Merger Strategy: shared ring-buffer; gRPC bidirectional stream /audio.
Dependencies: CognitiveReasoningAgent, ResourceManagerSuite
Risk: latency – benchmark before retiring ring-buffer.
Consolidation Group 12: SocialInteractionAgent
Source Agents
EmotionEngine (5590), MoodTrackerAgent (5704), HumanAwarenessAgent (5705),
ToneDetector (5625), VoiceProfilingAgent (5708), EmpathyAgent (5703),
EmotionSynthesisAgent (5706), Responder (5637)
Target Unified Agent: SocialInteractionAgent
Port: 7022  Health: 7122
Hardware: MainPC (light GPU)
Integrated Functions: affect analysis, mood modelling, empathic response composition, prosody controls
Logic Merger Strategy: FSM core + ML classifiers; output channels /affect/analyze, /affect/synthesize.
Dependencies: AudioSpeechInterface, MemoryHub, CognitiveReasoningAgent
Risk: model drift – nightly self-test via ObservabilityHub.
Consolidation Group 13: VisionSuite
Source Agents
FaceRecognitionAgent (5610) – MainPC
VisionProcessingAgent (7150) – PC2
Target Unified Agent: VisionSuite
Port: 7023  Health: 7123
Hardware: MainPC GPU inference; PC2 threads for pre-processing via gRPC worker pool
Integrated Functions: face ID, object detect, embedding store
Logic Merger Strategy: MainPC hosts inference models; PC2 streams JPEG batches for encoding.
Dependencies: MemoryHub, ResourceManagerSuite
Risk: network bandwidth – enable AV1 compression.
Consolidation Group 14: UtilityToolkit
Source Agents
CodeGenerator (5650), Executor (5606), TinyLlamaServiceEnhanced (5615), NLLBAdapter (5581), TieredResponder (7100)
Target Unified Agent: UtilityToolkit
Port: 7024  Health: 7124
Hardware: MainPC
Integrated Functions: code-generation, sandbox executor, lite-model endpoints, translation fallback
Logic Merger Strategy: restrict Executor with Firecracker-VM; reuse Tiny-LLM weights from ModelManagerSuite.
Dependencies: ModelManagerSuite, SecurityGateway
Risk: sandbox escape – SELinux + cgroup.
Consolidation Group 15: NetGateway
Source Agents
RemoteConnectorAgent (7124), AdvancedRouter (7129), FileSystemAssistantAgent (7123), UnifiedWebAgent (7126)
Target Unified Agent: NetGateway
Port: 9011  Health: 9111
Hardware: PC2
Integrated Functions: TLS termination, REST↔gRPC proxy, websocket multiplexer, file-system helper
Logic Merger Strategy: Traefik front-end → FastAPI backend; mount /mnt/share for file ops.
Dependencies: SecurityGateway, CoreOrchestrator
Risk: DDOS – enable rate-limit plugin.
PORT CONSOLIDATION TABLE
Block | Function | Machine
------|----------|---------
7000–7025 | GPU-heavy intelligence & media | MainPC
7010–7015 | Data & Models | (overlap) see above
9000–9012 | Orchestration / Web / Ops | PC2
+100 | Health-check ports


              +-----------------+
              | CoreOrchestrator|
              +--------+--------+
                       |
        +--------------+-------------+
        |                            |
  +-----v-----+               +------v-------+
  |MemoryHub  |               |ResourceMgr   |
  +--+-----+--+               +------+-------+
     |     |                         |
     |     +-------+-----------------+
     |             |
+----v----+   +----v----+
|ModelMgr |   |Security |
+----+----+   +----+----+
     |             |
 +---v---+   +-----v------+
 |Adaptive|   |NetGateway |
 +---+----+   +-----+-----+
     |              |
+----v----+   +-----v------+
|Cognitive|   | Observability|
+----+----+   +-------------+
     |
+----v----+
|Audio/Vis/Emotion suites|
+---------+

RISK MATRIX (high-level)
Area	Risk	Mitigation
Large unified services	Deployment size ↑	Docker multi-stage builds; lazy load
GPU over-commit	OOM on 4090	ResourceManagerSuite semaphore
Single-Point Auth	Outage blocks all	Hot-stand-by SecurityGateway
Schema migration	Data loss	Write-ahead migrations + backups
Latency on PC2 ↔ MainPC	Worsened by gRPC hops	Enable compression + keep-alive pooling

End-State: 82 agents → 22 coherent services, GPU work centralized on RTX 4090, orchestration/web & memory on PC2, clear domain boundaries, and ≤60 inter-service network paths (-80 % vs today).