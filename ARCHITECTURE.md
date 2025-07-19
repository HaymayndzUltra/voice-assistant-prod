# Distributed AI System Architecture Documentation

## System Overview

This document describes the architecture of a distributed AI voice assistant system spanning two machines:
- **MainPC**: Primary machine hosting core AI services, speech processing, and cognitive capabilities
- **PC2**: Secondary machine handling specialized services, memory orchestration, and supplementary processing

The system implements a microservices architecture with ZMQ-based communication, centralized service registry, and comprehensive health monitoring.

## Network Architecture

### MainPC Network Configuration
- **Network**: `ai_system_network` (bridge driver)
- **Subnet**: `172.20.0.0/16`
- **Port Ranges**: Various ranges for different service types (5xxx, 6xxx, 7xxx, 8xxx)

### PC2 Network Configuration
- **Host**: `0.0.0.0` (all interfaces)
- **Agent Ports**: `7100-7199`
- **Health Check Ports**: `8100-8199`
- **Error Bus Port**: `7150`

### Inter-Machine Communication
- ObservabilityHub on PC2 syncs with MainPC endpoint: `http://192.168.100.16:9000`
- Cross-machine monitoring and health synchronization

## Global Configuration

### Resource Limits
- **MainPC**: CPU 80%, Memory 2GB, Max Threads 4
- **PC2**: CPU 80%, Memory 4GB, Max Threads 8

### Health Monitoring
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 300 seconds (5 minutes)

### Persistent Storage
MainPC volumes:
- `./logs` → `/app/logs`
- `./models` → `/app/models`
- `./data` → `/app/data`
- `./config` → `/app/config`

---

# MainPC Agent Architecture

## Core Services

### ServiceRegistry
- **Subsystem:** Core Services
- **Script Path:** `main_pc_code/agents/service_registry_agent.py`
- **Ports:**
  - Main: `7200`
  - Health Check: `8200`
- **Dependencies:** None
- **Required:** `true`
- **Config:**
  - backend: memory (options: memory, redis)
  - redis.url: redis://localhost:6379/0
  - redis.prefix: "service_registry:"
- **Purpose:** Central service discovery and registration hub for the entire system
- **Notes:** Foundation service - must start first

### SystemDigitalTwin
- **Subsystem:** Core Services
- **Script Path:** `main_pc_code/agents/system_digital_twin.py`
- **Ports:**
  - Main: `7220`
  - Health Check: `8220`
- **Dependencies:** ServiceRegistry
- **Required:** `true`
- **Config:**
  - db_path: data/unified_memory.db
  - redis.host: localhost
  - redis.port: 6379
  - redis.db: 0
  - zmq_request_timeout: 5000
- **Purpose:** Maintains real-time system state and agent coordination
- **Notes:** Critical for inter-agent communication and system state management

### RequestCoordinator
- **Subsystem:** Core Services
- **Script Path:** `main_pc_code/agents/request_coordinator.py`
- **Ports:**
  - Main: `26002`
  - Health Check: `27002`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Central request routing and workflow coordination
- **Notes:** Orchestrates complex multi-agent workflows

### UnifiedSystemAgent
- **Subsystem:** Core Services
- **Script Path:** `main_pc_code/agents/unified_system_agent.py`
- **Ports:**
  - Main: `7225`
  - Health Check: `8225`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Purpose:** High-level system integration and unified interface
- **Notes:** Provides system-wide coordination and unified API

### ObservabilityHub
- **Subsystem:** Core Services
- **Script Path:** `phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py`
- **Ports:**
  - Main: `9000`
  - Health Check: `9100`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Config:**
  - prometheus_enabled: true
  - parallel_health_checks: true
  - prediction_enabled: true
- **Purpose:** Centralized monitoring, metrics collection, and system observability
- **Notes:** Prometheus-compatible metrics endpoint

### ModelManagerSuite
- **Subsystem:** Core Services
- **Script Path:** `main_pc_code/model_manager_suite.py`
- **Ports:**
  - Main: `7211`
  - Health Check: `8211`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Config:**
  - models_dir: models
  - vram_budget_percentage: 80
  - idle_timeout: 300
