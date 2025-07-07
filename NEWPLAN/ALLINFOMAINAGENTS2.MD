AGENT: ModelManagerAgent
GROUP: AI Models & GPU Services
REASONING: Ang agent na ito ay direktang namamahala ng AI models at GPU resources. Malinaw ito sa code na gumagamit ng `torch.cuda`, nagmo-monitor ng VRAM usage, at may extensive VRAM management. Ito ay Tier 1 agent dahil sa mataas na resource consumption at critical role sa model loading/unloading.
RESOURCES: Heavy GPU/VRAM usage, actively monitors GPU memory, implements VRAM optimization, at namamahala ng multiple model types (GGUF, Ollama, custom API, ZMQ service).
DEPENDENCIES: VRAMOptimizerAgent, SystemDigitalTwin, TaskRouter.
FILE: main_pc_code/agents/model_manager_agent.py
PORT: 5570
HEALTH_CHECK_PORT: 6570

AGENT: CoordinatorAgent
GROUP: Core Infrastructure
REASONING: Central coordinator na namamahala sa flow ng information sa pagitan ng lahat ng agents. Ito ay nagha-handle ng system-wide communication, nagme-maintain ng service connections, at nagbibigay ng proactive assistance. Ito ay Tier 2 system-level agent.
RESOURCES: ZMQ sockets para sa communication, moderate memory usage, pero hindi gumagamit ng GPU resources.
DEPENDENCIES: Multiple service connections, memory system, proactive agent.
FILE: main_pc_code/agents/request_coordinator.py
PORT: 26002
HEALTH_CHECK_PORT: 27002

AGENT: ChainOfThoughtAgent
GROUP: Cognitive Frameworks
REASONING: Specialized AI reasoning agent na nagde-decompose ng complex problems into steps at gumagamit ng multi-step reasoning para sa code generation. Ito ay Tier 3 cognitive agent.
RESOURCES: Gumagamit ng LLM models via Remote Connector, moderate resource usage.
DEPENDENCIES: Remote Connector Agent, LLM models (phi3).
FILE: main_pc_code/FORMAINPC/ChainOfThoughtAgent.py
PORT: 5612
HEALTH_CHECK_PORT: 6612

AGENT: GoTToTAgent
GROUP: Cognitive Frameworks
REASONING: Advanced reasoning agent na gumagamit ng Graph/Tree-of-Thought methodology para sa complex problem solving. Ito ay Tier 3 cognitive agent na may specialized reasoning capabilities.
RESOURCES: Gumagamit ng HuggingFace models, may GPU usage via torch.
DEPENDENCIES: Transformer models (phi-2), may direct model loading (hindi umaasa sa ModelManagerAgent).
FILE: main_pc_code/FORMAINPC/GOT_TOTAgent.py
PORT: 5646
HEALTH_CHECK_PORT: 6646

AGENT: SystemDigitalTwin
GROUP: Core Infrastructure
REASONING: Central monitoring system na nagta-track ng system metrics, nagbibigay ng simulation capabilities, at serves as a central registry for other agents. Ito ay Tier 2 system-level agent.
RESOURCES: Moderate resource usage, primarily focused on system monitoring at metrics collection.
DEPENDENCIES: Prometheus for metrics, multiple agent connections for status reporting.
FILE: main_pc_code/agents/system_digital_twin.py
PORT: 7120
HEALTH_CHECK_PORT: 8120

AGENT: PredictiveHealthMonitor
GROUP: Utilities & Support Services
REASONING: Advanced monitoring agent na gumagamit ng machine learning para i-predict ang potential failures at proactively manage system health. Ito ay Tier 3 specialized function agent na nagbibigay ng utility function para sa pagpapanatili ng system health.
RESOURCES: Database para sa metrics storage, ML model para sa prediction, moderate CPU/memory usage.
DEPENDENCIES: SQLite database, ML prediction model, system metrics collection.
FILE: main_pc_code/agents/predictive_health_monitor.py
PORT: 5613
HEALTH_CHECK_PORT: 6613

AGENT: UltimateTTSAgent (streaming_tts_agent.py)
GROUP: Human Interaction Pipeline
REASONING: Ang agent na ito ay isang specialized agent para sa text-to-speech conversion na may 4-tier fallback system. Nagha-handle ito ng audio streaming at may direct audio output capabilities. Ito ay Tier 3 specialized agent na direktang nakikipag-ugnayan sa user sa pamamagitan ng speech.
RESOURCES: Audio processing, moderate CPU usage, may audio playback capabilities, at gumagamit ng caching para sa optimization.
DEPENDENCIES: StreamingInterruptHandler, UnifiedSystemAgent, at multiple TTS engines.
FILE: main_pc_code/agents/streaming_tts_agent.py
PORT: 5562
HEALTH_CHECK_PORT: 6562

AGENT: StreamingInterruptHandler
GROUP: Human Interaction Pipeline
REASONING: Ang specialized agent na ito ay nagmo-monitor ng partial transcripts para sa interruption keywords at nagse-send ng interrupt signals sa iba't ibang modules. Ito ay Tier 3 specialized agent na nakatuon sa pagpapabuti ng real-time na interaksyon ng tao.
RESOURCES: Light resource usage, primarily focused on text processing at communication.
DEPENDENCIES: StreamingSpeechRecognition, StreamingTtsAgent.
FILE: main_pc_code/agents/streaming_interrupt_handler.py
PORT: 5576
HEALTH_CHECK_PORT: 6576

