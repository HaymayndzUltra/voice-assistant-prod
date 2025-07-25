# BACKGROUND AGENT COMMAND: V3 Configuration Analysis & Docker Action Plan

## 🎯 **MISSION OBJECTIVE**
Analyze the new v3 configuration system and create a comprehensive action plan for Docker containerization of the 77-agent distributed AI system across MainPC (RTX 4090) and PC2 (RTX 3060).

## 📋 **ANALYSIS REQUIREMENTS**

### **1. V3 Configuration Analysis**
- **Primary Source**: `config/startup_config.v3.yaml` (NEW single source of truth)
- **Legacy Sources**: 
  - `main_pc_code/config/startup_config.yaml` (54 agents)
  - `pc2_code/config/startup_config.yaml` (23 agents)
- **Override System**: `config/overrides/mainpc.yaml` and `config/overrides/pc2.yaml`
- **Configuration Loader**: `common/utils/unified_config_loader.py`

### **2. Blueprint Implementation Status**
- **Reference**: `memory-bank/blueprint-implementation-complete.md` (ALL 7 STEPS COMPLETE)
- **Key Achievements**: 
  - ✅ Environment Variable Standardization (53 files, 198 changes)
  - ✅ Docker Path Fixes (235 files, 428 changes) 
  - ✅ Network Fixes (hostname-based discovery)
  - ✅ Dead Code Cleanup (186 files, 78,320 lines removed)
  - ✅ Configuration Consolidation (v3 system active)

### **3. Current Infrastructure Status**
- **NATS Error Bus**: `common/error_bus/nats_error_bus.py` (implemented)
- **Hostname Resolver**: `common/utils/hostname_resolver.py` (Docker/K8s aware)
- **Service Discovery**: `common/service_mesh/unified_discovery_client.py` (HTTP + ZMQ)
- **Path Management**: `common/utils/path_manager.py` (container-ready)
- **Network Configuration**: Hostname-based service discovery active

## 🔍 **DETAILED ANALYSIS TASKS**

### **Task 1: Agent Inventory & Grouping Analysis**
1. **Count total agents** from both legacy configs vs v3 config
2. **Identify missing agents** in v3 that exist in legacy configs
3. **Analyze agent groupings** for Docker containerization:
   - Core services (CPU only)
   - GPU infrastructure (RTX 4090/3060 specific)
   - Memory system (persistent data)
   - Reasoning services (GPU intensive)
   - Utility services (mixed CPU/GPU)
   - Learning services (GPU intensive)
   - PC2 services (utility focused)

### **Task 2: Docker Container Architecture Design**
Based on the completed Blueprint.md implementation, design:

1. **MainPC Container Groups** (RTX 4090 - 24GB VRAM):
   - `core-platform` (CPU): ServiceRegistry, SystemDigitalTwin, RequestCoordinator, ObservabilityHub
   - `model-manager-gpu` (8GB): ModelManagerSuite, UnifiedSystemAgent
   - `memory-stack` (CPU): MemoryClient, SessionMemoryAgent, KnowledgeBase
   - `utility-gpu` (14GB): CodeGenerator, TinyLlamaServiceEnhanced, LocalFineTunerAgent, NLLBAdapter + CPU sidecars
   - `reasoning-gpu` (10GB): ChainOfThoughtAgent, GoTToTAgent, CognitiveModelAgent
   - `vision-gpu` (6GB): FaceRecognitionAgent, VRAMOptimizerAgent
   - `language-stack-gpu` (20GB): ModelOrchestrator, GoalManager, IntentionValidatorAgent, NLUAgent, AdvancedCommandHandler, ChitchatAgent, FeedbackHandler, Responder, TranslationService, DynamicIdentityAgent, EmotionSynthesisAgent
   - `audio-emotion` (4GB): STTService, TTSService + CPU sidecars

