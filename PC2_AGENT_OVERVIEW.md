### PC2 Subsystem: Integration Layer Agents

#### Agent: TieredResponder
- **Purpose:** To provide a sophisticated, multi-layered response strategy, selecting from different response generators based on the request's complexity and real-time system resources.
- **Core Logic/Features:** The agent categorizes incoming queries into `'instant'`, `'fast'`, and `'deep'` tiers based on regex pattern matching. It has an internal `ResourceManager` class that uses `psutil` and `torch` to monitor CPU, RAM, and GPU load, and will delay processing if thresholds are exceeded. It uses `asyncio` for handling response generation.
- **Health Check:** Listens for synchronous health checks on a ZMQ REP socket. It also runs a background thread (`monitor_health`) that periodically broadcasts its health status (including resource stats and queue size) on a ZMQ PUB socket.
- **Error Handling:** Uses a central `error_bus` (ZMQ PUB socket) to report exceptions from its core loops, such as health monitoring or request processing failures.
- **Configuration/Parameters:** `host`, `port` (7100), `required: true`. Inherits global settings. Uses multiple ports defined in the config for REP, PUSH, and PUB sockets.
- **Inter-Agent Communication:** It receives requests on a ZMQ REP socket and sends responses on a ZMQ PUSH socket, allowing for an asynchronous response pattern. It also broadcasts health status on a ZMQ PUB socket.
- **Dependencies:** None listed, but implicitly depends on model services to handle `'fast'` and `'deep'` responses.

#### Agent: AsyncProcessor
- **Purpose:** To handle long-running or resource-intensive tasks asynchronously, using a priority-based queueing system.
- **Core Logic/Features:** Implements a `TaskQueue` class which contains separate `deque` objects for `'high'`, `'medium'`, and `'low'` priority tasks. It has its own `ResourceManager` to check system load before dequeuing a task. It also tracks detailed statistics on task success/failure rates and processing times.
- **Health Check:** Responds to synchronous health checks on its REP socket. It also runs a background health monitoring thread that broadcasts detailed status (including queue stats) on a ZMQ PUB socket.
- **Error Handling:** Reports all exceptions during task processing or health monitoring to a central `error_bus`.
- **Configuration/Parameters:** `host`, `port` (7101), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Uses a ZMQ REP socket to receive tasks and return an immediate acknowledgement. It uses a PUSH socket for fire-and-forget task submission and a PUB socket to broadcast health.
- **Dependencies:** None listed.

#### Agent: CacheManager
- **Purpose:** Provides a centralized caching service backed by Redis to store and retrieve frequently accessed data, reducing latency.
- **Core Logic/Features:** The agent is a wrapper around a Redis client. It uses a structured caching approach, with a pre-defined `cache_config` that specifies TTLs and priorities for different `cache_type`s (e.g., `nlu_results`, `model_decisions`, `memory`). It runs a background maintenance thread (`_run_maintenance`) for periodic stats logging.
- **Health Check:** Inherits from `BaseAgent` and uses its standard ZMQ REQ/REP health check mechanism. The health status (`_get_health_status`) is directly tied to the availability of the Redis connection.
- **Error Handling:** Reports all Redis connection errors or operational failures to the central `error_bus`.
- **Configuration/Parameters:** `host`, `port` (7102), `required: true`. It is configured via environment variables for Redis connection details (`REDIS_HOST`, `REDIS_PORT`, etc.).
- **Inter-Agent Communication:** Inherits from `BaseAgent` and uses its `handle_request` method as a dispatcher for a rich API supporting actions like `get`, `put`, `invalidate`, and `flush` for different cache types.
- **Dependencies:** None listed, but has a hard dependency on a running Redis server.

#### Agent: PerformanceMonitor
- **Purpose:** To aggregate application-level performance metrics from all other services and broadcast them for real-time monitoring and alerting.
- **Core Logic/Features:** Its primary role is to act as a data aggregator. It exposes a `log_metric` action for other agents to push metrics like `response_times`, `error_counts`, and `queue_sizes`. It has a built-in alerting mechanism that checks incoming data against `ALERT_THRESHOLDS` and will mark its own status as `'degraded'` if any are breached. It uses `numpy` for statistical calculations.
- **Health Check:** It is a monitoring agent itself. It broadcasts its own health status on a dedicated ZMQ PUB socket via the `_monitor_health` background thread.
- **Error Handling:** Reports errors from its own broadcasting and monitoring loops to the central `error_bus`.
- **Configuration/Parameters:** `host`, `port` (7103), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** This agent is primarily a **publisher**. It runs two background threads, `_broadcast_metrics` and `_monitor_health`, which continuously send data out on two different ZMQ PUB sockets. Its REP socket is for receiving metric logs and serving alert data, not for its primary monitoring function.
- **Dependencies:** None listed.

