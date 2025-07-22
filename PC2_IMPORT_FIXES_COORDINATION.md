# 🤝 PC2 AI IMPORT FIXES - PARALLEL WORK COORDINATION

## 📊 CURRENT STATUS
- **Total Agents**: 81 (54 MainPC + 27 PC2)
- **Import Success Rate**: 14/81 (17%) ❌
- **Target Success Rate**: 65+/81 (80%+) ✅

## 🎯 WORK DIVISION

### MAINPC AI (Current Session) - 54 agents
**I will handle all MainPC agents** including:
- Fix `get_project_root()` / `get_main_pc_code()` imports
- Fix `PathManager` import issues  
- Fix `ErrorSeverity` import problems
- Fix config file and permission issues
- Fix typos (`aseAgent` → `BaseAgent`)

### PC2 AI (Your Responsibility) - 27 agents
**You must handle all PC2 agents** with these specific issues:

## 🔧 PC2 SPECIFIC IMPORT PATTERNS TO FIX

### PATTERN 1: Missing error_bus_template Module (6 agents)
**Agents affected:**
- `tiered_responder.py`
- `async_processor.py` 
- `DreamWorldAgent.py`
- `tutor_agent.py`
- `remote_connector_agent.py`
- `advanced_router.py`

**Fix Required:**
```python
# CREATE this missing module: pc2_code/agents/error_bus_template.py
# Content should be a simple error bus interface that agents can import
```

### PATTERN 2: Path Concatenation Issues (8 agents)
**Error:** `unsupported operand type(s) for /: 'str' and 'str'`

**Fix Required:**
```python
# WRONG:
path = "some/path" / "file.txt"  # str + Path operator fails

# CORRECT:
from pathlib import Path
path = Path("some/path") / "file.txt"  # Convert str to Path first
```

### PATTERN 3: Missing get_pc2_code Import (Multiple agents)
**Error:** `name 'get_pc2_code' is not defined`

**Fix Required:**
```python
# Add this import at the top:
from common.utils.path_env import get_pc2_code

# Or use PathManager instead:
from common.utils.path_manager import PathManager
pc2_code_path = PathManager.get_project_root() / "pc2_code"
```

### PATTERN 4: as_posix Attribute Issues (4 agents)
**Error:** `'str' object has no attribute 'as_posix'`

**Fix Required:**
```python
# WRONG:
path_str = "some/path"
posix_path = path_str.as_posix()  # str has no as_posix method

# CORRECT:
from pathlib import Path
path_obj = Path("some/path")
posix_path = path_obj.as_posix()  # Path object has as_posix
```

### PATTERN 5: join_path Usage (Remaining instances)
**Error:** `name 'join_path' is not defined`

**Fix Required:**
```python
# WRONG:
path = join_path("dir", "file")  # join_path not imported

# CORRECT:
from pathlib import Path
path = Path("dir") / "file"  # Use pathlib instead
```

## 🚨 CRITICAL REQUIREMENTS - PRESERVE FUNCTIONALITY

### ✅ DO NOT BREAK EXISTING FUNCTIONALITY
1. **Test imports after each fix** - Import each agent after modification
2. **Preserve original logic** - Only fix imports, don't change business logic
3. **Maintain error handling** - Keep existing try/catch blocks
4. **Keep configuration loading** - Don't modify config file access patterns

### ✅ TESTING APPROACH
```bash
# After each fix, test the agent:
python3 -c "import pc2_code.agents.AGENT_NAME"

# If successful: ✅ Continue to next agent
# If failed: ❌ Revert and try different approach
```

### ✅ IMPORT STANDARDS TO FOLLOW
```python
# Standard header for all PC2 agents:
import sys
from pathlib import Path
from common.utils.path_manager import PathManager

# Add project root to path
project_root = str(PathManager.get_project_root())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import other modules
from common.core.base_agent import BaseAgent
# ... other imports
```

## 📋 PRIORITY ORDER FOR PC2 AI

1. **HIGHEST**: Create `pc2_code/agents/error_bus_template.py` (fixes 6 agents immediately)
2. **HIGH**: Fix path concatenation issues (8 agents)
3. **MEDIUM**: Fix get_pc2_code imports (multiple agents)
4. **LOW**: Fix as_posix attribute issues (4 agents)

