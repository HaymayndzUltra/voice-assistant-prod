AGENT: ResourceManager
GROUP: Core Infrastructure
REASONING: This agent monitors and manages system resources (CPU, memory, disk, GPU). It provides resource allocation, tracking, and health monitoring capabilities. This agent is critical for system stability and performance optimization, making it a foundational core infrastructure component.
RESOURCES: CPU, memory, disk, GPU (if available)
DEPENDENCIES: BaseAgent, psutil, torch (optional), zmq.

AGENT: HealthMonitor
GROUP: Core Infrastructure
REASONING: This agent provides system-wide health monitoring capabilities. It tracks the status of other agents and provides health information to clients. The agent is essential for system reliability and serves as a foundational service that other components rely on for health reporting and monitoring.
RESOURCES: Minimal (primarily monitoring)
DEPENDENCIES: BaseAgent, ResourceManager, zmq.

AGENT: TaskScheduler
GROUP: High-Level Orchestration
REASONING: This agent coordinates and schedules tasks across the system. It forwards tasks to the AsyncProcessor for execution and manages task prioritization. This agent is a critical part of the system's workflow management and belongs in the High-Level Orchestration group due to its role in coordinating complex tasks.
RESOURCES: Minimal (primarily coordination)
DEPENDENCIES: BaseAgent, HealthMonitor, AsyncProcessor, zmq.

AGENT: AdvancedRouter
GROUP: Cognitive Frameworks
REASONING: This agent provides intelligent task classification and routing based on natural language input. It analyzes tasks and determines the appropriate processing path or model. This agent is a critical part of the system's decision-making infrastructure, fitting the Cognitive Frameworks group due to its intelligent routing capabilities.
RESOURCES: Minimal (primarily computational logic)
DEPENDENCIES: BaseAgent, TaskScheduler, re (regex), zmq.

AGENT: UnifiedMemoryReasoningAgent
GROUP: Memory & Knowledge
REASONING: This agent manages a sophisticated memory system with decay, reinforcement, and query capabilities. It maintains an in-memory store of memories with complex operations. This agent is the central component of the memory system, fitting the Memory & Knowledge group.
RESOURCES: Medium-High (memory storage, query processing)
DEPENDENCIES: BaseAgent, HealthMonitor, zmq, secure_zmq (optional), threading, service_discovery_client.

AGENT: MemoryManager
GROUP: Data & Storage Services
REASONING: This agent provides persistent storage and retrieval of memories using an SQLite database. It handles memory storage, retrieval, updating, and expiration. This agent works closely with UnifiedMemoryReasoningAgent and belongs in the Data & Storage Services group due to its role in persistent data management.
RESOURCES: Moderate to High (database operations)
DEPENDENCIES: BaseAgent, UnifiedMemoryReasoningAgent, sqlite3, zmq.

AGENT: EpisodicMemoryAgent
GROUP: Data & Storage Services
REASONING: This agent provides episodic memory storage using SQLite for persistence. It manages episodes, interactions, and relationships between memories. It requires moderate resources for database operations and potentially for text vectorization, fitting the Data & Storage Services group.
RESOURCES: Medium (CPU, Memory, Disk)
DEPENDENCIES: zmq, sqlite3, sklearn (optional), BaseAgent.

AGENT: ContextManager
GROUP: Cognitive Frameworks
REASONING: This agent manages conversation context with dynamic sizing based on importance. It maintains separate contexts per speaker and handles context pruning. The agent is lightweight, using simple data structures, and is crucial for maintaining conversational flow, fitting the Cognitive Frameworks group.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, numpy, BaseAgent.

AGENT: ExperienceTracker
GROUP: Utilities & Support Services
REASONING: This agent acts as an interface to the EpisodicMemoryAgent, forwarding experience tracking requests. It's a lightweight component that primarily relays data without heavy processing, serving as a utility for memory interaction.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, EpisodicMemoryAgent.

AGENT: MemoryDecayManager
GROUP: Memory & Knowledge
REASONING: This agent manages memory decay processes, implementing forgetting mechanisms for the memory system. It applies decay rates to different memory types and handles memory consolidation. The agent is lightweight, primarily performing periodic calculations and communicating with the UnifiedMemoryReasoningAgent, fitting the Memory & Knowledge group.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, UnifiedMemoryReasoningAgent.

AGENT: EnhancedContextualMemory
GROUP: Memory & Knowledge
REASONING: This agent provides advanced context management with hierarchical memory organization, intelligent compression, and summarization. It implements a sophisticated memory system with multiple memory levels, requiring moderate resources for its operations, fitting the Memory & Knowledge group.
RESOURCES: Medium (CPU, Memory)
DEPENDENCIES: zmq, numpy, threading.

