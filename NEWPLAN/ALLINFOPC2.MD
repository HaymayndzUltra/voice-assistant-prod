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
REASONING: This agent now serves as a compatibility layer that forwards requests to the MemoryOrchestratorService. It maintains backward compatibility with existing code while leveraging the consolidated memory infrastructure. The agent's core functionality has been integrated into MemoryOrchestratorService.
RESOURCES: Low (primarily forwarding requests)
DEPENDENCIES: BaseAgent, MemoryOrchestratorService, zmq, threading.

AGENT: EpisodicMemoryAgent
GROUP: Data & Storage Services
REASONING: This agent provides episodic memory storage capabilities. It now integrates with MemoryOrchestratorService for persistence and advanced memory features. It manages episodes, interactions, and relationships between memories.
RESOURCES: Medium (CPU, Memory)
DEPENDENCIES: zmq, MemoryOrchestratorService, BaseAgent.

AGENT: ContextManager
GROUP: Cognitive Frameworks
REASONING: This agent manages conversation context with dynamic sizing based on importance. It maintains separate contexts per speaker and handles context pruning. The agent now leverages MemoryOrchestratorService for more efficient context storage and retrieval.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, numpy, BaseAgent, MemoryOrchestratorService.

AGENT: ExperienceTracker
GROUP: Utilities & Support Services
REASONING: This agent tracks user experiences and interactions. It now forwards experience tracking requests directly to MemoryOrchestratorService. It's a lightweight component that primarily relays data without heavy processing.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, MemoryOrchestratorService.

AGENT: CacheManager
GROUP: Data & Storage Services
REASONING: This agent now serves as a compatibility layer for the caching system. Its core functionality has been integrated into MemoryOrchestratorService which directly uses Redis for improved performance. The agent maintains backward compatibility while delegating actual cache operations to MemoryOrchestratorService.
RESOURCES: Low (primarily forwarding requests)
DEPENDENCIES: zmq, BaseAgent, MemoryOrchestratorService.

AGENT: RemoteConnectorAgent
GROUP: Network & Communication
REASONING: This agent serves as a bridge between the system and external AI models/APIs. It handles model requests, maintains response caching, and manages connections to various model endpoints like Ollama and Deepseek. The agent requires substantial network resources for API calls, making it a core communication component.
RESOURCES: Medium-High (CPU, Memory, Network)
DEPENDENCIES: zmq, requests, yaml, BaseAgent.

AGENT: FileSystemAssistantAgent
GROUP: Utilities & Support Services
REASONING: This agent provides controlled file system operations to other components in the distributed system. It handles file reading/writing, directory operations, and file management tasks. The agent serves as a utility for system-level file interactions.
RESOURCES: Low-Medium (CPU, Disk I/O)
DEPENDENCIES: zmq, os, shutil, BaseAgent.

AGENT: UnifiedWebAgent
GROUP: Network & Communication
REASONING: This agent provides advanced web browsing, information gathering, and context-aware navigation capabilities. It uses Selenium for browser automation and now integrates with MemoryOrchestratorService for caching and memory storage. The agent requires significant resources for browser automation and heavy network usage.
RESOURCES: High (CPU, Memory, Network)
DEPENDENCIES: zmq, selenium, requests, BeautifulSoup, MemoryOrchestratorService, BaseAgent.

AGENT: TutoringAgent
GROUP: Human Interaction Pipeline
REASONING: This agent provides tutoring services by generating educational lessons on various topics. It uses an LLM for content generation, maintains a cache of lessons, and handles student profiles. The agent requires moderate resources primarily for network communication with the LLM service.
RESOURCES: Low-Medium (CPU, Memory, Network)
DEPENDENCIES: zmq, json, threading, BaseAgent.

