# Group: Language Processing

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: ModelOrchestrator
- **Main Class:** `ModelOrchestrator` (`main_pc_code/agents/model_orchestrator.py`)
- **Host Machine:** MainPC (default, can be configured)
- **Role:** Orchestrates all model interactions, from simple chat to complex, iterative code generation and safe execution.
- **🎯 Responsibilities:** 
  - Task classification (code, tool use, reasoning, chat)
  - Dispatches tasks to appropriate handlers
  - Tracks metrics and telemetry
  - Manages downstream services (ModelManagerAgent, UnifiedMemoryReasoningAgent, WebAssistant)
  - Error reporting to central error bus
- **🔗 Interactions:** 
  - Communicates with ModelManagerAgent, UnifiedMemoryReasoningAgent, WebAssistant via ZMQ
  - Uses CircuitBreaker pattern for resilience
- **🧬 Technical Deep Dive:** 
  - Uses sentence-transformer for task classification (with fallback to keyword-based)
  - Maintains metrics (requests, response times, success rates)
  - Embedding cache for fast classification
  - Background thread for metrics reporting
  - Handles requests via `handle_request()`, dispatching to code generation, tool use, reasoning, or chat handlers
- **⚠️ Panganib:** 
  - If embedding model is not available, falls back to less accurate keyword-based classification
  - Potential for resource exhaustion if background threads or subprocesses are not managed