---

### PC2 Subsystem: Core Agents

#### Agent: DreamWorldAgent
- **Purpose:** Simulates experiences and generates synthetic data during system downtime, a process referred to as "dreaming," to facilitate offline learning and system improvement.
- **Core Logic/Features:** This agent is activated during idle periods. It uses existing knowledge and memory to generate novel scenarios, conversations, or problems. These simulations can be used as training data for other agents, allowing the system to learn without constant real-world interaction.
- **Health Check:** Listens on port `7104`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Manages complex state for simulations and logs errors encountered during data generation.
- **Configuration/Parameters:** `host`, `port` (7104), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Relies heavily on the `UnifiedMemoryReasoningAgent` to access and manipulate the system's knowledge base to create its simulations. Its output is likely consumed by the `LearningAgent`.
- **Dependencies:** `UnifiedMemoryReasoningAgent`.

#### Agent: UnifiedMemoryReasoningAgent
- **Purpose:** A cornerstone of the PC2 memory system, combining memory retrieval with reasoning capabilities to answer complex queries.
- **Core Logic/Features:** This agent doesn't just retrieve data; it reasons over it. It can synthesize information from multiple memory sources, draw inferences, and provide answers to queries that require understanding relationships within the data. It's a "unified" agent, suggesting it sits atop other, more specialized memory agents.
- **Health Check:** Listens on port `7105`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Must handle errors from underlying memory systems and gracefully fail on queries it cannot resolve.
- **Configuration/Parameters:** `host`, `port` (7105), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** A central hub for memory. It is used by nearly all agents that need to access or reason about the system's memory, including `DreamWorldAgent`, `EpisodicMemoryAgent`, and `MemoryManager`. It uses `CacheManager` to improve performance.
- **Dependencies:** `CacheManager`.

#### Agent: EpisodicMemoryAgent
- **Purpose:** Manages the memory of specific events or "episodes" in the AI's experience, providing a timeline of past interactions.
- **Core Logic/Features:** Stores sequences of events in chronological order. This allows the system to recall specific conversations or interactions, which is crucial for context and learning from past experiences.
- **Health Check:** Listens on port `7106`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Manages the persistence and retrieval of sequential data.
- **Configuration/Parameters:** `host`, `port` (7106), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Works under the `UnifiedMemoryReasoningAgent`, which orchestrates access to this and other memory types. `LearningAgent` and `ExperienceTracker` are key consumers of its data.
- **Dependencies:** `UnifiedMemoryReasoningAgent`.

#### Agent: LearningAgent
- **Purpose:** Responsible for the actual process of learning by updating models or knowledge based on new data or experiences.
- **Core Logic/Features:** This agent takes processed data (e.g., from `DreamWorldAgent` or `EpisodicMemoryAgent`) and uses it to improve the system. This could involve initiating model fine-tuning, updating a knowledge graph, or adjusting internal parameters.
- **Health Check:** Listens on port `7107`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Must handle errors during the learning process and ensure that failed updates do not corrupt the system.
- **Configuration/Parameters:** `host`, `port` (7107), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Consumes data from `EpisodicMemoryAgent`. It is the "hands" of the learning system, carrying out the updates.
- **Dependencies:** `EpisodicMemoryAgent`.

#### Agent: TutoringAgent
- **Purpose:** Provides a guided, interactive learning experience for users, acting as a specialized tutor.
- **Core Logic/Features:** This agent likely has a curriculum or a set of learning goals. It can present information, ask questions, and adapt its teaching style based on user responses.
- **Health Check:** Listens on port `7108`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Manages the state of a tutoring session.
- **Configuration/Parameters:** `host`, `port` (7108), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** A high-level application agent. It would interact with memory and reasoning agents to access its teaching material and track user progress.
- **Dependencies:** None listed.

#### Agent: KnowledgeBaseAgent
- **Purpose:** Manages the system's long-term, factual knowledge base.
- **Core Logic/Features:** Provides a structured database (likely a graph or vector database) for storing and retrieving factual information. It is focused on providing the "what" (facts) rather than the "when" (episodes).
- **Health Check:** Listens on port `7109`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Manages database connections and query errors.
- **Configuration/Parameters:** `host`, `port` (7109), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Provides factual data to the `UnifiedMemoryReasoningAgent`. Uses `CacheManager` to speed up frequent queries.
- **Dependencies:** `CacheManager`.

