# Communication Patterns of Agents/Services

This document summarizes how agents and services communicate in your system, based on `startup_config.yaml` and codebase analysis.

---

## General Findings
- **Primary Protocol:** ZMQ (ZeroMQ) is used for nearly all inter-agent communication.
- **Message Format:** JSON or serialized Python dicts.
- **Patterns:** REQ/REP (request/reply) is the most common; some agents may use PUB/SUB for broadcasting.

---

## Per Group Communication Summary

### core_services
- **SystemDigitalTwin**: Inherits from `BaseAgent`. ZMQ REP socket; receives requests from other agents (e.g., RequestCoordinator, UnifiedSystemAgent).
- **RequestCoordinator**: Inherits from `BaseAgent`. ZMQ REQ/REP; coordinates and relays tasks between agents.
- **UnifiedSystemAgent**: Inherits from `BaseAgent`. ZMQ REQ/REP; sends/receives system-level commands/events.

### memory_system
- **MemoryClient**: Inherits from `BaseAgent`. ZMQ REQ; initiates memory-related requests to SessionMemoryAgent/KnowledgeBase.
- **SessionMemoryAgent**: Inherits from `BaseAgent`. ZMQ REQ/REP; serves memory requests and interacts with MemoryClient/RequestCoordinator.
- **KnowledgeBase**: Inherits from `BaseAgent`. ZMQ REP; serves knowledge/memory queries from MemoryClient or others.

### utility_services
- **CodeGenerator**: Inherits from `BaseAgent`. ZMQ REP; receives code generation requests from other agents.
- **SelfTrainingOrchestrator**: Inherits from `BaseAgent`. ZMQ REP; manages self-training cycles for models, receives training requests from ModelManagerAgent and GGUFModelManager, coordinates resource allocation and training job status via direct requests.

### ai_models_gpu_services
- **GGUFModelManager**: Inherits from `BaseAgent`. ZMQ REP; manages GGUF-format models for GPU deployment, responds to model load/unload/status requests from ModelManagerAgent and PredictiveLoader, and coordinates with VRAMOptimizerAgent for resource management.
- **ModelManagerAgent**: Inherits from `BaseAgent`. ZMQ REQ/REP; orchestrates model lifecycle operations, sends requests to GGUFModelManager and VRAMOptimizerAgent, and receives preloading instructions from PredictiveLoader.
- **VRAMOptimizerAgent**: Inherits from `BaseAgent`. ZMQ REP; monitors and optimizes GPU VRAM usage, receives model/resource status requests from ModelManagerAgent and GGUFModelManager, and sends optimization triggers.
- **PredictiveLoader**: Inherits from `BaseAgent`. ZMQ REP; predicts and preloads models based on upcoming demand, sends preloading requests to ModelManagerAgent and GGUFModelManager, and receives model status updates.

### audio_processing
- **AudioCapture**: Inherits from `BaseAgent`. ZMQ REP; captures streaming audio input and provides audio frames to downstream agents such as FusedAudioPreprocessor and StreamingSpeechRecognition.
- **FusedAudioPreprocessor**: Inherits from `BaseAgent`. ZMQ REP; performs audio preprocessing (e.g., denoising, normalization) on captured audio, communicates with AudioCapture and StreamingInterruptHandler.
- **StreamingInterruptHandler**: Inherits from `BaseAgent`. ZMQ REP; detects and handles interruptions in audio streams, interacts with FusedAudioPreprocessor, StreamingSpeechRecognition, and ProactiveAgent.
- **StreamingSpeechRecognition**: Inherits from `BaseAgent`. ZMQ REP; converts processed audio into text, receives audio from FusedAudioPreprocessor, sends transcriptions to StreamingLanguageAnalyzer and other agents.
- **StreamingTTSAgent**: Inherits from `BaseAgent`. ZMQ REP; generates speech/audio output from text, communicates with Responder and other agents needing TTS services.
- **WakeWordDetector**: Inherits from `BaseAgent`. ZMQ REP; detects wake words in audio streams, interacts with AudioCapture and triggers downstream actions.
- **StreamingLanguageAnalyzer**: Inherits from `BaseAgent`. ZMQ REP; analyzes transcribed speech for language features, intent, or sentiment, receives input from StreamingSpeechRecognition, outputs to ProactiveAgent or NLU agents.
- **ProactiveAgent**: Inherits from `BaseAgent`. ZMQ REP; monitors ongoing audio/language context and triggers proactive actions or alerts, interacts with StreamingLanguageAnalyzer, StreamingInterruptHandler, and other agents.