- **Purpose:** AI model lifecycle management, loading, and VRAM optimization
- **Notes:** Manages model resources across the system

## Memory System

### MemoryClient
- **Subsystem:** Memory System
- **Script Path:** `main_pc_code/agents/memory_client.py`
- **Ports:**
  - Main: `5713`
  - Health Check: `6713`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Interface for memory operations and data persistence
- **Notes:** Primary memory access layer for all agents

### SessionMemoryAgent
- **Subsystem:** Memory System
- **Script Path:** `main_pc_code/agents/session_memory_agent.py`
- **Ports:**
  - Main: `5574`
  - Health Check: `6574`
- **Dependencies:** RequestCoordinator, SystemDigitalTwin, MemoryClient
- **Required:** `true`
- **Purpose:** Manages conversation state and session-specific memory
- **Notes:** Critical for conversation continuity

### KnowledgeBase
- **Subsystem:** Memory System
- **Script Path:** `main_pc_code/agents/knowledge_base.py`
- **Ports:**
  - Main: `5715`
  - Health Check: `6715`
- **Dependencies:** MemoryClient, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Long-term knowledge storage and retrieval system
- **Notes:** Persistent knowledge and facts database

## Utility Services

### CodeGenerator
- **Subsystem:** Utility Services
- **Script Path:** `main_pc_code/agents/code_generator_agent.py`
- **Ports:**
  - Main: `5650`
  - Health Check: `6650`
- **Dependencies:** SystemDigitalTwin, ModelManagerAgent
- **Required:** `true`
- **Purpose:** Generates code based on natural language requests
- **Notes:** Supports multiple programming languages

### SelfTrainingOrchestrator
- **Subsystem:** Utility Services
- **Script Path:** `main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py`
- **Ports:**
  - Main: `5660`
  - Health Check: `6660`
- **Dependencies:** SystemDigitalTwin, ModelManagerAgent
- **Required:** `true`
- **Purpose:** Coordinates self-improvement and model fine-tuning
- **Notes:** Enables autonomous learning capabilities

### PredictiveHealthMonitor
- **Subsystem:** Utility Services
- **Script Path:** `main_pc_code/agents/predictive_health_monitor.py`
- **Ports:**
  - Main: `5613`
  - Health Check: `6613`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Proactive system health monitoring and issue prediction
- **Notes:** AI-driven health analytics

### FixedStreamingTranslation
- **Subsystem:** Utility Services
- **Script Path:** `main_pc_code/agents/fixed_streaming_translation.py`
- **Ports:**
  - Main: `5584`
  - Health Check: `6584`
- **Dependencies:** ModelManagerAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Real-time language translation with streaming support
- **Notes:** Supports multiple language pairs

### Executor
- **Subsystem:** Utility Services
- **Script Path:** `main_pc_code/agents/executor.py`
- **Ports:**
  - Main: `5606`
  - Health Check: `6606`
- **Dependencies:** CodeGenerator, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Safely executes generated code and system commands
- **Notes:** Sandboxed execution environment

### TinyLlamaServiceEnhanced
- **Subsystem:** Utility Services
- **Script Path:** `main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py`
- **Ports:**
  - Main: `5615`
  - Health Check: `6615`
- **Dependencies:** ModelManagerAgent, SystemDigitalTwin
- **Required:** `false`
- **Purpose:** Lightweight language model service for quick responses
- **Notes:** Optional service for resource-constrained scenarios

### LocalFineTunerAgent
- **Subsystem:** Utility Services
- **Script Path:** `main_pc_code/FORMAINPC/LocalFineTunerAgent.py`
- **Ports:**
  - Main: `5642`
  - Health Check: `6642`
- **Dependencies:** SelfTrainingOrchestrator, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Performs local model fine-tuning on user data
- **Notes:** Privacy-preserving model customization

### NLLBAdapter
- **Subsystem:** Utility Services
- **Script Path:** `main_pc_code/FORMAINPC/NLLBAdapter.py`
- **Ports:**
  - Main: `5581`
  - Health Check: `6581`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Purpose:** No Language Left Behind translation model adapter
- **Notes:** Multi-language support with 200+ languages

## GPU Infrastructure

