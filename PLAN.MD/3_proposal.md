PHASE 2: Model & Language Service Consolidation
Target Reduction: 12 agents → 3 agents (Model, Language, and Translation)

Consolidation Group 3: Unified Model Management
Source Agents:

GGUFModelManager (5575)
ModelManagerAgent (5570)
VRAMOptimizerAgent (5572)
PredictiveLoader (5617)
Secondary
CONSOLIDATION PROPOSAL
This proposal is based on a comprehensive analysis of both MainPC and PC2 agent configurations, their dependencies, communication patterns, and functional groupings. The plan is phased, with each phase executable independently, and is designed to maximize hardware utilization, minimize inter-agent communication, and improve maintainability.

PHASE 1: Core System & Memory Consolidation
Target Reduction: 18 agents → 7 agents (Core, Memory, and Reasoning)

Consolidation Group 1: Unified Core Orchestrator
Source Agents:

ServiceRegistry (port: 7100, service discovery)
RequestCoordinator (26002, request routing)
UnifiedSystemAgent (7125, system status/health)
PredictiveHealthMonitor (5613, health prediction)
Executor (5606, code execution)
ProactiveAgent (5624, proactive context)
DynamicIdentityAgent (5802, persona/voice)
Target Unified Agent: CoreOrchestratorAgent

Port: 7100 (reuse ServiceRegistry port for centralization)
Hardware: MainPC (RTX 4090) — high concurrency, central role
Integrated Functions: Service registration, request routing, system health, code execution, proactive context, dynamic identity/persona management
Logic Merger Strategy:
Merge ServiceRegistry and UnifiedSystemAgent as the base.
Integrate request routing and execution logic from RequestCoordinator and Executor.
Add health monitoring and prediction as submodules.
Embed proactive and dynamic identity logic as internal services.
Dependencies: UnifiedMemoryOrchestrator, ModelManagerAgent, StreamingTTSAgent, etc.
Risk Assessment:
Potential Issues: Overloading a single agent, complex error handling.
Mitigations: Modularize subcomponents, use thread/process pools, circuit breakers.
Consolidation Group 2: Unified Memory & Reasoning System
Source Agents:

UnifiedMemoryOrchestrator (7120, memory)
MemoryClient (5713, memory access)
SessionMemoryAgent (5574, session memory)
KnowledgeBase (5715, knowledge)
UnifiedMemoryReasoningAgent (PC2, 7105)
MemoryScheduler (PC2, scheduled memory tasks)
MemoryDecayManager (PC2, memory decay)
Target Unified Agent: UnifiedMemoryReasoningService

Port: 7140 (PC2, as per current orchestrator)
Hardware: PC2 (RTX 3060) — memory-centric, less GPU-intensive
Integrated Functions: All memory types (episodic, session, knowledge), context management, memory decay, scheduled tasks, reasoning, error pattern learning
Logic Merger Strategy:
Use UnifiedMemoryOrchestrator as the base.
Integrate session, knowledge, and client logic as internal modules.
Merge reasoning and error pattern logic from UnifiedMemoryReasoningAgent.
Add scheduler and decay as background threads.
Dependencies: Redis (optional), CoreOrchestratorAgent, ModelManagerAgent
Risk Assessment:
Potential Issues: Data migration, concurrency.
Mitigations: Use SQLite/Redis for concurrency, phased migration, extensive testing.
PHASE 2: Model & Language Service Consolidation
Target Reduction: 12 agents → 3 agents (Model, Language, and Translation)

Consolidation Group 3: Unified Model Management
Source Agents:

GGUFModelManager (5575)
ModelManagerAgent (5570)
VRAMOptimizerAgent (5572)
PredictiveLoader (5617)
SecondaryModelService (PC2, 5590)
NLLBAdapter, StreamingTranslation, DictionaryTranslator (PC2, currently inside SecondaryModelService)
Target Unified Agent: ModelManagementService

