# TECHNICAL DEBUGGING CONTEXT

**Background Agent: Detailed technical context for "0 phases detected" debugging**

---

## 🔧 **EXACT IMPLEMENTATION DETAILS**

### **Current Container Commands:**
```yaml
# docker/docker-compose.mainpc.yml - All 11 services have:
command: ["python", "/app/main_pc_code/scripts/start_system.py", "--group", "<group_name>"]

# Examples:
core-services:     ["python", "/app/main_pc_code/scripts/start_system.py", "--group", "core_services"]
memory-system:     ["python", "/app/main_pc_code/scripts/start_system.py", "--group", "memory_system"]
gpu-infrastructure: ["python", "/app/main_pc_code/scripts/start_system.py", "--group", "gpu_infrastructure"]
```

### **Environment Variables (All Containers):**
```yaml
environment:
  - PYTHONPATH=/app:/app/main_pc_code:/app/common
  - LOG_LEVEL=INFO
  - DEBUG_MODE=false
  - ENABLE_METRICS=true
  - ENABLE_TRACING=true
```

### **Import Path Fix Applied:**
```python
# Added to main_pc_code/scripts/start_system.py (line 11-14):
app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if app_root not in sys.path:
    sys.path.insert(0, app_root)
```

---

## 📁 **FILE LOCATIONS & VERIFICATION**

### **Key Files in Container:**
```bash
# Verified accessible in containers:
/app/main_pc_code/config/startup_config.yaml (15014 bytes)
/app/main_pc_code/scripts/start_system.py (270 lines)
/app/common/env_helpers.py (98 lines)

# Directory structure:
/app/
├── main_pc_code/
│   ├── config/startup_config.yaml
│   ├── scripts/start_system.py
│   └── agents/ (58 agent files)
├── common/
│   └── env_helpers.py
└── requirements/ (new split structure)
```

### **startup_config.yaml Structure:**
```yaml
# Expected structure from local file:
global_settings: {...}
agent_groups:
  core_services:
    ServiceRegistry:
      script_path: main_pc_code/agents/service_registry_agent.py
      port: 7200
      health_check_port: 8200
      required: true
      dependencies: []
    SystemDigitalTwin:
      script_path: main_pc_code/agents/system_digital_twin.py
      port: 7220
      health_check_port: 8220
      dependencies: [ServiceRegistry]
    # ... more agents

  memory_system: {...}
  gpu_infrastructure: {...}
  # ... 11 groups total
```

---

## 🔍 **DEBUGGING BEHAVIOR OBSERVED**

### **Successful Parts:**
```bash
# 1. Container startup:
✅ All 11 containers start without crashes
✅ No "No module named main_pc_code.startup" error
✅ No "ModuleNotFoundError: No module named 'common'" error

# 2. Script execution:
✅ start_system.py runs without Python import errors
✅ Configuration loading starts: "[SYSTEM STARTUP] Loading configuration..."
✅ Clean exit: Exit code 0 (not crash)
```

### **Problematic Behavior:**
```bash
# Output pattern (ALL containers):
[SYSTEM STARTUP] Loading configuration and resolving dependencies...
[SYSTEM STARTUP] 0 phases detected.
[SYSTEM STARTUP] All phases complete. System is fully started.

# Expected behavior:
[SYSTEM STARTUP] Loading configuration and resolving dependencies...
[SYSTEM STARTUP] Phase 1: Starting core_services (6 agents)
[AGENT START] ServiceRegistry on port 7200...
[AGENT START] SystemDigitalTwin on port 7220...
# ... etc
```

---

## 🧪 **SPECIFIC TESTS TO REPRODUCE**

### **Container Test Commands:**
```bash
# 1. Basic script test:
docker run --rm -e PYTHONPATH=/app:/app/main_pc_code:/app/common \
  ai-system/core-services:optimized \
  python /app/main_pc_code/scripts/start_system.py --help

# 2. Group filtering test:
docker run --rm -e PYTHONPATH=/app:/app/main_pc_code:/app/common \
  ai-system/core-services:optimized \
  python /app/main_pc_code/scripts/start_system.py --group core_services

# 3. Config file validation:
docker run --rm ai-system/core-services:optimized \
  head -50 /app/main_pc_code/config/startup_config.yaml

# 4. Agent script path validation:
docker run --rm ai-system/core-services:optimized \
  ls -la /app/main_pc_code/agents/service_registry_agent.py
```

---

## 🎯 **SUSPECTED DEBUG AREAS**

### **1. Configuration Parsing Logic:**
```python
# Check in start_system.py:
def load_config():
    # Is startup_config.yaml being parsed correctly?
    # Are agent_groups being loaded?
    # Is the YAML structure valid?
```

### **2. Group Filtering Implementation:**
```python
# Check argument parsing:
if __name__ == "__main__":
    # Is --group parameter being parsed correctly?
    # Is group name matching config keys?
    # Is case sensitivity an issue?
```

### **3. Agent Script Path Resolution:**
```python
# Check script_path validation:
for agent in group_agents:
    script_path = agent.get('script_path')
    # Do these paths exist in container?
    # Are they absolute vs relative path issues?
```

### **4. Dependency Resolution Algorithm:**
```python
# Check phase generation:
def build_dependency_graph():
    # Is the dependency graph being built?
    # Are phases being generated from dependencies?
    # Is the algorithm working with current agent structure?
```

---

## 🚨 **CRITICAL DEBUGGING QUESTIONS**

### **For Background Agent Analysis:**

1. **Configuration Loading:**
   - Is `startup_config.yaml` being parsed correctly by PyYAML?
   - Are the `agent_groups` section keys matching command line `--group` values?
   - Is there a case sensitivity issue (core_services vs core-services)?

2. **Group Filtering Logic:**
   - Does the group filtering logic in `start_system.py` work correctly?
   - Is the `--group` argument being processed properly?
   - Are empty groups causing "0 phases detected"?

3. **Script Path Validation:**
   - Do the agent script paths in `startup_config.yaml` exist in containers?
   - Are there absolute vs relative path issues?
   - Are file permissions correct for agent scripts?

4. **Dependency Resolution:**
   - Is the dependency graph algorithm working?
   - Are agents with no dependencies being detected?
   - Is the phase generation logic correct?

---

## 📊 **CURRENT SUCCESS METRICS**

```
✅ Container Optimization: 49% space reduction (132GB → 67GB)
✅ Startup Fix: No crashes, clean container startup
✅ Import Resolution: All Python import errors fixed
✅ Infrastructure: Redis, NATS, networks working
❌ Agent Execution: "0 phases detected" preventing agent startup

Success Rate: 80% complete
Blocking Issue: Agent phase detection and execution
```

### **Expected Outcome:**
```bash
# Target successful output:
[SYSTEM STARTUP] Loading configuration and resolving dependencies...
[SYSTEM STARTUP] Phase 1: Starting core_services (6 agents)
[AGENT START] ServiceRegistry starting on port 7200...
[AGENT HEALTH] ServiceRegistry healthy at localhost:8200
[AGENT START] SystemDigitalTwin starting on port 7220...
[SYSTEM STARTUP] Phase 1 complete. Starting Phase 2...
```

**Background Agent: Please perform deep analysis to identify and fix the "0 phases detected" root cause!** 🔍 