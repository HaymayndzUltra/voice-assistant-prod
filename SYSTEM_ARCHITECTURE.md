# Distributed AI System Architecture

> **Hosts**  
> • **MainPC** – NVIDIA RTX 4090  
> • **PC2** – NVIDIA RTX 3060

---

## 1  High-Level Architecture Diagram

```mermaid
graph TD
  %%==================== MainPC ====================%%
  subgraph MAINPC [MainPC (RTX 4090)]
    direction TB
    %% Core Services
    subgraph Core_Services
      ServiceRegistry[ServiceRegistry\n7200 / 8200]
      SystemDigitalTwin[SystemDigitalTwin\n7220 / 8220]
      RequestCoordinator[RequestCoordinator\n26002 / 27002]
      UnifiedSystemAgent[UnifiedSystemAgent\n7225 / 8225]
      ObservabilityHub_MP[ObservabilityHub\n9000 / 9100]
      ModelManagerSuite[ModelManagerSuite*\n7211 / 8211]
      ServiceRegistry --> SystemDigitalTwin
      SystemDigitalTwin --> RequestCoordinator
      SystemDigitalTwin --> UnifiedSystemAgent
      SystemDigitalTwin -. metrics .-> ObservabilityHub_MP
      ModelManagerSuite -->|GPU| VRAMOptimizerAgent
    end

    %% GPU Infrastructure
    subgraph GPU_Infrastructure
      VRAMOptimizerAgent[VRAMOptimizerAgent*\n5572 / 6572]
    end

    %% Vision Processing (sample)
    subgraph Vision_Processing
      FaceRecognitionAgent[FaceRecognitionAgent*\n5610 / 6610]
    end
  end

  %%==================== PC2 ====================%%
  subgraph PC2 [PC2 (RTX 3060)]
    direction TB
    MemoryOrchestratorService[MemoryOrchestratorService\n7140 / 8140]
    TieredResponder[TieredResponder\n7100 / 8100]
    AsyncProcessor[AsyncProcessor\n7101 / 8101]
    CacheManager[CacheManager\n7102 / 8102]
    VisionProcessingAgent_PC2[VisionProcessingAgent*\n7150 / 8150]
    ObservabilityHub_PC2[ObservabilityHub\n9000 / 9100]
    MemoryOrchestratorService --> TieredResponder
    MemoryOrchestratorService --> CacheManager
    TieredResponder --> AsyncProcessor
    CacheManager --> VisionProcessingAgent_PC2
  end

  %%==================== Cross-Host Links ====================%%
  ObservabilityHub_PC2 --"cross-machine sync"--> ObservabilityHub_MP
  MemoryOrchestratorService -. data .-> SystemDigitalTwin
```
Note: Nodes marked with an asterisk (*) utilise GPU resources.

---

## 2  System Overview
The system is a distributed set of AI services running across two physical hosts:

• **MainPC** (Linux, NVIDIA RTX 4090) – runs core reasoning, language, memory, GPU-heavy LLM and vision components.  
• **PC2** (Linux, NVIDIA RTX 3060) – offloads memory orchestration, specialised tutoring/vision agents, and auxiliary services.  

Services communicate primarily over ZeroMQ and HTTP on a shared bridge network `ai_system_network` (subnet 172.20.0.0/16). Consolidated monitoring is provided by `ObservabilityHub`, which synchronises metrics between hosts.

---

## 3  System-Wide Settings
| Setting                                  | MainPC | PC2 |
|------------------------------------------|:------:|:---:|
| CPU limit                                | 80 %   | 80 % |
| RAM limit                                | 2048 MB| 4096 MB |
| Max threads per agent                    | 4      | 8 |
| Health-check interval / timeout / retries| 30 s / 10 s / 3 | 30 s / 10 s / 3 |
| Network bridge & subnet                  | `ai_system_network` 172.20.0.0/16 | same bridge |
| Volumes mounted                          | `./logs`, `./models`, `./data`, `./config` | n/a (handled per-agent) |

---

## 4  Agent / Service Catalogue

### Legend
• **Req.** – service marked `required: true` in config  
• **GPU** – service performs GPU inference or optimisation (RTX model shown)  
• **Deps** – direct runtime dependencies  

### 4.1  MainPC Agents (RTX 4090)

