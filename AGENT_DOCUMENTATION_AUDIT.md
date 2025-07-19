### Agent Documentation Audit Report (MainPC) - Detailed Review

---

#### Agent: ServiceRegistry
- **Documentation Gap(s):** Minor. The documentation is good but could be more explicit about its inheritance and exact request handling.
- **Suggested Details to Add:**
    - **Core Logic/Features:** Add that it inherits from `common.core.base_agent.BaseAgent`. The `handle_request` method is a dispatcher that specifically routes `register_agent` and `get_agent_endpoint` actions.
    - **Health Check:** Clarify that the health check is the standard mechanism from `BaseAgent`, responding to `ping` and `health` actions via ZMQ.

---

#### Agent: SystemDigitalTwin
- **Documentation Gap(s):** The documentation is accurate but lacks detail on its internal mechanisms.
- **Suggested Details to Add:**
    - **Core Logic/Features:** Specify that it runs a background thread (`_collect_metrics_loop`) which uses the `psutil` library to gather system resource metrics. Mention that the HTTP health check is a `BaseHTTPRequestHandler` running in its own thread via the `_start_http_health_server` method.
    - **Error Handling:** Highlight the use of a dedicated `ErrorPublisher` class to standardize error reporting over a ZMQ PUB/SUB channel.

---

#### Agent: RequestCoordinator
- **Documentation Gap(s):** Key architectural patterns like the priority queue and specific threading models were missed.
- **Suggested Details to Add:**
    - **Core Logic/Features:** Detail the multi-threaded architecture, specifically the main `_handle_requests` loop, a `_dispatch_loop` for the task queue, and a `_listen_for_interrupts` thread for barge-in capability. Explain that the task queue is a `heapq` (priority queue), with priority determined by `_calculate_priority`. Note the use of Pydantic models (`TextRequest`, `AudioRequest`) for validating incoming request structures.
    - **Inter-Agent Communication:** Specify that it uses ZMQ REQ sockets for downstream commands and a ZMQ SUB socket for interrupts.

---

#### Agent: ModelManagerSuite
- **Documentation Gap(s):** The original documentation was significantly understated. It missed the agent's consolidated nature, complex multi-threaded architecture, specific VRAM logic, evaluation framework, and backward-compatibility layers.
- **Suggested Details to Add:**
    - **Purpose:** State explicitly that this agent is a **consolidation** of four previous agents: `GGUFModelManager`, `ModelManagerAgent`, `PredictiveLoader`, and `ModelEvaluationFramework`. This is a critical architectural decision.
    - **Core Logic/Features:**
        *   Describe the multi-threaded architecture, highlighting the five key background threads: the main ZMQ request loop (`_main_loop`), the health check loop (`_health_check_loop`), the VRAM management loop (`_vram_management_loop`), the predictive pre-loading loop (`_prediction_loop`), and the GGUF KV cache cleanup loop (`_kv_cache_cleanup_loop`).
        *   Detail the VRAM management logic: The `_vram_management_loop` periodically calls `_check_idle_models`, which unloads models if their idle time exceeds `idle_unload_timeout_seconds`.
        *   Explain the Model Evaluation Framework, which uses an SQLite database (`data/model_evaluation.db`) to log performance metrics and evaluation scores via `log_performance_metric` and `log_model_evaluation` actions.
    - **Error Handling:** Note the use of a dedicated `report_error` method to publish structured errors to a central ZMQ `error_bus_pub` socket.
    - **Dependencies / Compatibility:** Describe the `_LegacyModelManagerProxy` class, which is a critical backward-compatibility layer that ensures older agents can still import the previously separate components without breaking.

---

#### Agent: MemoryClient
- **Documentation Gap(s):** No major gaps, but the specifics of the circuit breaker can be elaborated.
- **Suggested Details to Add:**
    - **Error Handling:** Mention that its `CircuitBreaker` has three states: `CLOSED`, `OPEN`, and `HALF_OPEN`, using a `reset_timeout` to control the transition from `OPEN` to `HALF_OPEN`, making it more resilient.

---

#### Agent: NLUAgent
- **Documentation Gap(s):** The documentation completely missed the primary mechanism for intent extraction.
- **Suggested Details to Add:**
    - **Core Logic/Features:** State clearly that the core intent extraction mechanism is a list of pre-defined regex patterns stored in `self.intent_patterns`. This is a fundamental implementation detail that is not obvious from the name alone. Mention the `_extract_intent` and `_extract_entities` methods as the main processing functions.

---

#### Agent: EmotionEngine
- **Documentation Gap(s):** The documentation correctly identified the purpose but missed the specifics of the emotion model.
- **Suggested Details to Add:**
    - **Core Logic/Features:** Specify that the emotional state is a dictionary with keys like `tone`, `sentiment`, and `intensity`. Explain that it uses `emotion_thresholds` and `emotion_combinations` dictionaries to map raw scores to descriptive labels (e.g., a high negative sentiment maps to `'furious'` or `'annoyed'` based on intensity). Note that it uses a ZMQ PUB socket in `_broadcast_emotional_state` to publish state changes.

---

### Summary of Agents Needing Improved Documentation

The following agents and subsystems require documentation updates to reflect these deeper insights:

*   **Core Services**: `RequestCoordinator`, and especially `ModelManagerSuite`, which has a much more complex and critical role than originally documented.
*   **Memory System**: `MemoryClient` (minor update on error handling).
*   **Language Processing**: `NLUAgent` (critical update on regex-based logic).
*   **Emotion System**: `EmotionEngine` (key details on the emotion model).
*   **High-Level Agents** (`UnifiedSystemAgent`, `ObservabilityHub`): These remain high-level as their source code was not available for this detailed review. Their documentation is a known-gap.