Port: 5570 (MainPC, for GPU-intensive tasks)
Hardware: MainPC (RTX 4090) — model loading, VRAM optimization
Integrated Functions: Model loading/unloading, VRAM management, secondary model services (translation, NLLB, streaming)
Logic Merger Strategy:
Use ModelManagerAgent as the base.
Integrate GGUF, VRAM, and predictive loading as submodules.
Move SecondaryModelService logic as a submodule, but keep translation fallback on PC2 for redundancy.
Dependencies: UnifiedMemoryReasoningService, CoreOrchestratorAgent
Risk Assessment:
Potential Issues: VRAM contention, model conflicts.
Mitigations: Strict resource allocation, fallback to PC2 for overflow.
Consolidation Group 4: Unified Language & Translation Service
Source Agents:

TranslationService (5595)
NLUAgent (5709)
AdvancedCommandHandler (5710)
ChitchatAgent (5711)
FeedbackHandler (5636)
Responder (5637)
StreamingLanguageAnalyzer (5579)
PC2: UnifiedWebAgent, TutoringServiceAgent, TutorAgent
Target Unified Agent: LanguageAndTranslationService

Port: 5595 (MainPC, for low-latency)
Hardware: MainPC (RTX 4090) — language, translation, and dialogue
Integrated Functions: Translation, NLU, command handling, chitchat, feedback, response synthesis, streaming language analysis, web/tutoring integration
Logic Merger Strategy:
Use TranslationService as the base.
Integrate NLU, command, chitchat, and feedback as internal modules.
Add streaming and web/tutoring as optional
CONSOLIDATION PROPOSAL
This proposal is based on a comprehensive analysis of both MainPC and PC2 agent configurations, their dependencies, communication patterns, and functional groupings. The plan is phased, with each phase executable independently, and is designed to maximize hardware utilization, minimize inter-agent communication, and improve maintainability.

PHASE 1: Core System & Memory Consolidation
Target Reduction: 18 agents → 7 agents (Core, Memory, and Reasoning)

Consolidation Group 1: Unified Core Orchestrator
Source Agents:

ServiceRegistry (port: 7100, service discovery)
RequestCoordinator (26002, request routing)
UnifiedSystemAgent (7125, system status/health)
PredictiveHealthMonitor (5613, health prediction)
Executor (5606, code execution)
ProactiveAgent (5624, proactive context)
DynamicIdentityAgent (5802, persona/voice)
Target Unified Agent: CoreOrchestratorAgent

Port: 7100 (reuse ServiceRegistry port for centralization)
Hardware: MainPC (RTX 4090) — high concurrency, central role
Integrated Functions: Service registration, request routing, system health, code execution, proactive context, dynamic identity/persona management
Logic Merger Strategy:
Merge ServiceRegistry and UnifiedSystemAgent as the base.
Integrate request routing and execution logic from RequestCoordinator and Executor.
Add health monitoring and prediction as submodules.
Embed proactive and dynamic identity logic as internal services.
Dependencies: UnifiedMemoryOrchestrator, ModelManagerAgent, StreamingTTSAgent, etc.
Risk Assessment:
Potential Issues: Overloading a single agent, complex error handling.
Mitigations: Modularize subcomponents, use thread/process pools, circuit breakers.
Consolidation Group 2: Unified Memory & Reasoning System
Source Agents:

UnifiedMemoryOrchestrator (7120, memory)
MemoryClient (5713, memory access)
SessionMemoryAgent (5574, session memory)
KnowledgeBase (5715, knowledge)
UnifiedMemoryReasoningAgent (PC2, 7105)
MemoryScheduler (PC2, scheduled memory tasks)
MemoryDecayManager (PC2, memory decay)
Target Unified Agent: UnifiedMemoryReasoningService

Port: 7140 (PC2, as per current orchestrator)
Hardware: PC2 (RTX 3060) — memory-centric, less GPU-intensive
Integrated Functions: All memory types (episodic, session, knowledge), context management, memory decay, scheduled tasks, reasoning, error pattern learning
Logic Merger Strategy:
Use UnifiedMemoryOrchestrator as the base.
Integrate session, knowledge, and client logic as internal modules.
Merge reasoning and error pattern logic from UnifiedMemoryReasoningAgent.
Add scheduler and decay as background threads.
Dependencies: Redis (optional), CoreOrchestratorAgent, ModelManagerAgent
Risk Assessment:
Potential Issues: Data migration, concurrency.
Mitigations: Use SQLite/Redis for concurrency, phased migration, extensive testing.
PHASE 2: Model & Language Service Consolidation
Target Reduction: 12 agents → 3 agents (Model, Language, and Translation)