### VRAMOptimizerAgent
- **Subsystem:** GPU Infrastructure
- **Script Path:** `main_pc_code/agents/vram_optimizer_agent.py`
- **Ports:**
  - Main: `5572`
  - Health Check: `6572`
- **Dependencies:** ModelManagerSuite, RequestCoordinator, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Optimizes GPU memory usage and model loading strategies
- **Notes:** Critical for efficient GPU resource utilization

## Reasoning Services

### ChainOfThoughtAgent
- **Subsystem:** Reasoning Services
- **Script Path:** `main_pc_code/FORMAINPC/ChainOfThoughtAgent.py`
- **Ports:**
  - Main: `5612`
  - Health Check: `6612`
- **Dependencies:** ModelManagerAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Implements step-by-step reasoning for complex problems
- **Notes:** Enhances AI reasoning capabilities

### GoTToTAgent
- **Subsystem:** Reasoning Services
- **Script Path:** `main_pc_code/FORMAINPC/GOT_TOTAgent.py`
- **Ports:**
  - Main: `5646`
  - Health Check: `6646`
- **Dependencies:** ModelManagerAgent, SystemDigitalTwin, ChainOfThoughtAgent
- **Required:** `false`
- **Purpose:** Graph of Thoughts and Tree of Thoughts reasoning
- **Notes:** Advanced reasoning strategies for complex problem-solving

### CognitiveModelAgent
- **Subsystem:** Reasoning Services
- **Script Path:** `main_pc_code/FORMAINPC/CognitiveModelAgent.py`
- **Ports:**
  - Main: `5641`
  - Health Check: `6641`
- **Dependencies:** ChainOfThoughtAgent, SystemDigitalTwin
- **Required:** `false`
- **Purpose:** Cognitive modeling and human-like reasoning simulation
- **Notes:** Advanced AI reasoning patterns

## Vision Processing

### FaceRecognitionAgent
- **Subsystem:** Vision Processing
- **Script Path:** `main_pc_code/agents/face_recognition_agent.py`
- **Ports:**
  - Main: `5610`
  - Health Check: `6610`
- **Dependencies:** RequestCoordinator, ModelManagerAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Face detection, recognition, and identity management
- **Notes:** Supports multiple face recognition models

## Learning Knowledge

### LearningOrchestrationService
- **Subsystem:** Learning Knowledge
- **Script Path:** `main_pc_code/agents/learning_orchestration_service.py`
- **Ports:**
  - Main: `7212`
  - Health Check: `8212`
- **Dependencies:** ModelEvaluationFramework, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Coordinates learning processes across the system
- **Notes:** Central learning coordination hub

### LearningOpportunityDetector
- **Subsystem:** Learning Knowledge
- **Script Path:** `main_pc_code/agents/learning_opportunity_detector.py`
- **Ports:**
  - Main: `7202`
  - Health Check: `8202`
- **Dependencies:** LearningOrchestrationService, MemoryClient, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Identifies opportunities for system improvement and learning
- **Notes:** AI-driven continuous improvement

### LearningManager
- **Subsystem:** Learning Knowledge
- **Script Path:** `main_pc_code/agents/learning_manager.py`
- **Ports:**
  - Main: `5580`
  - Health Check: `6580`
- **Dependencies:** MemoryClient, RequestCoordinator, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Manages learning processes and knowledge acquisition
- **Notes:** Coordinates with other learning agents

### ActiveLearningMonitor
- **Subsystem:** Learning Knowledge
- **Script Path:** `main_pc_code/agents/active_learning_monitor.py`
- **Ports:**
  - Main: `5638`
  - Health Check: `6638`
- **Dependencies:** LearningManager, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Monitors active learning processes and effectiveness
- **Notes:** Real-time learning analytics

### LearningAdjusterAgent
- **Subsystem:** Learning Knowledge
- **Script Path:** `main_pc_code/FORMAINPC/LearningAdjusterAgent.py`
- **Ports:**
  - Main: `5643`
  - Health Check: `6643`
- **Dependencies:** SelfTrainingOrchestrator, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Adjusts learning parameters based on performance metrics
- **Notes:** Adaptive learning optimization

## Language Processing

