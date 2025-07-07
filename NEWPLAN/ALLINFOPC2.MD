AGENT: ResourceManager
GROUP: Core Infrastructure
REASONING: This agent monitors and manages system resources (CPU, memory, disk, GPU). It provides resource allocation, tracking, and health monitoring capabilities. This agent is critical for system stability and performance optimization, making it a foundational core infrastructure component.
RESOURCES: CPU, memory, disk, GPU (if available)
DEPENDENCIES: BaseAgent, psutil, torch (optional), zmq.
FILE: pc2_code/agents/resource_manager.py
PORT: 7113
HEALTH_CHECK_PORT: 8113

AGENT: HealthMonitor
GROUP: Core Infrastructure
REASONING: This agent provides system-wide health monitoring capabilities. It tracks the status of other agents and provides health information to clients. The agent is essential for system reliability and serves as a foundational service that other components rely on for health reporting and monitoring.
RESOURCES: Minimal (primarily monitoring)
DEPENDENCIES: BaseAgent, ResourceManager, zmq.
FILE: pc2_code/agents/health_monitor.py
PORT: 7114
HEALTH_CHECK_PORT: 8114

AGENT: TaskScheduler
GROUP: High-Level Orchestration
REASONING: This agent coordinates and schedules tasks across the system. It forwards tasks to the AsyncProcessor for execution and manages task prioritization. This agent is a critical part of the system's workflow management and belongs in the High-Level Orchestration group due to its role in coordinating complex tasks.
RESOURCES: Minimal (primarily coordination)
DEPENDENCIES: BaseAgent, AsyncProcessor, zmq.
FILE: pc2_code/agents/task_scheduler.py
PORT: 7115
HEALTH_CHECK_PORT: 8115

AGENT: AsyncProcessor
GROUP: Core Infrastructure
REASONING: This agent processes asynchronous tasks submitted by other components. It provides reliable task execution, queuing, and management capabilities for the distributed system.
RESOURCES: Moderate (CPU, Memory)
DEPENDENCIES: BaseAgent, ResourceManager, zmq.
FILE: pc2_code/agents/async_processor.py
PORT: 7101
HEALTH_CHECK_PORT: 8101

AGENT: AdvancedRouter
GROUP: Cognitive Frameworks
REASONING: This agent provides intelligent task classification and routing based on natural language input. It analyzes tasks and determines the appropriate processing path or model. This agent is a critical part of the system's decision-making infrastructure, fitting the Cognitive Frameworks group due to its intelligent routing capabilities.
RESOURCES: Minimal (primarily computational logic)
DEPENDENCIES: BaseAgent, TaskScheduler, re (regex), zmq.
FILE: pc2_code/agents/advanced_router.py
PORT: 7129
HEALTH_CHECK_PORT: 8129

AGENT: UnifiedMemoryReasoningAgent
GROUP: Memory & Knowledge
REASONING: This agent now serves as a compatibility layer that forwards requests to the MemoryOrchestratorService. It maintains backward compatibility with existing code while leveraging the consolidated memory infrastructure. The agent's core functionality has been integrated into MemoryOrchestratorService.
RESOURCES: Low (primarily forwarding requests)
DEPENDENCIES: BaseAgent, MemoryOrchestratorService, zmq, threading.
FILE: pc2_code/agents/UnifiedMemoryReasoningAgent.py
PORT: 7105
HEALTH_CHECK_PORT: 8105

AGENT: ContextManager
GROUP: Cognitive Frameworks
REASONING: This agent manages conversation context with dynamic sizing based on importance. It maintains separate contexts per speaker and handles context pruning. The agent now leverages MemoryOrchestratorService for more efficient context storage and retrieval.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, numpy, BaseAgent, MemoryOrchestratorService.
FILE: pc2_code/agents/context_manager.py
PORT: 7111
HEALTH_CHECK_PORT: 8111

AGENT: ExperienceTracker
GROUP: Utilities & Support Services
REASONING: This agent tracks user experiences and interactions. It now forwards experience tracking requests directly to MemoryOrchestratorService. It's a lightweight component that primarily relays data without heavy processing.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, MemoryOrchestratorService.
FILE: pc2_code/agents/experience_tracker.py
PORT: 7112
HEALTH_CHECK_PORT: 8112

AGENT: CacheManager
GROUP: Data & Storage Services
REASONING: This agent now serves as a compatibility layer for the caching system. Its core functionality has been integrated into MemoryOrchestratorService which directly uses Redis for improved performance. The agent maintains backward compatibility while delegating actual cache operations to MemoryOrchestratorService.
RESOURCES: Low (primarily forwarding requests)
DEPENDENCIES: zmq, BaseAgent, MemoryOrchestratorService.
FILE: pc2_code/agents/cache_manager.py
PORT: 7102
HEALTH_CHECK_PORT: 8102

