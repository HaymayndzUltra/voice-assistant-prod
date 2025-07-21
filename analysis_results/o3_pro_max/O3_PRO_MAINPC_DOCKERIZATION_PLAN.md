# 🐳 O3-PRO BACKGROUND AGENT: MAINPC DOCKERIZATION READINESS PLAN

## 📊 **MISSION OBJECTIVES**

**GOAL**: Prepare MainPC codebase for full Docker containerization by fixing all remaining syntax errors, import issues, and infrastructure gaps.

**CURRENT STATUS**: 
- ✅ Core unified error reporting implemented
- ✅ Critical PC2 agents fixed (AsyncProcessor, TieredResponder) 
- ✅ RequestCoordinator syntax errors resolved
- ❌ 30+ MainPC agents still have syntax/import errors
- ❌ Path management inconsistencies across codebase
- ❌ Health check standardization incomplete

**TARGET**: 100% error-free MainPC agents ready for Docker deployment

---

## 🎯 **PHASE 1: CRITICAL SYNTAX ERROR RESOLUTION (PRIORITY 1)**

### **P1.1: Fix Immediate Syntax Errors**

**TARGET AGENTS** (with confirmed syntax errors):
1. **NLUAgent** - `IndentationError: expected an indented block after 'if' statement on line 167`
2. **ModelManagerAgent** - Multiple import and path issues
3. **UnifiedSystemAgent** - Import path inconsistencies  
4. **CodeGeneratorAgent** - Error bus configuration issues
5. **VRAMOptimizerAgent** - Incomplete statements and import issues
6. **AdvancedCommandHandler** - Undefined function calls
7. **ModelOrchestrator** - Import and initialization issues
8. **ChitchatAgent** - Error bus setup problems
9. **ExecutorAgent** - Socket binding and configuration issues
10. **SessionMemoryAgent** - Error reporting setup issues

**ACTIONS REQUIRED:**
```bash
# For each agent, fix:
1. Indentation errors (missing blocks after if/for/while statements)
2. Undefined function calls (get_main_pc_code, join_path, etc.)
3. Circular import issues
4. Missing imports
5. Incomplete statements/expressions
```

### **P1.2: Path Management Standardization**

**PROBLEM**: Inconsistent path handling across agents
- Some use `get_main_pc_code()` (undefined)
- Some use `join_path()` (undefined) 
- Some have hardcoded paths
- Import paths are inconsistent

**SOLUTION**: Standardize to `PathManager` pattern:
```python
# Replace all instances of:
MAIN_PC_CODE_DIR = get_main_pc_code()  # ❌ BROKEN

# With:
from common.utils.path_manager import PathManager
project_root = PathManager.get_project_root()  # ✅ WORKING
```

### **P1.3: Import Path Unification**

**TARGET**: Fix all import issues across MainPC agents

**STANDARD PATTERN**:
```python
# At top of every agent file:
import sys
from pathlib import Path
from common.utils.path_manager import PathManager

# Add project root to path
project_root = PathManager.get_project_root()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now safe to import from common/main_pc_code
from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
```

---

## 🔧 **PHASE 2: INFRASTRUCTURE STANDARDIZATION (PRIORITY 2)**

### **P2.1: Error Reporting Standardization**

**TARGET**: All MainPC agents use unified error reporting

**CURRENT STATE**: Mixed implementations
- Some agents use old ZMQ error bus
- Some agents have broken error bus setup
- Some agents don't report errors at all

**REQUIRED CHANGES**:
```python
# Remove all custom error bus setup code like:
self.error_bus_port = 7150  # ❌ REMOVE
self.error_bus_host = get_service_ip("pc2")  # ❌ REMOVE
self.error_bus_pub = self.context.socket(zmq.PUB)  # ❌ REMOVE

# BaseAgent now handles all error reporting automatically ✅
self.report_error("error_type", "Error message", "critical")  # ✅ UNIFIED
```

### **P2.2: Health Check Standardization** 

**TARGET**: All agents use standardized health checking

**REQUIRED**: Ensure all agents properly implement:
```python
from common.health.standardized_health import StandardizedHealthChecker

# In __init__:
self.health_checker = StandardizedHealthChecker(
    agent_name=self.name,
    port=self.port
)
```

### **P2.3: Configuration Management Unification**

**TARGET**: All agents use unified config management

**REPLACE**:
```python
from main_pc_code.utils.config_loader import load_config  # ❌ OLD
config = load_config()

# WITH:
from common.config_manager import load_unified_config  # ✅ NEW
config = load_unified_config("main_pc_code/config/startup_config.yaml")
```

---

## 🐳 **PHASE 3: DOCKER READINESS (PRIORITY 3)**

### **P3.1: Environment Variable Standardization**

**TARGET**: All hardcoded IPs/ports use environment variables

**REPLACE PATTERNS**:
```python
# ❌ HARDCODED
host = "192.168.100.16"
port = 5556

# ✅ ENVIRONMENT-AWARE  
host = get_service_ip("mainpc")
port = int(os.environ.get("AGENT_PORT", "5556"))
```

### **P3.2: File Path Dockerization**

**TARGET**: All file paths work in Docker containers

**ENSURE PATTERNS**:
```python
# ✅ DOCKER-SAFE PATHS
logs_dir = Path("/app/logs")  # Inside container
models_dir = Path("/app/models")  # Mounted volume
config_dir = Path("/app/config")  # Configuration mount
```