### ModelOrchestrator
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/model_orchestrator.py`
- **Ports:**
  - Main: `7210`
  - Health Check: `8210`
- **Dependencies:** RequestCoordinator, ModelManagerAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Orchestrates multiple language models for complex tasks
- **Notes:** Model ensemble coordination

### GoalManager
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/goal_manager.py`
- **Ports:**
  - Main: `7205`
  - Health Check: `8205`
- **Dependencies:** RequestCoordinator, ModelOrchestrator, SystemDigitalTwin, MemoryClient
- **Required:** `true`
- **Purpose:** Manages long-term goals and task planning
- **Notes:** Strategic planning and goal tracking

### IntentionValidatorAgent
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/IntentionValidatorAgent.py`
- **Ports:**
  - Main: `5701`
  - Health Check: `6701`
- **Dependencies:** RequestCoordinator, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Validates user intentions and request semantics
- **Notes:** Intent classification and validation

### NLUAgent
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/nlu_agent.py`
- **Ports:**
  - Main: `5709`
  - Health Check: `6709`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Natural Language Understanding and intent extraction
- **Notes:** Core NLP processing agent

### AdvancedCommandHandler
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/advanced_command_handler.py`
- **Ports:**
  - Main: `5710`
  - Health Check: `6710`
- **Dependencies:** NLUAgent, CodeGenerator, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Processes complex multi-step commands
- **Notes:** Advanced command interpretation and execution

### ChitchatAgent
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/chitchat_agent.py`
- **Ports:**
  - Main: `5711`
  - Health Check: `6711`
- **Dependencies:** NLUAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Handles casual conversation and social interaction
- **Notes:** Conversational AI for social engagement

### FeedbackHandler
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/feedback_handler.py`
- **Ports:**
  - Main: `5636`
  - Health Check: `6636`
- **Dependencies:** NLUAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Processes user feedback for system improvement
- **Notes:** Feedback collection and analysis

### Responder
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/responder.py`
- **Ports:**
  - Main: `5637`
  - Health Check: `6637`
- **Dependencies:** EmotionEngine, FaceRecognitionAgent, NLUAgent, StreamingTTSAgent, SystemDigitalTwin, TTSService
- **Required:** `true`
- **Purpose:** Generates contextual responses with emotional awareness
- **Notes:** Multi-modal response generation

### TranslationService
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/translation_service.py`
- **Ports:**
  - Main: `5595`
  - Health Check: `6595`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Core translation service for multi-language support
- **Notes:** Integration with multiple translation models

### DynamicIdentityAgent
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/DynamicIdentityAgent.py`
- **Ports:**
  - Main: `5802`
  - Health Check: `6802`
- **Dependencies:** RequestCoordinator, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Manages dynamic personality and identity adaptation
- **Notes:** Personality-aware interactions

### EmotionSynthesisAgent
- **Subsystem:** Language Processing
- **Script Path:** `main_pc_code/agents/emotion_synthesis_agent.py`
- **Ports:**
  - Main: `5706`
  - Health Check: `6706`
- **Dependencies:** RequestCoordinator, ModelManagerAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Synthesizes emotional content in responses
- **Notes:** Emotional intelligence integration

## Speech Services

### STTService
- **Subsystem:** Speech Services
- **Script Path:** `main_pc_code/services/stt_service.py`
- **Ports:**
  - Main: `5800`
  - Health Check: `6800`
- **Dependencies:** ModelManagerAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Speech-to-Text conversion service
- **Notes:** Multiple STT model support

### TTSService
- **Subsystem:** Speech Services
- **Script Path:** `main_pc_code/services/tts_service.py`
- **Ports:**
  - Main: `5801`
  - Health Check: `6801`
- **Dependencies:** ModelManagerAgent, SystemDigitalTwin, StreamingInterruptHandler
- **Required:** `true`
- **Purpose:** Text-to-Speech synthesis service
- **Notes:** High-quality voice synthesis

## Audio Interface

### AudioCapture
- **Subsystem:** Audio Interface
- **Script Path:** `main_pc_code/agents/streaming_audio_capture.py`
- **Ports:**
  - Main: `6550`
  - Health Check: `7550`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Real-time audio capture and streaming