#### Agent: MemoryManager
- **Purpose:** Manages the lifecycle of data within the memory system, including consolidation, archiving, and forgetting.
- **Core Logic/Features:** This agent performs memory maintenance. It might move memories between different tiers (e.g., from short-term to long-term), summarize old episodes, or discard irrelevant information to keep the memory system efficient.
- **Health Check:** Listens on port `7110`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Performs background maintenance tasks.
- **Configuration/Parameters:** `host`, `port` (7110), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Works closely with `UnifiedMemoryReasoningAgent` to get a view of the entire memory landscape and execute its management tasks.
- **Dependencies:** `UnifiedMemoryReasoningAgent`.

#### Agent: ContextManager
- **Purpose:** To build and maintain the active context for the current task or conversation.
- **Core Logic/Features:** This agent assembles all the relevant information needed to process a request. It pulls data from different memory agents (`SessionMemory`, `KnowledgeBase`, `EpisodicMemory`) to create a comprehensive contextual snapshot.
- **Health Check:** Listens on port `7111`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Manages the assembly of context data from various sources.
- **Configuration/Parameters:** `host`, `port` (7111), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** A critical pre-processing step. It is likely called by a task router before a request is sent to a reasoning or response agent. It is orchestrated by `MemoryManager`.
- **Dependencies:** `MemoryManager`.

#### Agent: ExperienceTracker
- **Purpose:** Tracks and evaluates the outcomes of the AI's actions to create feedback for learning.
- **Core Logic/Features:** This agent observes the results of the system's actions. If an action was successful, it reinforces the pathway that led to it. If it failed, it records the failure, providing crucial data for the `LearningAgent`.
- **Health Check:** Listens on port `7112`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified.
- **Configuration/Parameters:** `host`, `port` (7112), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Consumes data from `EpisodicMemoryAgent` to understand what actions were taken and what the results were. It provides feedback to the learning system.
- **Dependencies:** `EpisodicMemoryAgent`.

#### Agent: ResourceManager
- **Purpose:** To manage and allocate hardware resources (CPU, GPU, memory) for PC2 agents.
- **Core Logic/Features:** Monitors the resource usage of all agents on PC2. It can be used to enforce resource limits, prioritize tasks based on available resources, and prevent system overload.
- **Health Check:** Listens on port `7113`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified.
- **Configuration/Parameters:** `host`, `port` (7113), `required: true`. Inherits global settings, particularly `resource_limits`.
- **Inter-Agent Communication:** A system-level utility that can be queried by `TaskScheduler` to make decisions about when and where to run a task.
- **Dependencies:** None listed.

#### Agent: HealthMonitor
- **Purpose:** A dedicated agent for monitoring the health and status of all other PC2 services.
- **Core Logic/Features:** Actively polls the health check endpoints of all other agents listed in the configuration. It aggregates this status information to provide a single view of the PC2 subsystem's health.
- **Health Check:** Listens on port `7114`. Its own health is critical.
- **Error Handling:** Not specified. Must be highly resilient and clearly report which services are unhealthy.
- **Configuration/Parameters:** `host`, `port` (7114), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Polls every other PC2 agent. It provides its aggregated report to the main PC's `ObservabilityHub` and the local `RCAAgent` (Root Cause Analysis Agent).
- **Dependencies:** None listed.

#### Agent: TaskScheduler
- **Purpose:** To schedule and dispatch tasks to other agents based on priority, dependencies, and resource availability.
- **Core Logic/Features:** Manages a queue of tasks. Unlike a simple processor, a scheduler understands task dependencies (e.g., task B cannot start until task A is complete). It decides the order of execution.
- **Health Check:** Listens on port `7115`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Must handle failed tasks and deadlocks in the task dependency graph.
- **Configuration/Parameters:** `host`, `port` (7115), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** A central orchestration agent. It dispatches jobs to workers like `AsyncProcessor`. It may query `ResourceManager` before scheduling.
- **Dependencies:** `AsyncProcessor`.

---

### PC2 Subsystem: ForPC2 Agents (Specialized Services)

