# AI System Agent Consolidation – Draft Plan (Phase 1)

This document aggregates agents from MainPC (RTX 4090) and PC2 (RTX 3060) startup configurations and proposes functional consolidation groups. Each block includes rationale, risk analysis and preservation strategies strictly derived from scanned configuration data.

---

```yaml
Group Name: SystemCore
Included Agents:
  # MainPC
  - CoreOrchestrator
  - SecurityGateway
  # PC2
  - ObservabilityHub
  - ResourceManagerSuite
  - ErrorBusSuite
Reasoning: >
  These agents sit at the heart of orchestration, security, monitoring and resource/error management for
the whole distributed system.  They expose foundational APIs consumed by nearly every other agent.
Potential Risks:
  - Naming collisions when merging REST / gRPC endpoints.
  - SecurityGateway and ErrorBusSuite both enforce trust / error policies that could overlap.
  - ResourceManagerSuite’s VRAM tracking may conflict with CoreOrchestrator’s existing quotas.
Suggested Mitigations:
  - Dedicate **core** namespace under a shared package (e.g. core.*) and expose versioned REST routes.
  - Introduce unified policy layer so SecurityGateway & ErrorBusSuite rules are loaded from one schema.
  - Keep ResourceManagerSuite as pluggable sub-module behind an interface implemented by CoreOrchestrator.
Behavioral Preservation Plan: >
  Preserve existing startup order (CoreOrchestrator → ObservabilityHub → SecurityGateway → ResourceManagerSuite → ErrorBusSuite).
  Maintain identical health-check ports and retain Prometheus metrics endpoints.  Wrap consolidation with extensive integration tests.
```

```yaml
Group Name: MemoryServices
Included Agents:
  # PC2 (authoritative)
  - MemoryHub
  # Legacy (MainPC – deprecated)
  - MemoryClient
  - SessionMemoryAgent
  - KnowledgeBase
Reasoning: >
  MemoryHub already consolidates legacy memory agents.  Centralising them formalises single-source-of-truth
  for vector / session / knowledge storage across machines.
Potential Risks:
  - Latency increase for MainPC components now calling remote MemoryHub over network.
  - Schema mismatch between old SQLite files and new consolidated DB.
  - Cache invalidation if Redis DB assignments differ.
Suggested Mitigations:
  - Introduce local read-through cache on MainPC (Redis DB 1) with TTL-based invalidation.
  - Provide migration script converting legacy SQLite tables into MemoryHub schema.
  - Add circuit-breaker fallback to CoreOrchestrator when MemoryHub unreachable.
Behavioral Preservation Plan: >
  Keep existing external endpoint (http://172.20.0.11:7010).  All MainPC agents already reference MemoryHub.
  Maintain Redis (DB 2) and SQLite path exactly as configured to avoid state loss.
```

```yaml
Group Name: ModelManagementSuite
Included Agents:
  - GGUFModelManager
  - ModelManagerAgent
  - PredictiveLoader
  - ModelOrchestrator
  - ModelEvaluationFramework
Reasoning: >
  Handles lifecycle of ML models (loading, unloading, evaluation, predictive pre-loading). They share
  dependency chain GGUFModelManager → ModelManagerAgent → higher-level orchestration.
Potential Risks:
  - VRAM allocation logic duplicated between ResourceManagerSuite and GGUFModelManager.
  - PredictiveLoader may issue load requests before consolidated manager is ready.
  - Tight coupling with GPU hardware (RTX 4090) vs PC2 resource limits.
Suggested Mitigations:
  - Centralise VRAM accounting in ResourceManagerSuite via API.
  - Gate PredictiveLoader behind health check of ModelManagerAgent.
  - Provide hardware-aware profiles; keep heavy model ops on MainPC.
Behavioral Preservation Plan: >
  Expose consolidated `model_manager` service with backward-compatible /status & /load endpoints.
  Retain message schema currently consumed by ChainOfThoughtAgent, Vision, Speech and Translation services.
```

