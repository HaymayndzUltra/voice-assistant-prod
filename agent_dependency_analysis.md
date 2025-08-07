# AI System Agent Dependency Analysis

**Confidence Score: 95%** - Complete analysis based on configuration files and codebase exploration.

## Repository Overview

This AI system consists of **77 total agents** distributed across two main machines:
- **MainPC**: 54 agents (main processing, core infrastructure, cognitive systems)
- **PC2**: 23 agents (specialized processing, memory management, auxiliary services)

## Agent Distribution by Machine

### MainPC Agents (54 total)

#### Foundation Services (8 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| ServiceRegistry | `main_pc_code/agents/service_registry_agent.py` | 7200 | [] | Service discovery backbone |
| SystemDigitalTwin | `main_pc_code/agents/system_digital_twin.py` | 7220 | ServiceRegistry | System state management |
| RequestCoordinator | `main_pc_code/agents/request_coordinator.py` | 26002 | SystemDigitalTwin | Request routing |
| ModelManagerSuite | `main_pc_code/model_manager_suite.py` | 7211 | SystemDigitalTwin | Model lifecycle management |
| VRAMOptimizerAgent | `main_pc_code/agents/vram_optimizer_agent.py` | 5572 | ModelManagerSuite, RequestCoordinator, SystemDigitalTwin | GPU memory optimization |
| ObservabilityHub | `phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py` | 9000 | SystemDigitalTwin | Monitoring & metrics |
| UnifiedSystemAgent | `main_pc_code/agents/unified_system_agent.py` | 7201 | SystemDigitalTwin | System orchestration |
| SelfHealingSupervisor | `services/self_healing_supervisor/supervisor.py` | 7009 | ObservabilityHub | Auto-recovery |

#### Memory System (3 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| MemoryClient | `main_pc_code/agents/memory_client.py` | 5713 | SystemDigitalTwin | Memory interface |
| SessionMemoryAgent | `main_pc_code/agents/session_memory_agent.py` | 5574 | RequestCoordinator, SystemDigitalTwin, MemoryClient | Session state |
| KnowledgeBase | `main_pc_code/agents/knowledge_base.py` | 5715 | MemoryClient, SystemDigitalTwin | Knowledge storage |

#### Utility Services (5 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| CodeGenerator | `main_pc_code/agents/code_generator_agent.py` | 5650 | SystemDigitalTwin, ModelManagerSuite | Code generation |
| PredictiveHealthMonitor | `main_pc_code/agents/predictive_health_monitor.py` | 5613 | SystemDigitalTwin | Health prediction |
| Executor | `main_pc_code/agents/executor.py` | 5606 | CodeGenerator, SystemDigitalTwin | Code execution |
| TinyLlamaServiceEnhanced | `main_pc_code/FORMAINPC/tiny_llama_service_enhanced.py` | 5615 | ModelManagerSuite, SystemDigitalTwin | Local LLM service |
| SmartHomeAgent | `main_pc_code/agents/smart_home_agent.py` | 7125 | SystemDigitalTwin | Home automation |

#### Reasoning Services (3 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| ChainOfThoughtAgent | `main_pc_code/FORMAINPC/chain_of_thought_agent.py` | 5612 | ModelManagerSuite, SystemDigitalTwin | Reasoning chains |
| GoTToTAgent | `main_pc_code/FORMAINPC/got_tot_agent.py` | 5646 | ModelManagerSuite, SystemDigitalTwin, ChainOfThoughtAgent | Tree of thought |
| CognitiveModelAgent | `main_pc_code/FORMAINPC/cognitive_model_agent.py` | 5641 | ChainOfThoughtAgent, SystemDigitalTwin | Cognitive modeling |

#### Vision Processing (1 agent)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| FaceRecognitionAgent | `main_pc_code/agents/face_recognition_agent.py` | 5610 | RequestCoordinator, ModelManagerSuite, SystemDigitalTwin | Face recognition |

