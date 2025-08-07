# COMPREHENSIVE TESTING SUITE FOR AI SYSTEM
## MainPC & PC2 Agent Testing Framework

> Based on analysis of GitHub workflows and active agent configurations

---

## 📋 OVERVIEW

This comprehensive testing suite provides complete coverage for your MainPC and PC2 AI systems, including:

- **54 MainPC agents** (from `main_pc_code/config/startup_config.yaml`)
- **25 PC2 agents** (from `pc2_code/config/startup_config.yaml`)
- Cross-machine communication testing
- Service discovery and health monitoring
- Real-time system state analysis

---

## 🧪 TEST COMPONENTS

### 1. **Comprehensive Agent Tests** (`test/comprehensive_agent_tests.py`)
**Main testing engine that validates all active agents**

```bash
python3 test/comprehensive_agent_tests.py
```

**Features:**
- ✅ Parses startup configs automatically
- ✅ Tests port accessibility for all required agents
- ✅ Validates health endpoints
- ✅ Checks dependency chains
- ✅ Generates detailed JSON reports
- ✅ Pytest integration included

**Output:** `comprehensive_test_results.json`

### 2. **Agent Discovery Tests** (`test/agent_discovery_tests.py`)
**Dynamic discovery of running agents with detailed health analysis**

```bash
python3 test/agent_discovery_tests.py
```

**Features:**
- 🔍 Port range scanning (7100-7299, 8100-8299, 9000-9199, 5570-5799)
- 🩺 Multi-endpoint health checks (`/health`, `/status`, `/metrics`)
- ⚡ Response time measurement
- 🔗 Dependency relationship validation
- 📊 Performance metrics collection

**Output:** `agent_discovery_report.json`

### 3. **Cross-Machine Communication Tests** (`test/cross_machine_tests.py`)
**Validates communication between MainPC and PC2 systems**

```bash
python3 test/cross_machine_tests.py
```

**Features:**
- 🌉 ZMQ Bridge testing (port 5600)
- 👁️ ObservabilityHub synchronization (ports 9000, 9100)
- 📡 Service discovery validation
- 📊 Data transfer performance testing
- 🛡️ Failover resilience testing

**Output:** `cross_machine_test_results.json`

### 4. **Simple Current Check** (`SIMPLE_CURRENT_CHECK.py`)
**Quick system status checker without external dependencies**

```bash
python3 SIMPLE_CURRENT_CHECK.py
```

**Features:**
- 🚀 No external dependencies (pure Python)
- ⚡ Fast port connectivity checks
- 🐳 Docker container status
- 📁 Configuration file validation
- 🐍 Python process detection

### 5. **Basic Service Starter** (`start_basic_services.py`)
**Automated service startup for testing**

```bash
python3 start_basic_services.py
```

**Features:**
- 🔧 Starts Translation Proxy (port 5596)
- 🖥️ Starts GPU Scheduler (port 7155)
- ✅ Validates startup success
- 📝 Provides troubleshooting guidance

---

## 🤖 GITHUB WORKFLOW INTEGRATION

### **Comprehensive Agent Tests** (`.github/workflows/comprehensive-agent-tests.yml`)

**Automated CI/CD testing with multiple execution modes:**

```yaml
# Trigger Options:
workflow_dispatch:
  inputs:
    test_level: [quick, full, discovery-only, cross-machine-only]
    skip_services: true/false
```

**7 Integrated Jobs:**

1. **📋 Config Validation** - Validates YAML configs and counts agents
2. **🔍 Quick Discovery** - Fast agent discovery and health checks  
3. **🚀 Service Testing** - Starts services and runs comprehensive tests
4. **🌐 Cross-Machine** - Tests inter-system communication
5. **🧪 Pytest Integration** - Runs pytest test suite
6. **📊 Summary & Reporting** - Generates reports and PR comments
7. **📈 Health Monitoring** - Creates monitoring dashboard data

---

## 📊 CONFIGURATION ANALYSIS RESULTS

### **MainPC Agents (54 required agents identified):**

**Foundation Services:**
- ServiceRegistry (port 7200)
- SystemDigitalTwin (port 7220)  
- ObservabilityHub (port 9000)
- ModelManagerSuite (port 7211)
- RequestCoordinator (port 26002)

**Specialized Groups:**
- **Memory System:** MemoryClient, SessionMemoryAgent, KnowledgeBase
- **Learning & Knowledge:** LearningOrchestrationService, LearningManager
- **Language Processing:** ModelOrchestrator, GoalManager, NLUAgent
- **Vision Processing:** FaceRecognitionAgent
- **Reasoning Services:** ChainOfThoughtAgent, GOT_TOTAgent

### **PC2 Agents (25 required agents identified):**

