# AGENTS ORDERED BY CONTAINER GROUPS

## Core Infrastructure Container
- **RequestCoordinator**: Unified central coordinator that handles the flow of information between all agents and routes tasks to appropriate services. Combines the functionality of the former CoordinatorAgent and TaskRouter. Fully compliant with Phase 0 standards, using Pydantic data models for type safety, BaseAgent helper methods for standardized communication, and dynamic service discovery. This agent coordinates and dispatches requests on the Main PC. It now reports errors via the distributed Error Bus (ZMQ PUB/SUB, topic 'ERROR:') to the SystemHealthManager on PC2, enabling scalable, decoupled error reporting.
- **SystemDigitalTwin**: Central monitoring system na nagta-track ng system metrics at serves as a central registry for other agents.
- **DynamicIdentityAgent**: Manages system identity and persona switching, connecting to multiple core services.
- **UnifiedSystemAgent**: Central command center for system orchestration, service discovery, maintenance, and monitoring.

## Data & Storage Services Container
- **SessionMemoryAgent**: Manages conversation history and context for LLM prompts.
- **MemoryClient**: Sole interface for all memory operations on Main PC, forwarding requests to the central MemoryOrchestratorService on PC2. Replaces all legacy memory managers.
- **KnowledgeBase**: Manages the system's knowledge base using SQLite for storing, retrieving, and searching facts.
- **TTSCache**: Provides caching functionality for text-to-speech operations to avoid redundant processing.
- **MemoryOrchestratorService**: This service is the central memory hub for the distributed system, consolidating memory orchestration, robust SQLite persistence, and Redis-based distributed caching. This agent now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').

## AI Models & GPU Services Container
- **ModelManagerAgent**: Direktang namamahala ng AI models at GPU resources, nagmo-monitor ng VRAM usage.
- **VRAMOptimizerAgent**: Namamahala ng GPU memory optimization at nag-i-implement ng predictive model loading.
- **PredictiveLoader**: Predicts which models will be needed and preloads them to minimize latency.
- **GGUFModelManager**: Directly manages GGUF models using `llama-cpp-python` with explicit GPU resource management.
- **SelfTrainingOrchestrator**: Manages training cycles and resource allocation for agent training.
- **TinyLlamaServiceEnhanced**: Provides access to the TinyLlama model with explicit GPU management.
- **NLLBTranslationAdapter**: Provides translation services using the NLLB model with GPU resource management.
- **LocalFineTunerAgent**: Manages model fine-tuning and artifact management with direct GPU usage.
- **StreamingSpeechRecognition**: Performs speech-to-text conversion using Whisper models with heavy CPU/GPU usage.
- **FaceRecognitionAgent**: Provides comprehensive face analysis capabilities with GPU acceleration.

## Cognitive Frameworks Container
- **ChainOfThoughtAgent**: Specialized AI reasoning agent na nagde-decompose ng complex problems into steps.
- **GoTToTAgent**: Advanced reasoning agent na gumagamit ng Graph/Tree-of-Thought methodology.
- **CognitiveModelAgent**: Manages belief systems and cognitive reasoning using graph-based representations.
- **NLUAgent**: Handles natural language understanding through rule-based pattern matching.
- **CodeGeneratorAgent**: Generates code based on natural language descriptions using local LLMs.
- **MetaCognitionAgent**: Monitors and analyzes system performance, optimizes memory usage, and analyzes learning patterns.

## Language & Translation Services Container
- **StreamingLanguageAnalyzer**: Analyzes transcribed text to determine language and calculate language ratios.
- **TranslationService**: Unified, modular translation service that orchestrates all translation requests and fallback logic. Depends on NLLBAdapter, FixedStreamingTranslation, and SystemDigitalTwin. (ADDED Phase 4)

## Human Interaction Pipeline Container
- **UltimateTTSAgent**: Specialized agent para sa text-to-speech conversion na may 4-tier fallback system.
- **StreamingInterruptHandler**: Nagmo-monitor ng partial transcripts para sa interruption keywords.
- **ProactiveAgent**: Manages scheduled tasks and reminders, providing proactive user engagement.
- **EmotionEngine**: Manages emotional states and responses for the system.
- **MoodTrackerAgent**: Tracks and analyzes user mood over time based on emotional state updates.
- **HumanAwarenessAgent**: Monitors and analyzes human presence and behavior.
- **ToneDetector**: Detects and analyzes tone in speech and text.
- **VoiceProfilingAgent**: Handles voice enrollment, speaker recognition, and voice profile management.
- **EmpathyAgent**: Adapts voice settings based on emotional state to create empathetic responses.
- **EmotionSynthesisAgent**: Adds emotional nuance to text based on specified emotions.
- **TTSAgent**: Handles text-to-speech synthesis requests with interrupt handling capability.
- **StreamingAudioCapture**: Handles the critical first step in the audio processing pipeline for raw audio capture.
- **FusedAudioPreprocessor** (script_path: main_pc_code/agents/fused_audio_preprocessor.py): Handles critical audio preprocessing functions including noise reduction and VAD.
- **WakeWordDetector**: Specializes in wake word detection to trigger system activation.
- **ChitChatAgent**: Handles casual conversation interactions and maintains conversation history. (Now uses TranslationService for all translation requests.)
- **FeedbackHandler**: Provides visual and voice confirmation feedback for command execution.
- **Responder**: Handles text-to-speech conversion and audio response generation with emotion-based modulation.
- **VisionCaptureAgent**: Serves as the first step in the vision pipeline for screen capture.