#### Core Services
| Name | Port / HC | Script Path | Req. | Deps | Notes |
|------|-----------|-------------|:----:|------|-------|
| ServiceRegistry | 7200 / 8200 | `main_pc_code/agents/service_registry_agent.py` | ✅ | – | In-memory registry (Redis optional) |
| SystemDigitalTwin | 7220 / 8220 | `main_pc_code/agents/system_digital_twin.py` | ✅ | ServiceRegistry | Central state DB, shared with PC2 agents |
| RequestCoordinator | 26002 / 27002 | `main_pc_code/agents/request_coordinator.py` | ✅ | SystemDigitalTwin | Orchestrates request routing |
| UnifiedSystemAgent | 7225 / 8225 | `main_pc_code/agents/unified_system_agent.py` | ✅ | SystemDigitalTwin | High-level orchestrator |
| ObservabilityHub | 9000 / 9100 | `phase1_implementation/.../observability_hub.py` | ✅ | SystemDigitalTwin | Consolidated monitoring; syncs with PC2 |
| ModelManagerSuite | 7211 / 8211 | `main_pc_code/model_manager_suite.py` | ✅ | SystemDigitalTwin | GPU model loading / VRAM budget (GPU-RTX 4090) |

... etc (tables for each group)

#### GPU Infrastructure
| Name | Port / HC | Path | Req. | Deps | GPU | Notes |
|------|-----------|------|:----:|------|-----|-------|
| VRAMOptimizerAgent | 5572 / 6572 | `main_pc_code/agents/vram_optimizer_agent.py` | ✅ | ModelManagerSuite, RequestCoordinator, SystemDigitalTwin | RTX 4090 | Dynamically frees/reserves VRAM |

#### Vision Processing
| Name | Port / HC | Path | Req. | Deps | GPU | Notes |
|------|-----------|------|:----:|------|-----|-------|
| FaceRecognitionAgent | 5610 / 6610 | `main_pc_code/agents/face_recognition_agent.py` | ✅ | ReqCoord, ModelManagerSuite, SystemDigitalTwin | RTX 4090 | Uses vision encoder on GPU |

*(Continue with other MainPC agent groups following the same table format — memory_system, utility_services, reasoning_services, language_processing, speech_services, audio_interface, emotion_system, etc.)*

### 4.2  PC2 Agents (RTX 3060)

| Name | Port / HC | Script Path | Req. | Deps | GPU | Notes |
|------|-----------|-------------|:----:|------|-----|-------|
| MemoryOrchestratorService | 7140 / 8140 | `pc2_code/agents/memory_orchestrator_service.py` | ✅ | – | – | Manages distributed memory shards |
| TieredResponder | 7100 / 8100 | `pc2_code/agents/tiered_responder.py` | ✅ | ResourceManager | – | Multi-tier response logic |
| AsyncProcessor | 7101 / 8101 | `pc2_code/agents/async_processor.py` | ✅ | ResourceManager | – | Background task executor |
| CacheManager | 7102 / 8102 | `pc2_code/agents/cache_manager.py` | ✅ | MemoryOrchestratorService | – | LRU / KV cache |
| VisionProcessingAgent | 7150 / 8150 | `pc2_code/agents/VisionProcessingAgent.py` | ✅ | CacheManager | RTX 3060 | GPU-accelerated inference |
| DreamWorldAgent | 7104 / 8104 | `pc2_code/agents/DreamWorldAgent.py` | ✅ | MemoryOrchestratorService | RTX 3060 | Generative dreaming mode |
| UnifiedMemoryReasoningAgent | 7105 / 8105 | `pc2_code/agents/unified_memory_reasoning_agent.py` | ✅ | MemoryOrchestratorService | – | Complex queries across memory shards |
| ObservabilityHub (PC2) | 9000 / 9100 | same as MainPC path | ✅ | — | – | `scope: pc2_agents`, syncs to MainPC hub |
| ... | ... | ... | ... | ... | ... | ... |

*(Continue for remaining PC2 agents.)*

---

## 5  Cross-Host Relationships & Data Flows
1. **ObservabilityHub ↔ Cross-Machine Sync** – PC2 hub pushes metrics to MainPC hub endpoint `http://192.168.100.16:9000`.
2. **MemoryOrchestratorService → SystemDigitalTwin** – distributed memory updates.
3. **VisionProcessingAgent (PC2) → FaceRecognitionAgent (MainPC)** – optional raw/processed vision frames.
4. **UnifiedWebAgent (PC2) → RequestCoordinator (MainPC)** – web-derived actions.

---

## 6  Update & Extension Guidelines
• Each new agent must declare: unique port + health port, dependencies, and whether it requires GPU.  
• Update the Mermaid diagram blocks (subgraphs) accordingly.  
• Keep cross-host links explicit for easier troubleshooting.