#### Agent: AuthenticationAgent
- **Purpose:** To handle user authentication and manage security sessions.
- **Core Logic/Features:** Provides a secure endpoint for user login and session validation. It ensures that only authorized users can access the system or specific features.
- **Health Check:** Listens on port `7116`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Must securely handle authentication failures and invalid session tokens.
- **Configuration/Parameters:** `host`, `port` (7116), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Acts as a security gateway. Other agents would query it to validate a user's session or permissions before performing a sensitive action.
- **Dependencies:** None listed.

#### Agent: UnifiedErrorAgent
- **Purpose:** A centralized service for aggregating, logging, and processing error reports from all other PC2 agents.
- **Core Logic/Features:** Subscribes to an error bus where other agents publish their errors. It logs these errors in a structured format and can trigger alerts or other automated responses (like notifying the `SelfHealingAgent`).
- **Health Check:** Listens on port `7117`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. As the central error handler, its own reliability is critical.
- **Configuration/Parameters:** `host`, `port` (7117), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Receives error messages from all other PC2 agents. It provides data to monitoring and analysis agents.
- **Dependencies:** None listed.

#### Agent: UnifiedUtilsAgent
- **Purpose:** Provides a set of common utility functions as a shared service to reduce code duplication across other agents.
- **Core Logic/Features:** Exposes common, stateless functions that might be needed by multiple agents, such as data format conversions, complex calculations, or text processing routines.
- **Health Check:** Listens on port `7118`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified.
- **Configuration/Parameters:** `host`, `port` (7118), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** A shared library exposed as a service. It can be called by any other agent that needs its functions.
- **Dependencies:** None listed.

#### Agent: ProactiveContextMonitor
- **Purpose:** Actively monitors the system's context to identify opportunities for proactive interaction.
- **Core Logic/Features:** This agent observes the user's actions and the system's state via the `ContextManager`. If it detects a pattern or a situation where the AI could helpfully interject (e.g., the user seems stuck on a task), it can trigger a proactive response.
- **Health Check:** Listens on port `7119`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified.
- **Configuration/Parameters:** `host`, `port` (7119), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Consumes data from the `ContextManager`. When it decides to act, it likely sends a command to an orchestration agent like `TaskScheduler`.
- **Dependencies:** `ContextManager`.

#### Agent: SystemDigitalTwin
- **Purpose:** To maintain a real-time model of the PC2 subsystem's state, acting as the local source of truth.
- **Core Logic/Features:** This agent serves a similar role to the main system's `SystemDigitalTwin`, but it is scoped to PC2. It tracks the status, configuration, and health of all PC2 agents.
- **Health Check:** Listens on port `7120`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Must reliably maintain the state of the subsystem.
- **Configuration/Parameters:** `host`, `port` (7120), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** A central hub for PC2. It is queried by almost every agent for service discovery and configuration information. It synchronizes its state with the main system's `SystemDigitalTwin`.
- **Dependencies:** None listed.

#### Agent: RCAAgent (Root Cause Analysis Agent)
- **Purpose:** To automatically diagnose the root cause of failures within the PC2 subsystem.
- **Core Logic/Features:** When the `HealthMonitor` reports a failure, this agent is triggered. It gathers logs and metrics from multiple sources (including `PerformanceMonitor` and `UnifiedErrorAgent`) to try and pinpoint the original cause of the problem, going beyond just identifying the symptom.
- **Health Check:** Listens on port `7121`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified.
- **Configuration/Parameters:** `host`, `port` (7121), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Consumes data from `HealthMonitor`. Its analysis can be used by `SelfHealingAgent` to perform a targeted fix.
- **Dependencies:** `HealthMonitor`.

---

### PC2 Subsystem: Additional Core Agents

#### Agent: AgentTrustScorer
- **Purpose:** To evaluate the reliability and trustworthiness of different agents or data sources.
- **Core Logic/Features:** This agent maintains a trust score for other agents. The score might be based on historical performance, success rate, and error frequency. This allows the system to prefer more reliable agents over less reliable ones.
- **Health Check:** Listens on port `7122`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified.
- **Configuration/Parameters:** `host`, `port` (7122), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Provides trust scores to decision-making agents like `TaskScheduler` or `AdvancedRouter`.
- **Dependencies:** None listed.

#### Agent: FileSystemAssistantAgent
- **Purpose:** To provide a natural language interface for interacting with the file system.
- **Core Logic/Features:** Allows the user to perform file operations (e.g., "find my presentation from last week," "delete all temporary files") using commands in plain English.
- **Health Check:** Listens on port `7123`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Must handle file system errors (e.g., file not found, permission denied) gracefully.
- **Configuration/Parameters:** `host`, `port` (7123), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** A high-level application agent.
- **Dependencies:** None listed.

