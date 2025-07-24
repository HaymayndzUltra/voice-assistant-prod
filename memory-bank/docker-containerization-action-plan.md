# Docker Containerization Action Plan - UPDATED WITH BLIND SPOT ANALYSIS
**Based on o3 Recommendations + Critical Blind Spot Discovery**

## 🎯 **OBJECTIVE**
Containerize 77 agents across MainPC (RTX 4090) and PC2 (RTX 3060) using optimized GPU allocation and production-ready architecture.

## ⚠️ **CRITICAL BLIND SPOTS ADDRESSED**

### **Blind Spot 1: Cross-Machine Communication**
- **Problem**: ObservabilityHub uses hardcoded IPs, script-path detection will fail in containers
- **Solution**: Container-aware environment detection, Docker service DNS, dynamic endpoint discovery

### **Blind Spot 2: Docker Networking Complexity**  
- **Problem**: ZMQ `tcp://localhost:port` won't work between containers
- **Solution**: Docker Compose service names, standardized networking strategy

### **Blind Spot 3: Configuration Management**
- **Problem**: `startup_config.yaml` file paths, `${PORT_OFFSET}` variables undefined in containers
- **Solution**: Environment variable injection, container-specific configs

### **Blind Spot 4: Data Persistence Strategy**
- **Problem**: SQLite paths relative to project root, HuggingFace cache locations scattered
- **Solution**: Standardized volume mount strategy, persistent data directories

### **Blind Spot 5: Service Discovery**
- **Problem**: SystemDigitalTwin as single registry, no PC2 equivalent, container discovery undefined
- **Solution**: Distributed service registry, DNS-based discovery, container health integration

## 📋 **PHASE 1: Container Structure Setup (Week 1) - UPDATED**

### **MainPC Container Groups (8 containers):**

#### **A. core_platform (CPU)**
- **Agents**: ServiceRegistry, RequestCoordinator, ObservabilityHub, SystemDigitalTwin
- **Resources**: CPU only, 2GB RAM
- **Requirements**: fastapi, uvicorn, grpcio, pydantic, prometheus-client
- **🔧 Blind Spot Fix**: Container-aware ObservabilityHub with DNS-based cross-machine sync

#### **B. model_manager_gpu (GPU)**
- **Agents**: ModelManagerSuite, UnifiedSystemAgent  
- **GPU Memory**: 8GB allocation
- **Requirements**: torch==2.3.*, transformers, accelerate, bitsandbytes, safetensors
- **🔧 Blind Spot Fix**: Shared model cache volume, GPU device mapping

#### **C. memory_stack (CPU)**
- **Agents**: MemoryClient, SessionMemoryAgent, KnowledgeBase
- **Resources**: CPU + SSD volume mount
- **Requirements**: chromadb, sentence-transformers, faiss-cpu
- **🔧 Blind Spot Fix**: Persistent volume for memory databases

#### **D. utility_gpu (GPU + CPU sidecars)**
- **GPU Agents**: CodeGenerator, TinyLlamaServiceEnhanced, LocalFineTunerAgent, NLLBAdapter
- **CPU Sidecars**: SelfTrainingOrchestrator, Executor, PredictiveHealthMonitor, FixedStreamingTranslation
- **GPU Memory**: 14GB allocation (fine-tuning spikes)
- **Requirements**: torch, transformers, peft, bitsandbytes, llmtuner, sacrebleu, evaluate
- **🔧 Blind Spot Fix**: Dynamic VRAM allocation, shared model weights volume

#### **E. reasoning_gpu (GPU)**
- **Agents**: ChainOfThoughtAgent, GoTToTAgent, CognitiveModelAgent
- **GPU Memory**: 10GB allocation
- **Requirements**: torch, llama-cpp-python, langchain, networkx
- **🔧 Blind Spot Fix**: Cross-container reasoning coordination

#### **F. vision_gpu (GPU)**
- **Agents**: FaceRecognitionAgent, VRAMOptimizerAgent
- **GPU Memory**: 6GB allocation (dynamic VRAM rewiring)
- **Requirements**: opencv-python-headless, torch, facenet-pytorch, torchvision
- **🔧 Blind Spot Fix**: VRAM optimization across container boundaries

