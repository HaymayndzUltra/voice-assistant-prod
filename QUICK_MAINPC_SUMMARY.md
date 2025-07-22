# 🚀 QUICK MAINPC AI COORDINATION SUMMARY

## 📋 WORK DIVISION:

### ❌ PC2 AI FILES (HANDS OFF):
- **request_coordinator.py** (relative imports)
- **HumanAwarenessAgent.py** (BaseAgent + .as_posix() issues)
- **15+ agents with .as_posix() errors** (runtime crashes)

### ✅ MAINPC AI TASKS:
1. **Secure ZMQ cleanup** (12 agents) - Remove non-existent imports
2. **join_path modernization** (8 agents) - Convert to PathManager  
3. **Startup config validation** (25+ agents) - Test functionality

## 🔧 KEY PATTERNS:

### Pattern 1: Secure ZMQ Fix
```python
# Remove:
from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled
# Add:
def is_secure_zmq_enabled() -> bool:
    return False
```

### Pattern 2: join_path Fix  
```python
# Remove:
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
# Add:
sys.path.insert(0, str(PathManager.get_project_root()))
```

### Pattern 3: Testing
```python
# Use importlib.util, NOT exec()
spec = importlib.util.spec_from_file_location(name, path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
```

## 🎯 TARGET: 40% → 70%+ functional agents

**Read full details in MAINPC_AI_SESSION_INSTRUCTIONS.md** 