AGENT: AuthenticationAgent
GROUP: Security & Authentication
REASONING: This agent handles user authentication and authorization, managing user sessions and tokens. It provides secure login/logout functionality and token validation. The agent is lightweight, primarily performing cryptographic operations and maintaining session state, making Security its primary function.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, hashlib, BaseAgent.

AGENT: UnifiedErrorAgent
GROUP: Utilities & Support Services
REASONING: This agent provides centralized error handling and analysis for the system. It tracks error patterns, determines severity, and triggers alerts when thresholds are exceeded. The agent is lightweight, primarily focused on error tracking and pattern recognition, serving as a system utility.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, threading.

AGENT: UnifiedUtilsAgent
GROUP: Utilities & Support Services
REASONING: This agent provides system maintenance utilities like cleaning temporary files, logs, and caches. It interacts directly with the file system and can run system commands. The agent requires moderate resources when performing cleanup operations, serving as a system utility.
RESOURCES: Medium (CPU, Disk)
DEPENDENCIES: zmq, BaseAgent, os, platform, shutil, subprocess.

AGENT: AgentTrustScorer
GROUP: Learning & Knowledge
REASONING: This agent tracks and evaluates the performance of AI models, maintaining trust scores based on success rates and response times. It uses SQLite for persistent storage of model performance data, contributing to the learning and evaluation process.
RESOURCES: Low (CPU, Memory, Disk)
DEPENDENCIES: zmq, sqlite3, BaseAgent.

AGENT: TieredResponder
GROUP: High-Level Orchestration
REASONING: This agent implements a tiered response system with different levels of processing based on query complexity and available resources. It monitors system resources (CPU, memory, GPU) and routes requests to appropriate processing tiers. The agent can use significant resources, especially for deep processing tasks, and utilizes GPU if available, demonstrating orchestration.
RESOURCES: Medium-High (CPU, Memory, GPU)
DEPENDENCIES: zmq, BaseAgent, psutil, torch, asyncio, threading.

AGENT: AsyncProcessor
GROUP: Utilities & Support Services
REASONING: This agent handles asynchronous task processing with priority queuing. It monitors system resources (CPU, memory, GPU) to manage task execution. The agent provides a decorator for making functions run asynchronously, serving as a utility for concurrent task execution.
RESOURCES: Medium (CPU, Memory, GPU)
DEPENDENCIES: zmq, BaseAgent, psutil, torch, threading.

AGENT: CacheManager
GROUP: Data & Storage Services
REASONING: This agent manages a sophisticated caching system using Redis for improved performance. It handles different cache types with configurable TTLs and size limits, and monitors resource usage to prevent memory issues. The agent requires moderate memory resources for Redis, fitting the Data & Storage Services group.
RESOURCES: Medium (Memory, Disk)
DEPENDENCIES: redis, zmq, BaseAgent, psutil.

AGENT: RemoteConnectorAgent
GROUP: Network & Communication
REASONING: This agent serves as a bridge between the system and external AI models/APIs. It handles model requests, maintains response caching, and manages connections to various model endpoints like Ollama and Deepseek. The agent requires substantial network resources for API calls, making it a core communication component.
RESOURCES: Medium-High (CPU, Memory, Network)
DEPENDENCIES: zmq, requests, yaml, BaseAgent.

AGENT: FilesystemAssistantAgent
GROUP: Utilities & Support Services
REASONING: This agent provides controlled file system operations to other components in the distributed system. It handles file reading/writing, directory operations, and file management tasks. The agent serves as a utility for system-level file interactions.
RESOURCES: Low-Medium (CPU, Disk I/O)
DEPENDENCIES: zmq, os, shutil, BaseAgent.

AGENT: PerformanceMonitor
GROUP: Utilities & Support Services
REASONING: This agent monitors system performance metrics including CPU usage, memory consumption, and service response times. It broadcasts metrics via ZMQ, detects performance degradation, and generates alerts. The agent primarily collects and analyzes metrics, serving as a system utility.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, psutil, numpy, BaseAgent.

AGENT: PerformanceLoggerAgent
GROUP: Data & Storage Services
REASONING: This agent logs performance metrics and resource usage to a SQLite database for historical analysis. It provides an API for other agents to log metrics and retrieve historical data. The agent has moderate disk I/O requirements for database operations, fitting the Data & Storage Services group.
RESOURCES: Low-Medium (CPU, Disk I/O)
DEPENDENCIES: zmq, sqlite3, threading, BaseAgent.