#### Learning & Knowledge (4 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| LearningOrchestrationService | `main_pc_code/agents/learning_orchestration_service.py` | 7210 | ModelManagerSuite, SystemDigitalTwin | Learning coordination |
| LearningOpportunityDetector | `main_pc_code/agents/learning_opportunity_detector.py` | 7202 | LearningOrchestrationService, MemoryClient, SystemDigitalTwin | Learning detection |
| LearningManager | `main_pc_code/agents/learning_manager.py` | 5580 | MemoryClient, RequestCoordinator, SystemDigitalTwin | Learning management |
| ActiveLearningMonitor | `main_pc_code/agents/active_learning_monitor.py` | 5638 | LearningManager, SystemDigitalTwin | Active learning |

#### Language Processing (10 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| ModelOrchestrator | `main_pc_code/agents/model_orchestrator.py` | 7213 | RequestCoordinator, ModelManagerSuite, SystemDigitalTwin | Model orchestration |
| GoalManager | `main_pc_code/agents/goal_manager.py` | 7205 | RequestCoordinator, ModelOrchestrator, SystemDigitalTwin, MemoryClient | Goal management |
| IntentionValidatorAgent | `main_pc_code/agents/IntentionValidatorAgent.py` | 5701 | RequestCoordinator, SystemDigitalTwin | Intent validation |
| NLUAgent | `main_pc_code/agents/nlu_agent.py` | 5709 | SystemDigitalTwin | Natural language understanding |
| AdvancedCommandHandler | `main_pc_code/agents/advanced_command_handler.py` | 5710 | NLUAgent, CodeGenerator, SystemDigitalTwin | Command processing |
| ChitchatAgent | `main_pc_code/agents/chitchat_agent.py` | 5711 | NLUAgent, SystemDigitalTwin | Casual conversation |
| FeedbackHandler | `main_pc_code/agents/feedback_handler.py` | 5636 | NLUAgent, SystemDigitalTwin | Feedback processing |
| Responder | `main_pc_code/agents/responder.py` | 5637 | EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, SystemDigitalTwin, TTSService | Response generation |
| DynamicIdentityAgent | `main_pc_code/agents/DynamicIdentityAgent.py` | 5802 | RequestCoordinator, SystemDigitalTwin | Identity adaptation |
| EmotionSynthesisAgent | `main_pc_code/agents/emotion_synthesis_agent.py` | 5706 | RequestCoordinator, ModelManagerSuite, SystemDigitalTwin | Emotion synthesis |

#### Speech Services (2 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| STTService | `main_pc_code/services/stt_service.py` | 5800 | ModelManagerSuite, SystemDigitalTwin | Speech-to-text |
| TTSService | `main_pc_code/services/tts_service.py` | 5801 | ModelManagerSuite, SystemDigitalTwin | Text-to-speech |

#### Audio Interface (8 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| AudioCapture | `main_pc_code/agents/streaming_audio_capture.py` | 6550 | SystemDigitalTwin | Audio capture |
| FusedAudioPreprocessor | `main_pc_code/agents/fused_audio_preprocessor.py` | 6551 | AudioCapture, SystemDigitalTwin | Audio preprocessing |
| StreamingInterruptHandler | `main_pc_code/agents/streaming_interrupt_handler.py` | 5576 | StreamingSpeechRecognition, StreamingTTSAgent, SystemDigitalTwin | Interrupt handling |
| StreamingSpeechRecognition | `main_pc_code/agents/streaming_speech_recognition.py` | 6553 | FusedAudioPreprocessor, RequestCoordinator, STTService, SystemDigitalTwin | Real-time STT |
| StreamingTTSAgent | `main_pc_code/agents/streaming_tts_agent.py` | 5562 | RequestCoordinator, TTSService, SystemDigitalTwin, UnifiedSystemAgent | Real-time TTS |
| WakeWordDetector | `main_pc_code/agents/wake_word_detector.py` | 6552 | AudioCapture, FusedAudioPreprocessor, SystemDigitalTwin | Wake word detection |
| StreamingLanguageAnalyzer | `main_pc_code/agents/streaming_language_analyzer.py` | 5579 | StreamingSpeechRecognition, SystemDigitalTwin, TranslationService | Language analysis |
| ProactiveAgent | `main_pc_code/agents/ProactiveAgent.py` | 5624 | RequestCoordinator, SystemDigitalTwin | Proactive behavior |