AGENT: TaskRouter
GROUP: Core Infrastructure
REASONING: Ang central routing agent na ito ay namamahala sa flow ng tasks sa pagitan ng different cognitive agents. Nag-i-implement ito ng Circuit Breaker pattern para sa resilient connections at nagha-handle ng system-wide task distribution. Ito ay Tier 2 system-level agent.
RESOURCES: Moderate resource usage, primarily for task queuing at routing.
DEPENDENCIES: ChainOfThoughtAgent, GoTToTAgent, at may interrupt handling capabilities.
FILE: main_pc_code/agents/model_orchestrator.py
PORT: 7010
HEALTH_CHECK_PORT: 8010

AGENT: VRAMOptimizerAgent
GROUP: AI Models & GPU Services
REASONING: Ang advanced agent na ito ay namamahala ng GPU memory optimization, nagmo-monitor ng VRAM usage, at nag-i-implement ng predictive model loading. Ito ay Tier 1 resource-intensive agent dahil sa direct interaction nito sa GPU resources.
RESOURCES: Heavy GPU/VRAM monitoring at management, active memory optimization.
DEPENDENCIES: SystemDigitalTwin, ModelManagerAgent, at GPU metrics.
FILE: main_pc_code/agents/vram_optimizer_agent.py
PORT: 5572
HEALTH_CHECK_PORT: 6572

AGENT: GoalOrchestratorAgent
GROUP: High-Level Orchestration
REASONING: Ang high-level agent na ito ay namamahala ng user goals at tasks, nagta-track ng goal progress, at nagko-coordinate ng task execution. Ito ay Tier 2 system-level agent na nagpapakita ng complex, multi-step goal management.
RESOURCES: Moderate resource usage, primarily for task tracking at coordination.
DEPENDENCIES: UnifiedPlanningAgent, PerformanceLoggerAgent.
FILE: main_pc_code/agents/goal_manager.py
PORT: 7005
HEALTH_CHECK_PORT: 8005

AGENT: IntentionValidatorAgent
GROUP: Security & Authentication
REASONING: Ang security-focused agent na ito ay nagva-validate ng user intentions at commands, nagme-maintain ng validation history, at nag-i-implement ng security checks. Ito ay Tier 3 specialized function agent na nakatuon sa seguridad.
RESOURCES: Database storage para sa validation history, moderate CPU/memory usage.
DEPENDENCIES: SQLite database, TaskRouter.
FILE: main_pc_code/agents/IntentionValidatorAgent.py
PORT: 5701
HEALTH_CHECK_PORT: 6701

AGENT: DynamicIdentityAgent
GROUP: Core Infrastructure
REASONING: This agent manages system identity and persona switching, connecting to multiple core services like TaskRouter, EnhancedModelRouter, and EmpathyAgent. It's a Tier 2 agent that coordinates system behavior across multiple components.
RESOURCES: Moderate CPU/memory usage, no GPU requirements, primarily focused on communication and coordination.
DEPENDENCIES: TaskRouter, EnhancedModelRouter, EmpathyAgent, and relies on persona configuration files.
FILE: main_pc_code/agents/DynamicIdentityAgent.py
PORT: 5802
HEALTH_CHECK_PORT: 6802

AGENT: ProactiveAgent
GROUP: Human Interaction Pipeline
REASONING: This agent manages scheduled tasks and reminders, providing proactive user engagement. Ito ay Tier 3 specialized function agent na nakatuon sa direktang pakikipag-ugnayan sa user at pagpapabuti ng user experience sa pamamagitan ng timely notifications, na akma sa "Human Interaction Pipeline" group.
RESOURCES: Light CPU/memory usage, no GPU requirements, primarily uses threading for background monitoring.
DEPENDENCIES: CoordinatorAgent for delivering reminders and notifications.
FILE: main_pc_code/agents/ProactiveAgent.py
PORT: 5624
HEALTH_CHECK_PORT: 6624

AGENT: PredictiveLoader
GROUP: AI Models & GPU Services
REASONING: This agent predicts which models will be needed and preloads them to minimize latency. It's a Tier 1 agent that directly impacts model loading performance and resource usage.
RESOURCES: Moderate CPU usage, indirectly affects GPU memory through model loading decisions.
DEPENDENCIES: TaskRouter, connects to model services to trigger preloading.
FILE: main_pc_code/agents/predictive_loader.py
PORT: 5617
HEALTH_CHECK_PORT: 6617

AGENT: GGUFModelManager
GROUP: AI Models & GPU Services
REASONING: This agent directly manages GGUF models using `llama-cpp-python`, handling loading/unloading and memory management. It's a Tier 1 agent with explicit GPU resource management (`n_gpu_layers` parameter).
RESOURCES: Heavy GPU/VRAM usage (imports `torch`, manages `n_gpu_layers`), tracks model memory usage, and implements VRAM optimization.
DEPENDENCIES: Requires `llama-cpp-python`, tracks VRAM usage through GGUFStateTracker.
FILE: main_pc_code/agents/gguf_model_manager.py
PORT: 5575
HEALTH_CHECK_PORT: 6575