---

## 7  Detailed Agent Feature & Purpose Reference

### 7.1  MainPC Agents (RTX 4090)

#### core_services

##### ServiceRegistry
- **Subsystem:** core_services  
- **Script Path:** `main_pc_code/agents/service_registry_agent.py`  
- **Ports:** 7200 (main), 8200 (health)  
- **Dependencies:** —  
- **Required:** ✅  
- **Config:** `backend`, `redis.url`, `redis.prefix`  
- **Features & Purpose:**  
  - Central directory for dynamic service discovery across the AI platform.  
  - Supports in-memory mode or external Redis for high availability.  
  - Handles heart-beats and endpoint look-ups for all registered agents.  
  - TODO: Needs clarification on authentication / ACL support.

##### SystemDigitalTwin
- **Subsystem:** core_services  
- **Script Path:** `main_pc_code/agents/system_digital_twin.py`  
- **Ports:** 7220 / 8220  
- **Dependencies:** ServiceRegistry  
- **Required:** ✅  
- **Config:** `db_path`, `redis.*`, `zmq_request_timeout`  
- **Features & Purpose:**  
  - Maintains a real-time, unified representation of system state (memory, metrics, topology).  
  - Exposes fast ZMQ/HTTP API for querying and updating state.  
  - Synchronises with PC2 services (e.g., MemoryOrchestratorService) to keep distributed state consistent.

##### RequestCoordinator
- **Subsystem:** core_services  
- **Script Path:** `main_pc_code/agents/request_coordinator.py`  
- **Ports:** 26002 / 27002  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Routes incoming user / system requests to the correct downstream service(s).  
  - Provides back-pressure, prioritisation, and aggregation mechanisms.  
  - Acts as the main entry point for higher-level orchestration.

##### UnifiedSystemAgent
- **Subsystem:** core_services  
- **Script Path:** `main_pc_code/agents/unified_system_agent.py`  
- **Ports:** 7225 / 8225  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - High-level controller that exposes consolidated commands to manage the entire AI system.  
  - Coordinates complex multi-agent workflows.  
  - TODO: Needs clarification on supported command set.

##### ObservabilityHub (MainPC)
- **Subsystem:** core_services  
- **Script Path:** `phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py`  
- **Ports:** 9000 / 9100  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** `prometheus_enabled`, `parallel_health_checks`, `prediction_enabled`  
- **Features & Purpose:**  
  - Centralised monitoring, logging, and predictive-health analytics.  
  - Exposes Prometheus metrics and health dashboards.  
  - Serves as cross-machine sync target for PC2 ObservabilityHub.

##### ModelManagerSuite
- **Subsystem:** core_services  
- **Script Path:** `main_pc_code/model_manager_suite.py`  
- **Ports:** 7211 / 8211  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** `models_dir`, `vram_budget_percentage`, `idle_timeout`  
- **Features & Purpose:**  
  - Consolidates GGUF/LLM model loading, unloading, and performance tracking.  
  - Manages VRAM allocation (RTX 4090) and auto-eviction of idle models.  
  - Performs model health checks, warm-up, and version management.  
  - TODO: Needs clarification on batch inference / multi-GPU scaling.

#### memory_system

##### MemoryClient
- **Subsystem:** memory_system  
- **Script Path:** `main_pc_code/agents/memory_client.py`  
- **Ports:** 5713 / 6713  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Acts as lightweight client interfacing with distributed memory services (incl. PC2).  
  - Provides caching, retry logic, and simple CRUD API for memory entries.

##### SessionMemoryAgent
- **Subsystem:** memory_system  
- **Script Path:** `main_pc_code/agents/session_memory_agent.py`  
- **Ports:** 5574 / 6574  
- **Dependencies:** RequestCoordinator, SystemDigitalTwin, MemoryClient  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Manages short-lived session context for user conversations.  
  - Performs context window trimming and relevancy scoring.  
  - TODO: Needs clarification on persistence strategy.

##### KnowledgeBase
- **Subsystem:** memory_system  
- **Script Path:** `main_pc_code/agents/knowledge_base.py`  
- **Ports:** 5715 / 6715  
- **Dependencies:** MemoryClient, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Provides long-term semantic storage and retrieval (vector or symbolic).  
  - Supplies grounding facts to reasoning services.  
  - TODO: Needs clarification on indexing backend.

#### utility_services

