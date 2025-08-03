# 🔧 PC2 Subsystem Optimization & Testing Plan
**Based sa successful Main PC deployment (91% success rate)**

## 📊 PC2 ARCHITECTURE ANALYSIS

### **🎯 PC2 Service Groups (7 Groups Total):**
1. **infra_core** (2 agents) - ObservabilityHub, ResourceManager
2. **memory_stack** (5 agents) - MemoryOrchestratorService, CacheManager, UnifiedMemoryReasoningAgent, ContextManager, ExperienceTracker  
3. **async_pipeline** (4 agents) - AsyncProcessor, TaskScheduler, AdvancedRouter, TieredResponder
4. **tutoring_cpu** (2 agents) - TutorAgent, TutoringAgent
5. **vision_dream_gpu** (3 agents) - VisionProcessingAgent, DreamWorldAgent, DreamingModeAgent
6. **utility_suite** (5 agents) - UnifiedUtilsAgent, FileSystemAssistantAgent, RemoteConnectorAgent, AuthenticationAgent, AgentTrustScorer, ProactiveContextMonitor
7. **web_interface** (1 agent) - UnifiedWebAgent

**Total: 22 PC2 agents across 7 service groups**

---

## 🔥 **MAIN CHALLENGE: PC2 ↔ MAIN PC SYNCHRONIZATION**

### **🎯 SYNCHRONIZATION STRATEGY:**

#### **Option A: Docker Build sa Main PC, Deploy sa PC2**
```bash
# Main PC build process
1. Build PC2 images sa main PC Docker environment
2. Export images (docker save)
3. Transfer sa PC2 via SCP/rsync
4. Import sa PC2 (docker load)
5. Deploy using PC2-specific compose files
```

#### **Option B: Remote Docker Context**
```bash
# Setup remote Docker context sa main PC
docker context create pc2 --docker "host=ssh://user@pc2"
docker --context pc2 build -t pc2_infra_core:latest .
```

#### **Option C: GitOps + Docker Registry**
```bash
# Push to registry from main PC, pull from PC2
docker push registry/pc2_infra_core:latest
# On PC2:
docker pull registry/pc2_infra_core:latest
```

---

## 🏗️ **DOCKER DEPLOYMENT ARCHITECTURE**

### **Infrastructure Requirements:**
- **Redis Instances**: 7 dedicated Redis servers (one per group)
- **NATS Servers**: 7 NATS instances for inter-group communication
- **Cross-Machine Sync**: ObservabilityHub → Main PC ObservabilityHub
- **Port Management**: PC2 uses PORT_OFFSET for isolation

### **Network Configuration:**
```yaml
# PC2 Docker Networks
networks:
  pc2_infra_core_network:
    driver: bridge
  pc2_memory_stack_network:
    driver: bridge
  pc2_async_pipeline_network:
    driver: bridge
  pc2_tutoring_cpu_network:
    driver: bridge
  pc2_vision_dream_gpu_network:
    driver: bridge
  pc2_utility_suite_network:
    driver: bridge
  pc2_web_interface_network:
    driver: bridge
  pc2_cross_machine_sync:
    driver: bridge
    external: true  # For main PC communication
```

---

## 🧪 **PC2 TESTING PLAN (7-Group Test Suite)**

### **Test Execution Priority:**
1. **infra_core** (foundation) - ObservabilityHub, ResourceManager
2. **memory_stack** (core functionality) - Memory services
3. **async_pipeline** (task processing) - Async workflow
4. **utility_suite** (support services) - Authentication, utils
5. **tutoring_cpu** (specialized services) - Educational agents
6. **vision_dream_gpu** (GPU workloads) - Vision processing, dream world
7. **web_interface** (user-facing) - Web agent

### **Test Scenarios per Group:**

#### **GROUP 1: infra_core** 🏗️
```bash
# Purpose: Core monitoring and resource management
A. Test ObservabilityHub cross-machine sync
B. ResourceManager allocation and limits
C. Health check endpoints validation

# Test Scripts:
# 1) ObservabilityHub health check
curl http://localhost:9100/metrics | wc -l | xargs -I{} test {} -gt 500

# 2) ResourceManager status
curl http://localhost:7113/resources | jq '.cpu_percent < 80'

# 3) Cross-machine sync test
curl http://localhost:9100/sync/mainpc | jq '.status=="connected"'
```

#### **GROUP 2: memory_stack** 🧠
```bash
# Purpose: Memory orchestration and reasoning
A. MemoryOrchestratorService coordination
B. CacheManager performance (<5ms latency)
C. UnifiedMemoryReasoningAgent inference

# Test Scripts:
# 1) Memory latency test
curl -w '%{time_total}\\n' -d '{"key":"test","value":"data"}' http://localhost:7140/memory/set

# 2) Reasoning agent test  
curl -d '{"query":"What is the capital of France?"}' http://localhost:7105/reason | jq '.confidence > 0.8'

# 3) Cache hit rate test
curl http://localhost:7102/cache/stats | jq '.hit_rate > 0.7'
```

#### **GROUP 3: async_pipeline** ⚡
```bash
# Purpose: Asynchronous task processing pipeline
A. AsyncProcessor queue management
B. TaskScheduler job execution
C. TieredResponder load balancing

# Test Scripts:
# 1) Async processing test
curl -d '{"task":"background_job","priority":"high"}' http://localhost:7101/tasks/submit

# 2) Scheduler status
curl http://localhost:7115/scheduler/status | jq '.active_jobs < 10'

# 3) Router load balancing
seq 1 10 | xargs -n1 -P10 -I{} curl -s http://localhost:7129/route/test > /dev/null
```

