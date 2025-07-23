
``python
# Core BaseAgent Pattern (✅ REAL - Used by 90% of agents)
from common.core.base_agent import BaseAgent

# Configuration Management (✅ REAL - Standard across all agents)
from common.config_manager import get_service_ip, get_service_url, get_redis_url, load_unified_config

# ZMQ Pools (✅ REAL - WP-05 implemented)
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket

# Path Management (✅ REAL - Containerization ready)
from common.utils.path_manager import PathManager

# Environment Helpers (✅ REAL - Standard)
from common.env_helpers import get_env

# Standard Python Libraries (✅ REAL)
import zmq, json, logging, threading, time, os, sys
from pathlib import Path
from typing import Dict, Any, Optional, List
```

### REAL NETWORK CONFIG (✅ VERIFIED)

- **MainPC IP**: 192.168.100.16 (RTX 4090)
- **PC2 IP**: 192.168.100.17 (RTX 3060)
- **Environment**: localhost (dev) / actual IPs (prod)

### REAL COMMUNICATION PATTERNS (✅ WORKING)

- **ZMQ REQ/REP**: Request-Reply (primary)
- **ZMQ PUB/SUB**: Publish-Subscribe (events)
- **Port Pattern**: service_port + 1000 = health_port
- **Timeout**: 5000ms standard
- **Message Format**: JSON



# MainPC Agent Inventory Table (by Group) RTX 4090 

## core_services

| #   | Agent Name         | File Path                                                                                                 | Port  | Health Port | Dependencies      | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes                    |
| --- | ------------------ | --------------------------------------------------------------------------------------------------------- | ----- | ----------- | ----------------- | -------------- | -------- | ----------------- | -------------------- | ------------------------ |
| 1   | ServiceRegistry    | main_pc_code/agents/service_registry_agent.py                                                             | 7200  | 8200        | ---               | ---            | ---      | ---               | ---                  | Registry backend options |
| 2   | SystemDigitalTwin  | main_pc_code/agents/system_digital_twin.py                                                                | 7220  | 8220        | ServiceRegistry   | ---            | ---      | ---               | ---                  | Digital twin & state     |
| 3   | RequestCoordinator | main_pc_code/agents/request_coordinator.py                                                                | 26002 | 27002       | SystemDigitalTwin | ---            | ---      | ---               | ---                  | Handles agent requests   |
| 4   | UnifiedSystemAgent | main_pc_code/agents/unified_system_agent.py                                                               | 7225  | 8225        | SystemDigitalTwin | ---            | ---      | ---               | ---                  | System orchestration     |
| 5   | ObservabilityHub   | phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py | 9000  | 9100        | SystemDigitalTwin | ---            | ---      | ---               | ---                  | Consolidated monitoring  |
| 6   | ModelManagerSuite  | main_pc_code/model_manager_suite.py                                                                       | 7211  | 8211        | SystemDigitalTwin | ---            | ---      | ---               | ---                  | Model management         |

## memory_system

| #   | Agent Name         | File Path                                   | Port | Health Port | Dependencies                                        | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes                |
| --- | ------------------ | ------------------------------------------- | ---- | ----------- | --------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | -------------------- |
| 1   | MemoryClient       | main_pc_code/agents/memory_client.py        | 5713 | 6713        | SystemDigitalTwin                                   | ---            | ---      | ---               | ---                  | Memory access        |
| 2   | SessionMemoryAgent | main_pc_code/agents/session_memory_agent.py | 5574 | 6574        | RequestCoordinator, SystemDigitalTwin, MemoryClient | ---            | ---      | ---               | ---                  | Session-level memory |
| 3   | KnowledgeBase      | main_pc_code/agents/knowledge_base.py       | 5715 | 6715        | MemoryClient, SystemDigitalTwin                     | ---            | ---      | ---               | ---                  | Knowledge database   |

## utility_services

| #   | Agent Name                | File Path                                          | Port | Health Port | Dependencies                                | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes                   |
| --- | ------------------------- | -------------------------------------------------- | ---- | ----------- | ------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | ----------------------- |
| 1   | CodeGenerator             | main_pc_code/agents/code_generator_agent.py        | 5650 | 6650        | SystemDigitalTwin, ModelManagerSuite        | ---            | ---      | ---               | ---                  | Code generation         |
| 2   | SelfTrainingOrchestrator  | main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py | 5660 | 6660        | SystemDigitalTwin, ModelManagerSuite        | ---            | ---      | ---               | ---                  | Self-training pipeline  |
| 3   | PredictiveHealthMonitor   | main_pc_code/agents/predictive_health_monitor.py   | 5613 | 6613        | SystemDigitalTwin                           | ---            | ---      | ---               | ---                  | Health prediction       |
| 4   | FixedStreamingTranslation | main_pc_code/agents/fixed_streaming_translation.py | 5584 | 6584        | ModelManagerSuite, SystemDigitalTwin        | ---            | ---      | ---               | ---                  | Streaming translation   |
| 5   | Executor                  | main_pc_code/agents/executor.py                    | 5606 | 6606        | CodeGenerator, SystemDigitalTwin            | ---            | ---      | ---               | ---                  | Task execution          |
| 6   | TinyLlamaServiceEnhanced  | main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py | 5615 | 6615        | ModelManagerSuite, SystemDigitalTwin        | ---            | ---      | ---               | ---                  | Small LLM, not required |
| 7   | LocalFineTunerAgent       | main_pc_code/FORMAINPC/LocalFineTunerAgent.py      | 5642 | 6642        | SelfTrainingOrchestrator, SystemDigitalTwin | ---            | ---      | ---               | ---                  | Local model finetuning  |
| 8   | NLLBAdapter               | main_pc_code/FORMAINPC/NLLBAdapter.py              | 5581 | 6581        | SystemDigitalTwin                           | ---            | ---      | ---               | ---                  | NLLB translation        |

## gpu_infrastructure

| #   | Agent Name         | File Path                                   | Port | Health Port | Dependencies                                             | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes             |
| --- | ------------------ | ------------------------------------------- | ---- | ----------- | -------------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | ----------------- |
| 1   | VRAMOptimizerAgent | main_pc_code/agents/vram_optimizer_agent.py | 5572 | 6572        | ModelManagerSuite, RequestCoordinator, SystemDigitalTwin | ---            | ---      | ---               | ---                  | VRAM optimization |

## reasoning_services

| #   | Agent Name          | File Path                                     | Port | Health Port | Dependencies                                              | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes            |
| --- | ------------------- | --------------------------------------------- | ---- | ----------- | --------------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | ---------------- |
| 1   | ChainOfThoughtAgent | main_pc_code/FORMAINPC/ChainOfThoughtAgent.py | 5612 | 6612        | ModelManagerSuite, SystemDigitalTwin                      | ---            | ---      | ---               | ---                  | Chain-of-thought |
| 2   | GoTToTAgent         | main_pc_code/FORMAINPC/GOT_TOTAgent.py        | 5646 | 6646        | ModelManagerSuite, SystemDigitalTwin, ChainOfThoughtAgent | ---            | ---      | ---               | ---                  | Tree-of-thought  |
| 3   | CognitiveModelAgent | main_pc_code/FORMAINPC/CognitiveModelAgent.py | 5641 | 6641        | ChainOfThoughtAgent, SystemDigitalTwin                    | ---            | ---      | ---               | ---                  | Reasoning model  |

## vision_processing

| #   | Agent Name           | File Path                                     | Port | Health Port | Dependencies                                             | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes            |
| --- | -------------------- | --------------------------------------------- | ---- | ----------- | -------------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | ---------------- |
| 1   | FaceRecognitionAgent | main_pc_code/agents/face_recognition_agent.py | 5610 | 6610        | RequestCoordinator, ModelManagerSuite, SystemDigitalTwin | ---            | ---      | ---               | ---                  | Face recognition |

## learning_knowledge

| #   | Agent Name                   | File Path                                             | Port | Health Port | Dependencies                                                  | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes                   |
| --- | ---------------------------- | ----------------------------------------------------- | ---- | ----------- | ------------------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | ----------------------- |
| 1   | LearningOrchestrationService | main_pc_code/agents/learning_orchestration_service.py | 7210 | 8212        | ModelManagerSuite, SystemDigitalTwin                          | ---            | ---      | ---               | ---                  | Orchestration           |
| 2   | LearningOpportunityDetector  | main_pc_code/agents/learning_opportunity_detector.py  | 7202 | 8202        | LearningOrchestrationService, MemoryClient, SystemDigitalTwin | ---            | ---      | ---               | ---                  | Detects learning ops    |
| 3   | LearningManager              | main_pc_code/agents/learning_manager.py               | 5580 | 6580        | MemoryClient, RequestCoordinator, SystemDigitalTwin           | ---            | ---      | ---               | ---                  | Central learning mgr    |
| 4   | ActiveLearningMonitor        | main_pc_code/agents/active_learning_monitor.py        | 5638 | 6638        | LearningManager, SystemDigitalTwin                            | ---            | ---      | ---               | ---                  | Active learning monitor |
| 5   | LearningAdjusterAgent        | main_pc_code/FORMAINPC/LearningAdjusterAgent.py       | 5643 | 6643        | SelfTrainingOrchestrator, SystemDigitalTwin                   | ---            | ---      | ---               | ---                  | Adjusts learning config |

## language_processing

| #   | Agent Name              | File Path                                       | Port | Health Port | Dependencies                                                                                    | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes                |
| --- | ----------------------- | ----------------------------------------------- | ---- | ----------- | ----------------------------------------------------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | -------------------- |
| 1   | ModelOrchestrator       | main_pc_code/agents/model_orchestrator.py       | 7213 | 8213        | RequestCoordinator, ModelManagerSuite, SystemDigitalTwin                                        | ---            | ---      | ---               | ---                  | LLM Orchestration    |
| 2   | GoalManager             | main_pc_code/agents/goal_manager.py             | 7205 | 8205        | RequestCoordinator, ModelOrchestrator, SystemDigitalTwin, MemoryClient                          | ---            | ---      | ---               | ---                  | Goal management      |
| 3   | IntentionValidatorAgent | main_pc_code/agents/IntentionValidatorAgent.py  | 5701 | 6701        | RequestCoordinator, SystemDigitalTwin                                                           | ---            | ---      | ---               | ---                  | Intention validation |
| 4   | NLUAgent                | main_pc_code/agents/nlu_agent.py                | 5709 | 6709        | SystemDigitalTwin                                                                               | ---            | ---      | ---               | ---                  | NLU component        |
| 5   | AdvancedCommandHandler  | main_pc_code/agents/advanced_command_handler.py | 5710 | 6710        | NLUAgent, CodeGenerator, SystemDigitalTwin                                                      | ---            | ---      | ---               | ---                  | Command handler      |
| 6   | ChitchatAgent           | main_pc_code/agents/chitchat_agent.py           | 5711 | 6711        | NLUAgent, SystemDigitalTwin                                                                     | ---            | ---      | ---               | ---                  | Smalltalk            |
| 7   | FeedbackHandler         | main_pc_code/agents/feedback_handler.py         | 5636 | 6636        | NLUAgent, SystemDigitalTwin                                                                     | ---            | ---      | ---               | ---                  | Feedback             |
| 8   | Responder               | main_pc_code/agents/responder.py                | 5637 | 6637        | EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, SystemDigitalTwin, TTSService | ---            | ---      | ---               | ---                  | Dialogue response    |
| 9   | TranslationService      | main_pc_code/agents/translation_service.py      | 5595 | 6595        | SystemDigitalTwin                                                                               | ---            | ---      | ---               | ---                  | Language translation |
| 10  | DynamicIdentityAgent    | main_pc_code/agents/DynamicIdentityAgent.py     | 5802 | 6802        | RequestCoordinator, SystemDigitalTwin                                                           | ---            | ---      | ---               | ---                  | Dynamic persona      |
| 11  | EmotionSynthesisAgent   | main_pc_code/agents/emotion_synthesis_agent.py  | 5706 | 6706        | RequestCoordinator, ModelManagerSuite, SystemDigitalTwin                                        | ---            | ---      | ---               | ---                  | Synthesis of emotion |

## speech_services

| #   | Agent Name | File Path                            | Port | Health Port | Dependencies                                                    | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes          |
| --- | ---------- | ------------------------------------ | ---- | ----------- | --------------------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | -------------- |
| 1   | STTService | main_pc_code/services/stt_service.py | 5800 | 6800        | ModelManagerSuite, SystemDigitalTwin                            | ---            | ---      | ---               | ---                  | Speech to text |
| 2   | TTSService | main_pc_code/services/tts_service.py | 5801 | 6801        | ModelManagerSuite, SystemDigitalTwin, StreamingInterruptHandler | ---            | ---      | ---               | ---                  | Text to speech |

## audio_interface

| #   | Agent Name                 | File Path                                           | Port | Health Port | Dependencies                                                              | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes                  |
| --- | -------------------------- | --------------------------------------------------- | ---- | ----------- | ------------------------------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | ---------------------- |
| 1   | AudioCapture               | main_pc_code/agents/streaming_audio_capture.py      | 6550 | 7550        | SystemDigitalTwin                                                         | ---            | ---      | ---               | ---                  | Audio capture          |
| 2   | FusedAudioPreprocessor     | main_pc_code/agents/fused_audio_preprocessor.py     | 6551 | 7551        | AudioCapture, SystemDigitalTwin                                           | ---            | ---      | ---               | ---                  | Audio preprocessing    |
| 3   | StreamingInterruptHandler  | main_pc_code/agents/streaming_interrupt_handler.py  | 5576 | 6576        | StreamingSpeechRecognition, StreamingTTSAgent, SystemDigitalTwin          | ---            | ---      | ---               | ---                  | Handles interrupts     |
| 4   | StreamingSpeechRecognition | main_pc_code/agents/streaming_speech_recognition.py | 6553 | 7553        | FusedAudioPreprocessor, RequestCoordinator, STTService, SystemDigitalTwin | ---            | ---      | ---               | ---                  | Streaming STT          |
| 5   | StreamingTTSAgent          | main_pc_code/agents/streaming_tts_agent.py          | 5562 | 6562        | RequestCoordinator, TTSService, SystemDigitalTwin, UnifiedSystemAgent     | ---            | ---      | ---               | ---                  | Streaming TTS          |
| 6   | WakeWordDetector           | main_pc_code/agents/wake_word_detector.py           | 6552 | 7552        | AudioCapture, FusedAudioPreprocessor, SystemDigitalTwin                   | ---            | ---      | ---               | ---                  | Wake word detection    |
| 7   | StreamingLanguageAnalyzer  | main_pc_code/agents/streaming_language_analyzer.py  | 5579 | 6579        | StreamingSpeechRecognition, SystemDigitalTwin, TranslationService         | ---            | ---      | ---               | ---                  | Live language analysis |
| 8   | ProactiveAgent             | main_pc_code/agents/ProactiveAgent.py               | 5624 | 6624        | RequestCoordinator, SystemDigitalTwin                                     | ---            | ---      | ---               | ---                  | Proactive actions      |

## emotion_system

| #   | Agent Name          | File Path                                    | Port | Health Port | Dependencies                                        | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes           |
| --- | ------------------- | -------------------------------------------- | ---- | ----------- | --------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | --------------- |
| 1   | EmotionEngine       | main_pc_code/agents/emotion_engine.py        | 5590 | 6590        | SystemDigitalTwin                                   | ---            | ---      | ---               | ---                  | Core emotion    |
| 2   | MoodTrackerAgent    | main_pc_code/agents/mood_tracker_agent.py    | 5704 | 6704        | EmotionEngine, SystemDigitalTwin                    | ---            | ---      | ---               | ---                  | Mood tracking   |
| 3   | HumanAwarenessAgent | main_pc_code/agents/human_awareness_agent.py | 5705 | 6705        | EmotionEngine, SystemDigitalTwin                    | ---            | ---      | ---               | ---                  | Human awareness |
| 4   | ToneDetector        | main_pc_code/agents/tone_detector.py         | 5625 | 6625        | EmotionEngine, SystemDigitalTwin                    | ---            | ---      | ---               | ---                  | Tone detection  |
| 5   | VoiceProfilingAgent | main_pc_code/agents/voice_profiling_agent.py | 5708 | 6708        | EmotionEngine, SystemDigitalTwin                    | ---            | ---      | ---               | ---                  | Voice profiling |
| 6   | EmpathyAgent        | main_pc_code/agents/EmpathyAgent.py          | 5703 | 6703        | EmotionEngine, StreamingTTSAgent, SystemDigitalTwin | ---            | ---      | ---               | ---                  | Empathy/emotion |



# PC2 Agent RTX 3060 





| #  | Agent Name                  | File Path                                                                                                       | Port | Health Port | Dependencies                                        | Design Pattern | Registry | Service Discovery | Error/Event Handling | Notes                        |
| -- | --------------------------- | --------------------------------------------------------------------------------------------------------------- | ---- | ----------- | --------------------------------------------------- | -------------- | -------- | ----------------- | -------------------- | ---------------------------- |
| 1  | MemoryOrchestratorService   | pc2\_code/agents/memory\_orchestrator\_service.py                                                               | 7140 | 8140        | ---                                                 | ---            | ---      | ---               | ---                  | Core memory orchestrator     |
| 2  | TieredResponder             | pc2\_code/agents/tiered\_responder.py                                                                           | 7100 | 8100        | ResourceManager                                     | ---            | ---      | ---               | ---                  | Tiered logic                 |
| 3  | AsyncProcessor              | pc2\_code/agents/async\_processor.py                                                                            | 7101 | 8101        | ResourceManager                                     | ---            | ---      | ---               | ---                  | Async task processor         |
| 4  | CacheManager                | pc2\_code/agents/cache\_manager.py                                                                              | 7102 | 8102        | MemoryOrchestratorService                           | ---            | ---      | ---               | ---                  | Cache features               |
| 5  | VisionProcessingAgent       | pc2\_code/agents/VisionProcessingAgent.py                                                                       | 7150 | 8150        | CacheManager                                        | ---            | ---      | ---               | ---                  | Vision pipeline              |
| 6  | DreamWorldAgent             | pc2\_code/agents/DreamWorldAgent.py                                                                             | 7104 | 8104        | MemoryOrchestratorService                           | ---            | ---      | ---               | ---                  | Dream/visualization tasks    |
| 7  | UnifiedMemoryReasoningAgent | pc2\_code/agents/unified\_memory\_reasoning\_agent.py                                                           | 7105 | 8105        | MemoryOrchestratorService                           | ---            | ---      | ---               | ---                  | Unified memory logic         |
| 8  | TutorAgent                  | pc2\_code/agents/tutor\_agent.py                                                                                | 7108 | 8108        | MemoryOrchestratorService                           | ---            | ---      | ---               | ---                  | Tutoring service             |
| 9  | TutoringAgent               | pc2\_code/agents/tutoring\_agent.py                                                                             | 7131 | 8131        | MemoryOrchestratorService                           | ---            | ---      | ---               | ---                  | Alternate tutor agent        |
| 10 | ContextManager              | pc2\_code/agents/context\_manager.py                                                                            | 7111 | 8111        | MemoryOrchestratorService                           | ---            | ---      | ---               | ---                  | Context control              |
| 11 | ExperienceTracker           | pc2\_code/agents/experience\_tracker.py                                                                         | 7112 | 8112        | MemoryOrchestratorService                           | ---            | ---      | ---               | ---                  | Tracks user/agent experience |
| 12 | ResourceManager             | pc2\_code/agents/resource\_manager.py                                                                           | 7113 | 8113        | ObservabilityHub                                    | ---            | ---      | ---               | ---                  | Resource allocation          |
| 13 | TaskScheduler               | pc2\_code/agents/task\_scheduler.py                                                                             | 7115 | 8115        | AsyncProcessor                                      | ---            | ---      | ---               | ---                  | Schedules agent tasks        |
| 14 | AuthenticationAgent         | pc2\_code/agents/ForPC2/AuthenticationAgent.py                                                                  | 7116 | 8116        | UnifiedUtilsAgent                                   | ---            | ---      | ---               | ---                  | Auth service for PC2         |
| 15 | UnifiedUtilsAgent           | pc2\_code/agents/ForPC2/unified\_utils\_agent.py                                                                | 7118 | 8118        | ObservabilityHub                                    | ---            | ---      | ---               | ---                  | Utilities for PC2 agents     |
| 16 | ProactiveContextMonitor     | pc2\_code/agents/ForPC2/proactive\_context\_monitor.py                                                          | 7119 | 8119        | ContextManager                                      | ---            | ---      | ---               | ---                  | Proactive context watcher    |
| 17 | AgentTrustScorer            | pc2\_code/agents/AgentTrustScorer.py                                                                            | 7122 | 8122        | ObservabilityHub                                    | ---            | ---      | ---               | ---                  | Agent trust scoring          |
| 18 | FileSystemAssistantAgent    | pc2\_code/agents/filesystem\_assistant\_agent.py                                                                | 7123 | 8123        | UnifiedUtilsAgent                                   | ---            | ---      | ---               | ---                  | Filesystem operations        |
| 19 | RemoteConnectorAgent        | pc2\_code/agents/remote\_connector\_agent.py                                                                    | 7124 | 8124        | AdvancedRouter                                      | ---            | ---      | ---               | ---                  | Remote system connector      |
| 20 | UnifiedWebAgent             | pc2\_code/agents/unified\_web\_agent.py                                                                         | 7126 | 8126        | FileSystemAssistantAgent, MemoryOrchestratorService | ---            | ---      | ---               | ---                  | Unified web interface        |
| 21 | DreamingModeAgent           | pc2\_code/agents/DreamingModeAgent.py                                                                           | 7127 | 8127        | DreamWorldAgent                                     | ---            | ---      | ---               | ---                  | Dreaming/visualization       |
| 22 | AdvancedRouter              | pc2\_code/agents/advanced\_router.py                                                                            | 7129 | 8129        | TaskScheduler                                       | ---            | ---      | ---               | ---                  | Advanced routing logic       |
| 23 | ObservabilityHub            | phase1\_implementation/consolidated\_agents/observability\_hub/backup\_observability\_hub/observability\_hub.py | 9000 | 9100        | ---                                                 | ---            | ---      | ---               | ---                  | Consolidated monitoring      |


## REAL ARCHITECTURAL PATTERNS (✅ VERIFIED)

### BASEAGENT INHERITANCE (✅ 90% ADOPTION)

```python
class YourAgent(BaseAgent):
    def __init__(self, port=None, **kwargs):
        super().__init__(name="YourAgent", port=port, **kwargs)
        # Your initialization here

    def handle_request(self, request_data):
        # Handle incoming requests
        pass
```

### ZMQ COMMUNICATION (✅ WORKING)

```python
# Standard pattern across agents:
from common.pools.zmq_pool import get_req_socket, get_rep_socket

# Usage:
socket = get_rep_socket(self.port)  # For servers
socket = get_req_socket(target_port)  # For clients
```

### CONFIGURATION LOADING (✅ STANDARD)

```python
# Most agents use:
from common.config_manager import load_unified_config
config = load_unified_config("path/to/startup_config.yaml")

# Or:
from common.config_manager import get_service_ip, get_service_url
ip = get_service_ip("service_name")
```

### PATH MANAGEMENT (✅ CONTAINERIZATION READY)

```python
from common.utils.path_manager import PathManager
project_root = PathManager.get_project_root()
logs_dir = PathManager.get_logs_dir()
```

### LOGGING PATTERN (✅ STANDARD)

```python
import logging
logger = logging.getLogger(__name__)
# or
logger = logging.getLogger("AgentName")
```

### REDIS USAGE (✅ BASIC IMPLEMENTATION)