- **📡 Communication Details:** 
  - **🔌 Health Port:** From config, default 8010
  - **🛰️ Port:** From config, default 7010
  - **🔧 Environment Variables:** Reads config via `load_config()`, can be customized
  - **📑 Sample Request:** 
    ```json
    {
      "action": "execute_task",
      "task": { ... }
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses background threads, embedding model (if available), and ZMQ sockets
  - **🔒 Security & Tuning Flags:** CircuitBreaker for downstream services, error bus reporting

---

### 🧠 AGENT PROFILE: GoalManager
- **Main Class:** `GoalManager` (`main_pc_code/agents/goal_manager.py`)
- **Host Machine:** MainPC (default, can be configured)
- **Role:** Manages high-level goals from inception to completion; decomposes goals into tasks, dispatches to agents, monitors progress, and synthesizes results.
- **🎯 Responsibilities:** 
  - Receives and stores goals
  - Breaks down goals into tasks
  - Dispatches tasks to agents (e.g., ModelOrchestrator, AutoGenFramework)
  - Monitors and updates goal/task status
  - Uses central memory for persistence
- **🔗 Interactions:** 
  - Communicates with MemoryClient for persistence
  - Sends tasks to ModelOrchestrator, AutoGenFramework
  - Uses CircuitBreaker for resilience
- **🧬 Technical Deep Dive:** 
  - Maintains in-memory and persistent state for goals and tasks
  - Background threads for task processing and goal monitoring
  - Error reporting via ZMQ PUB to error bus
  - Handles requests via `handle_request()`
- **⚠️ Panganib:** 
  - If memory system is unavailable, may lose state
  - CircuitBreaker prevents repeated failures but may block service
- **📡 Communication Details:** 
  - **🔌 Health Port:** main_port+1 (default **7006**) – inherits BaseAgent default
  - **🛰️ Port:** Default 7005
  - **🔧 Environment Variables:** Reads config via `load_config()`, uses `PC2_IP` for error bus
  - **📑 Sample Request:** 
    ```json
    {
      "action": "set_goal",
      "data": { "description": "Sample goal" }
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses background threads, ZMQ sockets, and SQLite for persistence
  - **🔒 Security & Tuning Flags:** CircuitBreaker for downstream services, error bus reporting

---

### 🧠 AGENT PROFILE: IntentionValidatorAgent
- **Main Class:** `IntentionValidatorAgent` (`main_pc_code/agents/IntentionValidatorAgent.py`)
- **Host Machine:** MainPC (default, can be configured)
- **Role:** Validates user intentions and commands, maintains validation history, implements security checks.
- **🎯 Responsibilities:** 
  - Validates command structure and parameters
  - Maintains SQLite database of validation history
  - Implements security checks for sensitive commands
- **🔗 Interactions:** 
  - Publishes errors to central error bus (ZMQ PUB)
  - Can connect to RequestCoordinator for coordination
- **🧬 Technical Deep Dive:** 
  - Uses SQLite for persistent validation history
  - Background thread for initialization
  - Handles requests via `handle_request()`
  - Sensitive command patterns are configurable
- **⚠️ Panganib:** 
  - If database is unavailable, cannot log or validate history
  - Security depends on completeness of command patterns
- **📡 Communication Details:** 
  - **🔌 Health Port:** main_port+1 (default **5001**) – inherits BaseAgent default
  - **🛰️ Port:** Default 5000 (from config)
  - **🔧 Environment Variables:** Reads config via `load_config()`, uses `PC2_IP` for error bus
  - **📑 Sample Request:** 
    ```json
    {
      "action": "validate_command",
      "command": "delete_file",
      "parameters": { "file_path": "/tmp/test.txt" },
      "user_id": "user1",
      "profile": "admin"
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses SQLite, ZMQ sockets, background threads
  - **🔒 Security & Tuning Flags:** Sensitive command patterns, error bus reporting

---

### 🧠 AGENT PROFILE: NLUAgent
- **Main Class:** `NLUAgent` (`main_pc_code/agents/nlu_agent.py`)
- **Host Machine:** MainPC (default, can be configured)
- **Role:** Analyzes user input and extracts intents and entities.
- **🎯 Responsibilities:** 
  - Pattern-based intent extraction
  - Entity extraction from user text
  - Error reporting to central error bus
- **🔗 Interactions:** 
  - Publishes errors to error bus (ZMQ PUB)
  - Receives requests via ZMQ REP socket
- **🧬 Technical Deep Dive:** 
  - Uses regex patterns for intent extraction
  - Threaded initialization for ZMQ context
  - Handles requests via `_handle_requests()`
- **⚠️ Panganib:** 
  - Pattern-based intent extraction may miss complex intents
  - If ZMQ or error bus is unavailable, may lose error reporting
- **📡 Communication Details:** 
  - **🔌 Health Port:** main_port+1 (default **5559**) – inherits BaseAgent default
  - **🛰️ Port:** Default 5558 (from config)
  - **🔧 Environment Variables:** Reads config via `load_config()`, uses `PC2_IP` for error bus
  - **📑 Sample Request:** 
    ```json
    {
      "action": "analyze",
      "text": "What is the weather today?"
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses regex, ZMQ sockets, background threads
  - **🔒 Security & Tuning Flags:** Error bus reporting

---

### 🧠 AGENT PROFILE: AdvancedCommandHandler
- **Main Class:** `AdvancedCommandHandler` (`main_pc_code/agents/advanced_command_handler.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Extends the custom command handler with advanced features: command sequences, script execution, domain-specific modules, and advanced coordination.
- **🎯 Responsibilities:**
  - Execute multiple commands in sequence
  - Run local Python/Bash/other scripts
  - Load and manage domain-specific command modules
  - Register new command patterns (including Tagalog)
  - Report errors to central error bus
- **🔗 Interactions:**
  - Communicates with Executor Agent, RequestCoordinator, Jarvis Memory Agent via ZMQ
  - Publishes errors to error bus (ZMQ PUB)
- **🧬 Technical Deep Dive:**
  - Inherits from `BaseAgent` and `CustomCommandHandler`
  - Uses ZMQ REQ sockets for Executor and Coordinator
  - Loads domain modules dynamically from `domain_modules/`
  - Tracks running background scripts and sequences
  - Registers command patterns using regex (English and Tagalog)
  - Reports errors to error bus at port 7150
- **⚠️ Panganib:**
  - If Executor/Coordinator is unavailable, command execution may fail
  - Dynamic script execution can be a security risk if not sandboxed
- **📡 Communication Details:**
  - **🔌 Health Port:** main_port+1 (default **5599**) – inherits BaseAgent default
  - **🛰️ Port:** Default 5598 (from config)
  - **🔧 Environment Variables:** Uses `EXECUTOR_HOST`, `PC2_IP` for error bus
  - **📑 Sample Request:**
    ```json
    {
      "action": "execute_command",
      "command": "run_script",
      "parameters": {"script_path": "test.py"}
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses ZMQ sockets, background threads, subprocesses
  - **🔒 Security & Tuning Flags:** Sensitive to script execution permissions, error bus reporting

---
### 🧠 AGENT PROFILE: ChitchatAgent
- **Main Class:** `ChitchatAgent` (`main_pc_code/agents/chitchat_agent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Handles natural conversational interactions, connects to LLMs, maintains context, and integrates with personality engine.
- **🎯 Responsibilities:**
  - Process casual conversation requests
  - Connect to local or remote LLM for responses (default: remote GPT-4o)
  - Maintain conversation history per user
  - Integrate with personality engine
  - Report errors to error bus
- **🔗 Interactions:**
  - Communicates with remote LLM on PC2 (port 5557)
  - Publishes errors to error bus (ZMQ PUB)
  - Health status via PUB socket
- **🧬 Technical Deep Dive:**
  - Inherits from `BaseAgent`
  - Uses ZMQ REP for chitchat, PUB for health, REQ for LLM
  - Conversation history is capped (max 10 turns, 2000 tokens)
  - Formats messages for LLM, supports fallback to local LLM (not yet implemented)
- **⚠️ Panganib:**
  - If LLM is unavailable, fallback is limited
  - Large conversation history may increase memory usage
- **📡 Communication Details:**
  - **🔌 Health Port:** main_port+1 (default **5712**) – inherited & bound by agent
  - **🛰️ Port:** Default 5711 (from config)
  - **🔧 Environment Variables:** Uses `PC2_IP` for error bus
  - **📑 Sample Request:**
    ```json
    {
      "action": "chitchat",
      "text": "Kumusta ka?"
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses ZMQ sockets, background threads, LLM API calls
  - **🔒 Security & Tuning Flags:** Error bus reporting

---
### 🧠 AGENT PROFILE: FeedbackHandler
- **Main Class:** `FeedbackHandler` (`main_pc_code/agents/feedback_handler.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Provides visual and voice confirmation feedback for command execution.
- **🎯 Responsibilities:**
  - Send visual feedback to GUI (PUB socket)
  - Send voice feedback to TTS system (PUB socket)
  - Combined feedback for command execution
  - Report errors to error bus
- **🔗 Interactions:**
  - Publishes to GUI (default port 5578) and voice feedback (port 5574)
  - Uses ErrorPublisher for error bus
- **🧬 Technical Deep Dive:**
  - Inherits from `BaseAgent`
  - Uses ZMQ PUB for GUI and voice
  - Feedback styles (success, warning, error, info, processing)
  - Health check thread for connection status
- **⚠️ Panganib:**
  - If GUI/voice sockets are unavailable, feedback is not delivered
  - Error reporting depends on ErrorPublisher
- **📡 Communication Details:**
  - **🔌 Health Port:** Not explicitly set; uses main port for health/status
  - **🛰️ Port:** Default 5578 (from config)
  - **🔧 Environment Variables:** Uses `PC2_IP` for error bus
  - **📑 Sample Request:**
    ```json
    {
      "type": "visual_feedback",
      "message": "Command executed",
      "status": "success"
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses ZMQ sockets, background threads
  - **🔒 Security & Tuning Flags:** Error bus reporting

---
### 🧠 AGENT PROFILE: Responder
- **Main Class:** `Responder` (`main_pc_code/agents/responder.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Handles TTS (text-to-speech) responses, emotion/voice modulation, and visual feedback for spoken output.
- **🎯 Responsibilities:**
  - Receive TTS requests and generate speech
  - Modulate voice/emotion based on input
  - Show visual feedback overlays
  - Integrate with face recognition and emotion detection
- **🔗 Interactions:**
  - Subscribes to TTS requests (ZMQ SUB)
  - Connects to interrupt handler, TTS services, face recognition
  - Publishes visual feedback
- **🧬 Technical Deep Dive:**
  - Inherits from `BaseAgent`
  - Uses ZMQ SUB for TTS and interrupts
  - Loads TTS models in background thread
  - Supports emotion-to-voice parameter mapping
  - Health monitoring and service discovery
- **⚠️ Panganib:**
  - TTS model loading is resource-intensive
  - If TTS/interrupt/face services are unavailable, response is degraded
- **📡 Communication Details:**
  - **🔌 Health Port:** Not explicitly set; uses main port for health/status
  - **🛰️ Port:** Default 5637 (from config)
  - **🔧 Environment Variables:** Uses config for service addresses
  - **📑 Sample Request:**
    ```json
    {
      "action": "speak",
      "text": "Hello, world!",
      "emotion": "joy"
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses ZMQ sockets, background threads, TTS models
  - **🔒 Security & Tuning Flags:** Secure ZMQ optional, error bus reporting

---
### 🧠 AGENT PROFILE: TranslationService
- **Main Class:** `TranslationService` (`main_pc_code/agents/translation_service.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Central, modular, and robust translation agent for all translation-related features.
- **🎯 Responsibilities:**
  - Translate text between languages (Tagalog, English, others)
  - Detect language and handle Taglish
  - Manage translation cache and session
  - Report errors to error bus
- **🔗 Interactions:**
  - Communicates with NLLB, Google, Streaming, Dictionary, and Pattern engines
  - Publishes errors to error bus
  - Uses CircuitBreaker for resilience
- **🧬 Technical Deep Dive:**
  - Inherits from `BaseAgent`
  - Uses ZMQ sockets for communication
  - Translation cache with LRU and persistence
  - Language detection via langdetect/fasttext
  - Modular engine clients for translation
  - Health monitoring and metrics
- **⚠️ Panganib:**
  - If translation engines are unavailable, falls back to dictionary/patterns
  - Large cache/session may increase memory usage
- **📡 Communication Details:**
  - **🔌 Health Port:** Not explicitly set; uses main port for health/status
  - **🛰️ Port:** From config (default varies)
  - **🔧 Environment Variables:** Uses config for engine addresses
  - **📑 Sample Request:**
    ```json
    {
      "action": "translate",
      "text": "Kamusta ka?",
      "source_lang": "tl",
      "target_lang": "en"
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses ZMQ sockets, background threads, translation engines
  - **🔒 Security & Tuning Flags:** CircuitBreaker, error bus reporting

---
### 🧠 AGENT PROFILE: DynamicIdentityAgent
- **Main Class:** `DynamicIdentityAgent` (`main_pc_code/agents/DynamicIdentityAgent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Manages dynamic persona switching and identity for the system, updating ModelOrchestrator and EmpathyAgent.
- **🎯 Responsibilities:**
  - Switch persona and update system prompt
  - Update EmpathyAgent with new emotional profile
  - Maintain persona configuration and state
  - Report errors to error bus
- **🔗 Interactions:**
  - Communicates with ModelOrchestrator and EmpathyAgent via ZMQ REQ
  - Publishes errors to error bus
  - Connects to RequestCoordinator for coordination
- **🧬 Technical Deep Dive:**
  - Inherits from `BaseAgent`
  - Loads persona config from JSON
  - Uses ZMQ REQ sockets for communication
  - Background threads for initialization and service discovery
- **⚠️ Panganib:**
  - If persona config is missing/corrupt, cannot switch personas
  - If ModelOrchestrator/EmpathyAgent is unavailable, update fails
- **📡 Communication Details:**
  - **🔌 Health Port:** Not explicitly set; uses main port for health/status
  - **🛰️ Port:** Default 5802 (from config)
  - **🔧 Environment Variables:** Uses config for service addresses
  - **📑 Sample Request:**
    ```json
    {
      "action": "switch_persona",
      "persona": "teacher"
    }
    ```
  - **📊 Resource Footprint (baseline):** Uses ZMQ sockets, background threads
  - **🔒 Security & Tuning Flags:** Error bus reporting

---
### 🧠 AGENT PROFILE: EmotionSynthesisAgent (Moved from emotion_system group)
- **Main Class:** `EmotionSynthesisAgent` (`main_pc_code/agents/emotion_synthesis_agent.py`)
- **Host Machine:** MainPC (default, configurable)
- **Role:** Adds emotional nuance to text responses based on specified emotions.
- **🎯 Responsibilities:** 
  - Synthesizes emotional markers in text
  - Adds appropriate interjections, sentence starters, and modifiers
  - Adjusts text based on emotion and intensity
  - Reports errors to error bus
- **🔗 Interactions:** 
  - Receives text synthesis requests
  - Reports errors to error bus
- **🧬 Technical Deep Dive:** 
  - Maintains emotion markers dictionary for different emotions
  - Implements probabilistic text modification based on intensity
  - Tracks metrics for synthesis operations
  - Provides health status reporting
- **⚠️ Panganib:** 
  - Synthesized emotions may not always be appropriate
  - Potential for overuse of emotional markers
  - Limited emotional vocabulary for some emotions
- **📡 Communication Details:** 
  - **🔌 Health Port:** 6643 (explicit)
  - **🛰️ Port:** Default 5643
  - **🔧 Environment Variables:** PC2_IP
- **📝 Note:** This agent has been moved from the **emotion_system** group to the **language_processing** group because it primarily processes and modifies text content based on emotional context, making it more aligned with language processing functionality than core emotion system operations.

---

### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| ModelOrchestrator | ✓ | |
| GoalManager | ✓ | |
| IntentionValidatorAgent | ✓ | |
| NLUAgent | ✓ | |
| AdvancedCommandHandler | ✓ | |
| ChitchatAgent | ✓ | |
| FeedbackHandler | ✓ | |
| Responder | ✓ | |
| TranslationService | ✓ | |
| DynamicIdentityAgent | ✓ | |
| EmotionSynthesisAgent | ✓ | |

---

### Container Grouping Updates

Ang **language_processing** group ay na-optimize para sa containerization:

- **EmotionSynthesisAgent** ay inilipat mula sa **emotion_system** group papunta sa **language_processing** group dahil ito ay pangunahing nagpoproseso ng text content batay sa emotional context, na mas naaangkop sa language processing functionality.

Ang pagbabagong ito ay nagbibigay ng mga sumusunod na benepisyo:
- Mas mahusay na logical grouping batay sa functionality
- Mas mababang network overhead sa pagitan ng mga agents na madalas na nakikipag-communicate
- Mas malinaw na separation of concerns sa pagitan ng emotion detection at text processing
