### Agent Documentation Audit Report (PC2) - Detailed Review

---

#### Agent: TieredResponder
- **Documentation Gap(s):** The original documentation was highly generic. It completely missed the agent's core logic, which is a sophisticated, resource-aware, pattern-matching response system.
- **Suggested Details to Add:**
    - **Core Logic/Features:**
        *   Explain the tiering system. The agent categorizes queries into `'instant'`, `'fast'`, and `'deep'` tiers based on regex patterns.
        *   Describe the `ResourceManager` class, which actively monitors CPU, memory, and GPU (`psutil`, `torch`) and will delay processing if usage exceeds thresholds.
        *   Mention the use of `asyncio` for handling responses and the multi-threaded architecture for health monitoring and request processing.
    - **Inter-Agent Communication:** Clarify its unique ZMQ socket setup: a REP socket for receiving requests and synchronous health checks, a PUSH socket for sending responses, and a PUB socket for broadcasting health status.

---

#### Agent: AsyncProcessor
- **Documentation Gap(s):** The original documentation correctly identified its purpose but lacked any detail about its implementation.
- **Suggested Details to Add:**
    - **Core Logic/Features:**
        *   Describe the `TaskQueue` class, which maintains separate `deque` objects for `'high'`, `'medium'`, and `'low'` priority tasks.
        *   Mention its internal `ResourceManager` that checks system load before processing, similar to `TieredResponder`.
        *   Note that it tracks detailed statistics for each task type, including success/failure counts and average duration.
    - **Inter-Agent Communication:** Specify the ZMQ socket setup: a REP socket for receiving tasks and returning immediate acknowledgements, a PUSH socket for fire-and-forget tasks, and a PUB socket for broadcasting health.

---

#### Agent: CacheManager
- **Documentation Gap(s):** The documentation correctly identified Redis as the backend but missed the structured nature of the cache and its full API.
- **Suggested Details to Add:**
    - **Core Logic/Features:**
        *   Explain that the cache is structured by `cache_type`. There is a pre-defined `cache_config` dictionary that specifies different TTLs and priorities for types like `nlu_results`, `model_decisions`, and `memory`.
        *   Detail the background maintenance thread (`_run_maintenance`) that periodically logs cache stats and can be extended for advanced eviction policies.
    - **Inter-Agent Communication:** Describe its rich ZMQ API, which inherits from `BaseAgent`. The `handle_request` method is a dispatcher that supports actions like `get`, `put`, `invalidate`, and `flush` for different cache types.

---

#### Agent: PerformanceMonitor
- **Documentation Gap(s):** The documentation was too generic. It missed the agent's primary role as a data aggregator and publisher, and its alerting capabilities.
- **Suggested Details to Add:**
    - **Core Logic/Features:**
        *   Explain that its main function is to aggregate metrics from other services. It exposes a `log_metric` action for other agents to push data to it.
        *   Describe the built-in alerting feature. It checks incoming metrics against `ALERT_THRESHOLDS` and will change its own health status to `'degraded'` if they are breached.
        *   Note its use of `numpy` for statistical calculations.
    - **Inter-Agent Communication:** Clarify that this agent is primarily a **publisher**. It runs two background threads (`_broadcast_metrics`, `_monitor_health`) that continuously send data out on two different ZMQ PUB sockets. Its REQ/REP socket is for receiving metric logs and serving alert data, not for its primary monitoring function.

---

### Summary of Agents Needing Code-Level Review

The audit reveals that the configuration files provide only a surface-level view. A complete and accurate documentation requires code-level analysis. The following agents from the PC2 subsystem still need to be audited against their source code to ensure the final documentation is not just an assumption based on a name:

*   **PC2 Memory & Reasoning**: `DreamWorldAgent`, `UnifiedMemoryReasoningAgent`, `EpisodicMemoryAgent`, `ContextManager`
*   **PC2 Learning & Healing**: `LearningAgent`, `HealthMonitor`, `SelfHealingAgent`, `RCAAgent`
*   **PC2 Entry & Task Management**: `AdvancedRouter`, `TaskScheduler`, `RemoteConnectorAgent`
*   **Other Agents**: `AgentTrustScorer`, `FileSystemAssistantAgent`, `UnifiedWebAgent`, etc.

Without this, their documentation will remain speculative.