AGENT: RemoteConnectorAgent
GROUP: Network & Communication
REASONING: This agent serves as a bridge between the system and external AI models/APIs. It handles model requests, maintains response caching, and manages connections to various model endpoints like Ollama and Deepseek. The agent requires substantial network resources for API calls, making it a core communication component.
RESOURCES: Medium-High (CPU, Memory, Network)
DEPENDENCIES: zmq, requests, yaml, BaseAgent, AdvancedRouter.
FILE: pc2_code/agents/remote_connector_agent.py
PORT: 7124
HEALTH_CHECK_PORT: 8124

AGENT: FileSystemAssistantAgent
GROUP: Utilities & Support Services
REASONING: This agent provides controlled file system operations to other components in the distributed system. It handles file reading/writing, directory operations, and file management tasks. The agent serves as a utility for system-level file interactions.
RESOURCES: Low-Medium (CPU, Disk I/O)
DEPENDENCIES: zmq, os, shutil, BaseAgent, UnifiedUtilsAgent.
FILE: pc2_code/agents/filesystem_assistant_agent.py
PORT: 7123
HEALTH_CHECK_PORT: 8123

AGENT: UnifiedWebAgent
GROUP: Network & Communication
REASONING: This agent provides advanced web browsing, information gathering, and context-aware navigation capabilities. It uses Selenium for browser automation and now integrates with MemoryOrchestratorService for caching and memory storage. The agent requires significant resources for browser automation and heavy network usage.
RESOURCES: High (CPU, Memory, Network)
DEPENDENCIES: zmq, selenium, requests, BeautifulSoup, MemoryOrchestratorService, FileSystemAssistantAgent.
FILE: pc2_code/agents/unified_web_agent.py
PORT: 7126
HEALTH_CHECK_PORT: 8126

AGENT: TutorAgent
GROUP: Human Interaction Pipeline
REASONING: This agent provides tutoring services by generating educational lessons on various topics. It manages personalized learning paths for users.
RESOURCES: Low-Medium (CPU, Memory, Network)
DEPENDENCIES: zmq, json, threading, BaseAgent, TutoringServiceAgent.
FILE: pc2_code/agents/tutor_agent.py
PORT: 7108
HEALTH_CHECK_PORT: 8108

AGENT: TutoringAgent
GROUP: Human Interaction Pipeline
REASONING: This agent provides secondary tutoring capabilities. It works in conjunction with TutorAgent to implement educational functionalities. This agent is marked as non-required in the configuration, suggesting it provides supplementary functionality.
RESOURCES: Low-Medium (CPU, Memory, Network)
DEPENDENCIES: zmq, json, threading, BaseAgent, TutoringServiceAgent.
FILE: pc2_code/agents/tutoring_agent.py
PORT: 7131
HEALTH_CHECK_PORT: 8131

AGENT: TutoringServiceAgent
GROUP: Human Interaction Pipeline
REASONING: This agent provides the core tutoring service infrastructure. It generates educational content, manages lesson plans, and tracks learning progress.
RESOURCES: Moderate (CPU, Memory, Network)
DEPENDENCIES: zmq, BaseAgent, MemoryOrchestratorService.
FILE: pc2_code/agents/tutoring_service_agent.py
PORT: 7130
HEALTH_CHECK_PORT: 8130

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
DEPENDENCIES: zmq, BaseAgent, threading, json, logging, HealthMonitor.
FILE: pc2_code/agents/ForPC2/system_health_manager.py
PORT: 7117
HEALTH_CHECK_PORT: 8117
ERROR_BUS_PORT: 7150

AGENT: AgentTrustScorer
GROUP: Cognitive Frameworks
REASONING: This agent calculates and manages trust scores for AI models based on their performance metrics. It maintains a database of model reliability scores, tracks successful vs. failed interactions, and factors in response times to compute dynamic trust scores. The system uses these scores to make informed decisions about which models to prioritize for different tasks. This agent now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
RESOURCES: Low-Medium (CPU, Memory, Database I/O)
DEPENDENCIES: zmq, sqlite3, BaseAgent, datetime, threading, HealthMonitor.
FILE: pc2_code/agents/AgentTrustScorer.py
PORT: 7122
HEALTH_CHECK_PORT: 8122

AGENT: PerformanceLoggerAgent
GROUP: Utilities & Support Services
REASONING: This agent logs and analyzes system performance metrics from all agents. It provides detailed performance monitoring, generates reports, and helps identify bottlenecks in the system. The agent reports errors via the central Error Bus.
RESOURCES: Low-Medium (CPU, Memory, Database I/O)
DEPENDENCIES: zmq, sqlite3, BaseAgent, datetime, threading, SystemHealthManager.
FILE: pc2_code/agents/PerformanceLoggerAgent.py
PORT: 7128
HEALTH_CHECK_PORT: 8128

