# TECHNICAL ENVIRONMENT CONTEXT

**Background Agent: Complete technical environment details for comprehensive analysis**

---

## 🖥️ INFRASTRUCTURE ENVIRONMENT

### **Machine Specifications:**
```
MainPC (192.168.100.16):
├── OS: Linux 5.15.167.4-microsoft-standard-WSL2 
├── GPU: RTX 4090 (primary GPU workload)
├── Shell: /bin/bash
├── Docker: 28.2.2 (Docker Desktop)
├── Python: 3.11 
└── Role: Heavy GPU inference, model management, audio processing

PC2 (192.168.100.17):
├── GPU: RTX 3060 (lighter GPU workload)  
├── Role: Task processing, memory orchestration
├── Status: Not yet deployed
└── Cross-machine communication with MainPC
```

### **Network Architecture:**
```
Network Setup:
├── MainPC Subnet: 172.20.0.0/16
├── PC2 Subnet: 172.21.0.0/16  
├── Cross-machine: 192.168.100.0/24
├── Service Discovery: NATS-based
└── Load Balancing: Manual distribution
```

---

## 📦 DEPENDENCY ENVIRONMENT

### **Current Dependency Status:**
```
✅ Core Dependencies (Installed):
├── orjson-3.11.0 (JSON processing)
├── pyzmq-27.0.0 (ZeroMQ messaging) 
├── numpy-2.3.1 (Numerical computing)
├── redis-6.2.0 (Caching/storage)
├── PyYAML-6.0.2 (Configuration)
└── python-dotenv-1.1.1 (Environment)

✅ Audio Dependencies (Installed with conflicts):
├── soundfile-0.9.0.post1 (vs TTS requirement 0.12.0+)
├── librosa-0.8.0 (vs TTS requirement 0.10.0+)
├── speechrecognition-3.14.3
└── pyaudio-0.2.13

⚠️ Conflict Warning: TTS 0.22.0 has version conflicts
```

### **Container Dependencies (104GB Issue):**
```
Each Container Installs:
├── PyTorch: ~3-4GB (AI/ML processing)
├── Transformers: ~2-3GB (NLP models)
├── OpenCV: ~1-2GB (Computer vision)
├── SciPy/NumPy: ~1-2GB (Scientific computing)
├── Audio Libraries: ~1GB (Speech processing)
└── Other ML libs: ~2-3GB (Various AI tools)

Total per container: ~12GB
11 containers × 12GB = 132GB+ total
```

---

## 🔧 CONFIGURATION MANAGEMENT

### **Configuration Files:**
```
Key Configuration Files:
├── main_pc_code/config/startup_config.yaml (MainPC agents)
├── pc2_code/config/startup_config.yaml (PC2 agents - analyze)
├── docker/config/env.template (Environment variables)
├── docker/docker-compose.mainpc.yml (MainPC containers)
├── docker/docker-compose.pc2.yml (PC2 containers)
└── requirements.txt (Unified dependencies - problematic)
```

### **Environment Variables Pattern:**
```
Standard Environment Variables:
├── PYTHONPATH=/app
├── LOG_LEVEL=INFO
├── DEBUG_MODE=false
├── ENABLE_METRICS=true
├── ENABLE_TRACING=true
├── REDIS_HOST=redis
├── NATS_HOST=nats
└── SERVICE_REGISTRY_HOST=core-services
```

---

## 🏗️ CURRENT ARCHITECTURE PATTERNS

### **Agent Communication:**
```
Communication Stack:
├── ZeroMQ (zmq): Inter-agent messaging
├── Redis: Shared data storage/caching
├── NATS: Event bus and pub/sub
├── HTTP/REST: External API interfaces
└── Service Registry: Agent discovery
```

### **Service Discovery Pattern:**
```
ServiceRegistry (port 7200):
├── Central service registration
├── Health check coordination  
├── Agent location tracking
└── Dependency resolution
```

### **Health Check Architecture:**
```
Health Check Pattern:
├── Each agent: health_check_port (service_port + 1000)
├── SystemDigitalTwin: Central health coordination
├── Health check scripts: scripts/verify_all_health_checks.py
└── Container health: Docker healthcheck directives
```

---