AGENT: SelfTrainingOrchestrator
GROUP: AI Models & GPU Services
REASONING: This agent manages training cycles and resource allocation for agent training. It's a Tier 1 agent that directly manages GPU resources for training.
RESOURCES: Heavy resource management (CPU, GPU, memory, storage, network), explicitly tracks and allocates resources for training cycles.
DEPENDENCIES: Database for tracking training cycles, resource monitoring.
FILE: main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py
PORT: 5644
HEALTH_CHECK_PORT: 6644

AGENT: TinyLlamaServiceEnhanced
GROUP: AI Models & GPU Services
REASONING: This agent provides access to the TinyLlama model with explicit GPU management. It's a Tier 1 agent with direct GPU resource handling and model loading/unloading.
RESOURCES: Heavy GPU usage (uses `torch.cuda` extensively), implements dynamic resource management based on system load.
DEPENDENCIES: Requires PyTorch, manages model loading/unloading based on resource availability.
FILE: main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py
PORT: 5615
HEALTH_CHECK_PORT: 6615

AGENT: NLLBTranslationAdapter
GROUP: AI Models & GPU Services
REASONING: This agent provides translation services using the NLLB model. Ito ay Tier 1 resource-intensive agent dahil sa direktang paggamit nito ng GPU resources (`torch.cuda` for memory tracking) at pagmamanage ng model loading/unloading. Bagama't specialized sa translation, ang mataas na paggamit ng GPU ang naglalagay dito sa Tier 1.
RESOURCES: Heavy GPU usage (uses `torch.cuda` for memory tracking), implements dynamic resource management, and handles model loading/unloading.
DEPENDENCIES: Requires PyTorch, Transformers library, and manages model loading/unloading based on resource availability.
FILE: main_pc_code/FORMAINPC/NLLBAdapter.py
PORT: 5581
HEALTH_CHECK_PORT: 6581

AGENT: EnhancedModelRouter
GROUP: Core Infrastructure
REASONING: This agent serves as a central intelligence hub for model routing, combining task classification, context-aware prompting, and chain of thought reasoning. It's a Tier 2 agent that coordinates communication between multiple services.
RESOURCES: Moderate CPU/memory usage, no direct GPU requirements, primarily focused on routing and coordination.
DEPENDENCIES: TaskRouter, ModelManager, ContextualMemory, ChainOfThoughtAgent, RemoteConnector, and other core services.
FILE: main_pc_code/agents/model_orchestrator.py
PORT: 7010
HEALTH_CHECK_PORT: 8010

AGENT: CognitiveModelAgent
GROUP: Cognitive Frameworks
REASONING: This agent manages belief systems and cognitive reasoning using graph-based representations. It's a Tier 3 specialized agent focused on belief consistency and reasoning. Napansin ang dependency sa `RemoteConnector on PC2`, na nagpapahiwatig ng cross-PC communication.
RESOURCES: Moderate CPU/memory usage, no GPU requirements, uses NetworkX for graph operations.
DEPENDENCIES: RemoteConnector on PC2, relies on graph-based belief system.
FILE: main_pc_code/FORMAINPC/CognitiveModelAgent.py
PORT: 5641
HEALTH_CHECK_PORT: 6641

AGENT: LearningAdjusterAgent
GROUP: Learning & Knowledge
REASONING: This agent manages and optimizes learning parameters for agents. Ito ay Tier 3 specialized agent na nakatuon sa pag-optimize ng proseso ng pagkatuto. Bagama't nakakaapekto ito sa performance ng model training, ang pangunahing function nito ay ang pag-adjust ng parameters, hindi ang direktang paggamit ng GPU para sa training. Napansin ang pagbanggit ng "PC2 agents", na nagpapahiwatig ng cross-PC functionality.
RESOURCES: Moderate CPU/memory usage, indirectly affects GPU through parameter optimization.
DEPENDENCIES: Database for parameter tracking, performance metrics, and optimization history.
FILE: main_pc_code/FORMAINPC/LearningAdjusterAgent.py
PORT: 5643
HEALTH_CHECK_PORT: 6643

AGENT: LocalFineTunerAgent
GROUP: AI Models & GPU Services
REASONING: This agent manages model fine-tuning and artifact management with direct GPU usage. It's a Tier 1 agent with explicit GPU resource management for training.
RESOURCES: Heavy GPU usage (uses `torch.cuda`, `AutoModelForCausalLM`, `PEFT` for fine-tuning), manages training jobs and artifacts.
DEPENDENCIES: Requires PyTorch, Transformers, PEFT, and manages database for job tracking.
FILE: main_pc_code/FORMAINPC/LocalFineTunerAgent.py
PORT: 5645
HEALTH_CHECK_PORT: 6645