##### CodeGenerator
- **Subsystem:** utility_services  
- **Script Path:** `main_pc_code/agents/code_generator_agent.py`  
- **Ports:** 5650 / 6650  
- **Dependencies:** SystemDigitalTwin, ModelManagerSuite  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Generates, refactors, or patches source code upon request.  
  - Leverages LLMs for code synthesis and unit-test creation.

##### SelfTrainingOrchestrator
- **Subsystem:** utility_services  
- **Script Path:** `main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py`  
- **Ports:** 5660 / 6660  
- **Dependencies:** SystemDigitalTwin, ModelManagerSuite  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Coordinates self-supervised fine-tuning cycles on local data.  
  - Schedules training jobs respecting VRAM/CPU limits.  
  - TODO: Needs clarification on checkpointing.

##### PredictiveHealthMonitor
- **Subsystem:** utility_services  
- **Script Path:** `main_pc_code/agents/predictive_health_monitor.py`  
- **Ports:** 5613 / 6613  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Applies ML models to forecast potential service degradations.  
  - Emits early-warning events to ObservabilityHub.

##### FixedStreamingTranslation
- **Subsystem:** utility_services  
- **Script Path:** `main_pc_code/agents/fixed_streaming_translation.py`  
- **Ports:** 5584 / 6584  
- **Dependencies:** ModelManagerSuite, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Provides low-latency streaming translation (speech / text) with predefined language pairs.  
  - Uses GPU models when available.

##### Executor
- **Subsystem:** utility_services  
- **Script Path:** `main_pc_code/agents/executor.py`  
- **Ports:** 5606 / 6606  
- **Dependencies:** CodeGenerator, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Safely executes generated code snippets inside sandboxes.  
  - Returns results or error traces back to coordinator.

##### TinyLlamaServiceEnhanced
- **Subsystem:** utility_services  
- **Script Path:** `main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py`  
- **Ports:** 5615 / 6615  
- **Dependencies:** ModelManagerSuite, SystemDigitalTwin  
- **Required:** ❌ (optional)  
- **Config:** —  
- **Features & Purpose:**  
  - Serves TinyLlama or similar compact models for fast responses.  
  - GPU optimised for RTX 4090.

##### LocalFineTunerAgent
- **Subsystem:** utility_services  
- **Script Path:** `main_pc_code/FORMAINPC/LocalFineTunerAgent.py`  
- **Ports:** 5642 / 6642  
- **Dependencies:** SelfTrainingOrchestrator, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Runs lightweight fine-tuning or LoRA adapters on selected models.  
  - Monitors training metrics and pushes to ObservabilityHub.

##### NLLBAdapter
- **Subsystem:** utility_services  
- **Script Path:** `main_pc_code/FORMAINPC/NLLBAdapter.py`  
- **Ports:** 5581 / 6581  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Bridges Facebook NLLB models into translation pipelines.  
  - Provides pre- and post-processing specific to NLLB.

#### gpu_infrastructure

##### VRAMOptimizerAgent
- **Subsystem:** gpu_infrastructure  
- **Script Path:** `main_pc_code/agents/vram_optimizer_agent.py`  
- **Ports:** 5572 / 6572  
- **Dependencies:** ModelManagerSuite, RequestCoordinator, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Continuously monitors GPU memory usage and unloads or swaps models to respect VRAM budget.  
  - Provides policies for pre-fetching and auto-compression.

#### reasoning_services

##### ChainOfThoughtAgent
- **Subsystem:** reasoning_services  
- **Script Path:** `main_pc_code/FORMAINPC/ChainOfThoughtAgent.py`  
- **Ports:** 5612 / 6612  
- **Dependencies:** ModelManagerSuite, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Implements advanced CoT prompting and reasoning chains.  
  - Supplies explanations to downstream services.

##### GoTToTAgent
- **Subsystem:** reasoning_services  
- **Script Path:** `main_pc_code/FORMAINPC/GOT_TOTAgent.py`  
- **Ports:** 5646 / 6646  
- **Dependencies:** ModelManagerSuite, SystemDigitalTwin, ChainOfThoughtAgent  
- **Required:** ❌ (optional)  
- **Config:** —  
- **Features & Purpose:**  
  - Experimental "Tree of Thoughts" agent building on CoT agent.  
  - TODO: Needs clarification on maturity and production readiness.