Consolidation Group 3: Unified Model Management
Source Agents:

GGUFModelManager (5575)
ModelManagerAgent (5570)
VRAMOptimizerAgent (5572)
PredictiveLoader (5617)
SecondaryModelService (PC2, 5590)
NLLBAdapter, StreamingTranslation, DictionaryTranslator (PC2, currently inside SecondaryModelService)
Target Unified Agent: ModelManagementService

Port: 5570 (MainPC, for GPU-intensive tasks)
Hardware: MainPC (RTX 4090) — model loading, VRAM optimization
Integrated Functions: Model loading/unloading, VRAM management, secondary model services (translation, NLLB, streaming)
Logic Merger Strategy:
Use ModelManagerAgent as the base.
Integrate GGUF, VRAM, and predictive loading as submodules.
Move SecondaryModelService logic as a submodule, but keep translation fallback on PC2 for redundancy.
Dependencies: UnifiedMemoryReasoningService, CoreOrchestratorAgent
Risk Assessment:
Potential Issues: VRAM contention, model conflicts.
Mitigations: Strict resource allocation, fallback to PC2 for overflow.
Consolidation Group 4: Unified Language & Translation Service
Source Agents:

TranslationService (5595)
NLUAgent (5709)
AdvancedCommandHandler (5710)
ChitchatAgent (5711)
FeedbackHandler (5636)
Responder (5637)
StreamingLanguageAnalyzer (5579)
PC2: UnifiedWebAgent, TutoringServiceAgent, TutorAgent
Target Unified Agent: LanguageAndTranslationService

Port: 5595 (MainPC, for low-latency)
Hardware: MainPC (RTX 4090) — language, translation, and dialogue
Integrated Functions: Translation, NLU, command handling, chitchat, feedback, response synthesis, streaming language analysis, web/tutoring integration
Logic Merger Strategy:
Use TranslationService as the base.
Integrate NLU, command, chitchat, and feedback as internal modules.
Add streaming and web/tutoring as optional plugins.
Dependencies: UnifiedMemoryReasoningService, ModelManagementService
Risk Assessment:
Potential Issues: Latency, feature regression.
Mitigations: Modular plugin system, fallback to PC2 for overflow.
PHASE 3: Speech, Audio, and Emotion System Consolidation
Target Reduction: 13 agents → 3 agents

Consolidation Group 5: Unified Speech & Audio Service
Source Agents:

STTService (5800)
TTSService (5801)
StreamingTTSAgent (5562)
StreamingSpeechRecognition (6553)
AudioCapture (6550)
FusedAudioPreprocessor (6551)
WakeWordDetector (6552)
StreamingInterruptHandler (5576)
ProactiveAgent (5624)
StreamingLanguageAnalyzer (5579)
Target Unified Agent: SpeechAndAudioService

Port: 5800 (MainPC)
Hardware: MainPC (RTX 4090) — real-time audio/speech
Integrated Functions: Speech-to-text, text-to-speech, streaming, audio capture, wake word, pre-processing, proactive audio
Logic Merger Strategy:
Use STT/TTS as the base.
Integrate streaming, capture, and wake word as submodules.
Add proactive and interrupt handling as background threads.
Dependencies: ModelManagementService, UnifiedMemoryReasoningService
Risk Assessment:
Potential Issues: Real-time performance.
Mitigations: Thread/process pools, fallback to PC2 for overflow.
Consolidation Group 6: Unified Emotion & Human Awareness System
Source Agents:

EmotionEngine (5590)
MoodTrackerAgent (5704)
HumanAwarenessAgent (5705)
ToneDetector (5625)
VoiceProfilingAgent (5708)
EmpathyAgent (5703)
EmotionSynthesisAgent (5706)
Target Unified Agent: EmotionAndAwarenessService