AGENT: AuthenticationAgent
GROUP: Security & Access Control
REASONING: This agent handles authentication and authorization services for PC2. It validates requests, manages permissions, and ensures secure access to system resources.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, UnifiedUtilsAgent.
FILE: pc2_code/agents/ForPC2/AuthenticationAgent.py
PORT: 7116
HEALTH_CHECK_PORT: 8116

AGENT: UnifiedUtilsAgent
GROUP: Utilities & Support Services
REASONING: This agent provides common utility functions to other PC2 agents. It centralizes shared functionality to reduce code duplication and improve maintainability.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, SystemHealthManager.
FILE: pc2_code/agents/ForPC2/unified_utils_agent.py
PORT: 7118
HEALTH_CHECK_PORT: 8118

AGENT: ProactiveContextMonitor
GROUP: Cognitive Frameworks
REASONING: This agent proactively monitors and manages context across the system. It works closely with the ContextManager to ensure optimal context handling and anticipation of contextual needs.
RESOURCES: Low-Medium (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, ContextManager.
FILE: pc2_code/agents/ForPC2/proactive_context_monitor.py
PORT: 7119
HEALTH_CHECK_PORT: 8119

AGENT: PerformanceMonitor
GROUP: Utilities & Support Services
REASONING: This agent monitors performance metrics of the system. It works with the PerformanceLoggerAgent to provide real-time performance analysis and optimization recommendations.
RESOURCES: Low (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, PerformanceLoggerAgent.
FILE: pc2_code/agents/performance_monitor.py
PORT: 7103
HEALTH_CHECK_PORT: 8103

AGENT: TieredResponder
GROUP: Integration Layer
REASONING: This agent provides tiered response capabilities for different types of requests. It implements a cascading response strategy to optimize response quality and latency.
RESOURCES: Moderate (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, ResourceManager.
FILE: pc2_code/agents/tiered_responder.py
PORT: 7100
HEALTH_CHECK_PORT: 8131

AGENT: VisionProcessingAgent
GROUP: Perception & Analysis
REASONING: This agent processes visual inputs and provides computer vision capabilities to the system. It handles image analysis, object recognition, and scene understanding.
RESOURCES: High (CPU, GPU, Memory)
DEPENDENCIES: zmq, BaseAgent, CacheManager.
FILE: pc2_code/agents/VisionProcessingAgent.py
PORT: 7150
HEALTH_CHECK_PORT: 8150

AGENT: DreamWorldAgent
GROUP: Creative & Generative
REASONING: This agent generates creative content and simulations. It provides dream-like scenarios and creative problem-solving capabilities.
RESOURCES: Medium-High (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, MemoryOrchestratorService.
FILE: pc2_code/agents/DreamWorldAgent.py
PORT: 7104
HEALTH_CHECK_PORT: 8104

AGENT: DreamingModeAgent
GROUP: Creative & Generative
REASONING: This agent works with the DreamWorldAgent to implement dreaming behaviors for the system. It manages the dreaming process and coordinates with other agents during dream states.
RESOURCES: Medium (CPU, Memory)
DEPENDENCIES: zmq, BaseAgent, DreamWorldAgent.
FILE: pc2_code/agents/DreamingModeAgent.py
PORT: 7127
HEALTH_CHECK_PORT: 8127

# PC2 Agents Documentation

## Core System Infrastructure

### SystemHealthManager
- **Purpose**: Centralized error management and system health monitoring
- **Port**: 7117
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
  - Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')

### RemoteConnectorAgent
- **Purpose**: Connects to remote model services
- **Port**: 7124
- **Key Functions**:
  - Manages connections to external AI models
  - Provides unified interface for model requests
  - Implements request routing and load balancing
  - Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')

### PerformanceLoggerAgent
- **Purpose**: Logs and analyzes system performance
- **Port**: 7128
- **Key Functions**:
  - Collects performance metrics from all agents
  - Generates performance reports and visualizations
  - Identifies performance bottlenecks
  - Reports errors via the central Error Bus (ZMQ PUB/SUB, topic 'ERROR:')

### ResourceManager
- **Purpose**: Manages system resources
- **Port**: 7113
- **Key Functions**:
  - Monitors CPU, memory, disk, and GPU usage
  - Allocates resources to agents
  - Prevents resource contention
  - Reports system resource status

### AgentTrustScorer
- **Purpose**: Evaluates agent reliability
- **Port**: 7122
- **Key Functions**:
  - Tracks agent success and failure rates
  - Computes trust scores based on performance
  - Provides reliability metrics to other agents
  - Helps optimize agent selection and routing

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