##### CognitiveModelAgent
- **Subsystem:** reasoning_services  
- **Script Path:** `main_pc_code/FORMAINPC/CognitiveModelAgent.py`  
- **Ports:** 5641 / 6641  
- **Dependencies:** ChainOfThoughtAgent, SystemDigitalTwin  
- **Required:** ❌  
- **Config:** —  
- **Features & Purpose:**  
  - Simulates human-like cognitive planning layers.  
  - Feeds high-level plans to GoalManager and Executor.

#### vision_processing

##### FaceRecognitionAgent
- **Subsystem:** vision_processing  
- **Script Path:** `main_pc_code/agents/face_recognition_agent.py`  
- **Ports:** 5610 / 6610  
- **Dependencies:** RequestCoordinator, ModelManagerSuite, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Performs real-time face detection and embedding extraction.  
  - Publishes identity and emotion cues to EmotionEngine.

#### learning_knowledge

##### LearningOrchestrationService
- **Subsystem:** learning_knowledge  
- **Script Path:** `main_pc_code/agents/learning_orchestration_service.py`  
- **Ports:** 7212 / 8212  
- **Dependencies:** ModelEvaluationFramework (TODO), SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Coordinates multi-stage active-learning loops.  
  - Interfaces with SelfTrainingOrchestrator for training jobs.  
  - TODO: Clarify dependency `ModelEvaluationFramework` (missing agent).

##### LearningOpportunityDetector
- **Subsystem:** learning_knowledge  
- **Script Path:** `main_pc_code/agents/learning_opportunity_detector.py`  
- **Ports:** 7202 / 8202  
- **Dependencies:** LearningOrchestrationService, MemoryClient, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Scans interaction logs to identify gaps for future training.  
  - Emits opportunity events for active learning.

##### LearningManager
- **Subsystem:** learning_knowledge  
- **Script Path:** `main_pc_code/agents/learning_manager.py`  
- **Ports:** 5580 / 6580  
- **Dependencies:** MemoryClient, RequestCoordinator, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Orchestrates curriculum and knowledge consolidation.  
  - Maintains learning schedules and priorities.

##### ActiveLearningMonitor
- **Subsystem:** learning_knowledge  
- **Script Path:** `main_pc_code/agents/active_learning_monitor.py`  
- **Ports:** 5638 / 6638  
- **Dependencies:** LearningManager, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Tracks progress and effectiveness of active learning cycles.  
  - Provides KPIs and alerts to ObservabilityHub.

##### LearningAdjusterAgent
- **Subsystem:** learning_knowledge  
- **Script Path:** `main_pc_code/FORMAINPC/LearningAdjusterAgent.py`  
- **Ports:** 5643 / 6643  
- **Dependencies:** SelfTrainingOrchestrator, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Dynamically tunes hyper-parameters during training.  
  - Suggests adaptive learning rates and sampling.

#### language_processing

##### ModelOrchestrator
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/model_orchestrator.py`  
- **Ports:** 7210 / 8210  
- **Dependencies:** RequestCoordinator, ModelManagerSuite, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Chooses the best language model for a given request (routing / ensemble).  
  - Handles model fall-back logic based on latency and cost.

##### GoalManager
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/goal_manager.py`  
- **Ports:** 7205 / 8205  
- **Dependencies:** RequestCoordinator, ModelOrchestrator, SystemDigitalTwin, MemoryClient  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Tracks and decomposes user goals into actionable tasks.  
  - Works with CognitiveModelAgent for planning.

##### IntentionValidatorAgent
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/IntentionValidatorAgent.py`  
- **Ports:** 5701 / 6701  
- **Dependencies:** RequestCoordinator, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Validates whether a proposed action aligns with user’s stated intent and safety rules.

##### NLUAgent
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/nlu_agent.py`  
- **Ports:** 5709 / 6709  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Performs intent recognition, entity extraction, and semantic parsing.

##### AdvancedCommandHandler
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/advanced_command_handler.py`  
- **Ports:** 5710 / 6710  
- **Dependencies:** NLUAgent, CodeGenerator, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Translates parsed intents into executable commands or code.  
  - Leverages CodeGenerator for implementation.

##### ChitchatAgent
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/chitchat_agent.py`  
- **Ports:** 5711 / 6711  
- **Dependencies:** NLUAgent, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Handles open-domain small-talk and social conversation.  
  - Keeps tone and personality consistent with DynamicIdentityAgent.

##### FeedbackHandler
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/feedback_handler.py`  
- **Ports:** 5636 / 6636  
- **Dependencies:** NLUAgent, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Collects explicit user feedback (thumbs-up/down, ratings) and logs to LearningManager.

##### Responder
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/responder.py`  
- **Ports:** 5637 / 6637  
- **Dependencies:** EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, SystemDigitalTwin, TTSService  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Composes and delivers multimodal responses (text + speech + facial cues).  
  - Ensures emotional alignment via EmotionEngine.

