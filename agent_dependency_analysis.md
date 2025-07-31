# Agent Dependency and Resource Analysis
## Docker Production Reorganization Project

**Analysis Date**: 2025-07-30  
**Systems Analyzed**: MainPC (RTX 4090) and PC2 (RTX 3060)

---

## 1. MainPC System Analysis

### 1.1 Current Agent Groups and Dependencies

#### Foundation Services (Critical Infrastructure)
- **ServiceRegistry** 
  - Port: 7200, Health: 8200
  - Dependencies: None (Root service)
  - Resource Usage: Low (in-memory registry)
  - Critical: YES - All agents depend on this for service discovery

- **SystemDigitalTwin**
  - Port: 7220, Health: 8220  
  - Dependencies: ServiceRegistry
  - Resource Usage: Medium (DB operations, Redis connections)
  - Critical: YES - Central state management

- **RequestCoordinator**
  - Port: 26002, Health: 27002
  - Dependencies: SystemDigitalTwin
  - Critical: YES - Routes all user requests

- **ModelManagerSuite**
  - Port: 7211, Health: 8211
  - Dependencies: SystemDigitalTwin
  - Resource Usage: HIGH (GPU/VRAM management, model loading)
  - Config: 80% VRAM budget, idle timeout 300s
  - Critical: YES - Manages all AI models

- **VRAMOptimizerAgent**
  - Port: 5572, Health: 6572
  - Dependencies: ModelManagerSuite, RequestCoordinator, SystemDigitalTwin
  - Resource Usage: Low (monitoring only)
  - Critical: YES - Prevents OOM errors

- **ObservabilityHub**
  - Port: 9000, Health: 9001
  - Dependencies: SystemDigitalTwin
  - Resource Usage: Medium (metrics collection)
  - Features: Prometheus, parallel health checks, predictions

- **UnifiedSystemAgent**
  - Port: 7201, Health: 8201
  - Dependencies: SystemDigitalTwin
  - Resource Usage: Low

#### Memory System
- **MemoryClient**: Base memory operations (deps: SystemDigitalTwin)
- **SessionMemoryAgent**: Session tracking (deps: RequestCoordinator, SystemDigitalTwin, MemoryClient)
- **KnowledgeBase**: Long-term storage (deps: MemoryClient, SystemDigitalTwin)

#### GPU-Intensive Services
- **ModelOrchestrator**: Manages model routing (deps: RequestCoordinator, ModelManagerSuite, SystemDigitalTwin)
- **STTService**: Speech-to-text (deps: ModelManagerSuite, SystemDigitalTwin)
- **TTSService**: Text-to-speech (deps: ModelManagerSuite, SystemDigitalTwin)
- **FaceRecognitionAgent**: Vision processing (deps: RequestCoordinator, ModelManagerSuite, SystemDigitalTwin)

### 1.2 Resource Usage Patterns

**High Resource Consumers**:
1. ModelManagerSuite (GPU/VRAM)
2. STTService/TTSService (GPU for inference)
3. FaceRecognitionAgent (GPU for vision)
4. Learning/Training agents (GPU for fine-tuning)

**Medium Resource Consumers**:
1. SystemDigitalTwin (DB/Redis operations)
2. ObservabilityHub (metrics/monitoring)
3. Memory agents (storage operations)

**Low Resource Consumers**:
1. ServiceRegistry
2. Coordinators/Routers
3. Monitoring agents

### 1.3 Startup Dependencies Chain
```
ServiceRegistry
  └── SystemDigitalTwin
       ├── RequestCoordinator
       ├── ModelManagerSuite
       │    ├── VRAMOptimizerAgent
       │    ├── STTService
       │    ├── TTSService
       │    └── All AI-based agents
       ├── ObservabilityHub
       └── All other agents
```

---

## 2. PC2 System Analysis

### 2.1 Current Agent Structure

**Core Services**:
- **ObservabilityHub** (Port 9100) - Monitoring hub
- **MemoryOrchestratorService** (Port 7140) - Memory management
- **ResourceManager** (Port 7113) - Resource allocation
- **AsyncProcessor** (Port 7101) - Async task handling
- **CacheManager** (Port 7102) - Caching layer

**Application Services**:
- Vision, Dream, Learning agents
- File system and web agents
- Authentication and utilities

### 2.2 Resource Patterns

PC2 has simpler resource patterns:
- No direct GPU model management (relies on MainPC)
- Focus on memory/cache optimization
- Async processing for efficiency
- Lower resource limits (RTX 3060 vs RTX 4090)

### 2.3 Cross-System Dependencies

PC2 agents communicate with MainPC for:
- Model inference (via MainPC's ModelManagerSuite)
- Shared memory/state (potential Redis cluster)
- Monitoring data (ObservabilityHub sync)

---

## 3. Key Findings

### 3.1 Dependency Issues
1. **Circular dependencies** avoided by careful layering
2. **Single points of failure**: ServiceRegistry, SystemDigitalTwin
3. **Heavy GPU concentration** on MainPC
4. **Network latency** between PC2-MainPC for inference

### 3.2 Resource Bottlenecks
1. **GPU Memory**: All models compete for 80% VRAM budget
2. **Model Loading**: Sequential loading can delay startup
3. **Network**: High traffic between systems for inference
4. **Database**: SystemDigitalTwin is central bottleneck

### 3.3 Current Grouping Problems
1. **Too many groups**: 11 groups in MainPC, harder to manage
2. **Unclear boundaries**: Some agents could fit multiple groups
3. **Uneven distribution**: Some groups have 1 agent, others have 8+
4. **No failure isolation**: Group failure affects many services

---

## 4. Recommendations for Docker Optimization

### 4.1 Reduce Group Count
- Consolidate from 11 to 5-6 logical groups
- Group by failure domains and resource needs
- Consider startup dependencies

### 4.2 Resource-Based Grouping
- Separate GPU-heavy from CPU-only services
- Isolate high-memory consumers
- Group by scaling needs

### 4.3 Dependency Optimization
- Minimize cross-group dependencies
- Use message queues for loose coupling
- Implement circuit breakers

### 4.4 Docker-Specific Considerations
- Use multi-stage builds for smaller images
- Implement health checks at container level
- Use resource limits matching actual usage
- Consider sidecar patterns for monitoring

---

## Next Steps
1. Map functional cohesion (TODO 1)
2. Design new logical groups (TODO 2)
3. Update configuration files (TODO 3-4)
4. Create visual diagrams (TODO 5)