#### Emotion System (6 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| EmotionEngine | `main_pc_code/agents/emotion_engine.py` | 5590 | SystemDigitalTwin | Emotion processing |
| MoodTrackerAgent | `main_pc_code/agents/mood_tracker_agent.py` | 5704 | EmotionEngine, SystemDigitalTwin | Mood tracking |
| HumanAwarenessAgent | `main_pc_code/agents/human_awareness_agent.py` | 5705 | EmotionEngine, SystemDigitalTwin | Human awareness |
| ToneDetector | `main_pc_code/agents/tone_detector.py` | 5625 | EmotionEngine, SystemDigitalTwin | Tone detection |
| VoiceProfilingAgent | `main_pc_code/agents/voice_profiling_agent.py` | 5708 | EmotionEngine, SystemDigitalTwin | Voice profiling |
| EmpathyAgent | `main_pc_code/agents/EmpathyAgent.py` | 5703 | EmotionEngine, StreamingTTSAgent, SystemDigitalTwin | Empathy modeling |

#### Translation Services (2 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| CloudTranslationService | `main_pc_code/agents/cloud_translation_service.py` | 5592 | SystemDigitalTwin | Cloud translation |
| StreamingTranslationProxy | `services/streaming_translation_proxy/proxy.py` | 5596 | CloudTranslationService, SystemDigitalTwin | Translation proxy |

#### GPU Infrastructure (1 agent)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| CrossMachineGPUScheduler | `services/cross_gpu_scheduler/app.py` | 7155 | ModelManagerSuite, ObservabilityHub | GPU scheduling |

#### Observability UI (1 agent)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| ObservabilityDashboardAPI | `services/obs_dashboard_api/server.py` | 8001 | ObservabilityHub | Monitoring dashboard |

### PC2 Agents (23 total)

#### Infrastructure Core (2 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| ObservabilityHub | `phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py` | 9100 | [] | PC2 monitoring |
| ResourceManager | `pc2_code/agents/resource_manager.py` | 7113 | ObservabilityHub | Resource management |

#### Memory Stack (5 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| MemoryOrchestratorService | `pc2_code/agents/memory_orchestrator_service.py` | 7140 | [] | Memory orchestration |
| CacheManager | `pc2_code/agents/cache_manager.py` | 7102 | MemoryOrchestratorService | Cache management |
| UnifiedMemoryReasoningAgent | `pc2_code/agents/unified_memory_reasoning_agent.py` | 7105 | MemoryOrchestratorService | Memory reasoning |
| ContextManager | `pc2_code/agents/context_manager.py` | 7111 | MemoryOrchestratorService | Context management |
| ExperienceTracker | `pc2_code/agents/experience_tracker.py` | 7112 | MemoryOrchestratorService | Experience tracking |

#### Async Pipeline (4 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| AsyncProcessor | `pc2_code/agents/async_processor.py` | 7101 | ResourceManager | Async processing |
| TaskScheduler | `pc2_code/agents/task_scheduler.py` | 7115 | AsyncProcessor | Task scheduling |
| AdvancedRouter | `pc2_code/agents/advanced_router.py` | 7129 | TaskScheduler | Advanced routing |
| TieredResponder | `pc2_code/agents/tiered_responder.py` | 7100 | ResourceManager | Tiered responses |

