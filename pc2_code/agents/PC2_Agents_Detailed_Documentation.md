Sige, heto ang inayos na format ng dokumentasyon. Bawat agent ay may malinaw na heading at ang mga mahahalagang teknikal na detalye ay naka-format para madaling basahin.

1. tutoring_service_agent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/core_agents/tutoring_service_agent.py

Purpose & Reasoning:
Nagbibigay ng ZMQ-based service wrapper para sa AdvancedTutoringAgent class, na nag-aalok ng personalized tutoring lessons.

Reasoning: Ang paghihiwalay ng core tutoring logic (AdvancedTutoringAgent) mula sa network communication (TutoringServiceAgent) ay nagpo-promote ng modularity, testability, at reusability. Ang AdvancedTutoringAgent ay maaaring manatiling isang simpleng Python class, habang ang TutoringServiceAgent ang namamahala sa ZMQ complexities. Ang pag-expose nito bilang ZMQ service ay nagpapahintulot sa ibang agents (e.g., Dialogue Manager) na gamitin ang tutoring functionality.

ZMQ Configuration:

Port: 5568 (Constant: TUTORING_PORT)

Reasoning for Port Choice: Ito ang port na napagkasunduan para sa serbisyong ito sa PC2, na na-configure na rin sa system_config.py.

Socket Type: zmq.REP (Reply)

Reasoning: Sumusunod sa standard request-reply pattern, kung saan ang client ay nagpapadala ng request at naghihintay ng tugon. Angkop para sa service-oriented interactions.

Binding: tcp://\*:5568

Reasoning: Nakikinig sa lahat ng available network interfaces sa PC2 sa port 5568, ginagawa itong accessible sa mga clients sa loob ng network ng PC2.

Message Format: JSON

Reasoning: Standard, human-readable, at madaling i-parse. Nagbibigay-daan sa structured data exchange.

Core Logic & Key Components:

TutoringServiceAgent

**init**(self): Ina-initialize ang ZMQ context, REP socket, bina-bind ang socket sa port, at hinahanda ang self.sessions dictionary para i-manage ang mga individual tutoring sessions.

Reasoning for self.sessions: Nagpapahintulot ng multiple, isolated tutoring interactions (bawat isa ay may sariling AdvancedTutoringAgent instance). Ang session state (e.g., current lesson, user progress) ay naka-encapsulate bawat session.

\_handle_request(self, request_data: dict): Sentral na method para sa pagproseso ng mga request.

Supported Actions & Reasoning:

"health_check": Standard endpoint para sa monitoring ng MMA.

Reasoning: Mahalaga para sa system reliability at fault detection.

"start_session" (Requires: session_id, user_profile): Gumagawa ng bagong AdvancedTutoringAgent instance.

Reasoning: Nagsisimula ng bagong tutoring context para sa isang user, base sa kanilang profile (e.g., edad, wika).

"get_lesson" (Requires: session_id): Kumukuha ng lesson mula sa active session.

Reasoning: Pangunahing paraan para makakuha ng educational content.

"submit_feedback" (Requires: session_id, engagement): Nagre-record ng user engagement.

Reasoning: Nagbibigay-daan sa AdvancedTutoringAgent na i-adapt ang difficulty ng mga susunod na lessons.

"get_history" (Requires: session_id): Kumukuha ng lesson history.

Reasoning: Nagbibigay ng paraan para i-review ang mga nakaraang interaksyon at progress.

"stop_session" (Requires: session_id): Naglilinis ng session data.

Reasoning: Mahalaga para sa resource management, lalo na kung maraming sessions ang maaaring mabuksan.

run(self): Ang main event loop na patuloy na nakikinig sa mga requests, pinoproseso ang mga ito, at nagpapadala ng responses.

stop(self): Method para sa graceful shutdown.

if **name** == "**main**": block: Ginagawang direktang executable ang script, namamahala sa startup, at nag-aasikaso ng graceful shutdown (e.g., KeyboardInterrupt).