#### **G. language_stack_gpu (GPU)**
- **Agents**: ModelOrchestrator, GoalManager, IntentionValidatorAgent, NLUAgent, AdvancedCommandHandler, ChitchatAgent, FeedbackHandler, Responder, TranslationService, DynamicIdentityAgent, EmotionSynthesisAgent
- **GPU Memory**: 20GB allocation (largest group, use NVIDIA MPS)
- **Requirements**: torch, transformers, sentencepiece, langchain, evaluate, nltk, spaCy
- **🔧 Blind Spot Fix**: Inter-agent communication via Docker service DNS

#### **H. audio_emotion (Mixed)**
- **GPU Agents**: STTService, TTSService (4GB allocation)
- **CPU Sidecars**: AudioCapture, FusedAudioPreprocessor, StreamingInterruptHandler, StreamingSpeechRecognition, StreamingTTSAgent, WakeWordDetector, StreamingLanguageAnalyzer, ProactiveAgent, EmotionEngine, MoodTrackerAgent, HumanAwarenessAgent, ToneDetector, VoiceProfilingAgent, EmpathyAgent
- **Requirements**: torchaudio, faster-whisper, TTS, praat-parselmouth, webrtcvad, librosa, nemo_toolkit
- **🔧 Blind Spot Fix**: Audio device access in containers, shared audio processing volume

### **PC2 Container Groups (4 containers) - VERIFIED COUNT: 23 AGENTS**

#### **A. vision_dream_gpu (GPU)**
- **Agents**: VisionProcessingAgent, DreamWorldAgent, DreamingModeAgent
- **GPU Memory**: 6-7GB allocation (55% of RTX 3060)
- **Requirements**: torch, diffusers, transformers, opencv-python-headless
- **🔧 Blind Spot Fix**: Cross-machine vision data streaming

#### **B. memory_reasoning_gpu (GPU)**
- **Agents**: UnifiedMemoryReasoningAgent, MemoryOrchestratorService
- **GPU Memory**: 4GB allocation
- **Requirements**: torch, faiss-gpu, langchain
- **🔧 Blind Spot Fix**: MainPC ↔ PC2 memory synchronization

#### **C. tutor_suite_cpu (CPU)**
- **Agents**: TutorAgent, TutoringAgent, ProactiveContextMonitor, TieredResponder
- **Requirements**: fastapi, pydantic, networkx, redis, rq
- **🔧 Blind Spot Fix**: Educational content persistence

#### **D. infra_core_cpu (CPU)**
- **Agents**: ContextManager, ExperienceTracker, CacheManager, ResourceManager, TaskScheduler, AuthenticationAgent, UnifiedUtilsAgent, AgentTrustScorer, FileSystemAssistantAgent, RemoteConnectorAgent, UnifiedWebAgent, AdvancedRouter, ObservabilityHub (PC2 instance)
- **Requirements**: fastapi, pydantic, networkx, redis, rq
- **🔧 Blind Spot Fix**: PC2-specific ObservabilityHub with MainPC sync, container-aware service discovery

## 🔧 **PHASE 2: Infrastructure Setup (Week 2) - ENHANCED**

### **Container Networking Strategy:**
```yaml
# docker-compose.yml - MainPC
networks:
  mainpc_internal:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
  cross_machine:
    driver: bridge
    ipam:
      config:
        - subnet: 172.30.0.0/16
        
# docker-compose.yml - PC2  
networks:
  pc2_internal:
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
  cross_machine:
    external: true
```

### **Service Discovery Strategy:**
```bash
# Container service names instead of localhost
# MainPC: core-platform, model-manager-gpu, memory-stack, etc.
# PC2: vision-dream-gpu, memory-reasoning-gpu, tutor-suite-cpu, etc.
# Cross-machine: mainpc-observability.cross_machine, pc2-observability.cross_machine
```