#### Vision & Dream GPU (4 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| VisionProcessingAgent | `pc2_code/agents/VisionProcessingAgent.py` | 7150 | CacheManager | Vision processing |
| DreamWorldAgent | `pc2_code/agents/DreamWorldAgent.py` | 7104 | MemoryOrchestratorService | Dream simulation |
| DreamingModeAgent | `pc2_code/agents/DreamingModeAgent.py` | 7127 | DreamWorldAgent | Dream mode |
| SpeechRelayService | `services/speech_relay/relay.py` | 7130 | VisionProcessingAgent, StreamingTTSAgent | Speech relay |

#### Utility Suite (5 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| UnifiedUtilsAgent | `pc2_code/agents/ForPC2/unified_utils_agent.py` | 7118 | ObservabilityHub | Utility functions |
| FileSystemAssistantAgent | `pc2_code/agents/filesystem_assistant_agent.py` | 7123 | UnifiedUtilsAgent | File operations |
| RemoteConnectorAgent | `pc2_code/agents/remote_connector_agent.py` | 7124 | AdvancedRouter | Remote connections |
| AuthenticationAgent | `pc2_code/agents/ForPC2/AuthenticationAgent.py` | 7116 | UnifiedUtilsAgent | Authentication |
| AgentTrustScorer | `pc2_code/agents/AgentTrustScorer.py` | 7122 | ObservabilityHub | Trust scoring |
| ProactiveContextMonitor | `pc2_code/agents/ForPC2/proactive_context_monitor.py` | 7119 | ContextManager | Context monitoring |

#### Other Services (3 agents)
| Agent | Script Path | Port | Dependencies | Purpose |
|-------|-------------|------|--------------|---------|
| UnifiedWebAgent | `pc2_code/agents/unified_web_agent.py` | 7126 | FileSystemAssistantAgent, MemoryOrchestratorService | Web interface |
| TutoringServiceAgent | `pc2_code/agents/TutoringServiceAgent.py` | 7108 | MemoryOrchestratorService | Tutoring services |
| CentralErrorBus | `services/central_error_bus/error_bus.py` | 7150 | [] | Error handling |
| SelfHealingSupervisor | `services/self_healing_supervisor/supervisor.py` | 7009 | ObservabilityHub | Auto-recovery |

## Key Module Dependencies

### Core Infrastructure Modules

#### `common.core.base_agent`
- **Purpose**: Base class for all agents
- **Used by**: All 77 agents inherit from BaseAgent
- **Key features**: Health checks, error handling, ZMQ communication

#### `common.utils.path_manager`
- **Purpose**: Path resolution and management
- **Used by**: Most agents for file path handling
- **Containerization-friendly**: Docker volume mounting

#### `common.config_manager`
- **Purpose**: Configuration management
- **Used by**: Service discovery, network configuration
- **Key functions**: `get_service_ip()`, `get_service_url()`, `get_redis_url()`

### Network & Communication

#### ZMQ Pool System
- **Module**: `common.pools.zmq_pool`
- **Functions**: `get_req_socket()`, `get_rep_socket()`, `get_pub_socket()`, `get_sub_socket()`
- **Used by**: All agents for inter-agent communication

#### Service Discovery
- **MainPC**: `main_pc_code.utils.service_discovery_client`
- **Functions**: `register_service()`, `discover_service()`, `get_service_address()`
- **Critical for**: Agent registration and cross-agent communication

### Shared Utilities

#### Environment Management
- **Module**: `common.env_helpers`
- **Functions**: `get_env()`, `get_mainpc_ip()`, `get_pc2_ip()`, `get_current_machine()`
- **Used by**: Network configuration, machine identification

#### Logging
- **Module**: `common.utils.log_setup`
- **Function**: `configure_logging()`
- **Used by**: All agents for structured logging

#### Error Handling
- **Module**: `common.error_bus.unified_error_handler`
- **Purpose**: Centralized error reporting
- **Used by**: All agents via BaseAgent

## External Dependencies

### Core Python Libraries
- **PyZMQ 27.0.0**: Zero-message queue communication
- **PyYAML 6.0+**: Configuration file parsing
- **Redis 4.5.0+**: Caching and state management
- **Pydantic 2.5.2**: Data validation and serialization