##### TranslationService
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/translation_service.py`  
- **Ports:** 5595 / 6595  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - General-purpose text translation across supported languages.

##### DynamicIdentityAgent
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/DynamicIdentityAgent.py`  
- **Ports:** 5802 / 6802  
- **Dependencies:** RequestCoordinator, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Manages persona, voice style, and presentation layer for consistency.  
  - Updates identity traits based on context (e.g., professional, friendly).

##### EmotionSynthesisAgent
- **Subsystem:** language_processing  
- **Script Path:** `main_pc_code/agents/emotion_synthesis_agent.py`  
- **Ports:** 5706 / 6706  
- **Dependencies:** RequestCoordinator, ModelManagerSuite, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Generates emotional speech prosody and facial animation parameters.

#### speech_services

##### STTService
- **Subsystem:** speech_services  
- **Script Path:** `main_pc_code/services/stt_service.py`  
- **Ports:** 5800 / 6800  
- **Dependencies:** ModelManagerSuite, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Provides streaming speech-to-text with low latency.  
  - Utilises GPU acoustic models.

##### TTSService
- **Subsystem:** speech_services  
- **Script Path:** `main_pc_code/services/tts_service.py`  
- **Ports:** 5801 / 6801  
- **Dependencies:** ModelManagerSuite, SystemDigitalTwin, StreamingInterruptHandler  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Converts text to speech, supporting multiple voices.  
  - Integrates with StreamingTTSAgent for chunked output.

#### audio_interface

##### AudioCapture
- **Subsystem:** audio_interface  
- **Script Path:** `main_pc_code/agents/streaming_audio_capture.py`  
- **Ports:** 6550 / 7550  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Captures microphone audio stream, applies basic noise suppression.

##### FusedAudioPreprocessor
- **Subsystem:** audio_interface  
- **Script Path:** `main_pc_code/agents/fused_audio_preprocessor.py`  
- **Ports:** 6551 / 7551  
- **Dependencies:** AudioCapture, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Performs voice activity detection and audio normalisation.

##### StreamingInterruptHandler
- **Subsystem:** audio_interface  
- **Script Path:** `main_pc_code/agents/streaming_interrupt_handler.py`  
- **Ports:** 5576 / 6576  
- **Dependencies:** StreamingSpeechRecognition, StreamingTTSAgent, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Detects interruptions or overlapping speech and coordinates pause/resume.

##### StreamingSpeechRecognition
- **Subsystem:** audio_interface  
- **Script Path:** `main_pc_code/agents/streaming_speech_recognition.py`  
- **Ports:** 6553 / 7553  
- **Dependencies:** FusedAudioPreprocessor, RequestCoordinator, STTService, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Converts live audio chunks into text with sub-second latency.

##### StreamingTTSAgent
- **Subsystem:** audio_interface  
- **Script Path:** `main_pc_code/agents/streaming_tts_agent.py`  
- **Ports:** 5562 / 6562  
- **Dependencies:** RequestCoordinator, TTSService, SystemDigitalTwin, UnifiedSystemAgent  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Streams TTS output back to the user while still generating next chunks.

##### WakeWordDetector
- **Subsystem:** audio_interface  
- **Script Path:** `main_pc_code/agents/wake_word_detector.py`  
- **Ports:** 6552 / 7552  
- **Dependencies:** AudioCapture, FusedAudioPreprocessor, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Listens for predefined wake words to start interactions.

##### StreamingLanguageAnalyzer
- **Subsystem:** audio_interface  
- **Script Path:** `main_pc_code/agents/streaming_language_analyzer.py`  
- **Ports:** 5579 / 6579  
- **Dependencies:** StreamingSpeechRecognition, SystemDigitalTwin, TranslationService  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Provides language ID, quality assessment, and automatic translation suggestions.

##### ProactiveAgent
- **Subsystem:** audio_interface  
- **Script Path:** `main_pc_code/agents/ProactiveAgent.py`  
- **Ports:** 5624 / 6624  
- **Dependencies:** RequestCoordinator, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Initiates proactive prompts (reminders, suggestions) based on context.

#### emotion_system

##### EmotionEngine
- **Subsystem:** emotion_system  
- **Script Path:** `main_pc_code/agents/emotion_engine.py`  
- **Ports:** 5590 / 6590  
- **Dependencies:** SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Computes emotional state vector from multimodal cues.  
  - Supplies emotion signals to Responder and TTSService.