AGENT: MemoryOrchestratorService
GROUP: Data & Storage Services
REASONING: This service is the central memory hub for the distributed system, consolidating memory orchestration, robust SQLite persistence, and Redis-based distributed caching. This agent now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:'). It exposes a unified ZMQ API for all memory operations (add, get, search, update, delete) and serves as the single source of truth for all memory data. The service implements advanced features including memory decay, reinforcement learning, hierarchical organization, and semantic search. It runs on port 7140 to avoid conflicts with other services and is foundational for all memory-related workflows.
RESOURCES: Moderate to High (database operations, Redis cache)
DEPENDENCIES: BaseAgent, sqlite3, zmq, pydantic, threading, redis.
FILE: pc2_code/agents/memory_orchestrator_service.py
PORT: 7140
HEALTH_CHECK_PORT: 7141

AGENT: SystemHealthManager
GROUP: Utilities & Support Services
REASONING: This agent is now the central event-driven error management and self-healing agent for PC2. It manages the Error Bus (ZMQ PUB/SUB, topic 'ERROR:') for scalable, decoupled error reporting and processing. It autonomously collects errors, analyzes logs, monitors agent health, and performs recovery actions.
RESOURCES: Moderate (event bus, log analysis, health monitoring)
DEPENDENCIES: zmq, BaseAgent, threading, json, logging, MemoryOrchestratorService.
FILE: pc2_code/agents/ForPC2/system_health_manager.py
PORT: 7117
HEALTH_CHECK_PORT: 8117
ERROR_BUS_PORT: 7150

# PC2 Agents Documentation

## Core System Agents

### SystemHealthManager
- **Purpose**: Centralized error management and system health monitoring
- **Port**: 7130
- **Error Bus Port**: 7150
- **Key Functions**:
  - Listens for errors on the Error Bus (ZMQ PUB/SUB, topic 'ERROR:')
  - Analyzes error patterns and determines appropriate responses
  - Implements recovery strategies based on error severity
  - Monitors agent health via heartbeats
  - Scans log files for error patterns
  - Consolidates functionality from former UnifiedErrorAgent, RCA_Agent, and SelfHealingAgent

### MemoryOrchestratorService
- **Purpose**: Central memory management service
- **Port**: 7140
- **Key Functions**:
  - Stores and retrieves memory entries
  - Implements memory importance scoring
  - Provides memory search capabilities
  - Broadcasts memory updates to subscribers
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### RemoteConnectorAgent
- **Purpose**: Connects to remote model services
- **Port**: 7160
- **Key Functions**:
  - Manages connections to external AI models
  - Provides unified interface for model requests
  - Implements request routing and load balancing
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### PerformanceLoggerAgent
- **Purpose**: Logs and analyzes system performance
- **Port**: 7170
- **Key Functions**:
  - Collects performance metrics from all agents
  - Generates performance reports and visualizations
  - Identifies performance bottlenecks
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

## Error Management Architecture

The system now uses an event-driven Error Bus architecture for error management:

1. **Error Bus**: ZMQ PUB/SUB pattern on port 7150
   - All agents publish errors to topic "ERROR:"
   - SystemHealthManager subscribes to all error messages

2. **Error Format**:
   ```json
   {
     "error_type": "string",
     "message": "string",
     "severity": "string",
     "context": {}
   }
   ```

3. **Error Processing Flow**:
   - Agent detects an error and calls its report_error method
   - Error is published to the Error Bus with topic "ERROR:"
   - SystemHealthManager receives the error message
   - SystemHealthManager analyzes the error and determines appropriate action
   - Recovery actions are executed based on error severity and patterns

4. **Benefits**:
   - Decoupled architecture improves system resilience
   - Centralized error processing enables better pattern detection
   - Event-driven model reduces system overhead
   - Simplified agent code for error reporting

## Additional Services

### UnifiedWebAgent
- **Purpose**: Provides web browsing and information retrieval
- **Port**: 7180
- **Key Functions**:
  - Searches the web for information
  - Extracts content from web pages
  - Summarizes web content
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### TutoringAgent
- **Purpose**: Provides tutoring services
- **Port**: 7190
- **Key Functions**:
  - Creates personalized learning plans
  - Provides interactive tutorials
  - Tracks learning progress
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**

### FileSystemAssistantAgent
- **Purpose**: Manages file system operations
- **Port**: 7200
- **Key Functions**:
  - Provides file search capabilities
  - Manages file organization
  - Implements file backup and recovery
  - **Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')**