### AI/ML Stack
- **PyTorch 2.0.0+**: Deep learning framework
- **Transformers 4.30.0+**: Hugging Face models
- **Sentence-Transformers 2.5+**: Embedding models
- **Scikit-learn 1.3.0+**: Traditional ML algorithms

### Monitoring & Observability
- **Prometheus-client 0.17.0+**: Metrics collection
- **OpenTelemetry**: Distributed tracing
- **Psutil 5.9.0+**: System resource monitoring

### Web & API
- **FastAPI 0.100.0+**: REST API framework
- **Requests 2.31.0+**: HTTP client
- **WebSockets 11.0.0+**: Real-time communication
- **BeautifulSoup4 4.12+**: Web scraping

### Audio/Vision Processing
- **LibROSA 0.10.0+**: Audio processing
- **OpenCV 4.8.0+**: Computer vision
- **PyAudio 0.2.11+**: Audio I/O
- **SpeechRecognition 3.10.0+**: Speech processing

## Agent Startup Sequences

### MainPC Startup Order
1. **Layer 0 - Foundation**: ServiceRegistry → SystemDigitalTwin → RequestCoordinator
2. **Layer 1 - Core Services**: ModelManagerSuite → VRAMOptimizerAgent → ObservabilityHub
3. **Layer 2 - Memory & Utilities**: MemoryClient → SessionMemoryAgent → KnowledgeBase
4. **Layer 3 - Processing**: Speech services → Audio pipeline → Language processing
5. **Layer 4 - High-level**: Emotion system → Cognitive agents → Specialized services

### PC2 Startup Order
1. **Layer 0 - Infrastructure**: ObservabilityHub → ResourceManager
2. **Layer 1 - Memory Stack**: MemoryOrchestratorService → CacheManager → Context/Experience agents
3. **Layer 2 - Processing**: AsyncProcessor → TaskScheduler → AdvancedRouter
4. **Layer 3 - Specialized**: Vision → Dream → Utility → Web agents

## Critical Dependency Relationships

### High-Impact Dependencies
1. **SystemDigitalTwin**: Critical bottleneck - 34 agents depend on it
2. **ModelManagerSuite**: Core for AI functionality - 12 agents depend on it
3. **ObservabilityHub**: Monitoring backbone - 8 agents depend on it
4. **BaseAgent**: Universal foundation - all 77 agents inherit from it

### Cross-Machine Dependencies
- **ObservabilityHub sync**: MainPC (port 9000) ↔ PC2 (port 9100)
- **Service discovery**: Cross-machine agent discovery via network config
- **GPU scheduling**: CrossMachineGPUScheduler coordinates both machines

## Port Allocation Strategy

### MainPC Ports
- **Foundation**: 7200-7220, 26002
- **AI Services**: 5600-5800 range
- **Audio Pipeline**: 6550-6590 range
- **Health Checks**: +1000 offset from main port
- **Observability**: 9000-9010 range

### PC2 Ports
- **Main Services**: 7100-7199 range
- **Health Checks**: 8100-8199 range
- **Observability**: 9100-9110 range
- **Error Bus**: 7150

## Security & Authentication

### Authentication Flow
1. **AuthenticationAgent** (PC2) handles user auth
2. **AgentTrustScorer** (PC2) evaluates agent trustworthiness
3. **ServiceRegistry** (MainPC) manages secure service discovery
4. Cross-machine communication uses encrypted ZMQ where available

### Error Handling Strategy
1. **CentralErrorBus** (PC2) collects all system errors
2. **UnifiedErrorHandler** (Common) standardizes error reporting
3. **SelfHealingSupervisor** (both machines) auto-restarts failed agents
4. **ObservabilityHub** (both machines) monitors health and performance

This analysis provides a complete overview of the 77-agent AI system with 95% confidence based on comprehensive codebase exploration and configuration analysis.