- **Notes:** Low-latency audio input

### FusedAudioPreprocessor
- **Subsystem:** Audio Interface
- **Script Path:** `main_pc_code/agents/fused_audio_preprocessor.py`
- **Ports:**
  - Main: `6551`
  - Health Check: `7551`
- **Dependencies:** AudioCapture, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Audio preprocessing and enhancement
- **Notes:** Noise reduction and audio quality improvement

### StreamingInterruptHandler
- **Subsystem:** Audio Interface
- **Script Path:** `main_pc_code/agents/streaming_interrupt_handler.py`
- **Ports:**
  - Main: `5576`
  - Health Check: `6576`
- **Dependencies:** StreamingSpeechRecognition, StreamingTTSAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Handles speech interruptions and conversation flow
- **Notes:** Real-time conversation management

### StreamingSpeechRecognition
- **Subsystem:** Audio Interface
- **Script Path:** `main_pc_code/agents/streaming_speech_recognition.py`
- **Ports:**
  - Main: `6553`
  - Health Check: `7553`
- **Dependencies:** FusedAudioPreprocessor, RequestCoordinator, STTService, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Real-time speech recognition with streaming
- **Notes:** Low-latency speech processing

### StreamingTTSAgent
- **Subsystem:** Audio Interface
- **Script Path:** `main_pc_code/agents/streaming_tts_agent.py`
- **Ports:**
  - Main: `5562`
  - Health Check: `6562`
- **Dependencies:** RequestCoordinator, TTSService, SystemDigitalTwin, UnifiedSystemAgent
- **Required:** `true`
- **Purpose:** Streaming text-to-speech with real-time output
- **Notes:** Continuous audio output

### WakeWordDetector
- **Subsystem:** Audio Interface
- **Script Path:** `main_pc_code/agents/wake_word_detector.py`
- **Ports:**
  - Main: `6552`
  - Health Check: `7552`
- **Dependencies:** AudioCapture, FusedAudioPreprocessor, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Detects wake words to activate the system
- **Notes:** Always-listening activation trigger

### StreamingLanguageAnalyzer
- **Subsystem:** Audio Interface
- **Script Path:** `main_pc_code/agents/streaming_language_analyzer.py`
- **Ports:**
  - Main: `5579`
  - Health Check: `6579`
- **Dependencies:** StreamingSpeechRecognition, SystemDigitalTwin, TranslationService
- **Required:** `true`
- **Purpose:** Real-time language detection and analysis
- **Notes:** Multi-language conversation support

### ProactiveAgent
- **Subsystem:** Audio Interface
- **Script Path:** `main_pc_code/agents/ProactiveAgent.py`
- **Ports:**
  - Main: `5624`
  - Health Check: `6624`
- **Dependencies:** RequestCoordinator, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Proactive conversation initiation and engagement
- **Notes:** Context-aware conversation starter

## Emotion System

### EmotionEngine
- **Subsystem:** Emotion System
- **Script Path:** `main_pc_code/agents/emotion_engine.py`
- **Ports:**
  - Main: `5590`
  - Health Check: `6590`
- **Dependencies:** SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Core emotion processing and state management
- **Notes:** Central emotional intelligence hub

### MoodTrackerAgent
- **Subsystem:** Emotion System
- **Script Path:** `main_pc_code/agents/mood_tracker_agent.py`
- **Ports:**
  - Main: `5704`
  - Health Check: `6704`
- **Dependencies:** EmotionEngine, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Tracks user mood and emotional patterns
- **Notes:** Long-term emotional state analysis

### HumanAwarenessAgent
- **Subsystem:** Emotion System
- **Script Path:** `main_pc_code/agents/human_awareness_agent.py`
- **Ports:**
  - Main: `5705`
  - Health Check: `6705`
- **Dependencies:** EmotionEngine, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Detects human presence and social context
- **Notes:** Social awareness and interaction optimization

### ToneDetector
- **Subsystem:** Emotion System
- **Script Path:** `main_pc_code/agents/tone_detector.py`
- **Ports:**
  - Main: `5625`
  - Health Check: `6625`
- **Dependencies:** EmotionEngine, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Analyzes emotional tone in speech and text
- **Notes:** Vocal emotion recognition