AGENT: ConsolidatedTranslator
GROUP: Utilities & Support Services
REASONING: This agent combines multiple translation engines with fallback mechanisms, caching, and session management. Ito ay Tier 3 specialized function agent na nagbibigay ng shared translation service na ginagamit ng maraming ahente, kaya akma ito sa `Utilities & Support Services` group.
RESOURCES: Moderate CPU/memory usage, no direct GPU requirements but connects to services that may use GPU.
DEPENDENCIES: ZMQ for network communication, NLTK for translation quality metrics, langdetect for language detection, MemoryOrchestrator for caching.
FILE: main_pc_code/agents/translation_service.py
PORT: 5595
HEALTH_CHECK_PORT: 6595

AGENT: FixedStreamingTranslation
GROUP: Utilities & Support Services
REASONING: This agent handles streaming translation with multiple fallback mechanisms. Ito ay Tier 3 specialized function agent na nagbibigay ng shared translation service na may streaming capability, kaya akma ito sa `Utilities & Support Services` group.
RESOURCES: Moderate CPU/memory usage, no direct GPU requirements but connects to PC2 translation service.
DEPENDENCIES: ZMQ for network communication, GoogleTranslator as fallback, ThreadPoolExecutor for parallel processing.
FILE: main_pc_code/agents/fixed_streaming_translation.py
PORT: 5584
HEALTH_CHECK_PORT: 6584

AGENT: EmotionEngine
GROUP: Human Interaction Pipeline
REASONING: This agent manages emotional states and responses for the system. Ito ay Tier 3 specialized function agent na nakatuon sa pagproseso ng emosyon, na direktang nauugnay sa user input/output at interaksyon, kaya akma ito sa `Human Interaction Pipeline` group.
RESOURCES: Light CPU/memory usage, no GPU requirements.
DEPENDENCIES: ZMQ for network communication, no external ML/AI dependencies.
FILE: main_pc_code/agents/emotion_engine.py
PORT: 5590
HEALTH_CHECK_PORT: 6590

AGENT: MoodTrackerAgent
GROUP: Human Interaction Pipeline
REASONING: This agent tracks and analyzes user mood over time based on emotional state updates. Ito ay Tier 3 specialized function agent na sumusuporta sa human interaction at perception sa pamamagitan ng pagsubaybay sa mood, kaya akma ito sa `Human Interaction Pipeline` group.
RESOURCES: Light CPU/memory usage, no GPU requirements.
DEPENDENCIES: ZMQ for network communication, subscribes to EmotionEngine broadcasts.
FILE: main_pc_code/agents/mood_tracker_agent.py
PORT: 5704
HEALTH_CHECK_PORT: 6704

AGENT: HumanAwarenessAgent
GROUP: Human Interaction Pipeline
REASONING: This agent monitors and analyzes human presence and behavior. Ito ay Tier 3 specialized function agent na nakatuon sa human awareness, na direktang nauugnay sa user input/output at perception, kaya akma ito sa `Human Interaction Pipeline` group.
RESOURCES: Light CPU/memory usage, no GPU requirements.
DEPENDENCIES: ZMQ for network communication, no external ML/AI dependencies.
FILE: main_pc_code/agents/human_awareness_agent.py
PORT: 5705
HEALTH_CHECK_PORT: 6705

AGENT: ToneDetector
GROUP: Human Interaction Pipeline
REASONING: This agent detects and analyzes tone in speech and text. Ito ay Tier 3 specialized function agent na nakatuon sa audio processing at pagtukoy ng tono, na direktang nauugnay sa human interaction, kaya akma ito sa `Human Interaction Pipeline` group. Ang "potential GPU usage" ay naitala sa resources ngunit hindi ito ang pangunahing driver ng pagpapangkat.
RESOURCES: Moderate CPU usage, potential GPU usage when Whisper model is loaded directly.
DEPENDENCIES: ZMQ for network communication, optional Whisper model for speech recognition, pyaudio for direct microphone access.
FILE: main_pc_code/agents/tone_detector.py
PORT: 5625
HEALTH_CHECK_PORT: 6625

AGENT: VoiceProfilingAgent
GROUP: Human Interaction Pipeline
REASONING: This agent handles voice enrollment, speaker recognition, and voice profile management. It's a Tier 3 specialized agent that directly processes and interprets human voice input, fitting the "Human Interaction Pipeline" group.
RESOURCES: Moderate CPU usage, no GPU requirements, implements continuous learning for voice profiles.
DEPENDENCIES: numpy for audio data processing, ZMQ for network communication, JSON for profile storage.
FILE: main_pc_code/agents/voice_profiling_agent.py
PORT: 5708
HEALTH_CHECK_PORT: 6708

AGENT: EmpathyAgent
GROUP: Human Interaction Pipeline
REASONING: This agent adapts voice settings based on emotional state to create empathetic responses. It's a Tier 3 specialized agent that influences system output to enhance human interaction, fitting the "Human Interaction Pipeline" group.
RESOURCES: Light CPU/memory usage, no GPU requirements, connects to EmotionEngine and TTSConnector.
DEPENDENCIES: ZMQ for network communication, threading for background monitoring of emotional states.
FILE: main_pc_code/agents/EmpathyAgent.py
PORT: 5703
HEALTH_CHECK_PORT: 6703