**Core Infrastructure:**
- MemoryOrchestratorService (port 7140)
- ResourceManager (port 7113)
- ObservabilityHub (port 9100)
- CentralErrorBus (port 7150)

**Processing Pipeline:**
- TieredResponder, AsyncProcessor, TaskScheduler
- CacheManager, ContextManager, ExperienceTracker
- VisionProcessingAgent, DreamWorldAgent

**Cross-Machine Services (newly added):**
- CrossMachineGPUScheduler (port 7155) ✨
- StreamingTranslationProxy (port 5596) ✨

---

## 🚀 USAGE EXAMPLES

### Quick System Health Check
```bash
# 1. Check current system state
python3 SIMPLE_CURRENT_CHECK.py

# 2. Start basic services if needed
python3 start_basic_services.py

# 3. Run discovery tests
python3 test/agent_discovery_tests.py
```

### Full Comprehensive Testing
```bash
# 1. Run all comprehensive tests
python3 test/comprehensive_agent_tests.py

# 2. Test cross-machine communication
python3 test/cross_machine_tests.py

# 3. Check results
ls -la *.json
```

### CI/CD Integration
```bash
# Trigger GitHub workflow manually
gh workflow run comprehensive-agent-tests.yml \
  -f test_level=full \
  -f skip_services=false
```

### Pytest Integration
```bash
# Run specific test classes
pytest test/comprehensive_agent_tests.py::TestComprehensiveAgents -v

# Run with coverage
pytest test/ --cov=. --cov-report=html
```

---

## 📈 OUTPUT FORMATS

### **JSON Reports Structure:**
```json
{
  "timestamp": "2025-01-XX",
  "mainpc": {
    "agent_name": {
      "accessibility": {"port_accessible": true, "health_response": {...}},
      "dependencies": {"dependencies_satisfied": true}
    }
  },
  "pc2": {...},
  "cross_machine": {...},
  "summary": {
    "total_agents": 79,
    "accessible_agents": X,
    "healthy_agents": Y,
    "critical_issues": [...],
    "recommendations": [...]
  }
}
```

### **Human-Readable Summary:**
```
📊 COMPREHENSIVE TEST SUMMARY
================================
Total Agents Tested: 79
  MainPC: 54
  PC2: 25
Accessible Agents: X/79
Healthy Agents: Y/79
Cross-Machine Status: HEALTHY/DEGRADED/CRITICAL

🚨 CRITICAL ISSUES:
  • Issue 1
  • Issue 2

💡 RECOMMENDATIONS:
  • Action 1
  • Action 2
```

---

## 🔧 TROUBLESHOOTING

### **Common Issues:**

1. **No Services Running**
```bash
# Solution: Start basic services
python3 start_basic_services.py
```

2. **ZMQ Bridge Not Accessible**
```bash
# Check ZMQ process
ps aux | grep zmq
netstat -tlnp | grep 5600
```

3. **Health Endpoints Not Responding**
```bash
# Test specific endpoint
curl http://localhost:7220/health
curl http://localhost:9000/metrics
```

4. **Configuration Errors**
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('main_pc_code/config/startup_config.yaml'))"
```

---

## 🎯 SUCCESS CRITERIA

### **Healthy System Indicators:**
- ✅ 80%+ agents accessible
- ✅ All critical services running (ServiceRegistry, SystemDigitalTwin, ObservabilityHubs)
- ✅ Cross-machine communication working
- ✅ Average response time < 500ms
- ✅ No critical dependency chains broken

### **Exit Codes:**
- `0` - Success (80%+ healthy)
- `1` - Critical failure (no services)
- `2` - Warning (partial functionality)

---

## 📚 BASED ON ANALYSIS OF:

- ✅ **10 GitHub workflows** analyzed for testing patterns
- ✅ **MainPC startup config** - 54 required agents identified  
- ✅ **PC2 startup config** - 25 required agents identified
- ✅ **Cross-machine architecture** - ZMQ Bridge, ObservabilityHub sync
- ✅ **New services integration** - GPU Scheduler, Translation Proxy
- ✅ **Health check endpoints** - `/health`, `/status`, `/metrics`
- ✅ **Dependency relationships** - Service startup order and requirements

---

## 🚀 NEXT STEPS

1. **Run initial system assessment:**
   ```bash
   python3 SIMPLE_CURRENT_CHECK.py
   ```

2. **Start services if needed:**
   ```bash
   python3 start_basic_services.py
   ```

3. **Execute comprehensive tests:**
   ```bash
   python3 test/comprehensive_agent_tests.py
   ```

4. **Monitor results and address recommendations from the generated reports**

---

> **Note:** This testing suite is designed to work with both active production systems and CI/CD environments. Tests gracefully handle missing services and provide actionable recommendations for system improvements.