```yaml
Group Name: ReasoningEngine
Included Agents:
  - ChainOfThoughtAgent
  - GoTToTAgent
  - CognitiveModelAgent
  - GoalManager
  - IntentionValidatorAgent
Reasoning: >
  All agents perform high-level cognitive or planning tasks built on language models. They depend on
  ModelManagerAgent and Memory services and feed goals/intents back to CoreOrchestrator.
Potential Risks:
  - Different reasoning paradigms (Tree-of-Thought vs CoT) could conflict in shared state.
  - GoalManager already exposes management API – consolidation must not dead-lock intent validation.
Suggested Mitigations:
  - Introduce strategy registry letting requests pick reasoning algorithm.
  - Keep each algorithm in separate sub-module with common interface.
Behavioral Preservation Plan: >
  Preserve existing ports and maintain call order: IntentionValidatorAgent → ChainOfThought → GoTToT / Cognitive.
```

```yaml
Group Name: LanguageProcessingSuite
Included Agents:
  - NLUAgent
  - AdvancedCommandHandler
  - ChitchatAgent
  - FeedbackHandler
  - TranslationService
  - DynamicIdentityAgent
Reasoning: >
  Suite covers natural language understanding, dialogue management and translation.
  All sit logically above ReasoningEngine and below Speech/Responder layers.
Potential Risks:
  - Overlapping tokenisation or language detection logic.
  - Circular dependency between TranslationService and NLU if merged naïvely.
Suggested Mitigations:
  - Standardise on shared tokenizer library.
  - Use dependency injection to avoid hard references.
Behavioral Preservation Plan: >
  Provide unified API (`/nlu/`, `/dialog/`, `/translate/`).  Keep internal queues so latency-sensitive
  agents (Responder) still receive async callbacks.
```

```yaml
Group Name: SpeechAudioPipeline
Included Agents:
  - STTService
  - TTSService
  - AudioCapture
  - FusedAudioPreprocessor
  - StreamingSpeechRecognition
  - StreamingTTSAgent
  - StreamingInterruptHandler
  - WakeWordDetector
  - StreamingLanguageAnalyzer
Reasoning: >
  Complete audio ingestion → recognition → interruption → synthesis loop.  Tight real-time constraints.
Potential Risks:
  - Buffer under-/over-flow across consolidated stream.
  - Conflicting sample-rates or codecs in different modules.
Suggested Mitigations:
  - Central ring-buffer with clear backpressure semantics.
  - Enforce global audio config (e.g. 16 kHz, 16-bit PCM).
Behavioral Preservation Plan: >
  Maintain event ordering: Capture → Preprocess → STT → Analyzer → Responder → TTS → InterruptHandler.
  Keep individual health checks to allow granular failovers.
```

```yaml
Group Name: VisionProcessingSuite
Included Agents:
  - FaceRecognitionAgent  # MainPC
  - VisionProcessingAgent # PC2
Reasoning: >
  Both perform computer vision tasks using shared GPU resources and feed identities/frames into Responder or Memory.
Potential Risks:
  - Model version mismatch between agents.
  - Simultaneous GPU access.
Suggested Mitigations:
  - Use ModelManagerSuite to allocate GPU sessions.
  - Align on single face/vision model version.
Behavioral Preservation Plan: >
  Expose `/vision/recognise` and `/vision/process` endpoints with common protobuf schema.
```

```yaml
Group Name: EmotionProcessingSuite
Included Agents:
  - EmotionEngine
  - MoodTrackerAgent
  - HumanAwarenessAgent
  - ToneDetector
  - VoiceProfilingAgent
  - EmpathyAgent
Reasoning: >
  Emotional state detection, tracking and synthesis form closed feedback loop impacting dialogue tone.
Potential Risks:
  - State explosion if multiple detectors write to same memory keys.
  - Latency spikes could desync emotion rendering.
Suggested Mitigations:
  - Central emotion state store inside MemoryHub.
  - Throttle update frequency based on conversation turn.
Behavioral Preservation Plan: >
  Keep identical REST verbs (`/emotion/state`, `/emotion/update`).  Ensure EmpathyAgent still hooks into StreamingTTSAgent for vocal tone modulation.
```