AGENT: EmotionSynthesisAgent
GROUP: Human Interaction Pipeline
REASONING: This agent adds emotional nuance to text based on specified emotions. It's a Tier 3 specialized agent that modifies text output for human consumption, fitting the "Human Interaction Pipeline" group.
RESOURCES: Light CPU/memory usage, no GPU requirements, uses rule-based text transformation.
DEPENDENCIES: ZMQ for network communication, random for emotion marker selection, no external ML libraries.
FILE: main_pc_code/agents/emotion_synthesis_agent.py
PORT: 5706
HEALTH_CHECK_PORT: 6706

AGENT: MemoryOrchestrator
GROUP: Data & Storage Services
REASONING: This agent provides centralized memory storage and retrieval services, acting as a core component for data persistence and access across the system. Ito ay Tier 3 specialized service na nakatuon sa data management, hindi Tier 1 core infrastructure.
RESOURCES: Moderate CPU/memory usage, no GPU requirements, implements in-memory storage with potential for persistence.
DEPENDENCIES: ZMQ for network communication, JSON for data serialization, threading for background tasks.
FILE: main_pc_code/agents/memory_client.py
PORT: 5713
HEALTH_CHECK_PORT: 6713

AGENT: SessionMemoryAgent
GROUP: Data & Storage Services
REASONING: This agent manages conversation history and context for LLM prompts. Ito ay Tier 3 specialized service na nagbibigay ng context management services, direktang sumusuporta sa cognitive functions sa pamamagitan ng pag-manage ng conversational memory.
RESOURCES: Moderate CPU/memory usage, no GPU requirements, uses SQLite for persistent storage and in-memory caching.
DEPENDENCIES: ZMQ for network communication, SQLite for database storage, MemoryClient for memory orchestration.
FILE: main_pc_code/agents/session_memory_agent.py
PORT: 5574
HEALTH_CHECK_PORT: 6574

AGENT: MemoryManager
GROUP: Data & Storage Services
REASONING: This agent coordinates memory operations across the system and provides short-term memory services. Ito ay Tier 3 specialized service na nagha-handle ng dynamic memory buffers, crucial para sa real-time processing at system responsiveness.
RESOURCES: Light CPU/memory usage, no GPU requirements, uses fixed-size deque for memory storage.
DEPENDENCIES: ZMQ for network communication, collections.deque for fixed-size memory buffer, threading for health monitoring.
FILE: main_pc_code/agents/memory_client.py
PORT: 5713
HEALTH_CHECK_PORT: 6713

AGENT: MemoryClient
GROUP: Data & Storage Services
REASONING: This is a Tier 3 agent that acts as a lightweight client interface to the Memory Orchestrator. It handles memory storage and retrieval requests by forwarding them to the orchestrator rather than implementing memory logic itself. The agent is primarily focused on communication rather than computation, serving as a utility for data access.
RESOURCES: Light CPU/memory usage, no GPU requirements. Uses ZMQ for network communication. Maintains minimal state with request tracking.
DEPENDENCIES: ZMQ for communication, BaseAgent as parent class, requires connection to Memory Orchestrator service.
FILE: main_pc_code/agents/memory_client.py
PORT: 5713
HEALTH_CHECK_PORT: 6713

AGENT: KnowledgeBase
GROUP: Data & Storage Services
REASONING: This is a Tier 2 agent that manages the system's knowledge base using SQLite. It provides core functionality for storing, retrieving, updating, and searching facts organized by topics. The agent implements robust error handling, resource management, and health reporting, serving as a central repository for structured data.
RESOURCES: Moderate CPU/memory usage, no GPU requirements. Uses SQLite for persistent storage. Implements background initialization and database connection management.
DEPENDENCIES: SQLite for database operations, threading for background tasks, psutil for system monitoring.
FILE: main_pc_code/agents/knowledge_base.py
PORT: 5578
HEALTH_CHECK_PORT: 6578

AGENT: LearningManager
GROUP: Learning & Knowledge
REASONING: This is a Tier 2 agent responsible for managing the learning process of the AI system. It tracks learning sessions, adjusts learning parameters based on performance metrics, and coordinates with other agents for continuous learning. The agent doesn't directly use GPU resources but manages processes that might, placing it in a coordination role for learning activities.
RESOURCES: Moderate CPU/memory usage, no direct GPU requirements but manages learning processes that may use GPU. Implements dynamic learning rate adjustment and session management.
DEPENDENCIES: ZMQ for communication, numpy for numerical operations, threading for background tasks.
FILE: main_pc_code/agents/learning_manager.py
PORT: 5580
HEALTH_CHECK_PORT: 6580

AGENT: MetaCognitionAgent
GROUP: Cognitive Frameworks
REASONING: This is a Tier 2 agent that monitors and analyzes system performance, optimizes memory usage, analyzes learning patterns, and provides insights into system behavior. While it uses `torch.cuda.empty_cache()`, its primary role is meta-cognitive analysis and optimization, not direct model inference or training, making it a high-level cognitive framework rather than a Tier 1 GPU service.
RESOURCES: Moderate to heavy CPU/memory usage, uses GPU for memory optimization. Implements memory compression with torch.cuda.empty_cache(). Uses SQLite for data storage and analysis.
DEPENDENCIES: PyTorch for GPU memory management, sklearn for data analysis, ZMQ for communication, SQLite for database operations, psutil for system monitoring.
FILE: main_pc_code/agents/MetaCognitionAgent.py
PORT: 5630
HEALTH_CHECK_PORT: 6630