##### MoodTrackerAgent
- **Subsystem:** emotion_system  
- **Script Path:** `main_pc_code/agents/mood_tracker_agent.py`  
- **Ports:** 5704 / 6704  
- **Dependencies:** EmotionEngine, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Tracks long-term mood trends for personalised responses.

##### HumanAwarenessAgent
- **Subsystem:** emotion_system  
- **Script Path:** `main_pc_code/agents/human_awareness_agent.py`  
- **Ports:** 5705 / 6705  
- **Dependencies:** EmotionEngine, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Recognises human presence and attention via sensor data.

##### ToneDetector
- **Subsystem:** emotion_system  
- **Script Path:** `main_pc_code/agents/tone_detector.py`  
- **Ports:** 5625 / 6625  
- **Dependencies:** EmotionEngine, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Detects tone (sarcasm, anger, etc.) in user speech.

##### VoiceProfilingAgent
- **Subsystem:** emotion_system  
- **Script Path:** `main_pc_code/agents/voice_profiling_agent.py`  
- **Ports:** 5708 / 6708  
- **Dependencies:** EmotionEngine, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Builds speaker profiles (pitch, timbre) for personalised TTS.

##### EmpathyAgent
- **Subsystem:** emotion_system  
- **Script Path:** `main_pc_code/agents/EmpathyAgent.py`  
- **Ports:** 5703 / 6703  
- **Dependencies:** EmotionEngine, StreamingTTSAgent, SystemDigitalTwin  
- **Required:** ✅  
- **Config:** —  
- **Features & Purpose:**  
  - Generates empathetic verbal and vocal responses.

### 7.2  PC2 Agents (RTX 3060)

##### MemoryOrchestratorService
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/memory_orchestrator_service.py`  
- **Ports:** 7140 / 8140  
- **Dependencies:** —  
- **Required:** ✅  
- **Features & Purpose:**  
  - Core memory sharding and reconciliation service for distributed memory.  
  - Exposes API consumed by MainPC MemoryClient and SessionMemoryAgent.

##### TieredResponder
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/tiered_responder.py`  
- **Ports:** 7100 / 8100  
- **Dependencies:** ResourceManager  
- **Required:** ✅  
- **Features & Purpose:**  
  - Implements multi-layer response hierarchy (fast heuristic vs deep reasoning).  
  - TODO: Needs clarification on tier selection logic.

##### AsyncProcessor
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/async_processor.py`  
- **Ports:** 7101 / 8101  
- **Dependencies:** ResourceManager  
- **Required:** ✅  
- **Features & Purpose:**  
  - Executes long-running or asynchronous tasks off the critical path.

##### CacheManager
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/cache_manager.py`  
- **Ports:** 7102 / 8102  
- **Dependencies:** MemoryOrchestratorService  
- **Required:** ✅  
- **Features & Purpose:**  
  - Provides shared in-memory / disk cache for quick lookup.  
  - Supports expiration and invalidation policies.

##### VisionProcessingAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/VisionProcessingAgent.py`  
- **Ports:** 7150 / 8150  
- **Dependencies:** CacheManager  
- **Required:** ✅  
- **Features & Purpose:**  
  - Performs computer-vision inference (RTX 3060).  
  - May post-process frames for MainPC FaceRecognitionAgent.

##### DreamWorldAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/DreamWorldAgent.py`  
- **Ports:** 7104 / 8104  
- **Dependencies:** MemoryOrchestratorService  
- **Required:** ✅  
- **Features & Purpose:**  
  - Generates simulated scenarios / "dreams" to augment training data.

##### UnifiedMemoryReasoningAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/unified_memory_reasoning_agent.py`  
- **Ports:** 7105 / 8105  
- **Dependencies:** MemoryOrchestratorService  
- **Required:** ✅  
- **Features & Purpose:**  
  - Executes complex queries across distributed memory shards and returns aggregated insights.

##### TutorAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/tutor_agent.py`  
- **Ports:** 7108 / 8108  
- **Dependencies:** MemoryOrchestratorService  
- **Required:** ✅  
- **Features & Purpose:**  
  - Provides personalised tutorial sessions based on learner profile.

##### TutoringAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/tutoring_agent.py`  
- **Ports:** 7131 / 8131  
- **Dependencies:** MemoryOrchestratorService  
- **Required:** ✅  
- **Features & Purpose:**  
  - Similar to TutorAgent; specialises in step-by-step guidance.