### emotion_system
- **EmotionEngine**: Inherits from `BaseAgent`. ZMQ REP; analyzes and manages system-wide emotion state, receives input from MoodTrackerAgent, ToneDetector, and other agents, provides emotion state to EmotionSynthesisAgent and EmpathyAgent.
- **MoodTrackerAgent**: Inherits from `BaseAgent`. ZMQ REP; tracks and updates the overall mood of the system/user, communicates mood changes to EmotionEngine and HumanAwarenessAgent.
- **HumanAwarenessAgent**: Inherits from `BaseAgent`. ZMQ REP; monitors user presence and awareness, provides human state context to EmotionEngine and EmpathyAgent.
- **ToneDetector**: Inherits from `BaseAgent`. ZMQ REP; detects tone and sentiment from audio/text input, sends tone data to EmotionEngine and MoodTrackerAgent.
- **VoiceProfilingAgent**: Inherits from `BaseAgent`. ZMQ REP; profiles user voice characteristics for emotion and identity, interacts with ToneDetector and EmotionEngine.
- **EmpathyAgent**: Inherits from `BaseAgent`. ZMQ REP; generates empathetic responses based on emotion and mood state, coordinates with EmotionEngine and HumanAwarenessAgent.
- **EmotionSynthesisAgent**: Inherits from `BaseAgent`. ZMQ REP; synthesizes emotional expression in system outputs, receives emotion state from EmotionEngine, provides feedback to MoodTrackerAgent and EmpathyAgent.

### utilities_support
- **PredictiveHealthMonitor**: Inherits from `BaseAgent`. ZMQ REP for health/status requests, ZMQ PUB for error/event reporting (Error Bus, topic 'ERROR:'). Coordinates with self-healing agents via ZMQ REQ. Monitors agents, resources, and initiates recovery actions.
- **FixedStreamingTranslation**: Inherits from `BaseAgent`. ZMQ REP for translation requests, uses PUB to report errors/events to Error Bus. May use REQ to interact with PC2/main translation services or fallback translators.
- **Executor**: Inherits from `BaseAgent`. ZMQ REP for command execution requests, PUB for feedback/logging and error reporting. Interacts with orchestrators or user-facing agents via REQ/REP.
- **TinyLlamaServiceEnhanced**: Inherits from `BaseAgent`. ZMQ REP for model inference and management requests; error/event reporting via Error Bus (PUB). Used by model managers or orchestrators via REQ.
- **LocalFineTunerAgent**: Inherits from `BaseAgent`. ZMQ REP for fine-tuning/model management requests, PUB for error/event reporting. Interacts with orchestrators, model managers, or CLI tools via REQ.
- **NLLBAdapter**: Inherits from `BaseAgent`. ZMQ REP for translation requests, PUB for error/event reporting. Invoked by translation agents or orchestrators via REQ.

### reasoning_services
- **ChainOfThoughtAgent**: Inherits from `BaseAgent`. ZMQ REP for stepwise reasoning requests. Receives REQ from orchestrators, NLU agents, or user-facing services. Reports errors/events via Error Bus (PUB).
- **GoTToTAgent**: Inherits from `BaseAgent`. ZMQ REP for graph/tree-of-thought reasoning requests. Invoked via REQ by orchestrators or other agents. Reports errors/events via Error Bus (PUB).
- **CognitiveModelAgent**: Inherits from `BaseAgent`. ZMQ REP for cognitive/belief state management and reasoning requests. Receives REQ from orchestrators or other agents. Reports errors/events via Error Bus (PUB).

### vision_system
- **FaceRecognitionAgent**: Inherits from `BaseAgent`. Uses ZMQ REP socket for request/reply pattern. Receives face recognition, emotion, and liveness requests from other agents/services. Publishes errors/events to the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:').