## 🐳 CONTAINER ARCHITECTURE ANALYSIS

### **Current Dockerfile Patterns:**
```
docker/gpu_base/Dockerfile:
├── Base: python:3.11-slim (temporarily, was CUDA)
├── User: ai:ai (non-root, UID 1000)
├── Workdir: /app
├── CMD: ["python", "/app/main_pc_code/scripts/start_system.py"]
└── Issue: Wrong startup command

docker/Dockerfile.base:
├── Base: python:3.11-slim  
├── For: Non-GPU services
├── Same pattern as gpu_base
└── Lighter dependency set
```

### **Volume Strategy:**
```
Volume Mapping:
├── logs:/app/logs (Persistent logging)
├── data:/app/data (Application data) 
├── models:/app/models (AI model storage)
├── ./config:/app/config (Configuration mounting)
└── Named volumes for Redis/NATS data
```

---

## 🔍 STARTUP SYSTEM ANALYSIS CONTEXT

### **Known Startup Scripts:**
```
Discovered Entry Points:
├── main_pc_code/scripts/start_system.py (Primary candidate)
├── main_pc_code/system_launcher.py (Syntax errors found)
├── main_pc_code/fixed_start_ai_system.py (Alternative)
└── scripts/start_group.py (May not exist yet)
```

### **Configuration Loading Pattern:**
```
startup_config.yaml Structure:
├── global_settings: Environment, resources, health checks
├── agent_groups: Organized by functional areas
├── Per-agent config: script_path, port, dependencies, config
└── Health check configuration: intervals, timeouts, retries
```

---

## 🚨 KNOWN ISSUES & FIXES APPLIED

### **Resolved Issues:**
```
✅ Fixed Issues:
├── Circular import: common/core/base_agent.py (self-reference removed)
├── Syntax errors: 25+ PC2 agents (extra parentheses)
├── Port conflicts: 3 services (7220→7222, etc.)
├── Script paths: ModelManagerSuite (11.py → model_manager_suite.py)
├── Docker context: All containers (. → ..)
├── Dependencies: soundfile, librosa version conflicts resolved
└── CUDA flags: LLAMA_CUBLAS → GGML_CUDA
```

### **Current Blocker:**
```
❌ Container Startup Issue:
├── Error: "No module named main_pc_code.startup"
├── Root cause: Wrong CMD in Dockerfile
├── Current: python -m main_pc_code.startup
├── Should be: python /app/main_pc_code/scripts/start_system.py
└── But: start_system.py doesn't support group filtering
```

---

## 📊 PERFORMANCE BASELINE DATA

### **Resource Usage Metrics:**
```
Current Container Stats:
├── Image sizes: 4.12GB to 12.5GB per container
├── Total images: 104GB+ (11 containers)
├── Memory per container: Estimated 2GB+ each
├── CPU usage: 24 cores available
├── GPU memory: RTX 4090 (24GB), RTX 3060 (12GB)
└── Network: Docker bridge networking
```

### **Agent Distribution:**
```
Agent Count by Group:
├── core_services: 6 agents
├── memory_system: 3 agents  
├── gpu_infrastructure: 4 agents
├── speech_services: 2 agents
├── audio_interface: 8 agents
├── emotion_system: 6 agents
├── language_processing: 12 agents
├── learning_knowledge: 6 agents
├── reasoning_services: 3 agents
├── vision_processing: 1 agent
├── utility_services: 8 agents
└── Total MainPC: 58 agents
```

---

## 🎯 CRITICAL SUCCESS METRICS

### **Deployment Success Criteria:**
```
Success Metrics:
├── All 11 MainPC containers running
├── All 58 agents started and healthy
├── Cross-container communication working
├── Health checks passing (30s intervals)
├── No startup errors in logs
├── Service registry populated
├── Redis/NATS connectivity confirmed
└── Resource usage within limits
```

### **Performance Targets:**
```
Performance Goals:
├── Container startup: <60 seconds
├── Agent initialization: <30 seconds
├── Health check response: <5 seconds
├── Memory usage: <2GB per container
├── CPU utilization: <80% total
└── Network latency: <100ms cross-machine
```

**Background Agent: Use this technical context to provide comprehensive, production-ready recommendations!** 