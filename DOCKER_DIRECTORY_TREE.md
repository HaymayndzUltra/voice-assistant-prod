# Docker Directory Tree Structure
## AI System Monorepo - Dedicated Docker Directory

```
AI_System_Monorepo/
└── 📁 docker/
    ├── 📁 base-images/
    │   ├── 📁 family-vision-cu121/
    │   │   └── 📄 Dockerfile
    │   ├── 📁 family-llm-cu121/
    │   │   └── 📄 Dockerfile
    │   ├── 📁 family-torch-cu121/
    │   │   └── 📄 Dockerfile
    │   ├── 📁 family-web/
    │   │   └── 📄 Dockerfile
    │   ├── 📁 legacy-py310-cpu/
    │   │   ├── 📄 Dockerfile
    │   │   └── 📄 .dockerignore
    │   ├── 📁 base-cpu-pydeps/
    │   │   └── 📄 Dockerfile
    │   ├── 📁 base-gpu-cu121/
    │   │   ├── 📄 Dockerfile
    │   │   └── 📄 .dockerignore
    │   ├── 📁 base-python/
    │   │   └── 📄 Dockerfile
    │   └── 📁 base-utils/
    │       └── 📄 Dockerfile
    │
    ├── 📁 families/
    │   ├── 📁 family-torch-cu121/
    │   │   ├── 📄 Dockerfile
    │   │   └── 📄 .dockerignore
    │   ├── 📁 family-vision-cu121/
    │   │   ├── 📄 Dockerfile
    │   │   └── 📄 .dockerignore
    │   ├── 📁 family-llm-cu121/
    │   │   └── 📄 Dockerfile
    │   └── 📁 family-web/
    │       └── 📄 Dockerfile
    │
    ├── 📁 reasoning_gpu/
    │   └── 📁 nats-server.conf/
    │
    ├── 📁 speech_gpu/
    │   └── 📁 nats-server.conf/
    │
    └── 📁 legacy/
        └── 📁 legacy-py310-cpu/
            ├── 📄 Dockerfile
            └── 📄 .dockerignore
```

## 📊 Docker Directory Architecture Summary

### **🏗️ Base Images (`base-images/`)**
**Foundation Layer - CUDA 12.1 GPU Support:**
- **base-gpu-cu121/** - Core GPU base with CUDA 12.1
- **base-python/** - Python runtime foundation
- **base-utils/** - Common utilities and tools
- **base-cpu-pydeps/** - CPU-only Python dependencies

**Family-Specific Base Images:**
- **family-vision-cu121/** - Computer vision foundation
- **family-llm-cu121/** - Large language model foundation
- **family-torch-cu121/** - PyTorch-specific foundation
- **family-web/** - Web service foundation

**Legacy Support:**
- **legacy-py310-cpu/** - Python 3.10 CPU legacy support

### **👨‍👩‍👧‍👦 Service Families (`families/`)**
**Production Service Containers:**
- **family-torch-cu121/** - PyTorch-based services
- **family-vision-cu121/** - Vision processing services
- **family-llm-cu121/** - LLM inference services
- **family-web/** - Web API services

### **🧠 Specialized GPU Services**
**Domain-Specific GPU Containers:**
- **reasoning_gpu/** - AI reasoning and logic services
- **speech_gpu/** - Speech processing and recognition

### **📜 Legacy Support (`legacy/`)**
**Backward Compatibility:**
- **legacy-py310-cpu/** - Python 3.10 CPU containers for older systems

---

## 🔧 **Docker Architecture Patterns**

### **Multi-Layer Strategy:**
1. **Base Layer** → Common runtime and dependencies
2. **Family Layer** → Domain-specific optimizations
3. **Service Layer** → Application-specific containers

### **CUDA 12.1 GPU Support:**
- **Primary GPU Framework:** CUDA 12.1
- **PyTorch Integration:** Optimized for deep learning
- **Vision Processing:** GPU-accelerated computer vision
- **LLM Inference:** High-performance language model serving

### **Container Optimization:**
- **Base Images:** Minimal, focused dependencies
- **Family Images:** Domain-optimized with shared libraries
- **Service Images:** Application-specific with minimal overhead

---

## 📈 **Usage Patterns**

### **Development Workflow:**
```bash
# Build base images first
docker build -t base-gpu-cu121 docker/base-images/base-gpu-cu121/

# Build family images
docker build -t family-vision-cu121 docker/families/family-vision-cu121/

# Build service-specific images
docker build -t my-vision-service docker/families/family-vision-cu121/
```

### **Production Deployment:**
- **GPU Services:** Use CUDA 12.1 family images
- **CPU Services:** Use legacy or base-cpu images
- **Web Services:** Use family-web base images

---

**Total Base Images:** 9 foundational containers  
**Service Families:** 4 domain-specific families  
**GPU Support:** CUDA 12.1 optimized  
**Legacy Support:** Python 3.10 CPU compatibility