### learning_knowledge
- **ModelEvaluationFramework**: Inherits from `BaseAgent`. Uses ZMQ REP socket for request/reply. Receives model evaluation requests from agents such as LearningManager and LearningOrchestrationService. Provides standardized metrics, historical data, and feedback to the learning pipeline.
- **LearningOrchestrationService**: Inherits from `BaseAgent`. Uses ZMQ REP socket for request/reply. Manages training cycles and resource allocation. Receives learning opportunities from LearningOpportunityDetector and coordinates training with LearningManager and ActiveLearningMonitor.
- **LearningOpportunityDetector**: Inherits from `BaseAgent`. Uses ZMQ REP for direct requests and ZMQ PUB for error/event reporting. Detects and scores learning opportunities, notifies LearningOrchestrationService, and can interact with MemoryClient. Subscribes to outputs from UMRA and RequestCoordinator (ZMQ SUB).
- **LearningManager**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Manages the learning process, tracks progress, and coordinates with LearningOrchestrationService and ActiveLearningMonitor for continuous learning.
- **ActiveLearningMonitor**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Subscribes (ZMQ SUB) to outputs from UMRA and RequestCoordinator for monitoring, and communicates with SelfTrainingOrchestrator via ZMQ REQ. Publishes errors/events to the Error Bus.
- **LearningAdjusterAgent**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Manages and optimizes learning parameters for PC2 agents. Publishes errors/events to the Error Bus (ZMQ PUB).
### language_processing
- **ModelOrchestrator**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Central orchestrator for model requests, task classification, and context-aware routing. Communicates with GoalManager, NLUAgent, and downstream model agents. Publishes metrics and errors to the Error Bus.
- **GoalManager**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Manages high-level goals, decomposes them into tasks, and dispatches to ModelOrchestrator and other agents. Uses MemoryClient for persistence. Publishes errors to the Error Bus (ZMQ PUB).
- **IntentionValidatorAgent**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Validates user intentions and commands, maintains validation history, and implements security checks. Communicates with RequestCoordinator and other language agents as needed.
- **NLUAgent**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Analyzes user input, extracts intents/entities, and provides structured output to ModelOrchestrator and GoalManager. Publishes errors to the Error Bus (ZMQ PUB/SUB).
- **AdvancedCommandHandler**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Handles advanced command parsing, sequences, and script execution. Coordinates with Jarvis Memory Agent and other command-related agents.
- **ChitchatAgent**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Handles open-domain conversational requests, connects to LLMs, and maintains context. Integrates with personality engines and other dialogue agents.
- **FeedbackHandler**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Provides visual and voice feedback for command execution. Publishes errors to the Error Bus (ZMQ PUB/SUB).
- **Responder**: Inherits from `BaseAgent`. Uses ZMQ SUB for receiving TTS requests and interrupt signals. Connects to StreamingTTSAgent and other services via ZMQ REQ. Publishes errors to the Error Bus (ZMQ PUB). Uses service discovery for dynamic connections.
- **TranslationService**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Centralized translation service, orchestrates translation requests, manages fallback chains, persistent caching, and session management. Communicates with MemoryOrchestrator, NLLBAdapter, and other translation engines. Publishes errors to the Error Bus.
- **DynamicIdentityAgent**: Inherits from `BaseAgent`. Uses ZMQ REP for request/reply. Manages and adapts agent persona/identity dynamically. Publishes status and errors to the Error Bus (ZMQ PUB).
### emotion_system
- **EmotionEngine**: ZMQ REP; receives emotion analysis requests from other agents.

---

## Communication Flow Example
- **REQ/REP:** MemoryClient (REQ) → SessionMemoryAgent (REP)
- **Serialization:** All messages are JSON-encoded.
- **Initiators:** MemoryClient, RequestCoordinator, UnifiedSystemAgent (can initiate and respond)
- **Responders:** Service agents (CodeGenerator, EmotionEngine, etc.)

---

## Notes
- For more detailed message schemas or payload examples, inspect each agent’s send/receive logic in their respective files.
- No REST API or HTTP-based communication found in core agents.

---

*This document serves as a high-level reference for understanding how your agents/services communicate. Update as needed when new agents or protocols are added.*

---

## Agent Communication Patterns in Practice

This section summarizes real-world patterns from several core agents, highlighting advanced and shared mechanisms.

### Summary Table: Agent Patterns

| Agent                   | Base Class  | Main Pattern | Error Bus (PUB/SUB) | Health Check | Notes                         |
|-------------------------|-------------|--------------|---------------------|--------------|-------------------------------|
| SystemDigitalTwin       | BaseAgent   | ZMQ REP      | Optional            | Yes          | Secure ZMQ support            |
| ProactiveContextMonitor | (Custom)    | ZMQ REP      | No                  | Yes (HTTP)   | Background analysis           |
| AuthenticationAgent     | BaseAgent   | ZMQ REP      | Optional            | Yes          | Session cleanup thread        |
| UnifiedErrorAgent       | (Custom)    | ZMQ REP      | No                  | Yes          | Error triage/analysis thread  |
| TaskSchedulerAgent      | BaseAgent   | ZMQ REP      | Yes (PUB)           | Yes          | Centralized error reporting   |

### BaseAgent Inheritance
- Most agents inherit from `BaseAgent`, which standardizes:
  - ZMQ REP socket setup for request/reply
  - Logging, config loading, and health check endpoints
  - Common methods: `send_message_to_agent()`, `broadcast_event()`, `handle_request()`, `start_health_check()`
- This ensures uniform communication and easier agent integration.

### Error Bus (PUB/SUB) Pattern
- Several agents (e.g., TaskSchedulerAgent, ResourceManager) use a central **Error Bus** for distributed error/event reporting.
- **Pattern:** ZMQ PUB socket publishes to a known endpoint (e.g., `tcp://<host>:7150`). Any agent can SUBSCRIBE to receive events.
- **Sample Publisher Code:**
  ```python
  self.error_bus_pub = self.context.socket(zmq.PUB)
  self.error_bus_pub.connect(self.error_bus_endpoint)
  self.error_bus_pub.send_json({
      "type": "error",
      "source": self.agent_name,
      "timestamp": datetime.now().isoformat(),
      "details": {...}
  })
  ```
