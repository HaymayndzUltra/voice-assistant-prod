# Voice Assistant System Integration Points

This document details the key integration points within the voice assistant system, focusing on two critical aspects:

1. The communication flow between MainPC and PC2
2. The integration of the enhanced agents into the mainPC streaming pipeline

## MainPC to PC2 Communication Flow

The voice assistant system spans two physical machines: the MainPC (192.168.1.27) which handles the primary user-facing functions and audio processing, and PC2 (192.168.1.2) which hosts advanced AI models and specialized services.

### ZMQ Bridge (Port 5600)

The cornerstone of the cross-machine communication is the **ZMQ Bridge** operating on port 5600. This component:

- Uses a ROUTER/DEALER socket pattern for bidirectional communication
- Handles message routing between the two machines
- Preserves message identity for proper request-response matching
- Serves as the single communication gateway between MainPC and PC2

### Key Integration Flows

#### 1. Model Requests Flow

```
ModelManagerAgent (mainPC, port 5556)
  → ZMQ Bridge (port 5600)
    → EnhancedModelRouter (PC2, port 5598)
      → Appropriate LLM Service (TinyLlama, Chain-of-Thought, etc.)
      → Response back through the same path
```

This flow is primarily used for code generation, complex reasoning tasks, and other LLM-based operations.

#### 2. Translation Flow

```
Language & Translation Coordinator (mainPC)
  → ZMQ Bridge (port 5600)
    → TranslatorAgent (PC2, port 5563)
      → NLLB Adapter (PC2, port 5581) or other translation engines
      → Response back through the same path
```

This flow handles language translation tasks, typically for non-English user inputs.

#### 3. Memory Operations Flow

```
Various mainPC agents
  → ZMQ Bridge (port 5600)
    → UnifiedMemoryReasoningAgent (PC2, port 5596)
      or DreamWorldAgent (PC2, port 5598-PUB)
      or other memory services
    → Response back through the same path
```

This flow is used for complex memory operations, especially those requiring semantic search or vector embeddings.

## Core Agent Integration

### 1. UnifiedPlanningAgent

**File:** `agents/unified_planning_agent.py`

**Integration Points:**
- **Reply socket:** Handles planning requests (REP 5571)
- **Health check:** Monitors agent health (REP 5572)
- **Task Router:** Routes tasks to appropriate agents (REQ 5571)
- **AutoGen Framework:** Integrates with AutoGen for advanced planning

**Key Features:**
- Task decomposition
- Code generation and execution
- Multi-language support
- Agent capability mapping

### 2. UnifiedWebAgent

**File:** `agents/unified_web_agent.py`

**Integration Points:**
- **Reply socket:** Handles web requests (REP 5604)
- **Health check:** Monitors agent health
- **Web services:** Integrates with web scraping and automation

**Key Features:**
- Web scraping
- Browser automation
- Session management
- Data extraction

### 3. UnifiedSystemAgent

**File:** `agents/unified_system_agent.py`

**Integration Points:**
- **Reply socket:** Handles system requests (REP 5573)
- **Health check:** Monitors agent health
- **Service discovery:** Manages service registration

**Key Features:**
- System orchestration
- Service discovery
- Maintenance tasks
- Resource management

### 4. CoordinatorAgent

**File:** `agents/coordinator_agent.py`

**Integration Points:**
- **Reply socket:** Handles coordination requests (REP 5574)
- **Health check:** Monitors agent health
- **Command routing:** Routes commands to appropriate agents

**Key Features:**
- Command routing
- Health monitoring
- Task coordination
- System state management

### 5. StreamingAudioCapture

**File:** `agents/streaming_audio_capture.py`

**Integration Points:**
- **Publish socket:** Streams audio data (PUB 6575)
- **Health check:** Monitors agent health
- **Wake word detection:** Integrates with wake word detection

**Key Features:**
- Audio capture
- Stream processing
- Wake word detection
- Audio buffering

## Memory Agent Integration

### 1. UnifiedMemoryReasoningAgent

**File:** `agents/unified_memory_reasoning_agent.py`

**Integration Points:**
- **Reply socket:** Handles memory requests (REP 5596)
- **Health check:** Monitors agent health
- **Memory operations:** Manages memory queries and updates

**Key Features:**
- Memory access
- Reasoning capabilities
- Migration support
- Agent integration

### 2. DreamWorldAgent

**File:** `agents/DreamWorldAgent.py`

**Integration Points:**
- **Publish socket:** Broadcasts dream world updates (PUB 5598)
- **Health check:** Monitors agent health
- **Memory integration:** Connects with memory systems

**Key Features:**
- Episodic memory
- Scenario simulation
- Context enrichment
- Memory management

### 3. EpisodicMemoryAgent

**File:** `agents/EpisodicMemoryAgent.py`

**Integration Points:**
- **Reply socket:** Handles episodic memory requests
- **Health check:** Monitors agent health
- **Storage:** Manages SQLite database

**Key Features:**
- Episode creation
- Search/query
- SQLite storage
- Context management

### 4. MemoryDecayManager

**File:** `agents/memory_decay_manager.py`

**Integration Points:**
- **Reply socket:** Handles decay requests
- **Health check:** Monitors agent health
- **Memory agents:** Manages memory lifecycle

**Key Features:**
- Periodic decay
- Memory pruning
- Retention policy
- Lifecycle management

## System Management Agent Integration

### 1. SelfHealingAgent

**File:** `agents/self_healing_agent.py`

**Integration Points:**
- **Reply socket:** Handles health requests (REP 5611)
- **Health check:** Monitors agent health
- **Agent monitoring:** Tracks all agent health

**Key Features:**
- Heartbeat monitoring
- Dependency management
- Auto-recovery
- System health

### 2. PerformanceLoggerAgent

**File:** `agents/PerformanceLoggerAgent.py`

**Integration Points:**
- **Reply socket:** Handles logging requests
- **Health check:** Monitors agent health
- **Metrics collection:** Gathers performance data

**Key Features:**
- Response time tracking
- Resource usage monitoring
- Historical data
- Performance analysis

### 3. ModelStatusMonitor

**File:** `agents/model_status_monitor.py`

**Integration Points:**
- **Reply socket:** Handles status requests
- **Health check:** Monitors agent health
- **Model monitoring:** Tracks model status

**Key Features:**
- Status tracking
- Health checks
- Alert system
- Model monitoring

## Model Management Agent Integration

### 1. EnhancedModelRouter

**File:** `agents/enhanced_model_router.py`

**Integration Points:**
- **Reply socket:** Handles routing requests (REP 5598)
- **Health check:** Monitors agent health
- **Model selection:** Routes to appropriate models

**Key Features:**
- Model selection
- Fallback handling
- Load balancing
- Request routing

### 2. RemoteConnectorAgent

**File:** `agents/remote_connector_agent.py`

**Integration Points:**
- **Reply socket:** Handles connection requests (REP 5557)
- **Health check:** Monitors agent health
- **API management:** Manages model connections

**Key Features:**
- Model connections
- Response caching
- Status monitoring
- API management

### 3. ModelResponseCache

**File:** `agents/model_response_cache.py`

**Integration Points:**
- **Reply socket:** Handles cache requests
- **Health check:** Monitors agent health
- **Cache management:** Manages response caching

**Key Features:**
- Response caching
- Cache invalidation
- Cache management
- Performance optimization