AGENT: SelfHealingAgent
GROUP: System Reliability
REASONING: This agent monitors and maintains the health of all agents in the system. It detects failures through missed heartbeats, recovers agents by restarting them, and analyzes error patterns to prevent future failures. The agent requires moderate resources to track multiple agents and perform recovery operations, making it a critical reliability component.
RESOURCES: Medium (CPU, Memory)
DEPENDENCIES: zmq, threading, subprocess, BaseAgent.

AGENT: ProactiveContextMonitor
GROUP: Cognitive Frameworks
REASONING: This agent monitors and analyzes context for proactive actions within the system. It maintains context history and can trigger proactive responses based on analysis. The agent is designed for lightweight context monitoring, contributing to cognitive functions.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, http.server, BaseAgent.

AGENT: RCAAgent
GROUP: Utilities & Support Services
REASONING: This agent analyzes log files to identify error patterns and provides proactive recommendations to the Self-Healing Agent. It scans logs periodically, uses regex patterns to identify common error types, and tracks error frequency over time, serving as a utility for error analysis.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, re, threading, BaseAgent.

AGENT: DreamWorldAgent
GROUP: Cognitive Frameworks
REASONING: This agent provides scenario simulation capabilities using Monte Carlo Tree Search (MCTS) for decision-making and planning. It maintains a database of scenarios and simulations, performs causal analysis, and generates counterfactual scenarios, fitting the Cognitive Frameworks group.
RESOURCES: Medium (CPU, Memory, Disk I/O)
DEPENDENCIES: zmq, sqlite3, numpy, BaseAgent.

AGENT: DreamingModeAgent
GROUP: High-Level Orchestration
REASONING: This agent coordinates with DreamWorldAgent to manage system dreaming and simulation cycles. It schedules and manages dreaming intervals, monitors system state for optimal dreaming times, and provides dreaming insights. The agent has minimal resource requirements as it primarily manages scheduling and coordination, making it an orchestration component.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, threading, BaseAgent.

AGENT: TutoringServiceAgent
GROUP: Human Interaction Pipeline
REASONING: This agent provides a lightweight interface for tutoring services. It appears to be a simple service wrapper or coordinator that handles basic health checks and service state management, directly facilitating human interaction for educational purposes.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent.

AGENT: TutorAgent
GROUP: Learning & Knowledge
REASONING: This agent provides adaptive tutoring capabilities with personalized learning experiences. It uses neural networks for difficulty prediction, clustering for learning style analysis, and maintains student profiles. The agent requires significant resources for machine learning models, particularly for PyTorch neural networks, fitting the Learning & Knowledge group.
RESOURCES: High (CPU, Memory, GPU)
DEPENDENCIES: zmq, torch, sklearn, pandas, numpy, BaseAgent.

AGENT: UnifiedWebAgent
GROUP: Network & Communication
REASONING: This agent provides advanced web browsing, information gathering, and context-aware navigation capabilities. It uses Selenium for browser automation, maintains a cache database, and integrates with memory systems. The agent requires significant resources for browser automation and heavy network usage, making it a core network component.
RESOURCES: High (CPU, Memory, Network)
DEPENDENCIES: zmq, selenium, requests, BeautifulSoup, sqlite3, BaseAgent.

AGENT: TutoringAgent
GROUP: Human Interaction Pipeline
REASONING: This agent provides tutoring services by generating educational lessons on various topics. It uses an LLM via EnhancedModelRouter for content generation, maintains a cache of lessons, and handles student profiles. The agent requires moderate resources primarily for network communication with the LLM service, directly facilitating human interaction for educational purposes.
RESOURCES: Low-Medium (CPU, Memory, Network)
DEPENDENCIES: zmq, json, threading, BaseAgent.

AGENT: UnifiedMemoryReasoningAgent (Duplicate path, likely a typo in list)
GROUP: Memory & Knowledge
REASONING: This agent combines multiple memory-related functionalities including contextual memory, error pattern memory, and digital twin storage. It maintains context windows with importance scoring, handles session histories, and coordinates with other memory agents. The agent requires significant memory and CPU resources for context processing, summarization, and maintaining multiple data stores with disk I/O operations.
RESOURCES: Medium-High (CPU, Memory, Disk I/O)
DEPENDENCIES: zmq, numpy, threading, json, BaseAgent.

AGENT: AgentUtils
GROUP: Utilities & Support Services
REASONING: This is not a standalone agent but a utility library providing shared functionality for other agents. It includes ZMQ communication helpers, a base agent class, logging utilities, and various helper functions. The module requires minimal resources as it primarily provides infrastructure rather than performing intensive operations itself, serving as a general utility.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, json, threading, uuid, logging.