## 🎯 SUCCESS METRICS

**Before Fixes:**
- PC2 Success Rate: 0/27 (0%) ❌

**After Fixes Target:**
- PC2 Success Rate: 22+/27 (80%+) ✅
- Combined System: 65+/81 (80%+) ✅

## ⚠️ COORDINATION RULES

1. **NO MAINPC FILE MODIFICATIONS** - Only touch `pc2_code/` directory
2. **NO SHARED FILE CHANGES** - Don't modify `common/` files
3. **REPORT PROGRESS** - Update when major milestones achieved
4. **ASK IF STUCK** - Don't guess, ask for clarification

## 📞 COMMUNICATION PROTOCOL

**When to notify MainPC AI:**
- ✅ Completed error_bus_template creation
- ✅ Fixed major import pattern (5+ agents)  
- ❌ Stuck on specific error pattern
- ❌ Need shared file modification

**Expected Timeline:**
- **Phase 1**: Create error_bus_template (15 mins)
- **Phase 2**: Fix path concatenation (20 mins)
- **Phase 3**: Fix remaining imports (15 mins)
- **Total**: ~50 minutes for 22+ working agents

## 🏁 FINAL VALIDATION

After both AIs complete their work:
```bash
python3 validate_all_agents.py
# Target: 65+/81 agents (80%+) importing successfully
```

**Ready to start? Begin with creating error_bus_template.py first!** 🚀

---

## 📋 COMPLETE PC2 AGENT LIST (27 agents):
```
Core PC2 Agents:
- tutoring_agent.py
- experience_tracker.py
- memory_orchestrator_service.py
- cache_manager.py
- VisionProcessingAgent.py
- DreamWorldAgent.py
- unified_memory_reasoning_agent.py
- tutor_agent.py
- context_manager.py
- resource_manager.py
- task_scheduler.py
- AgentTrustScorer.py
- filesystem_assistant_agent.py
- remote_connector_agent.py
- unified_web_agent.py
- DreamingModeAgent.py
- advanced_router.py
- PerformanceLoggerAgent.py
- tutoring_service_agent.py

ForPC2 Specialized:
- AuthenticationAgent.py
- unified_utils_agent.py
- proactive_context_monitor.py

Shared Services:
- observability_hub.py (runs on both machines)
```

## 🎯 ERROR_BUS_TEMPLATE.PY TEMPLATE

**Create this file first**: `pc2_code/agents/error_bus_template.py`

```python
"""
Error Bus Template - Legacy compatibility interface
Provides basic error bus interface for PC2 agents that require it
"""

import json
import zmq
from datetime import datetime
from typing import Dict, Any, Optional

class ErrorBusTemplate:
    """Simple error bus interface for backward compatibility"""
    
    def __init__(self):
        self.context = zmq.Context()
        self.publisher = None
        
    def connect(self, endpoint: str):
        """Connect to error bus endpoint"""
        try:
            self.publisher = self.context.socket(zmq.PUB)
            self.publisher.connect(endpoint)
        except Exception as e:
            print(f"Error bus connection failed: {e}")
    
    def publish_error(self, error_type: str, message: str, severity: str = "ERROR", context: Optional[Dict[str, Any]] = None):
        """Publish error message to bus"""
        try:
            if self.publisher:
                error_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "error_type": error_type,
                    "message": message,
                    "severity": severity,
                    "context": context or {}
                }
                self.publisher.send_string(f"ERROR:{json.dumps(error_data)}")
        except Exception as e:
            print(f"Failed to publish error: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.publisher:
                self.publisher.close()
            self.context.term()
        except Exception:
            pass

# Global instance for backward compatibility
error_bus = ErrorBusTemplate()

def report_error(error_type: str, message: str, severity: str = "ERROR", context: Optional[Dict[str, Any]] = None):
    """Global function for error reporting"""
    error_bus.publish_error(error_type, message, severity, context)
```

**This template will immediately fix 6 agents that import from error_bus_template!** 