### **P3.3: Dependency Verification**

**TARGET**: All agent dependencies are properly defined

**REQUIRED**: For each agent, verify:
1. Python package dependencies listed in requirements.txt
2. Inter-agent dependencies defined in startup_config.yaml
3. External service dependencies (Redis, NATS) properly configured
4. Model dependencies clearly specified

---

## 📋 **DETAILED EXECUTION COMMANDS**

### **COMMAND SEQUENCE FOR O3-PRO BACKGROUND AGENT:**

```bash
# PHASE 1: SYNTAX FIXES
# Command 1: Fix NLU Agent indentation error
sed -i '167,169s/^/    /' main_pc_code/agents/nlu_agent.py

# Command 2: Standardize path imports across all agents
find main_pc_code/agents -name "*.py" -exec sed -i 's/get_main_pc_code()/PathManager.get_project_root()/g' {} \;
find main_pc_code/agents -name "*.py" -exec sed -i 's/join_path/Path/g' {} \;

# Command 3: Remove undefined imports
find main_pc_code/agents -name "*.py" -exec sed -i '/from.*path_env.*import.*join_path/d' {} \;

# Command 4: Add standard imports to all agents
for agent in main_pc_code/agents/*.py; do
    if ! grep -q "PathManager" "$agent"; then
        sed -i '1i from common.utils.path_manager import PathManager' "$agent"
    fi
done

# PHASE 2: INFRASTRUCTURE
# Command 5: Remove custom error bus code
find main_pc_code/agents -name "*.py" -exec sed -i '/self\.error_bus_port/d' {} \;
find main_pc_code/agents -name "*.py" -exec sed -i '/self\.error_bus_host/d' {} \;
find main_pc_code/agents -name "*.py" -exec sed -i '/self\.error_bus_pub/d' {} \;

# Command 6: Standardize config loading
find main_pc_code/agents -name "*.py" -exec sed -i 's/from main_pc_code.utils.config_loader import load_config/from common.config_manager import load_unified_config/g' {} \;

# PHASE 3: DOCKER READINESS  
# Command 7: Replace hardcoded IPs
find main_pc_code/agents -name "*.py" -exec sed -i 's/"192\.168\.100\.[0-9]*"/get_service_ip("mainpc")/g' {} \;

# Command 8: Validate all agents compile
for agent in main_pc_code/agents/*.py; do
    python3 -m py_compile "$agent" || echo "SYNTAX ERROR in $agent"
done

# Command 9: Generate dependency map
python3 -c "
import yaml
with open('main_pc_code/config/startup_config.yaml') as f:
    config = yaml.safe_load(f)
    
agents = {}
for group_name, group_agents in config['agent_groups'].items():
    for agent_name, agent_config in group_agents.items():
        agents[agent_name] = {
            'script': agent_config.get('script_path'),
            'port': agent_config.get('port'),
            'dependencies': agent_config.get('dependencies', []),
            'group': group_name
        }

with open('mainpc_agent_dependencies.json', 'w') as f:
    import json
    json.dump(agents, f, indent=2)
print('Generated mainpc_agent_dependencies.json')
"

# Command 10: Create Docker health check validation
python3 main_pc_code/scripts/health_check_client.py --validate-all-agents
```

---

## 🎯 **SUCCESS CRITERIA**

### **PHASE 1 SUCCESS METRICS:**
- [ ] All 50+ MainPC agents compile without syntax errors
- [ ] No undefined function calls (get_main_pc_code, join_path, etc.)
- [ ] No circular imports
- [ ] Consistent import patterns across all agents

### **PHASE 2 SUCCESS METRICS:**
- [ ] All agents use unified error reporting (BaseAgent.report_error)
- [ ] All agents use standardized health checking
- [ ] All agents use unified config management
- [ ] No custom error bus implementation code

### **PHASE 3 SUCCESS METRICS:**
- [ ] No hardcoded IP addresses or file paths
- [ ] All environment variables properly defined
- [ ] All dependencies clearly mapped
- [ ] Docker Compose file validates successfully

---

## 🚀 **FINAL DELIVERABLES**

**EXPECTED OUTPUTS:**
1. **mainpc_syntax_fixes.log** - Complete log of all syntax errors fixed
2. **mainpc_agent_dependencies.json** - Full dependency mapping
3. **docker-compose.mainpc.READY.yml** - Production-ready Docker configuration
4. **MAINPC_DOCKERIZATION_REPORT.md** - Complete validation report

**VALIDATION COMMANDS:**
```bash
# Final validation suite
docker compose -f docker-compose.mainpc.READY.yml config  # Validate compose file
python3 main_pc_code/scripts/start_system_v2.py --validate-only  # Validate startup
python3 -m pytest tests/ -v  # Run all tests
```

---

## ⚠️ **CRITICAL NOTES FOR O3-PRO AGENT**

1. **BACKUP FIRST**: Create branch backup before making bulk changes
2. **INCREMENTAL TESTING**: Test after each phase, don't proceed if errors remain
3. **DEPENDENCY ORDER**: Fix syntax errors before infrastructure changes
4. **PRESERVE FUNCTIONALITY**: Maintain all existing agent behaviors
5. **DOCKER CONTEXT**: All changes must work in containerized environment

**ESTIMATED COMPLETION**: 4-6 hours for complete MainPC dockerization readiness

**STATUS**: 🚀 **READY FOR O3-PRO BACKGROUND AGENT EXECUTION** 