AGENT: ActiveLearningMonitor
GROUP: Learning & Knowledge
REASONING: This is a Tier 3 agent that monitors interactions between users and the system to identify valuable learning opportunities. It analyzes interactions for training value and triggers fine-tuning jobs when valuable interactions are detected. The agent serves a specialized role in the learning pipeline without heavy resource requirements.
RESOURCES: Light CPU/memory usage, no GPU requirements. Uses a deque for buffering interactions and ZMQ for communication.
DEPENDENCIES: ZMQ for communication, requires connections to UMRA, Coordinator, and SelfTrainingOrchestrator services.
FILE: main_pc_code/agents/active_learning_monitor.py
PORT: 5638
HEALTH_CHECK_PORT: 6638

AGENT: UnifiedPlanningAgent
GROUP: High-Level Orchestration
REASONING: This is a Tier 1 agent that combines chain of thought reasoning, code execution, task planning, and progressive code generation. It handles complex multi-step tasks with iterative refinement, provides a safe code execution environment, and integrates with the AutoGen framework. The agent's central role in planning and orchestrating complex tasks places it at the core infrastructure level.
RESOURCES: Moderate CPU/memory usage, no direct GPU requirements but manages processes that may use specialized resources. Implements sophisticated planning, code generation, and execution capabilities.
DEPENDENCIES: ZMQ for communication, requires connections to TaskRouter and AutoGenFramework, tempfile for code execution sandboxing.
FILE: main_pc_code/agents/goal_manager.py
PORT: 7005
HEALTH_CHECK_PORT: 8005

AGENT: MultiAgentSwarmManager
GROUP: High-Level Orchestration
REASONING: This is a Tier 1 agent that manages and coordinates a swarm of specialized agents to accomplish complex tasks. It decomposes high-level goals into specific tasks, coordinates execution across multiple agents, synthesizes results, and handles task prioritization and scheduling. The agent's central role in orchestrating complex multi-agent workflows places it at the core infrastructure level.
RESOURCES: Moderate CPU/memory usage, no direct GPU requirements. Uses ZMQ for communication with multiple agent coordination. Implements sophisticated task planning and execution orchestration.
DEPENDENCIES: ZMQ for communication, requires connections to CoordinatorAgent and AutoGenFramework, threading for parallel task processing.
FILE: main_pc_code/agents/model_orchestrator.py
PORT: 7010
HEALTH_CHECK_PORT: 8010

AGENT: UnifiedSystemAgent
GROUP: Core Infrastructure
REASONING: This is a Tier 1 agent that serves as the central command center for system orchestration, service discovery, maintenance, and monitoring. It provides comprehensive system management capabilities through a ZMQ interface, handles service registration and discovery, monitors service health, and manages system resources. The agent's critical role in system-wide coordination and health monitoring places it at a core infrastructure level.
RESOURCES: Moderate CPU/memory usage, no GPU requirements. Uses ZMQ ROUTER and REP sockets for communication. Implements service discovery, monitoring, and management.
DEPENDENCIES: ZMQ for communication, psutil for system monitoring, requires connections to various system services.
FILE: main_pc_code/agents/system_digital_twin.py
PORT: 7120
HEALTH_CHECK_PORT: 8120

AGENT: TTSConnector
GROUP: Network & Communication
REASONING: This is a Tier 3 agent that connects the modular system's text processor to the Bark TTS agent. It handles request queuing, prioritization, and batch processing to optimize TTS operations. The agent implements sophisticated connection pooling and health reporting but primarily serves as a middleware component for communication, not core TTS functionality.
RESOURCES: Light to moderate CPU/memory usage, no direct GPU requirements. Implements connection pooling for efficient resource management and batch processing of TTS requests.
DEPENDENCIES: ZMQ for communication, requires connections to text processor and TTS agent, psutil for system monitoring.
FILE: main_pc_code/agents/tts_connector.py
PORT: 5582
HEALTH_CHECK_PORT: 6582

AGENT: TTSCache
GROUP: Data & Storage Services
REASONING: This is a Tier 3 agent that provides caching functionality for text-to-speech operations. It stores generated audio data to avoid redundant processing of identical text, implements cache pruning strategies to manage disk usage, and provides utilities for retrieving and playing cached audio. The agent serves a specialized optimization role for data storage.
RESOURCES: Light CPU/memory usage, no GPU requirements. Uses disk storage for caching audio data and implements cache management strategies.
DEPENDENCIES: NumPy for audio data handling, sounddevice for audio playback, requires filesystem access for cache storage.
FILE: main_pc_code/agents/tts_cache.py
PORT: 5628
HEALTH_CHECK_PORT: 6628

AGENT: TTSAgent
GROUP: Human Interaction Pipeline
REASONING: This is a Tier 2 agent that handles text-to-speech synthesis requests. It provides an interface for TTS operations, implements interrupt handling to stop ongoing speech synthesis, and registers with service discovery. While this implementation is lightweight, the referenced archive version suggests it can use GPU acceleration, indicating its core function is TTS, which is part of human interaction.
RESOURCES: Light CPU/memory usage, no direct GPU requirements in this implementation (though the referenced archive version shows GPU usage with torch.cuda). Implements interrupt handling for speech synthesis.
DEPENDENCIES: ZMQ for communication, requires connection to StreamingInterruptHandler, service discovery for registration.
FILE: main_pc_code/agents/tts_agent.py
PORT: 5563
HEALTH_CHECK_PORT: 6563