##### ContextManager
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/context_manager.py`  
- **Ports:** 7111 / 8111  
- **Dependencies:** MemoryOrchestratorService  
- **Required:** ✅  
- **Features & Purpose:**  
  - Maintains contextual information for PC2-based agents.

##### ExperienceTracker
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/experience_tracker.py`  
- **Ports:** 7112 / 8112  
- **Dependencies:** MemoryOrchestratorService  
- **Required:** ✅  
- **Features & Purpose:**  
  - Records user interactions and outcomes for analytics.

##### ResourceManager
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/resource_manager.py`  
- **Ports:** 7113 / 8113  
- **Dependencies:** ObservabilityHub  
- **Required:** ✅  
- **Features & Purpose:**  
  - Monitors CPU/GPU/memory usage on PC2 and allocates resources to child agents.

##### TaskScheduler
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/task_scheduler.py`  
- **Ports:** 7115 / 8115  
- **Dependencies:** AsyncProcessor  
- **Required:** ✅  
- **Features & Purpose:**  
  - Queues and schedules background jobs based on priority and resource availability.

##### AuthenticationAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/ForPC2/AuthenticationAgent.py`  
- **Ports:** 7116 / 8116  
- **Dependencies:** UnifiedUtilsAgent  
- **Required:** ✅  
- **Features & Purpose:**  
  - Handles user/session authentication for PC2 services.  
  - TODO: Clarify supported auth strategies (JWT/OAuth).

##### UnifiedUtilsAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/ForPC2/unified_utils_agent.py`  
- **Ports:** 7118 / 8118  
- **Dependencies:** ObservabilityHub  
- **Required:** ✅  
- **Features & Purpose:**  
  - Provides shared utility functions (logging, metrics, common helpers).

##### ProactiveContextMonitor
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/ForPC2/proactive_context_monitor.py`  
- **Ports:** 7119 / 8119  
- **Dependencies:** ContextManager  
- **Required:** ✅  
- **Features & Purpose:**  
  - Detects context shifts and triggers tiered responders proactively.

##### AgentTrustScorer
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/AgentTrustScorer.py`  
- **Ports:** 7122 / 8122  
- **Dependencies:** ObservabilityHub  
- **Required:** ✅  
- **Features & Purpose:**  
  - Scores reliability of agents based on historical performance.

##### FileSystemAssistantAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/filesystem_assistant_agent.py`  
- **Ports:** 7123 / 8123  
- **Dependencies:** UnifiedUtilsAgent  
- **Required:** ✅  
- **Features & Purpose:**  
  - Provides file manipulation, search, and organisation tasks.

##### RemoteConnectorAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/remote_connector_agent.py`  
- **Ports:** 7124 / 8124  
- **Dependencies:** AdvancedRouter  
- **Required:** ✅  
- **Features & Purpose:**  
  - Manages secure remote connections / tunnels between MainPC and external systems.

##### AdvancedRouter
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/advanced_router.py`  
- **Ports:** 7129 / 8129  
- **Dependencies:** TaskScheduler  
- **Required:** ✅  
- **Features & Purpose:**  
  - Intelligent routing layer for network packets and agent messages.

##### UnifiedWebAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/unified_web_agent.py`  
- **Ports:** 7126 / 8126  
- **Dependencies:** FileSystemAssistantAgent, MemoryOrchestratorService  
- **Required:** ✅  
- **Features & Purpose:**  
  - Crawls, scrapes, and processes web content for knowledge ingestion.

##### DreamingModeAgent
- **Subsystem:** pc2_services  
- **Script Path:** `pc2_code/agents/DreamingModeAgent.py`  
- **Ports:** 7127 / 8127  
- **Dependencies:** DreamWorldAgent  
- **Required:** ✅  
- **Features & Purpose:**  
  - Engages in generative "dreaming" when system idle to discover novel ideas.

##### ObservabilityHub (PC2)
- **Subsystem:** pc2_services  
- **Script Path:** same as MainPC  
- **Ports:** 9000 / 9100  
- **Dependencies:** —  
- **Required:** ✅  
- **Config:** `scope`, `prometheus_port`, `cross_machine_sync`, `mainpc_hub_endpoint`  
- **Features & Purpose:**  
  - Mirrors metrics collection on PC2; pushes data to MainPC hub.


---

*Document generated automatically from `main_pc_code/config/startup_config.yaml` and `pc2_code/config/startup_config.yaml` — **{date}**.*