### **GPU Configuration - ENHANCED:**
```bash
# MainPC - Enable NVIDIA MPS with container support
sudo nvidia-cuda-mps-control -d
export CUDA_MPS_ACTIVE_THREAD_PERCENTAGE=70
export CUDA_VISIBLE_DEVICES=0

# PC2 - Single GPU optimization with container isolation
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
export CUDA_VISIBLE_DEVICES=0
```

### **Volume Mount Strategy:**
```yaml
volumes:
  # Shared model cache (large - 50GB+)
  huggingface_cache:
    driver: local
    driver_opts:
      type: none
      device: /data/models/huggingface
      o: bind
      
  # Persistent databases
  observability_data:
    driver: local
    driver_opts:
      type: none  
      device: /data/observability
      o: bind
      
  # Cross-container logs
  system_logs:
    driver: local
    driver_opts:
      type: none
      device: /data/logs
      o: bind
```

### **Environment Variable Strategy:**
```bash
# Container-specific environment variables
CONTAINER_ROLE=core_platform|model_manager_gpu|memory_stack|etc
MACHINE_TYPE=mainpc|pc2
CROSS_MACHINE_DISCOVERY_ENDPOINT=http://mainpc-observability:9000|http://pc2-observability:9100
GPU_MEMORY_LIMIT=8GB|14GB|10GB|etc
SERVICE_DISCOVERY_MODE=container_dns
BIND_ADDRESS=0.0.0.0
```

## 🌐 **PHASE 3: Service Discovery & Communication (Week 3) - CONTAINER-AWARE**

### **Container Service Discovery:**
```python
# Updated service discovery for containers
def discover_service(service_name: str, machine: str = "local") -> str:
    """
    Container-aware service discovery
    Returns: tcp://container-name:port or tcp://machine-container:port
    """
    if machine == "local":
        return f"tcp://{service_name.lower().replace('_', '-')}:8000"
    else:
        return f"tcp://{machine}-{service_name.lower().replace('_', '-')}:8000"
```

### **Cross-Machine Communication:**
```yaml
# MainPC containers → PC2 containers
services:
  core-platform:
    environment:
      - PC2_OBSERVABILITY_ENDPOINT=http://pc2-observability:9100
      - CROSS_MACHINE_SYNC=true
      
# PC2 containers → MainPC containers  
services:
  pc2-observability:
    environment:
      - MAINPC_OBSERVABILITY_ENDPOINT=http://mainpc-observability:9000
      - CROSS_MACHINE_SYNC=true
```

### **Container Health Checks:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

## 📊 **PHASE 4: Monitoring & Observability (Week 4) - CONTAINER-NATIVE**

### **Enhanced ObservabilityHub Configuration:**
```python
# Container-aware ObservabilityHub
class ContainerObservabilityConfig:
    def __init__(self):
        self.container_role = os.getenv('CONTAINER_ROLE')
        self.machine_type = os.getenv('MACHINE_TYPE', 'mainpc')
        self.cross_machine_endpoint = os.getenv('CROSS_MACHINE_DISCOVERY_ENDPOINT')
        self.service_discovery_mode = os.getenv('SERVICE_DISCOVERY_MODE', 'container_dns')
        
    def detect_environment(self) -> str:
        # Container-aware detection instead of script path
        return self.machine_type
```

### **Container Metrics Collection:**
```yaml
# Prometheus container metrics
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus_data:/prometheus
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--web.console.libraries=/etc/prometheus/console_libraries'
    - '--web.console.templates=/etc/prometheus/consoles'
```

## 🚀 **PHASE 5: Deployment & Testing (Week 5) - PRODUCTION-READY**

### **Docker Compose Deployment:**
```bash
# MainPC deployment
cd docker/mainpc
docker-compose up -d

# PC2 deployment  
cd docker/pc2
docker-compose up -d

# Cross-machine network setup
docker network create --driver=bridge --attachable cross-machine
```