### VoiceProfilingAgent
- **Subsystem:** Emotion System
- **Script Path:** `main_pc_code/agents/voice_profiling_agent.py`
- **Ports:**
  - Main: `5708`
  - Health Check: `6708`
- **Dependencies:** EmotionEngine, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Creates voice profiles for user identification
- **Notes:** Voice biometrics and personalization

### EmpathyAgent
- **Subsystem:** Emotion System
- **Script Path:** `main_pc_code/agents/EmpathyAgent.py`
- **Ports:**
  - Main: `5703`
  - Health Check: `6703`
- **Dependencies:** EmotionEngine, StreamingTTSAgent, SystemDigitalTwin
- **Required:** `true`
- **Purpose:** Provides empathetic responses and emotional support
- **Notes:** Emotional intelligence and support system

---

# PC2 Agent Architecture

## Integration Layer Agents

### MemoryOrchestratorService
- **Subsystem:** Integration Layer
- **Script Path:** `pc2_code/agents/memory_orchestrator_service.py`
- **Ports:**
  - Main: `7140`
  - Health Check: `8140`
- **Dependencies:** None
- **Required:** `true`
- **Purpose:** Orchestrates memory operations across the distributed system
- **Notes:** Central memory coordination for PC2 services

### TieredResponder
- **Subsystem:** Integration Layer
- **Script Path:** `pc2_code/agents/tiered_responder.py`
- **Ports:**
  - Main: `7100`
  - Health Check: `8100`
- **Dependencies:** ResourceManager
- **Required:** `true`
- **Purpose:** Implements tiered response strategies based on request complexity
- **Notes:** Optimizes response quality vs. speed trade-offs

### AsyncProcessor
- **Subsystem:** Integration Layer
- **Script Path:** `pc2_code/agents/async_processor.py`
- **Ports:**
  - Main: `7101`
  - Health Check: `8101`
- **Dependencies:** ResourceManager
- **Required:** `true`
- **Purpose:** Handles asynchronous processing tasks and background operations
- **Notes:** Enables non-blocking operations

### CacheManager
- **Subsystem:** Integration Layer
- **Script Path:** `pc2_code/agents/cache_manager.py`
- **Ports:**
  - Main: `7102`
  - Health Check: `8102`
- **Dependencies:** MemoryOrchestratorService
- **Required:** `true`
- **Purpose:** Manages caching strategies and cache invalidation
- **Notes:** Performance optimization through intelligent caching

### VisionProcessingAgent
- **Subsystem:** Integration Layer
- **Script Path:** `pc2_code/agents/VisionProcessingAgent.py`
- **Ports:**
  - Main: `7150`
  - Health Check: `8150`
- **Dependencies:** CacheManager
- **Required:** `true`
- **Purpose:** Advanced vision processing and computer vision tasks
- **Notes:** Complements MainPC's FaceRecognitionAgent

## PC2-Specific Core Agents

### DreamWorldAgent
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/DreamWorldAgent.py`
- **Ports:**
  - Main: `7104`
  - Health Check: `8104`
- **Dependencies:** MemoryOrchestratorService
- **Required:** `true`
- **Purpose:** Manages dream-like simulation and creative processing
- **Notes:** Experimental AI consciousness simulation

### UnifiedMemoryReasoningAgent
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/unified_memory_reasoning_agent.py`
- **Ports:**
  - Main: `7105`
  - Health Check: `8105`
- **Dependencies:** MemoryOrchestratorService
- **Required:** `true`
- **Purpose:** Advanced reasoning with integrated memory access
- **Notes:** Combines memory and reasoning for complex problem-solving

### TutorAgent
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/tutor_agent.py`
- **Ports:**
  - Main: `7108`
  - Health Check: `8108`
- **Dependencies:** MemoryOrchestratorService
- **Required:** `true`
- **Purpose:** Provides tutoring and educational assistance
- **Notes:** Adaptive learning and teaching capabilities

### TutoringAgent
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/tutoring_agent.py`
- **Ports:**
  - Main: `7131`
  - Health Check: `8131`