```yaml
Group Name: LearningOptimizationSuite
Included Agents:
  - ModelEvaluationFramework
  - LearningOrchestrationService
  - LearningOpportunityDetector
  - LearningManager
  - ActiveLearningMonitor
  - SelfTrainingOrchestrator
  - LocalFineTunerAgent
  - LearningAdjusterAgent
Reasoning: >
  End-to-end continual learning loop – detect opportunities, fine-tune models, evaluate and deploy.
Potential Risks:
  - Race conditions between fine-tuning jobs and PredictiveLoader.
  - Over-consumption of GPU during peak dialogue load.
Suggested Mitigations:
  - Schedule learning tasks via ResourceManagerSuite’s priority queues.
  - Impose GPU quota via ModelManagerSuite.
Behavioral Preservation Plan: >
  Keep dataset paths unchanged; migrate SQLite DBs to single learning DB.  Maintain Canary deployment checks before model promotion.
```

```yaml
Group Name: RoutingAndConnectivity
Included Agents:
  - AdvancedRouter (PC2)
  - RemoteConnectorAgent
  - TieredResponder
  - ProactiveAgent
Reasoning: >
  Handles message routing, remote links and multi-tier response logic bridging MainPC and PC2.
Potential Risks:
  - Infinite routing loops or duplicate message delivery.
  - Port overlaps (AdvancedRouter 7129 vs TieredResponder 7100).
Suggested Mitigations:
  - Implement hop-count header and deduplicate IDs.
  - Reserve dedicated port range 7200-7250 for consolidated router.
Behavioral Preservation Plan: >
  Maintain ZMQ & REST hybrid transport used by AdvancedRouter; keep TieredResponder’s fallback path intact.
```

```yaml
Group Name: ObservabilityAndErrorHandling
Included Agents:
  - ObservabilityHub
  - ErrorBusSuite
Reasoning: >
  These are cross-cutting concerns that provide metrics, tracing and distributed error handling for all agents.
Potential Risks:
  - Event bus flood if high-frequency streams (Audio) generate too many metrics.
Suggested Mitigations:
  - Apply sampling and back-pressure in ObservabilityHub.
Behavioral Preservation Plan: >
  Preserve topic schema on ZMQ (error.*, metric.*).  Keep Prometheus exporter on :9090 unchanged.
```

```yaml
Group Name: TutoringAndDreamWorldServices
Included Agents:
  - DreamWorldAgent
  - DreamingModeAgent
  - TutoringServiceAgent
  - TutorAgent
  - TutoringAgent
Reasoning: >
  These user-facing cognitive/educational experiences share similar long-context generation and rely on MemoryHub.
Potential Risks:
  - Resource over-use on PC2’s RTX 3060.
  - Overlap in prompt-engineering templates between tutoring and dream modes.
Suggested Mitigations:
  - Allocate lower GPU priority in ResourceManagerSuite.
  - Separate prompt libraries by namespace.
Behavioral Preservation Plan: >
  Ensure DreamWorld features remain opt-in.  Keep tutoring agents’ API stable (`/tutor/ask`).
```

```yaml
Group Name: WebInteractionSuite
Included Agents:
  - UnifiedWebAgent
  - FileSystemAssistantAgent
Reasoning: >
  Combines web scraping/navigation with file system manipulation in support of higher-level agents.
Potential Risks:
  - Security risks from unrestricted file operations.
Suggested Mitigations:
  - Enforce SecurityGateway token validation on all requests.
Behavioral Preservation Plan: >
  Retain existing port 7126 for UnifiedWebAgent and ensure FS operations are sandboxed via container volume rules.
```

---

## Cross-Group Dependencies (summary)

* Most groups depend on **SystemCore** and **ModelManagementSuite**.
* **ObservabilityAndErrorHandling** should be initialised before any non-core service.
* **MemoryServices** is a critical shared dependency across MainPC and PC2 – keep network link health checks.

---

> **Status:** Draft generated automatically by background agent – requires human review before refactor.