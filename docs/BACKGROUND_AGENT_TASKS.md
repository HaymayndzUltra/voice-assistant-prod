# BACKGROUND AGENT SPECIFIC ANALYSIS TASKS

**Session Context:** New Assistant Session - Requires Deep Codebase Analysis  
**Project:** AI System Monorepo Container Deployment Issues  
**Urgency:** HIGH - Production Deployment Blocked  

---

## 🔍 TASK 1: STARTUP SYSTEM DEEP ANALYSIS

**Background Agent: Please analyze the entire startup system architecture**

### Files to Analyze:
- `main_pc_code/scripts/start_system.py`
- `main_pc_code/config/startup_config.yaml`
- `main_pc_code/system_launcher.py`
- `main_pc_code/scripts/start_system.py`
- `main_pc_code/fixed_start_ai_system.py`
- Any other startup/launcher scripts in the repo

### Specific Questions:
1. **How is startup_config.yaml actually consumed?**
2. **Does start_system.py support group filtering?**
3. **What parameters does start_system.py accept?**
4. **Are there existing mechanisms to start specific agent groups?**
5. **What's the correct entry point for containerized deployment?**

### Analysis Output Needed:
- Startup flow diagram
- Command line options available
- Configuration loading mechanism
- Group filtering capabilities (if any)
- Recommended container commands

---

## 🔍 TASK 2: CONTAINER ARCHITECTURE VALIDATION

**Background Agent: Validate my container-to-group mapping approach**

### Current Mapping (Validate if Correct):
```
docker-compose services → startup_config.yaml groups:
├── core-services      → core_services
├── memory-system      → memory_system
├── gpu-infrastructure → gpu_infrastructure
├── speech-services    → speech_services
├── audio-interface    → audio_interface
├── emotion-system     → emotion_system
├── language-processing → language_processing
├── learning-knowledge → learning_knowledge
├── reasoning-services → reasoning_services
├── vision-processing  → vision_processing
└── utility-services   → utility_services
```

### Analysis Questions:
1. **Is this mapping architecturally sound?**
2. **Are there dependency conflicts between groups?**
3. **Should some groups be combined or separated?**
4. **What's the intended deployment pattern for this codebase?**
5. **Are there existing container patterns I should follow?**

---

## 🔍 TASK 3: DOCKERFILE PATTERN ANALYSIS

**Background Agent: Analyze all Dockerfile patterns in the repo**

### Files to Examine:
- `docker/gpu_base/Dockerfile`
- `docker/Dockerfile.base`
- Any other Dockerfiles in the repo
- `docker/docker-compose.mainpc.yml`
- `docker/docker-compose.pc2.yml`

### Analysis Needs:
1. **Current CMD/ENTRYPOINT patterns**
2. **Multi-stage build opportunities**
3. **Dependency optimization strategies**
4. **Environment variable usage patterns**
5. **Volume and networking conventions**

---

## 🔍 TASK 4: DEPENDENCY OPTIMIZATION ANALYSIS

**Background Agent: Analyze the 104GB container size issue**

### Current Problem:
- Each container = 12.5GB (7 containers)
- Each container = 4.12GB (4 containers)  
- Total = 104GB for 11 containers
- All install same massive requirements.txt

### Analysis Required:
1. **Map actual dependencies per agent group**
2. **Identify shared vs unique requirements**
3. **Find opportunities for base image sharing**
4. **Recommend requirements.txt splitting strategy**
5. **Suggest multi-stage build optimizations**

### Output Needed:
- Dependency matrix by agent group
- Minimal requirements per container
- Shared base image strategy
- Size reduction recommendations

---

## 🔍 TASK 5: AGENT COMMUNICATION PATTERNS

**Background Agent: Understand inter-agent communication architecture**

### Analysis Focus:
1. **How do agents discover each other?**
2. **What communication protocols are used?**
3. **How does service registry work?**
4. **What are the network requirements?**
5. **How do cross-container agents communicate?**

### Files to Analyze:
- All agent files in `main_pc_code/agents/`
- Service registry implementation
- Network configuration files
- Communication helper modules

---

## 🔍 TASK 6: EXISTING SCRIPTS AND TOOLS INVENTORY

**Background Agent: Find all existing deployment/startup tools**

### Search for:
- All scripts in `scripts/` directories
- Deployment automation tools
- Container management scripts
- Health check implementations
- Testing and validation tools

### Inventory Output:
- Complete script inventory with descriptions
- Existing automation tools I can leverage
- Health check and validation mechanisms
- Testing frameworks available

---

## 📋 EXPECTED DELIVERABLES

**Background Agent: Please provide these outputs:**

1. **STARTUP_SYSTEM_ANALYSIS.md** - Complete startup architecture analysis
2. **CONTAINER_MAPPING_VALIDATION.md** - Container architecture validation
3. **DOCKERFILE_OPTIMIZATION.md** - Docker patterns and optimization strategies  
4. **DEPENDENCY_MATRIX.md** - Dependency analysis and requirements optimization
5. **COMMUNICATION_ARCHITECTURE.md** - Inter-agent communication patterns
6. **TOOLS_INVENTORY.md** - Available scripts and automation tools

**Each document should include:**
- Current state analysis
- Problems identified
- Recommended solutions
- Implementation steps
- Code examples where applicable

---

## 🚨 CRITICAL SUCCESS FACTORS

**Background Agent: Focus on these outcomes:**

1. **Get containers running with correct startup commands**
2. **Validate agent group architecture is sound**
3. **Provide size optimization roadmap**  
4. **Ensure I understand the codebase patterns**
5. **Fill all my blind spots about the system architecture**

**I am standing by to implement your recommendations immediately upon completion of analysis.** 