#### Agent: RemoteConnectorAgent
- **Purpose:** Acts as the primary bridge for communication between the main PC and PC2, allowing for remote procedure calls.
- **Core Logic/Features:** This agent exposes a secure endpoint that the main PC can call to offload tasks to PC2. It handles the network communication, serialization, and deserialization of data between the two systems.
- **Health Check:** Listens on port `7124`. This is a critical port listed in `main_pc_to_pc2_connections`.
- **Error Handling:** Not specified. Must be extremely robust to handle network failures, timeouts, and disconnections between the two physical machines.
- **Configuration/Parameters:** `host`, `port` (7124), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** The main gateway from the main PC into the PC2 subsystem. It routes incoming requests to the appropriate PC2 agent, likely a router or scheduler.
- **Dependencies:** None listed.

#### Agent: SelfHealingAgent
- **Purpose:** To automatically detect and attempt to fix problems within the PC2 subsystem.
- **Core Logic/Features:** This agent takes action based on reports from `HealthMonitor` or `RCAAgent`. Its fixes could range from simple actions, like restarting a crashed agent, to more complex ones, like re-routing traffic away from a failing service.
- **Health Check:** Listens on port `7125`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified.
- **Configuration/Parameters:** `host`, `port` (7125), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** A high-level system management agent that can control the lifecycle of other agents. It consumes analysis from `RCAAgent`.
- **Dependencies:** None listed.

#### Agent: UnifiedWebAgent
- **Purpose:** Provides a comprehensive interface for interacting with the web, including browsing, scraping, and data extraction.
- **Core Logic/Features:** Can take a high-level goal (e.g., "find the reviews for this product") and execute the necessary steps, such as navigating to a website, clicking links, and parsing HTML to extract the relevant information.
- **Health Check:** Listens on port `7126`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Must handle all manner of web-related errors, including network issues, HTTP errors, and changes in website layouts.
- **Configuration/Parameters:** `host`, `port` (7126), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** A powerful tool that can be used by many other agents to gather external information.
- **Dependencies:** None listed.

#### Agent: DreamingModeAgent
- **Purpose:** Manages the "dreaming" state of the system, activating and deactivating the `DreamWorldAgent`.
- **Core Logic/Features:** This agent monitors system activity. When it detects a prolonged period of idleness, it activates the `DreamWorldAgent` to begin generating synthetic data. When a new user request comes in, it signals the `DreamWorldAgent` to gracefully shut down.
- **Health Check:** Listens on port `7127`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Manages the state transitions of the dreaming process.
- **Configuration/Parameters:** `host`, `port` (7127), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Orchestrates the `DreamWorldAgent`.
- **Dependencies:** `DreamWorldAgent`.

#### Agent: PerformanceLoggerAgent
- **Purpose:** A dedicated agent for logging detailed performance metrics to a persistent store for later analysis.
- **Core Logic/Features:** Unlike `PerformanceMonitor`, which focuses on real-time data, this agent is responsible for writing performance logs to disk. This allows for historical analysis of system performance over time.
- **Health Check:** Listens on port `7128`. Health check details are inherited from the global `health_checks` configuration.
- **Error Handling:** Not specified. Handles file I/O errors.
- **Configuration/Parameters:** `host`, `port` (7128), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Likely consumes data from `PerformanceMonitor` and writes it to a database or log files.
- **Dependencies:** None listed.

#### Agent: AdvancedRouter
- **Purpose:** A sophisticated task router that makes intelligent decisions about where to send a request based on content, priority, and system state.
- **Core Logic/Features:** This agent is more advanced than a simple pattern-based router. It might use a small AI model to classify incoming requests and route them to the most appropriate specialized agent. It's a key entry point from the main PC.
- **Health Check:** Listens on port `7129`. This is a critical port listed in `main_pc_to_pc2_connections`.
- **Error Handling:** Not specified. Manages routing logic and handles cases where no appropriate agent can be found for a request.
- **Configuration/Parameters:** `host`, `port` (7129), `required: true`. Inherits global settings.
- **Inter-Agent Communication:** Receives requests from `RemoteConnectorAgent` and dispatches them to other PC2 agents like `TieredResponder` or `TaskScheduler`.
- **Dependencies:** None listed.