#### **GROUP 4: tutoring_cpu** 🎓
```bash
# Purpose: Educational and tutoring services
A. TutorAgent response quality
B. TutoringAgent session management

# Test Scripts:
# 1) Tutor response test
curl -d '{"question":"Explain quantum physics"}' http://localhost:7108/ask | jq '.explanation | length > 100'

# 2) Tutoring session test
curl -d '{"student_id":"test","topic":"math"}' http://localhost:7131/session/start | jq '.session_id'
```

#### **GROUP 5: vision_dream_gpu** 👁️
```bash
# Purpose: GPU-intensive vision processing and dream simulation
A. VisionProcessingAgent GPU utilization (<95%)
B. DreamWorldAgent simulation accuracy
C. DreamingModeAgent resource management

# Test Scripts:
# 1) Vision processing test
curl -F 'image=@test/sample.jpg' http://localhost:7150/process | jq '.objects | length > 0'

# 2) Dream world simulation
curl -d '{"scenario":"peaceful_forest"}' http://localhost:7104/dream/generate | jq '.generated==true'

# 3) GPU utilization check
curl http://localhost:7127/gpu/status | jq '.utilization < 95'
```

#### **GROUP 6: utility_suite** 🛠️
```bash
# Purpose: Support utilities and authentication
A. AuthenticationAgent security validation
B. FileSystemAssistantAgent operations
C. AgentTrustScorer metrics

# Test Scripts:
# 1) Authentication test
curl -d '{"user":"test","password":"secret"}' http://localhost:7116/auth | jq '.authenticated==true'

# 2) Filesystem operations
curl -d '{"path":"/tmp","operation":"list"}' http://localhost:7123/fs | jq '.files | length >= 0'

# 3) Trust scoring
curl -d '{"agent":"test_agent","actions":["successful_task"]}' http://localhost:7122/trust/score | jq '.score > 0.5'
```

#### **GROUP 7: web_interface** 🌐
```bash
# Purpose: User-facing web interface
A. UnifiedWebAgent HTTP response time (<200ms)
B. Web interface accessibility
C. Session management

# Test Scripts:
# 1) Web interface response test
curl -w '%{time_total}\\n' http://localhost:7126/ | awk '{print ($1 < 0.2)}'

# 2) API endpoint test
curl http://localhost:7126/api/status | jq '.status=="operational"'
```

---

## 🔧 **IMPLEMENTATION STEPS**

### **Phase 1: Infrastructure Setup**
1. **Docker Environment Preparation**
   ```bash
   # Create PC2 docker directories
   mkdir -p docker/pc2/{infra_core,memory_stack,async_pipeline,tutoring_cpu,vision_dream_gpu,utility_suite,web_interface}
   ```

2. **NATS Configuration Fix** (Apply same hot-patch as Main PC)
   ```bash
   # Apply localhost:4222 → nats_pc2_infra_core:4222 fix
   grep -Rl 'localhost:4222' --include='*.py' pc2_code/ | xargs sed -i 's/localhost:4222/nats_pc2_infra_core:4222/g'
   ```

3. **Environment Variables**
   ```bash
   # Add to .env
   PC2_NATS_URL=nats://nats_pc2_infra_core:4222
   PC2_REDIS_URL=redis://redis_pc2_infra_core:6379/0
   MAINPC_OBS_HUB=http://main_pc_ip:9000
   PORT_OFFSET=0  # PC2 specific offset
   ```

### **Phase 2: Docker Compose Generation**
```bash
# Generate compose files for each group
for group in infra_core memory_stack async_pipeline tutoring_cpu vision_dream_gpu utility_suite web_interface; do
    generate_pc2_compose_file $group
done
```

### **Phase 3: Cross-Machine Sync Setup**
```bash
# Setup ObservabilityHub cross-machine communication
1. Configure VPN/SSH tunnel between Main PC ↔ PC2
2. Setup Redis replication for shared state
3. Configure NATS cross-machine bridges
4. Test bidirectional health check sync
```

### **Phase 4: Deployment & Testing**
```bash
# Execute 7-group testing in dependency order
1. Deploy infra_core (foundation)
2. Deploy memory_stack (core functionality) 
3. Deploy async_pipeline (task processing)
4. Deploy utility_suite (support services)
5. Deploy tutoring_cpu (specialized services)
6. Deploy vision_dream_gpu (GPU workloads)
7. Deploy web_interface (user-facing)
```

---

## 📊 **SUCCESS METRICS TARGET**

Based sa Main PC success rate (91%), target natin for PC2:

- **Infrastructure Success Rate**: >90% (6/7 groups operational)
- **Cross-Machine Sync**: 100% ObservabilityHub connectivity
- **Container Deployment**: 100% successful (22+ containers)
- **Service Discovery**: 100% PC2 ↔ Main PC communication
- **Resource Utilization**: GPU <95%, CPU <80%, Memory <4GB

---

## 🚀 **DEPLOYMENT TIMELINE**

1. **Week 1**: Infrastructure setup + NATS hot-patch
2. **Week 2**: Docker compose generation + cross-machine sync
3. **Week 3**: Group-by-group deployment (1 group per day)
4. **Week 4**: Integration testing + optimization

---

## 🎯 **NEXT ACTIONS**

1. ✅ Create PC2 optimization plan (COMPLETED)
2. 🔄 Apply NATS hot-patch to PC2 codebase  
3. 🔄 Generate Docker infrastructure for 7 groups
4. 🔄 Setup cross-machine synchronization
5. 🔄 Execute 7-group testing sequence
6. 🔄 Deploy optimized PC2 subsystem

**🎉 Expected Result: Fully optimized PC2 subsystem with >90% success rate and seamless Main PC synchronization!**