- **Dependencies:** MemoryOrchestratorService
- **Required:** `true`
- **Purpose:** Extended tutoring capabilities and curriculum management
- **Notes:** Complements TutorAgent with advanced features

### ContextManager
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/context_manager.py`
- **Ports:**
  - Main: `7111`
  - Health Check: `8111`
- **Dependencies:** MemoryOrchestratorService
- **Required:** `true`
- **Purpose:** Manages conversation context across sessions
- **Notes:** Enhanced context awareness for PC2 services

### ExperienceTracker
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/experience_tracker.py`
- **Ports:**
  - Main: `7112`
  - Health Check: `8112`
- **Dependencies:** MemoryOrchestratorService
- **Required:** `true`
- **Purpose:** Tracks user experiences and interaction patterns
- **Notes:** Learning from user behavior and preferences

### ResourceManager
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/resource_manager.py`
- **Ports:**
  - Main: `7113`
  - Health Check: `8113`
- **Dependencies:** ObservabilityHub
- **Required:** `true`
- **Purpose:** Manages PC2 computational resources and allocation
- **Notes:** Optimizes resource usage across PC2 services

### TaskScheduler
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/task_scheduler.py`
- **Ports:**
  - Main: `7115`
  - Health Check: `8115`
- **Dependencies:** AsyncProcessor
- **Required:** `true`
- **Purpose:** Schedules and prioritizes tasks across PC2 agents
- **Notes:** Intelligent task management and execution

## ForPC2 Specialized Agents

### AuthenticationAgent
- **Subsystem:** Specialized Services
- **Script Path:** `pc2_code/agents/ForPC2/AuthenticationAgent.py`
- **Ports:**
  - Main: `7116`
  - Health Check: `8116`
- **Dependencies:** UnifiedUtilsAgent
- **Required:** `true`
- **Purpose:** Handles authentication and authorization for PC2 services
- **Notes:** Security layer for PC2 operations

### UnifiedUtilsAgent
- **Subsystem:** Specialized Services
- **Script Path:** `pc2_code/agents/ForPC2/unified_utils_agent.py`
- **Ports:**
  - Main: `7118`
  - Health Check: `8118`
- **Dependencies:** ObservabilityHub
- **Required:** `true`
- **Purpose:** Provides utility functions and common services for PC2
- **Notes:** Shared utilities and helper functions

### ProactiveContextMonitor
- **Subsystem:** Specialized Services
- **Script Path:** `pc2_code/agents/ForPC2/proactive_context_monitor.py`
- **Ports:**
  - Main: `7119`
  - Health Check: `8119`
- **Dependencies:** ContextManager
- **Required:** `true`
- **Purpose:** Proactively monitors and adjusts context based on user behavior
- **Notes:** Advanced context awareness and adaptation

## Additional PC2 Core Agents

### AgentTrustScorer
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/AgentTrustScorer.py`
- **Ports:**
  - Main: `7122`
  - Health Check: `8122`
- **Dependencies:** ObservabilityHub
- **Required:** `true`
- **Purpose:** Evaluates and scores agent trustworthiness and reliability
- **Notes:** Agent performance and reliability metrics

### FileSystemAssistantAgent
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/filesystem_assistant_agent.py`
- **Ports:**
  - Main: `7123`
  - Health Check: `8123`
- **Dependencies:** UnifiedUtilsAgent
- **Required:** `true`
- **Purpose:** Provides file system operations and management
- **Notes:** File operations and data management

### RemoteConnectorAgent
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/remote_connector_agent.py`
- **Ports:**
  - Main: `7124`
  - Health Check: `8124`
- **Dependencies:** AdvancedRouter
- **Required:** `true`
- **Purpose:** Manages remote connections and inter-machine communication
- **Notes:** Cross-machine connectivity and communication

### UnifiedWebAgent
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/unified_web_agent.py`
- **Ports:**
  - Main: `7126`
  - Health Check: `8126`
- **Dependencies:** FileSystemAssistantAgent, MemoryOrchestratorService
- **Required:** `true`
- **Purpose:** Handles web operations, scraping, and internet interactions
- **Notes:** Web automation and internet services