AGENT: CodeGeneratorAgent
GROUP: Cognitive Frameworks
REASONING: This is a Tier 2 agent that generates code based on natural language descriptions. It supports multiple programming languages, integrates with the AutoGen framework, and uses local LLMs for code generation. The agent can manage GGUF models directly or forward requests to a Model Manager, indicating sophisticated cognitive capabilities in code generation.
RESOURCES: Moderate to heavy CPU/memory usage, potential GPU usage through GGUF models. Implements model loading/unloading and generation with local LLMs.
DEPENDENCIES: ZMQ for communication, GGUFModelManager for local model management, requests library for Ollama API integration.
FILE: main_pc_code/agents/code_generator_agent.py
PORT: 5604
HEALTH_CHECK_PORT: 6604

AGENT: Executor
GROUP: Utilities & Support Services
REASONING: This is a Tier 3 agent that handles user command execution with security controls. It receives commands via ZMQ, validates permissions, authenticates users for sensitive commands, and executes system commands. The agent provides a utility function for system interaction.
RESOURCES: Light CPU/memory usage, no GPU requirements. Uses system resources for executing commands.
DEPENDENCIES: ZMQ for communication, psutil for system monitoring, subprocess for command execution.
FILE: main_pc_code/agents/executor.py
PORT: 5606
HEALTH_CHECK_PORT: 6606

AGENT: StreamingAudioCapture
GROUP: Human Interaction Pipeline
REASONING: This is a Tier 1 agent that handles the critical first step in the audio processing pipeline. It captures raw audio from microphones, performs basic energy detection, manages wake word detection, and streams audio chunks to downstream components. Its reliability directly impacts the entire voice processing chain, making it a foundational part of human interaction.
RESOURCES: Moderate CPU usage, optional GPU usage for wake word detection. Manages audio hardware resources.
DEPENDENCIES: PyAudio/sounddevice for audio capture, ZMQ for communication, torch/CUDA for wake word detection (when enabled).
FILE: main_pc_code/agents/streaming_audio_capture.py
PORT: 6575
HEALTH_CHECK_PORT: 7575

AGENT: FusedAudioPreprocessor
GROUP: Human Interaction Pipeline
REASONING: This is a Tier 1 agent that handles critical audio preprocessing functions including noise reduction, voice activity detection (VAD), acoustic echo cancellation (AEC), and automatic gain control (AGC). It optimizes the audio pipeline by combining multiple processing steps into a single agent to reduce latency, directly impacting the quality of human audio input.
RESOURCES: Moderate to heavy CPU usage, GPU usage for VAD model. Implements sophisticated audio processing pipeline.
DEPENDENCIES: ZMQ for communication, torch/CUDA for VAD model, noisereduce and scipy for audio processing, librosa for audio analysis.
FILE: main_pc_code/agents/fused_audio_preprocessor.py
PORT: 6578
HEALTH_CHECK_PORT: 7578

AGENT: WakeWordDetector
GROUP: Human Interaction Pipeline
REASONING: This is a Tier 2 agent that specializes in wake word detection. It subscribes to audio streams, detects wake words using Porcupine, and publishes wake word events to trigger system activation. It integrates with VAD for improved accuracy and implements energy-based detection as a fallback, directly enabling human interaction.
RESOURCES: Light to moderate CPU usage, no direct GPU requirements. Uses Porcupine for wake word detection.
DEPENDENCIES: ZMQ for communication, pvporcupine for wake word detection, pyaudio for audio processing, requires API key.
FILE: main_pc_code/agents/wake_word_detector.py
PORT: 6577
HEALTH_CHECK_PORT: 7577

AGENT: StreamingSpeechRecognition
GROUP: AI Models & GPU Services
REASONING: This is a Tier 1 agent that performs speech-to-text conversion using Whisper models. It implements sophisticated resource management, dynamic model loading/unloading, noise reduction, and language detection. Its heavy CPU/GPU usage for speech recognition models places it firmly in the AI Models & GPU Services group.
RESOURCES: Heavy CPU/GPU usage for speech recognition models. Implements dynamic resource management.
DEPENDENCIES: ZMQ for communication, whisper for speech recognition, torch/CUDA for GPU acceleration, connects to ModelManagerAgent.
FILE: main_pc_code/agents/streaming_speech_recognition.py
PORT: 6580
HEALTH_CHECK_PORT: 7580

AGENT: StreamingLanguageAnalyzer
GROUP: Language & Translation Services
REASONING: This is a Tier 2 agent that analyzes transcribed text to determine language (English, Tagalog, Taglish), calculates language ratios, and determines if translation is needed. It integrates with other services like TagaBERTa for sentiment analysis and uses a combination of lexicon-based and model-based approaches for language detection.
RESOURCES: Light to moderate CPU usage, no GPU requirements. Primarily focused on text analysis.
DEPENDENCIES: ZMQ for communication, fastText (optional) for language identification, connects to TagaBERTa service.
FILE: main_pc_code/agents/streaming_language_analyzer.py
PORT: 5579
HEALTH_CHECK_PORT: 6579