2. **PC2 Container Groups** (RTX 3060 - 12GB VRAM):
   - `vision-dream-gpu` (6-7GB): VisionProcessingAgent, DreamWorldAgent, DreamingModeAgent
   - `memory-reasoning-gpu` (4GB): UnifiedMemoryReasoningAgent, MemoryOrchestratorService
   - `tutor-suite-cpu` (CPU): TutorAgent, TutoringAgent, ProactiveContextMonitor, TieredResponder
   - `infra-core-cpu` (CPU): ContextManager, ExperienceTracker, CacheManager, ResourceManager, TaskScheduler, AuthenticationAgent, UnifiedUtilsAgent, AgentTrustScorer, FileSystemAssistantAgent, RemoteConnectorAgent, UnifiedWebAgent, AdvancedRouter, ObservabilityHub

### **Task 3: NATS Integration Analysis**
1. **Current NATS Implementation**: `common/error_bus/nats_error_bus.py`
2. **Integration Points**: 
   - Error bus for distributed error handling
   - Service discovery coordination
   - Cross-machine communication
3. **Docker Requirements**: NATS server in Docker Compose, container networking

### **Task 4: Requirements Analysis Per Container**
For each container group, determine:
1. **Python Dependencies**: Specific requirements.txt per container
2. **GPU Requirements**: CUDA versions, PyTorch, transformers, etc.
3. **System Dependencies**: Audio libraries, vision libraries, etc.
4. **Resource Limits**: CPU, memory, GPU memory allocation
5. **Volume Mounts**: Models, logs, data, cache directories

### **Task 5: Network & Service Discovery**
1. **Docker Networks**: Internal networks per machine, cross-machine network
2. **Service Names**: Docker service naming conventions
3. **Health Checks**: HTTP endpoints, ZMQ fallbacks
4. **Cross-Machine Communication**: MainPC ↔ PC2 coordination

## 📊 **DELIVERABLES REQUIRED**

### **1. Complete Agent Inventory**
- Total agent count (should be 77)
- Missing agents in v3 config
- Agent-to-container mapping
- Resource requirements per agent

### **2. Docker Compose Architecture**
- `docker-compose.mainpc.yml` with 8 container groups
- `docker-compose.pc2.yml` with 4 container groups
- `docker-compose.network.yml` for cross-machine communication
- NATS and Redis services integration

### **Task 3: Container-Specific Requirements**
- 12 separate `requirements.txt` files (one per container)
- Dockerfile templates for each container type
- Environment variable configurations
- Volume mount specifications

### **Task 4: Deployment Action Plan**
- Container startup order and dependencies
- GPU allocation strategy
- Cross-machine communication setup
- Monitoring and health check configuration
- Rollback procedures

### **Task 5: Migration Strategy**
- How to migrate from current manual Docker setup to new v3 system
- Configuration migration from legacy to v3
- Testing procedures for each container group
- Performance validation steps

## 🎯 **SUCCESS CRITERIA**

1. **Complete Coverage**: All 77 agents properly mapped to containers
2. **Resource Optimization**: GPU memory allocation within limits (24GB MainPC, 12GB PC2)
3. **Network Integration**: NATS, Redis, and cross-machine communication working
4. **Configuration Unity**: Single v3 config driving all containers
5. **Production Ready**: Health checks, monitoring, and rollback procedures

## 📝 **BACKGROUND AGENT INSTRUCTIONS**

1. **Start with agent inventory** - compare legacy configs vs v3 config
2. **Design container architecture** - ensure GPU limits are respected
3. **Create Docker Compose files** - with proper networking and volumes
4. **Generate requirements files** - per container group
5. **Plan deployment strategy** - startup order, testing, validation
6. **Provide complete action plan** - step-by-step implementation guide

**IMPORTANT**: Use the completed Blueprint.md implementation as foundation. The codebase is already Docker-ready with hostname-based discovery, container-friendly paths, and unified configuration system. Focus on container architecture and deployment strategy. 