### DreamingModeAgent
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/DreamingModeAgent.py`
- **Ports:**
  - Main: `7127`
  - Health Check: `8127`
- **Dependencies:** DreamWorldAgent
- **Required:** `true`
- **Purpose:** Manages dream mode operations and creative processing
- **Notes:** Enhanced creativity and imagination simulation

### AdvancedRouter
- **Subsystem:** Core Agents
- **Script Path:** `pc2_code/agents/advanced_router.py`
- **Ports:**
  - Main: `7129`
  - Health Check: `8129`
- **Dependencies:** TaskScheduler
- **Required:** `true`
- **Purpose:** Advanced request routing and load balancing
- **Notes:** Intelligent routing for optimal performance

## Consolidated Monitoring

### ObservabilityHub (PC2)
- **Subsystem:** Monitoring
- **Script Path:** `phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py`
- **Ports:**
  - Main: `9000`
  - Health Check: `9100`
- **Dependencies:** None
- **Required:** `true`
- **Config:**
  - scope: "pc2_agents"
  - prometheus_port: 9000
  - cross_machine_sync: true
  - mainpc_hub_endpoint: "http://192.168.100.16:9000"
  - parallel_health_checks: true
  - prediction_enabled: true
- **Purpose:** Centralized monitoring and observability for PC2 agents
- **Notes:** Syncs with MainPC ObservabilityHub for system-wide monitoring

---

# System Integration and Communication

## Inter-Agent Communication
- **Protocol**: ZMQ (ZeroMQ) for high-performance messaging
- **Service Discovery**: ServiceRegistry provides centralized agent discovery
- **Health Monitoring**: Dual health check system (internal + ObservabilityHub)
- **Cross-Machine**: PC2 ObservabilityHub syncs with MainPC at `192.168.100.16:9000`

## Data Flow Architecture
1. **Audio Input**: AudioCapture → FusedAudioPreprocessor → StreamingSpeechRecognition
2. **Language Processing**: NLUAgent → RequestCoordinator → ModelOrchestrator
3. **Memory Operations**: MemoryClient ↔ MemoryOrchestratorService (PC2)
4. **Response Generation**: Responder → StreamingTTSAgent → Audio Output
5. **Cross-Machine**: MainPC ↔ PC2 via ObservabilityHub sync and direct agent communication

## Resource Management
- **MainPC**: Optimized for real-time audio processing and primary AI models
- **PC2**: Handles memory-intensive operations, background processing, and specialized services
- **GPU Coordination**: VRAMOptimizerAgent ensures efficient GPU utilization
- **Load Balancing**: AdvancedRouter and TieredResponder optimize request distribution

## Monitoring and Health
- **Centralized Monitoring**: Dual ObservabilityHub instances with cross-machine sync
- **Predictive Health**: PredictiveHealthMonitor uses AI to predict system issues
- **Performance Tracking**: AgentTrustScorer evaluates agent reliability
- **Resource Monitoring**: ResourceManager tracks computational resource usage

## Security and Trust
- **Authentication**: AuthenticationAgent handles PC2 security
- **Trust Scoring**: AgentTrustScorer evaluates agent reliability
- **Service Validation**: IntentionValidatorAgent ensures request authenticity

---

# Deployment and Scaling Considerations

## High Availability
- **Service Registry**: Supports Redis backend for HA deployments
- **Health Monitoring**: 30-second intervals with 3 retries and 5-minute startup grace period
- **Graceful Degradation**: Optional agents marked with `required: false`

## Performance Optimization
- **Parallel Processing**: AsyncProcessor and TaskScheduler enable concurrent operations
- **Caching Strategy**: CacheManager optimizes response times
- **VRAM Management**: VRAMOptimizerAgent prevents GPU memory issues
- **Streaming Operations**: Real-time audio and response streaming

## Scalability
- **Microservices Architecture**: Each agent is independently scalable
- **Resource Limits**: CPU and memory limits prevent resource exhaustion
- **Network Segmentation**: Dedicated port ranges for different service types
- **Cross-Machine Distribution**: Services distributed across multiple machines

This architecture provides a robust, scalable, and maintainable distributed AI system with comprehensive monitoring, intelligent resource management, and advanced AI capabilities across multiple domains including speech processing, natural language understanding, emotion recognition, and cognitive reasoning.