Port: 5590 (MainPC)
Hardware: MainPC (RTX 4090) — emotion synthesis, awareness
Integrated Functions: Emotion detection, mood tracking, tone, voice profiling, empathy, synthesis
Logic Merger Strategy:
Use EmotionEngine as the base.
Integrate mood, awareness, tone, voice, empathy, and synthesis as submodules.
Dependencies: UnifiedMemoryReasoningService, SpeechAndAudioService
Risk Assessment:
Potential Issues: Feature regression.
Mitigations: Modularize, extensive testing.
PHASE 4: PC2 System & Utility Consolidation
Target Reduction: 15+ agents → 4 agents

Consolidation Group 7: PC2 System Utility & Coordination
Source Agents:

ResourceManager, HealthMonitor, PerformanceMonitor, SystemHealthManager, UnifiedHealthOrchestrator, ErrorManagementSystem, RecoveryManagerModule, FileSystemAssistantAgent, RemoteConnectorAgent, AdvancedRouter, TaskScheduler, AsyncProcessor, CacheManager, ExperienceTracker, AgentTrustScorer, ProactiveContextMonitor, SystemToolkitAgent
Target Unified Agent: PC2SystemUtilityService

Port: 7113 (PC2)
Hardware: PC2 (RTX 3060) — system, health, utility, coordination
Integrated Functions: Resource management, health, error management, recovery, file system, remote connection, routing, scheduling, async, caching, experience tracking, trust scoring, context monitoring, toolkit
Logic Merger Strategy:
Use ResourceManager as the base.
Integrate health, error, recovery, and utility as submodules.
Add coordination, scheduling, and async as background threads.
Dependencies: UnifiedMemoryReasoningService, CoreOrchestratorAgent
Risk Assessment:
Potential Issues: Over-complexity.
Mitigations: Modularize, clear API boundaries.
Summary Table
| Phase | Group | Source Agents | Target Agent | Port | Hardware | Key Functions | |-------|-------|---------------|-------------|------|----------|--------------| | 1 | Core | 7 | CoreOrchestratorAgent | 7100 | MainPC | Core, health, execution | | 1 | Memory | 7 | UnifiedMemoryReasoningService | 7140 | PC2 | Memory, reasoning | | 2 | Model | 6 | ModelManagementService | 5570 | MainPC | Model, VRAM, secondary models | | 2 | Language | 8 | LanguageAndTranslationService | 5595 | MainPC | Language, translation, dialogue | | 3 | Speech | 10 | SpeechAndAudioService | 5800 | MainPC | Speech, audio, streaming | | 3 | Emotion | 7 | EmotionAndAwarenessService | 5590 | MainPC | Emotion, awareness | | 4 | PC2 Utility | 15+ | PC2SystemUtilityService | 7113 | PC2 | System, health, utility |

Implementation Notes
Port Consolidation: Use the lowest-numbered port from the group for the unified agent.
Dependency Restructuring: All agents should use the new unified services as dependencies, reducing cross-agent chatter.
Hardware Allocation: MainPC for GPU/latency-critical, PC2 for memory/system/utility.
Migration: Each phase can be implemented and tested independently.
Fallbacks: For overflow or failure, allow fallback to PC2 for model/translation tasks.
Risk Assessment & Mitigation
Complexity: Modularize unified agents, use clear APIs.
Performance: Use thread/process pools, offload to PC2 as needed.
Data Migration: Use SQLite/Redis, phased migration, backup before merge.
Testing: Extensive integration and regression testing per phase.
Conclusion
This consolidation plan will reduce agent count by over 60%, dramatically simplify dependencies, optimize hardware usage, and improve maintainability. Each phase is actionable and can be executed independently, with clear rollback and fallback strategies.

Next Steps:

Review and approve the phase order and groupings.
Begin with Phase 1: Core and Memory consolidation.
Prepare migration scripts and test plans for each phase.
Monitor system performance and iterate as needed.
Full technical mapping, port assignments, and dependency diagrams available upon request.