Memory Interaction:
Ang TutoringServiceAgent mismo ay namamahala ng session-specific memory sa pamamagitan ng AdvancedTutoringAgent instances na naka-store sa self.sessions. Ang bawat AdvancedTutoringAgent instance ay naglalaman ng sarili nitong state (e.g., lesson history, user's current level).

Reasoning: Ang session data ay iniiwang local sa AdvancedTutoringAgent instance para sa mabilis na access at encapsulation. Hindi ito direktang gumagamit ng external memory services (tulad ng contextual-memory-pc2) maliban kung ang AdvancedTutoringAgent mismo ay idinisenyo para gawin ito.

Dependencies:

Python Standard Libraries: zmq, json, logging, time.

Internal: tutoring_agent.AdvancedTutoringAgent (ang core logic provider).

Error Handling:

May error handling para sa ZMQ binding failures sa **init**.

Nagve-validate ng mga required parameters sa \_handle_request.

Sumasalo ng exceptions mula sa ZMQ operations (e.g., JSONDecodeError) at mula sa AdvancedTutoringAgent methods.

Nagbibigay ng structured error responses sa client.

Reasoning: Dinisenyo para maging robust, magbigay ng malinaw na feedback sa clients kapag may error, at maiwasan ang pag-crash ng buong serbisyo dahil sa isolated errors.

Reasoning for Overall Design:

Sumusunod sa common microservice/agent architecture: ang core business logic (AdvancedTutoringAgent) ay hiwalay sa network service layer (TutoringServiceAgent).

Ang session management ay nagbibigay-daan para sa stateful interactions sa loob ng isang ZMQ request-reply model, na karaniwang stateless.

2. self_healing_agent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/self_healing_agent.py

Purpose & Reasoning:

Monitors the health of all other registered agents within the PC2 ecosystem using a heartbeat mechanism.

Detects agent failures through missed heartbeats or exceeding configured resource usage thresholds (CPU, memory).

Attempts automated recovery of failed agents by restarting them using pre-configured start commands.

Scans agent log files for error patterns to identify root causes or recurring issues.

Records detected errors, recovery actions, and system resource snapshots in a persistent SQLite database for later analysis and reporting.

Provides an interface for manual intervention and status queries.

Reasoning: Enhances system resilience and uptime by automating the detection and recovery of failed components. Centralized monitoring and logging simplify diagnostics and maintenance.

ZMQ Configuration:

REP Socket (Requests/Commands):

Port: 5614 (Constant: SELF_HEALING_PORT or similar)

Socket Type: zmq.REP

Binding: tcp://\*:5614

Purpose: Receives commands such as health status requests, manual heartbeat checks, manual recovery triggers, and retrieval of logs.

PUB Socket (Broadcasts/Notifications):

Port: 5616 (Constant: SELF_HEALING_PUB_PORT or similar)

Socket Type: zmq.PUB

Binding: tcp://\*:5616

Purpose: Broadcasts periodic health status updates and notifications about significant events.

Message Format: JSON for both sockets.

Reasoning for Port Choices: Dedicated ports for self-healing functionalities ensure clear communication channels. Using PUB/SUB for status updates allows multiple listeners without direct coupling.

Core Logic & Key Components:

SelfHealingAgent

Manages the overall monitoring, detection, recovery, and reporting lifecycle.

monitor_agents(): Periodically checks heartbeats of registered agents.

recover_agent(agent_id): Attempts to restart a failed agent with exponential backoff.

monitor_system_resources(): Periodically checks system-wide resources using psutil.

scan_agent_logs(): Periodically scans log files for predefined error patterns.

handle_requests(): Processes incoming ZMQ requests on the REP socket.

broadcast_status(): Publishes system health on the PUB socket.

SelfHealingDatabase

Manages all interactions with an SQLite database.

Tables: agent_status, error_records, recovery_actions, system_resource_snapshots.

Key Data Structures: AgentStatus, ErrorRecord, RecoveryAction, SystemResourceSnapshot.

Dependencies:

Standard Python: zmq, json, sqlite3, subprocess, threading, time, logging, os, re.

Third-party: psutil (for system resource monitoring).

Internal: config.system_config, agents.agent_utils.

Error Handling & Logging:

Robust error handling for ZMQ, database, subprocess, and file operations.

Comprehensive logging of all actions, decisions, errors, and state changes to its own dedicated log file.

Configuration (from config.system_config):

ZMQ ports, logging level, database path, resource thresholds, heartbeat timeouts.

List of monitored agents, each with: agent_id, start_command, log_path, criticality.

Usage Examples / Key ZMQ Commands (sent to REP port 5614):

{"action": "get_system_health"}

{"action": "get_agent_status", "agent_id": "translator_agent"}

{"action": "trigger_recovery", "agent_id": "some_agent"}

{"action": "get_error_log", "agent_id": "some_agent", "limit": 10}

{"action": "health_check"}

3. tinyllama_service_enhanced.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/tinyllama_service_enhanced.py

Purpose & Reasoning:

Provides a ZMQ-based service interface to the TinyLlama language model (TinyLlama/TinyLlama-1.1B-Chat-v1.0).

Implements on-demand model loading and automatic unloading after a configurable idle period to efficiently manage VRAM resources.

Designed for integration with a Model Manager Agent (MMA).

Reasoning: This approach allows the system to utilize powerful LLMs like TinyLlama without constantly consuming VRAM. The ZMQ interface provides a standardized way for other agents to request text generation.

ZMQ Configuration:

Port: 5615 (Configurable via system_config.py, defaults to 5615).

Socket Type: zmq.REP (Reply)

Binding: tcp://0.0.0.0:<port>

Message Format: JSON

Core Logic & Key Components:

TinyLlamaService

**init**(self): Initializes ZMQ, sets model/tokenizer to None, configures model name, device, and idle timeout settings.

\_load_model(self): Loads the Hugging Face model and tokenizer, moving it to the configured device. Dynamically imports transformers.

\_unload_model(self): Deletes model/tokenizer references and calls torch.cuda.empty_cache() to free VRAM.

generate_text(self, prompt: str, ...): Ensures model is loaded, generates text, and resets the idle timer.

\_idle_monitoring_thread(self): Runs in a separate thread, periodically checking for idleness to unload the model.

handle_requests(self): Main ZMQ loop handling actions: "generate", "ensure_loaded", "request_unload", "health_check".

run(self): Starts the monitoring thread and the request handling loop.

cleanup(self): Graceful shutdown, ensuring the model is unloaded.

Memory Interaction:

Primary interaction is managing GPU VRAM by loading and unloading the TinyLlama model.

Does not directly interact with other specialized memory agents.

Dependencies:

Python Standard Libraries: zmq, json, time, logging, sys, os, threading, pathlib.

Third-party: torch, transformers (imported dynamically).

Internal: config.system_config.

Error Handling:

Handles ZMQ errors, model loading/unloading exceptions, and generation errors.

Returns structured JSON error responses to the client.

Implements graceful shutdown on KeyboardInterrupt.

Usage Examples / Key ZMQ Commands (Request Format):

Text Generation: {"action": "generate", "prompt": "Translate 'hello world' to Tagalog", "max_tokens": 50}

Ensure Model Loaded: {"action": "ensure_loaded"}

Request Model Unload: {"action": "request_unload"}

Health Check: {"action": "health_check"}

4. enhanced_model_router.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/enhanced_model_router.py

Purpose:
The EnhancedModelRouter acts as a consolidated central intelligence hub for routing model-related requests. It receives a task, understands its nature and context, selects the most appropriate AI model (local or remote), and dispatches the request to the relevant model-serving agent (e.g., Model Manager, Remote Connector).

Reasoning for Consolidation: To streamline agent communication, improve efficiency, enhance contextual awareness by integrating multiple logic points (task classification, memory, reasoning), and centralize routing intelligence for easier management.

ZMQ Configuration:

REP Socket (Requests/Commands):

Port: 5598 (Constant: ZMQ_MODEL_ROUTER_PORT)

Socket Type: zmq.REP

Binding: tcp://\*:5598

PUB Socket (Broadcasts/Notifications):

Port: 5603 (Constant: ZMQ_MODEL_ROUTER_PUB_PORT)

Socket Type: zmq.PUB

Binding: tcp://\*:5603

Message Format: JSON

Core Logic & Key Components:

EnhancedModelRouter

**init**(self, ...): Initializes ZMQ sockets and sets up client connections to other agents:

Model Manager Agent (192.168.1.27:5556)

Contextual Memory Agent (localhost:5596)

Chain of Thought Agent (localhost:5612)

Remote Connector Agent (localhost:5557)

Task Classification: Attempts to import detect_task_type from advanced_router; uses a basic keyword-based fallback if unavailable.

get_context_summary(...): Retrieves context from the Contextual Memory Agent.

use_chain_of_thought(...): Invokes the Chain of Thought Agent for complex reasoning.

select_model(...): Core logic to select the best model based on task type and other factors.

send_to_model_manager(...) / send_to_remote_connector(...): Forwards the request to the appropriate downstream agent.

process_request(...): The main handler that orchestrates the entire routing flow.

get_status(): Provides a detailed status report of the agent's activity.

Memory Interaction:

Primarily interacts with the Contextual Memory Agent to fetch context summaries and record interactions.

Integrates with web_automation.GLOBAL_TASK_MEMORY.

Dependencies:

External Libraries: zmq.

Internal/Project-Specific Modules: advanced_router (optional, with fallbacks), web_automation.GLOBAL_TASK_MEMORY.

Other PC2 Agents (via ZMQ): Model Manager, Contextual Memory, Chain of Thought, Remote Connector.

Error Handling:

Graceful fallback if the advanced_router module is unavailable.

Standard try-except blocks for request handling, returning structured JSON errors.

Comprehensive logging to logs/enhanced_model_router.log.

Usage Example/Flow:

An agent sends a request like {"action": "route", "prompt": "Write a python function...", "use_cot": true} to port 5598.

The EnhancedModelRouter receives it, gets context, detects the task type ("code", "reasoning").

It invokes the Chain of Thought agent.

It selects an appropriate coding model.

It forwards the request to the Model Manager Agent.

The result is returned to the router, which records the interaction and sends the final response back to the original agent.

5. unified_memory_reasoning_agent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/unified_memory_reasoning_agent.py

Purpose:
Acts as the central memory and contextual reasoning hub for the PC2 ecosystem. It manages conversational context, session-specific memory, learns from error patterns, and provides reasoning capabilities based on stored information.

Design & Key Features:

Context Management (ContextManager class):

Employs a dynamic context window with importance scoring to retain the most relevant interactions.

Maintains isolated session histories identified by session_id.

Error Pattern Learning:

Stores structured information about errors and their potential solutions.

Allows agents to query for solutions based on error messages.

Persistence:

Saves session context to individual JSON files (e.g., context_cache/context_UserX_ProjectY.json).

Persists error patterns to a dedicated JSON file.

Features periodic autosaving.

ZMQ Communication:

Main REP Socket: Listens on port 5596 for primary requests.

Health Check REP Socket: Responds on port 5597.

Handles requests in separate threads for non-blocking operations.

Core Actions (via ZMQ):

add_interaction: Adds a new user query or system response to a session's context.

get_context: Retrieves the relevant context for a session.

add_error_pattern: Registers a new error pattern and its solution.

get_error_solution: Queries for a solution given an error message.

get_status: Reports operational status.

clear_session_history: Clears a session's history.

health_check: Standard health probe.

Dependencies:

Standard Library: zmq, json, os, threading, time, logging, re, datetime, collections.deque, pathlib.

Third-party: numpy (potentially).

Internal: config.system_config.

Error Handling:

Extensive try/except blocks in request handling.

Returns structured JSON error responses to clients.

Detailed logging of exceptions with tracebacks.

6. unified_web_agent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/unified_web_agent.py

Purpose:
Acts as the comprehensive web interaction and information gathering service. It unifies capabilities for autonomous web assistance, advanced web scraping (static and dynamic), browser automation, and content summarization.

Design & Key Features:

Multi-role Unification: Consolidates functionalities of previous web-related agents.

Proactive & Reactive Gathering: Can execute specific tasks on request or autonomously search for information based on detected needs.

Advanced Web Scraping: Uses requests and BeautifulSoup for static content; can be integrated with browser automation tools for dynamic content.

Browser Automation: Can navigate, fill forms, and interact with page elements.

Caching & Persistence:

Caches fetched web pages locally (cache/web_agent/).

Uses an SQLite database (cache/web_agent/web_agent_cache.sqlite) to log history and cache metadata.

Integration: Connects with Model Manager Agent (for summarization) and potentially AutoGen/Executor agents.

ZMQ Communication:

Main REP Socket: Listens on port 5604.

Health Check REP Socket: Responds on port 5605.

Core Actions (via ZMQ):

navigate: Opens a URL.

scrape_content: Scrapes specific content from a URL.

fill_form: Fills and submits a web form.

proactive_info_gathering: Initiates an autonomous search.

health_check: Standard health probe.

Dependencies:

Standard Library: zmq, json, os, threading, time, logging, sqlite3, requests.

Third-party: pandas, bs4 (BeautifulSoup4).

Internal: config.system_config, web_automation.GLOBAL_TASK_MEMORY.

Error Handling:

Defensive checks for required fields in requests.

Structured JSON error responses for failures.

Comprehensive try/except blocks for network, parsing, and automation errors.

7. remote_connector_agent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/remote_connector_agent.py

Purpose:
Serves as a centralized client and gateway for interacting with various remote and locally-hosted LLMs (e.g., Ollama, Deepseek). It provides a unified interface for other agents, abstracting away API protocols and authentication.

Design & Key Features:

Unified Model Interface: Offers a consistent way to call different models.

API Abstraction: Hides the complexity of individual model API calls.

Response Caching: Implements a local file-based cache (cache/model_responses/) to improve performance and reduce costs. Cache TTL is configurable.

Integration with Model Manager Agent (MMA): Connects to the MMA to get real-time status of models and can operate in a "standalone mode" if MMA is unavailable.

ZMQ Communication:

REP Socket (Receiver): Listens on port 5557.

REQ Socket (to MMA): Connects to the MMA on port 5556 to query model status.

SUB Socket (from MMA): Subscribes to model status updates from the MMA.

Core Actions (via ZMQ):

generate: Requests text generation from a specified model.

Parameters: model, prompt, system_prompt (optional), temperature (optional), use_cache (optional).

check_status: Checks the availability of a specific model.

Dependencies:

Standard Library: zmq, json, time, logging, threading, requests, hashlib.

Internal: config.system_config.

Error Handling:

Handles API errors from external services gracefully.

Manages ZMQ communication errors and timeouts.

Provides structured JSON error responses.

Includes fallback mechanisms if a model is unavailable or an API call fails.

8. advanced_router.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/advanced_router.py

Purpose:
Provides a set of utility functions for intelligent task classification. It analyzes natural language prompts to determine the task type (e.g., coding, reasoning, factual question), which is then used by other agents like the EnhancedModelRouter to select the most appropriate AI model.

Design & Key Features:

Task Type Detection (detect_task_type function):

Uses a combination of keyword matching, regular expression patterns (for code), and heuristics to classify a prompt.

Has a priority-based system for tie-breaking and defaults to a general type.

Model Capability Mapping (map_task_to_model_capabilities function):

Maps a detected task type to a list of required model capabilities (e.g., "code-generation").

Configurable: Relies on configurable dictionaries (TASK_KEYWORDS) and patterns (CODE_PATTERNS) that can be extended.

Core Functions:

detect_task_type(prompt: str) -> str: Analyzes the prompt and returns the classified task type.

map_task_to_model_capabilities(task_type: str) -> List[str]: Takes a task type and returns a list of required model capabilities.

Dependencies:

Standard Library: re, logging.

Internal: web_automation (for GLOBAL_TASK_MEMORY).

Notes:

This is a utility module, not a standalone agent with a ZMQ socket. It is designed to be imported by other agents.

9. consolidated_translator.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/consolidated_translator.py

Purpose:
Serves as a robust, multi-engine translation service, primarily focusing on Tagalog-to-English. It uses a pipeline of different translation engines, local dictionaries, and advanced features like caching and session management to provide reliable translations.

Design & Key Features:

ZMQ Server (TranslatorServer class): Listens on port 5563 for translation requests.

Translation Pipeline (TranslationPipeline class):

Orchestrates translation through a sequence of engines with fallback logic.

Supported Engines (in order of priority):

Dictionary Engine: Uses predefined dictionaries and regex for common commands and phrases.

NLLB Engine: Interfaces with a Facebook NLLB model service (via ZMQ).

Phi Engine: Interfaces with a Phi language model service (via HTTP).

Google Engine: Uses Google Translate API via the RemoteConnectorAgent.

Translation Cache (TranslationCache class): Stores successful translations to avoid redundant processing.

Session Management (SessionManager class): Maintains a history of translations for individual user sessions.

Core Actions (via ZMQ):

translate:

Parameters: action, text, source_lang, target_lang, session_id (optional).

Response: JSON object with status, original text, translated text, engine used, etc.

health_check: Provides a detailed status report of the service and its engines.

Dependencies:

Standard Library: os, sys, json, time, zmq, logging, re, requests, datetime.

Error Handling:

Gracefully handles failures of individual translation engines and falls back to the next in priority.

Provides structured JSON error responses.

10. digital_twin_agent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/digital_twin_agent.py.DEPRECATED

Status: DEPRECATED/INACTIVE

Purpose (Deprecated):
The Digital Twin Agent was responsible for creating, managing, and persisting "digital twins" for users or entities within the PC2 ecosystem.

ZMQ Configuration (Deprecated):

Default Port: 5597

Port Conflict Resolution: Attempted alternative ports (7597-7601) if the default was in use.

Note: This agent is no longer active. All references to port 5597 now likely pertain to the UnifiedMemoryReasoningAgent's health check port.

11. filesystem_assistant_agent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/filesystem_assistant_agent.py

Purpose:
Provides a centralized, thread-safe ZMQ service to allow other agents to perform controlled filesystem operations. It acts as a secure and managed gateway for interacting with the file system.

Design & Key Features:

ZMQ Server: Operates a zmq.REP socket, typically on port 5606.

Thread Safety: Uses a threading.Lock() to serialize access to filesystem operations, preventing race conditions.

JSON Communication: All requests and responses are structured in JSON.

Security: Implements path validation to prevent directory traversal attacks and provides a controlled interface with detailed audit logging.

Supported Filesystem Operations:

list_directory

read_file / write_file

delete_file / delete_directory

file_exists / directory_exists

get_file_info

create_directory

move_item / copy_item

health_check

Dependencies:

Python Standard Libraries: zmq, json, os, threading, logging, shutil, pathlib, datetime.

Design Rationale:
Designed for modularity, security, and maintainability. It encapsulates filesystem logic, centralizes security controls, and simplifies the codebase of other agents by providing a robust, unified interface for all file operations.

12. AgentTrustScorer.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/AgentTrustScorer.py

Key Highlights: Centralized trust scoring, SQLite-backed, ZMQ REP interface, tracks agent/model success rates for adaptive selection.

Purpose & Reasoning:
Nagbibigay ng centralized trust scoring system para sa mga AI models/agents sa PC2 ecosystem. Ginagamit ito para mag-log, mag-track, at mag-evaluate ng performance ng bawat model/agent batay sa kanilang success/failure rates.

Reasoning: Ang trust scoring ay mahalaga para sa adaptive model selection at system reliability.

ZMQ Configuration:

Port: 5626 (Constant: TRUST_SCORER_PORT)

Socket Type: zmq.REP

Message Format: JSON

Core Logic:

AgentTrustScorer class: Manages a ZMQ REP socket and an SQLite database (agent_trust_scores.db).

Actions: log_interaction, get_score, reset_score.

Trust Score Calculation: Based on the ratio of successful vs. total interactions.

13. CognitiveModelAgent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/CognitiveModelAgent.py

Key Highlights: Manages a graph-based belief system (NetworkX), ZMQ REP interface, supports dynamic knowledge representation and reasoning.

Purpose & Reasoning:
Nag-e-embed ng cognitive modeling capabilities. Nagmamanage ng "belief system" (isang knowledge graph) para i-model ang knowledge, adaptation, at reasoning.

Reasoning: Pinapahintulutan ang advanced reasoning at dynamic adaptation ng agent behavior batay sa isang evolving knowledge graph.

ZMQ Configuration:

Port: 5641

Socket Type: zmq.REP

Message Format: JSON

Core Logic:

CognitiveModelAgent class: Manages a ZMQ REP socket and a belief system using a networkx.DiGraph.

Actions: add_belief, revise_belief, query_belief.

Memory: The belief system is stored in-memory.

14. DreamWorldAgent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/DreamWorldAgent.py

Key Highlights: Simulates hypothetical scenarios using Monte Carlo Tree Search (MCTS), ZMQ REP interface, for planning and creative reasoning.

Purpose & Reasoning:
Nagmo-model ng hypothetical/"dream" scenarios para sa simulation at planning. Gumagamit ng Monte Carlo Tree Search (MCTS) para mag-explore ng possible future states.

Reasoning: Nakakatulong sa advanced scenario planning at creative ideation.

ZMQ Configuration:

Socket Type: zmq.REP

Message Format: JSON

Core Logic:

DreamWorldAgent class: Manages a ZMQ REP socket and MCTS logic.

MCTSNode class: Represents nodes in the search tree.

Actions: Receives simulation/planning requests.

15. DreamingModeAgent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/DreamingModeAgent.py

Key Highlights: Background memory replay and insight generation, ZMQ REP interface, connects to EpisodicMemoryAgent and EnhancedModelRouter.

ZMQ Configuration:

Port: 5640

Socket Type: zmq.REP

Dependencies (Connects to):

EpisodicMemoryAgent (port 5596)

EnhancedModelRouter (port 5598)

Core Logic:

DreamingModeAgent class: Manages a ZMQ REP socket and a background "dreaming" thread.

\_get_random_memories: Kumukuha ng random memories mula sa EpisodicMemoryAgent para sa replay at insight generation.

EpisodicMemoryAgent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/EpisodicMemoryAgent.py

Key Highlights: Manages event-based history in SQLite, ZMQ REP interface, crucial for personalization and context.

Purpose & Reasoning:
Nagma-manage ng episodic memory (event-based history) para sa mga agents/users. Nag-i-store ng session data, summaries, at context sa isang SQLite database.

Reasoning: Mahalaga para sa personalization, context persistence, at long-term adaptation.

ZMQ Configuration:

Port: 5629

Socket Type: zmq.REP

Message Format: JSON

Core Logic:

EpisodicMemoryAgent class: Manages a ZMQ REP socket and an SQLite database (episodic_memory.db).

Actions: store_episode, get_history, summarize_episode.

16. LearningAdjusterAgent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/LearningAdjusterAgent.py

Key Highlights: Adapts learning strategies based on performance/trust, ZMQ REP interface, interacts with multiple other agents.

ZMQ Configuration:

Port: 5634

Socket Type: zmq.REP

Dependencies (Connects to):

PerformanceLoggerAgent (5632)

AgentTrustScorer (5626)

LearningAgent (5633)

Core Logic:

LearningAdjusterAgent class: Manages a ZMQ REP socket and a background analysis thread.

\_analyze_performance: Periodically analyzes performance and trust data to adjust learning strategies.

PerformanceLoggerAgent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/PerformanceLoggerAgent.py

Key Highlights: Logs and manages performance metrics in SQLite, ZMQ REP interface, thread-safe, includes data cleanup.

Purpose & Reasoning:
Naglo-log at nagma-manage ng performance metrics para sa mga agents/models sa isang thread-safe na paraan.

Reasoning: Mahalaga para sa monitoring, debugging, at adaptive optimization ng system.

ZMQ Configuration:

Port: 5632

Socket Type: zmq.REP

Message Format: JSON

Core Logic:

PerformanceLoggerAgent class: Manages a ZMQ REP socket, an SQLite database (performance_metrics.db), and a background thread for cleaning up old data.

17. got_tot_agent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/got_tot_agent.py

Key Highlights: Implements Graph/Tree-of-Thought (GoT/ToT) reasoning, ZMQ REP interface, uses a Hugging Face transformer model (e.g., microsoft/phi-2) for multi-step problem-solving.

Purpose & Reasoning:
Provides advanced reasoning by constructing a tree of thought processes, allowing for exploration of multiple reasoning paths, evaluation of intermediate steps, and selection of the most promising solution.

Reasoning: GoT/ToT can lead to more robust and explainable solutions for complex queries.

ZMQ Configuration:

Port: 5646

Socket Type: zmq.REP

Message Format: JSON

Core Logic:

GoTToTAgent class: Manages a ZMQ REP socket and loads a reasoning model (e.g., microsoft/phi-2).

Node class: Represents a node in the reasoning tree.

reason: Orchestrates the GoT/ToT process by expanding a tree of possibilities, scoring them, and tracing the best path.

18. local_fine_tuner_agent.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/local_fine_tuner_agent.py

Key Highlights: ZMQ REP agent for local model fine-tuning, supports full fine-tuning and specialized few-shot learning with LoRA. Manages training jobs in threads.

Purpose & Reasoning:
Provides a service to fine-tune Hugging Face models locally. It can handle full fine-tuning jobs and offers a "few-shot learning" capability for rapid adaptation using PEFT/LoRA.

Reasoning: Local fine-tuning allows for model customization without relying on external services. Running jobs in threads keeps the agent responsive.

ZMQ Configuration:

Port: 5622

Socket Type: zmq.REP

Message Format: JSON

Core Logic:

LocalFineTunerAgent class: Manages a ZMQ REP socket and a dictionary of active_jobs.

trigger_few_shot_learning: Quickly adapts a model (e.g., microsoft/phi-3-mini) to a small set of examples using LoRA.

\_run_training_job: Runs a full fine-tuning job in a separate thread.

Actions: start_finetune, get_status, trigger_few_shot.

19. memory_decay_manager.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/memory_decay_manager.py

Key Highlights: Manages memory decay and consolidation by interacting with UnifiedMemoryReasoningAgent (UMRA). Runs periodic decay cycles.

Purpose & Reasoning:
Implements a memory decay mechanism to manage the relevance of stored information over time. It periodically reduces the "freshness_score" of memories in UMRA and handles consolidation.

Reasoning: Prevents memory overload, prioritizes relevant information, and enables more realistic long-term memory management.

ZMQ Configuration:

REQ Socket (to UMRA): Connects to tcp://localhost:5596.

REP Socket (for queries): Listens on port 5624.

Core Logic:

MemoryDecayManager class: Manages ZMQ sockets and a background monitoring thread.

\_run_decay_cycle: Fetches all memories from UMRA, calculates a new freshness_score based on age and decay rate, and sends the updated memories back.

\_monitor_memories: Periodically calls the decay cycle.

20.Self_training_orchestrator.py

File Path: \_PC2 SOURCE OF TRUTH LATEST/self_training_orchestrator.py

Key Highlights: ZMQ REP agent that orchestrates fine-tuning jobs by communicating with LocalFineTunerAgent. Manages and monitors training job lifecycles.

Purpose & Reasoning:
Acts as a high-level manager for initiating and tracking self-training tasks. It delegates the actual training to the LocalFineTunerAgent and monitors progress.

Reasoning: Separating orchestration from execution allows for a cleaner architecture and more complex future workflows.

ZMQ Configuration:

REP Socket (for requests): Listens on port 5621.

REQ Socket (to LocalFineTunerAgent): Connects to tcp://localhost:5622.

Core Logic:

SelfTrainingOrchestrator class: Manages ZMQ sockets and a dictionary of training_jobs.

\_monitor_jobs: A background thread that periodically checks the status of running jobs by querying the LocalFineTunerAgent.

Actions: trigger_finetune, get_job_status, list_jobs.