AGENT: NLUAgent
GROUP: Cognitive Frameworks
REASONING: This is a Tier 3 agent that handles natural language understanding through rule-based pattern matching. It extracts intents and entities from user input using predefined patterns rather than ML models. The agent is lightweight and operates independently without external service dependencies, making it suitable for basic command recognition and intent classification.
RESOURCES: Light CPU/memory usage, no GPU requirements. Uses pattern matching for intent recognition.
DEPENDENCIES: ZMQ for communication, regex for pattern matching, no external ML models or services.
FILE: main_pc_code/agents/nlu_agent.py
PORT: 5709
HEALTH_CHECK_PORT: 6709

AGENT: AdvancedCommandHandler
GROUP: High-Level Orchestration
REASONING: This is a Tier 2 agent that extends basic command handling with advanced features like command sequences, script execution, and domain-specific command modules. It coordinates with other agents like the Executor Agent for script execution and the Coordinator Agent for parallel execution, demonstrating orchestration capabilities.
RESOURCES: Light to moderate CPU usage, no GPU requirements. Manages script execution and command sequences.
DEPENDENCIES: ZMQ for communication, connects to Executor Agent and Coordinator Agent, uses dynamic module loading for domain-specific commands.
FILE: main_pc_code/agents/advanced_command_handler.py
PORT: 5710
HEALTH_CHECK_PORT: 6710

AGENT: ChitChatAgent
GROUP: Human Interaction Pipeline
REASONING: This is a Tier 3 agent that handles casual conversation interactions. It maintains conversation history, formats messages for LLM processing, and delegates the actual response generation to a remote LLM service on PC2. The agent focuses on conversation state management, directly facilitating human interaction.
RESOURCES: Light CPU usage, no direct GPU requirements. Primarily focused on conversation management and coordination.
DEPENDENCIES: ZMQ for communication, connects to remote LLM on PC2 for response generation, maintains conversation context.
FILE: main_pc_code/agents/chitchat_agent.py
PORT: 5711
HEALTH_CHECK_PORT: 6711

AGENT: FeedbackHandler
GROUP: Human Interaction Pipeline
REASONING: This is a Tier 3 agent that provides visual and voice confirmation feedback for command execution. It maintains connections to GUI and voice systems, implements different feedback styles, and provides a unified interface for other agents to send feedback to users. The agent is focused on enhancing user experience through multi-modal feedback.
RESOURCES: Light CPU usage, no GPU requirements. Primarily focused on message passing and coordination.
DEPENDENCIES: ZMQ for communication, connects to GUI for visual feedback and voice system for audio feedback.
FILE: main_pc_code/agents/feedback_handler.py
PORT: 5636
HEALTH_CHECK_PORT: 6636

AGENT: Responder
GROUP: Human Interaction Pipeline
REASONING: This is a Tier 2 agent that handles text-to-speech conversion and audio response generation. It coordinates with multiple TTS services, implements emotion-based voice modulation, supports multiple languages, and provides visual feedback. The agent focuses on converting text responses into natural-sounding speech with appropriate emotional characteristics for human interaction.
RESOURCES: Moderate CPU usage, optional GPU usage for TTS model. Manages audio output and TTS processing.
DEPENDENCIES: ZMQ for communication, TTS library with XTTS model, torch for TTS processing, connects to multiple services (StreamingTtsAgent, TTSCache, TTSConnector).
FILE: main_pc_code/agents/responder.py
PORT: 5637
HEALTH_CHECK_PORT: 6637

AGENT: VisionCaptureAgent
GROUP: Human Interaction Pipeline
REASONING: This is a Tier 2 agent that serves as the first step in the vision pipeline. It captures screenshots from the primary display and provides them via ZMQ to downstream components. The agent handles screen capture requests, performs basic image processing, and optionally saves screenshots to disk, directly enabling visual input for human interaction.
RESOURCES: Light CPU usage, no GPU requirements. Uses minimal memory for screenshot capture and processing.
DEPENDENCIES: ZMQ for communication, PIL and mss for screen capture, base64 for image encoding.
FILE: main_pc_code/agents/vision_capture_agent.py
PORT: 5592
HEALTH_CHECK_PORT: 6592

AGENT: FaceRecognitionAgent
GROUP: AI Models & GPU Services
REASONING: This is a Tier 1 agent that provides comprehensive face analysis capabilities. It combines multiple specialized components to detect faces, recognize known individuals, analyze emotions, detect liveness, and apply privacy protections. The agent implements sophisticated tracking with Kalman filters and optimizes performance through GPU acceleration and model quantization, requiring significant computational resources.
RESOURCES: Heavy CPU/GPU usage for face detection, recognition, and emotion analysis. Implements GPU optimizations and quantization for better performance.
DEPENDENCIES: ZMQ for communication, insightface for face detection/recognition, torch/CUDA for GPU acceleration, onnxruntime for emotion model inference, OpenCV for image processing, filterpy for Kalman tracking.
FILE: main_pc_code/agents/face_recognition_agent.py
PORT: 5610
HEALTH_CHECK_PORT: 6610