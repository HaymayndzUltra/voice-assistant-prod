# 🚀 AGENT PATTERNS QUICK REFERENCE
## Essential Checklist for Modern Agents

---

## **🔍 6 CRITICAL PATTERNS TO CHECK**

### **✅ PATTERN 1: PATH MANAGEMENT**
```python
# ✅ MODERN:
from common.utils.path_manager import PathManager
PROJECT_ROOT = PathManager.get_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

# ❌ LEGACY:
from common.utils.path_env import join_path
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
```

### **✅ PATTERN 2: BASE AGENT IMPORT**
```python
# ✅ CORRECT:
from common.core.base_agent import BaseAgent

# ❌ WRONG:
from main_pc_code.src.core.base_agent import BaseAgent
```

### **✅ PATTERN 3: SECURE ZMQ**
```python
# ✅ COMMENT OUT:
# from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled

# ❌ IMPORT NON-EXISTENT:
from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled
```

### **✅ PATTERN 4: ERROR REPORTING**
```python
# ✅ USE BASEAGENT:
self.report_error(f"Error: {e}")

# ❌ CUSTOM ZMQ:
error_socket = zmq.Context().socket(zmq.PUSH)
```

### **✅ PATTERN 5: HEALTH CHECKS**
```python
# ✅ AUTOMATIC:
class Agent(BaseAgent):  # Health is built-in

# ❌ CUSTOM REDIS:
self.redis_client = redis.Redis(...)
```

### **✅ PATTERN 6: CLEANUP**
```python
# ✅ GOLD STANDARD:
def cleanup(self):
    cleanup_errors = []
    try:
        # agent cleanup
    except Exception as e:
        cleanup_errors.append(f"Error: {e}")
    finally:
        super().cleanup()  # ALWAYS in finally!

# ❌ NO GUARANTEE:
def cleanup(self):
    # cleanup
    super().cleanup()  # Could be skipped
```

---

## **📋 QUICK INSPECTION COMMANDS**

### **🧪 Test Import:**
```bash
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('agent', 'path/to/agent.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print('✅ Working')
"
```

### **🔍 Check Patterns:**
```bash
# Check for wrong patterns
| grep -n "join_path\ | src/core\ | src/network" agent.py |
grep -n "as_posix()" agent.py
grep -n "class.*BaseAgent" agent.py
```

---

## **🎯 SUCCESS CRITERIA**

### **✅ COMPLETE AGENT:**
- ✅ Import successful (no ModuleNotFoundError)
- ✅ Instantiation works (agent = AgentClass())
- ✅ All 6 patterns correct
- ✅ No legacy/anti-patterns

### **❌ BROKEN AGENT:**
- ❌ Import failures
- ❌ Legacy join_path usage
- ❌ Wrong BaseAgent path (src/core)
- ❌ Missing cleanup guarantee

---

**🎯 Use this as your agent checklist during development!**