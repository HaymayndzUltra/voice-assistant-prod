# AGENTS ORDERED BY CONTAINER GROUPS

## Core Infrastructure Container
- **RequestCoordinator**: Unified central coordinator that handles the flow of information between all agents and routes tasks to appropriate services. Combines the functionality of the former CoordinatorAgent and TaskRouter. Fully compliant with Phase 0 standards, using Pydantic data models for type safety, BaseAgent helper methods for standardized communication, and dynamic service discovery.
- **SystemDigitalTwin**: Central monitoring system na nagta-track ng system metrics at serves as a central registry for other agents.
- **DynamicIdentityAgent**: Manages system identity and persona switching, connecting to multiple core services.
- **UnifiedSystemAgent**: Central command center for system orchestration, service discovery, maintenance, and monitoring.

## Data & Storage Services Container
- **MemoryOrchestrator**: Provides centralized memory storage and retrieval services across the system.
- **SessionMemoryAgent**: Manages conversation history and context for LLM prompts.
- **MemoryManager**: Coordinates memory operations across the system and provides short-term memory services.
- **MemoryClient**: Lightweight client interface to the Memory Orchestrator for memory storage and retrieval requests.
- **KnowledgeBase**: Manages the system's knowledge base using SQLite for storing, retrieving, and searching facts.
- **TTSCache**: Provides caching functionality for text-to-speech operations to avoid redundant processing.

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
- **LanguageAndTranslationCoordinator**: Coordinates language detection and translation services with multi-tier fallback.

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
- **FusedAudioPreprocessor**: Handles critical audio preprocessing functions including noise reduction and VAD.
- **WakeWordDetector**: Specializes in wake word detection to trigger system activation.
- **ChitChatAgent**: Handles casual conversation interactions and maintains conversation history.
- **FeedbackHandler**: Provides visual and voice confirmation feedback for command execution.
- **Responder**: Handles text-to-speech conversion and audio response generation with emotion-based modulation.
- **VisionCaptureAgent**: Serves as the first step in the vision pipeline for screen capture.

## High-Level Orchestration Container
- **GoalManager**: Central authority for decomposing high-level goals, managing task dependencies, and coordinating swarms of specialized agents. Features priority-based task scheduling, circuit breaker pattern for resilient service connections, standardized communication using BaseAgent helpers, and comprehensive error handling. Fully compliant with Phase 0 standards, replacing the former GoalOrchestratorAgent and MultiAgentSwarmManager with a more robust, unified implementation.
- **ModelOrchestrator**: The system's primary reasoning and model execution engine. Consolidates the planning, multi-step reasoning, model selection, and execution logic of the former EnhancedModelRouter and UnifiedPlanningAgent. Handles dynamic model selection (LLMs, vision, code, API), context management, and robust execution with circuit breaker resilience. All complex tasks from RequestCoordinator and GoalManager are routed here for planning and execution.
- **AdvancedCommandHandler**: Extends basic command handling with advanced features like command sequences.

## Utilities & Support Services Container
- **PredictiveHealthMonitor**: Advanced monitoring agent na gumagamit ng machine learning para i-predict ang potential failures.
- **ConsolidatedTranslator**: Combines multiple translation engines with fallback mechanisms and caching.
- **FixedStreamingTranslation**: Handles streaming translation with multiple fallback mechanisms.
- **Executor**: Handles user command execution with security controls and authentication.

## Security & Authentication Container
- **IntentionValidatorAgent**: Security-focused agent na nagva-validate ng user intentions at commands.

## Learning & Knowledge Container
- **LearningAdjusterAgent**: Manages and optimizes learning parameters for agents.
- **LearningManager**: Responsible for managing the learning process of the AI system.
- **ActiveLearningMonitor**: Monitors interactions between users and the system for learning opportunities. 