## High-Level Orchestration Container
- **GoalManager**: Central authority for decomposing high-level goals, managing task dependencies, and coordinating swarms of specialized agents. Features priority-based task scheduling, circuit breaker pattern for resilient service connections, standardized communication using BaseAgent helpers, and comprehensive error handling. Fully compliant with Phase 0 standards, replacing the former GoalOrchestratorAgent and MultiAgentSwarmManager with a more robust, unified implementation.
- **ModelOrchestrator**: The system's primary reasoning and model execution engine. Consolidates the planning, multi-step reasoning, model selection, and execution logic of the former EnhancedModelRouter and UnifiedPlanningAgent. Handles dynamic model selection (LLMs, vision, code, API), context management, and robust execution with circuit breaker resilience. All complex tasks from RequestCoordinator and GoalManager are routed here for planning and execution.
- **AdvancedCommandHandler**: Extends basic command handling with advanced features like command sequences.

## Utilities & Support Services Container
- **PredictiveHealthMonitor** (script_path: main_pc_code/agents/predictive_health_monitor.py): Advanced monitoring agent na gumagamit ng machine learning para i-predict ang potential failures.
- **FixedStreamingTranslation**: Handles streaming translation with multiple fallback mechanisms.
- **Executor**: Handles user command execution with security controls and authentication.

## Security & Authentication Container
- **IntentionValidatorAgent**: Security-focused agent na nagva-validate ng user intentions at commands.

## Learning & Knowledge Container
- **LearningAdjusterAgent**: Manages and optimizes learning parameters for agents.
- **LearningManager**: Responsible for managing the learning process of the AI system.
- **ActiveLearningMonitor**: Monitors interactions between users and the system for learning opportunities.

# Main PC Agents Documentation

## Core System Agents

### RequestCoordinator
- **Purpose**: Central request handling and routing for all agents
- **Port**: 26002
- **Key Functions**:
  - Routes requests to appropriate agents
  - Manages request lifecycle and timeouts
  - Implements circuit breaker pattern for resilience
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### ModelOrchestrator
- **Purpose**: Orchestrates model selection and routing
- **Port**: 7010
- **Key Functions**:
  - Breaks down high-level goals into executable tasks
  - Selects appropriate models for each task
  - Manages execution flow and dependencies
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### SystemDigitalTwin
- **Purpose**: Maintains system-wide state and service discovery
- **Port**: 7120
- **Key Functions**:
  - Provides service discovery for all agents
  - Maintains system configuration and state
  - Handles agent registration and health monitoring
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### PredictiveHealthMonitor
- **Purpose**: Monitors and predicts agent health
- **Port**: 5613
- **Key Functions**:
  - Monitors agent health and performance
  - Predicts potential failures using machine learning
  - Implements tiered recovery strategies
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

## Error Management

The system now uses an event-driven Error Bus architecture for error management:

1. All agents report errors via the central Error Bus (ZMQ PUB/SUB, port 7150)
2. The SystemHealthManager agent (on PC2) subscribes to error events and handles them
3. Errors are published with the topic "ERROR:" and include:
   - Error type
   - Error message
   - Severity
   - Context (optional)

This architecture provides:
- Decoupled error reporting and processing
- Improved scalability and resilience
- Centralized error management and pattern detection
- Simplified agent code

## Memory System

### MemoryClient
- **Purpose**: Client for the central MemoryOrchestratorService on PC2
- **Port**: 5713
- **Key Functions**:
  - Provides memory storage and retrieval operations
  - Caches frequently accessed memories
  - Implements memory importance scoring
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### SessionMemoryAgent
- **Purpose**: Manages short-term session memory
- **Port**: 5574
- **Key Functions**:
  - Stores conversation context and session state
  - Provides recency-based memory retrieval
  - Implements memory summarization
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### LearningManager
- **Purpose**: Manages learning and adaptation
- **Port**: 5580
- **Key Functions**:
  - Identifies learning opportunities
  - Coordinates model fine-tuning
  - Tracks learning progress
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

## Speech Processing

### StreamingSpeechRecognition
- **Purpose**: Converts speech to text in real-time
- **Port**: 6580
- **Key Functions**:
  - Processes audio streams from AudioCapture
  - Provides real-time transcription
  - Supports multiple languages
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### StreamingTTSAgent
- **Purpose**: Converts text to speech in real-time
- **Port**: 5562
- **Key Functions**:
  - Generates high-quality speech from text
  - Supports multiple voices and languages
  - Implements streaming for low latency
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### StreamingInterruptHandler
- **Purpose**: Handles interruptions during speech output
- **Port**: 5576
- **Key Functions**:
  - Monitors for interruption keywords
  - Sends stop signals to TTS and other agents
  - Manages graceful interruption of ongoing speech
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

## Model Management

### ModelManagerAgent
- **Purpose**: Manages AI models and their lifecycle
- **Port**: 5570
- **Key Functions**:
  - Loads and unloads models based on demand
  - Manages model versions and updates
  - Provides unified interface for model inference
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### VRAMOptimizerAgent
- **Purpose**: Optimizes GPU memory usage
- **Port**: 5572
- **Key Functions**:
  - Monitors VRAM usage across all models
  - Implements model offloading strategies
  - Prevents VRAM fragmentation
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### GGUFModelManager
- **Purpose**: Manages GGUF format models
- **Port**: 5575
- **Key Functions**:
  - Loads and manages GGUF models
  - Provides inference API for GGUF models
  - Implements model caching and optimization
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')** 