- **Sample Subscriber Code:**
  ```python
  error_bus_sub = context.socket(zmq.SUB)
  error_bus_sub.connect("tcp://central_host:7150")
  error_bus_sub.setsockopt_string(zmq.SUBSCRIBE, "")
  while True:
      msg = error_bus_sub.recv_json()
      # handle error/event
  ```
- **Benefits:**
  - Decouples error reporting from handling
  - Enables real-time monitoring and self-healing

### Additional Patterns & Notes
- **Health Checks:** Most agents expose a health check endpoint (ZMQ or HTTP, usually on `main_port + 1`).
- **Background Threads:** Used for metrics collection, log scanning, session cleanup, etc.
- **JSON Serialization:** All agent communication is JSON-encoded for interoperability.
- **Configurable Ports/Endpoints:** Agents discover peer addresses via config files, env vars, or CLI args.
- **Security:** Some agents (like SystemDigitalTwin) can enable secure ZMQ (CURVE/TLS) for encrypted comms.

---

Edge Cases, Failure Points, and Tricky Scenarios (MainPC)
This section documents known issues, edge cases, and tricky scenarios in the MainPC system. Developers should review and monitor these areas carefully:

1. ZMQ Socket Binding/Port Conflicts
Symptom: "Address already in use" errors or agents failing to start.
Cause: Multiple agents/services trying to bind to the same port, or zombie processes not releasing sockets.
Mitigation: Ensure unique port assignments; check for lingering processes (lsof -i :<port>); use proper cleanup/shutdown logic.
2. Race Conditions on Startup
Symptom: Agents fail to connect to peers, resulting in connection refused or timeouts.
Cause: Agents depending on others that are not yet up (e.g., MemoryOrchestrator, HealthMonitor).
Mitigation: Implement retry logic, exponential backoff, or startup sequencing/wait-for-it scripts.
3. ZMQ PUB/SUB Message Loss
Symptom: Missed events/errors, especially right after agent startup.
Cause: Subscribers must connect before publishers start sending; ZMQ does not queue messages for late subscribers.
Mitigation: Add small startup delays, or have subscribers signal readiness before publishers send critical events.
4. Legacy/Deprecated Config Keys
Symptom: Unexpected agent behavior, ignored config, or silent failures.
Cause: Old config keys lingering in YAML files, not used by new code.
Mitigation: Regularly audit config files; remove or update deprecated keys; document all required/optional keys.
5. Threading/Background Task Issues
Symptom: Agents hang on shutdown, or background tasks keep running after main thread exits.
Cause: Daemon threads not properly joined or cleaned up.
Mitigation: Always implement and call 
cleanup()
 methods; join threads with timeouts; use logging to verify shutdown.
6. JSON Serialization Errors
Symptom: Crashes or dropped messages due to non-serializable objects (e.g., datetime, custom classes).
Cause: Passing raw Python objects in ZMQ messages without proper serialization.
Mitigation: Always use json.dumps() with custom encoders if needed; convert datetimes to ISO strings.
7. Health Check Endpoint Mismatches
Symptom: HealthMonitor reports agents as down, even if running.
Cause: Wrong port assignment, or health check endpoint not matching the expected URL/pattern.
Mitigation: Standardize health check port as main_port + 1; document all health endpoints.
8. Environment Variable/Secrets Leakage
Symptom: Sensitive info exposed in logs or config files.
Cause: Logging full config dicts or not masking secrets.
Mitigation: Mask secrets in logs; use .gitignore for secrets files; audit logs before sharing.
9. Inconsistent Error Handling
Symptom: Silent failures, hard-to-debug crashes.
Cause: Missing try/except blocks, or not logging exceptions.
Mitigation: Wrap all I/O and comms in try/except; use structured logging for errors.
Relevant Files per Issue
Issue/Scenario	Relevant Files (or Patterns)
ZMQ Socket Binding/Port Conflicts	main_pc_code/agents/*, main_pc_code/services/*, config YAMLs
Race Conditions on Startup	main_pc_code/agents/*, main_pc_code/services/*, startup scripts
ZMQ PUB/SUB Message Loss	Agents using PUB/SUB: e.g. TaskSchedulerAgent.py, ResourceManager.py
Legacy/Deprecated Config Keys	
config/startup_config.yaml
, all agent/service config parsers
Threading/Background Task Issues	Any agent/service with threading: *Agent.py, *Service.py
JSON Serialization Errors	All agent/service files with ZMQ send/recv, especially custom objects
Health Check Endpoint Mismatches	HealthMonitor, all agents with health check endpoints
Environment Variable/Secrets Leakage	Logging setup, config loaders, any file handling secrets
Inconsistent Error Handling	All agent/service files, especially I/O and comms code