### **Container Startup Order:**
```bash
# MainPC startup sequence
1. core-platform (ServiceRegistry, ObservabilityHub)
2. memory-stack (databases, caches)  
3. model-manager-gpu (GPU models)
4. language-stack-gpu, reasoning-gpu, vision-gpu, utility-gpu
5. audio-emotion (audio processing)

# PC2 startup sequence
1. infra-core-cpu (ResourceManager, ObservabilityHub)
2. memory-reasoning-gpu (UnifiedMemoryReasoningAgent)
3. vision-dream-gpu (VisionProcessing, DreamWorld)
4. tutor-suite-cpu (tutoring agents)
```

## 📝 **IMPLEMENTATION CHECKLIST - UPDATED**

### **Critical Blind Spot Fixes:**
- [ ] **Container-aware ObservabilityHub** with DNS-based service discovery
- [ ] **Docker Compose networks** for MainPC ↔ PC2 communication
- [ ] **Environment variable injection** replacing hardcoded paths/IPs
- [ ] **Volume mount strategy** for persistent data and model cache
- [ ] **Container service naming** convention for ZMQ connections
- [ ] **Cross-machine health check** coordination between containers
- [ ] **GPU memory allocation** management across container boundaries
- [ ] **Configuration file templating** for container environments

### **Phase 1 Tasks - ENHANCED:**
- [ ] Create **container-aware Dockerfiles** for 8 MainPC containers
- [ ] Create **container-aware Dockerfiles** for 4 PC2 containers  
- [ ] Generate **environment-specific requirements.txt** per container group
- [ ] Implement **container service discovery** mechanism
- [ ] Create **docker-compose.yml** with networking and volumes
- [ ] Test **individual container builds** and GPU allocation
- [ ] Verify **cross-container communication** within machines

### **Phase 2 Tasks - CONTAINER-FOCUSED:**
- [ ] Configure **NVIDIA Container Toolkit** for GPU sharing
- [ ] Set up **persistent volumes** for data and model cache
- [ ] Configure **Docker networks** for MainPC and PC2
- [ ] Test **GPU memory limits** per container group
- [ ] Implement **container health checks** and monitoring
- [ ] Set up **cross-machine Docker networking**

### **Phase 3 Tasks - CROSS-MACHINE:**
- [ ] Deploy **container-aware service registry**
- [ ] Configure **DNS-based service discovery**
- [ ] Set up **cross-machine container communication**
- [ ] Test **MainPC ↔ PC2 container networking**
- [ ] Implement **container-to-container health monitoring**

### **Phase 4 Tasks - CONTAINERIZED MONITORING:**
- [ ] Deploy **containerized Prometheus** and monitoring stack
- [ ] Configure **container-specific alerting** rules
- [ ] Set up **cross-machine log aggregation**
- [ ] Create **container resource monitoring** dashboards

### **Phase 5 Tasks - PRODUCTION DEPLOYMENT:**
- [ ] **Full system container deployment** testing
- [ ] **Cross-machine performance** benchmarking  
- [ ] **Container failure recovery** testing
- [ ] **Production deployment** documentation

## 🔄 **ROLLBACK PLAN - CONTAINER-AWARE**
- Keep current bare-metal setup as backup
- **Container-by-container rollback** capability
- **Cross-machine rollback coordination**
- Full system rollback to current state with **data preservation**

## 📈 **SUCCESS METRICS - UPDATED**
- **Performance**: 77 agents running across 12 containers with <2s startup time per container
- **Resource Utilization**: >80% GPU utilization efficiency across both machines
- **Reliability**: 99%+ uptime across both machines and cross-machine communication
- **Scalability**: Easy addition of new machines/containers with automatic discovery
- **Container Health**: <30s container startup time, successful health checks across all containers

## 🚨 **RISK MITIGATION - CONTAINER-SPECIFIC**
- **Container GPU OOM**: NVIDIA MPS + memory limits per container
- **Cross-machine network failures**: Container health checks + automatic retry logic
- **Container startup failures**: Dependency-aware startup order + health verification
- **Data loss**: Persistent volumes + cross-machine backup strategy
- **Service discovery failures**: DNS fallback + container restart policies

---
**Status**: Ready for implementation with blind spot fixes
**Est. Timeline**: 5 weeks total (enhanced with container-specific considerations)
**Next Action**: Begin Phase 1 - Container Structure Setup with blind spot fixes applied 