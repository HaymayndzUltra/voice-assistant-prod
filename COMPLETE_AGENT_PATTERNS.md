# 📋 COMPLETE AGENT PATTERNS - MODERNIZATION CHECKLIST
## Comprehensive Guide for Fully Modern Agents

**Date:** January 22, 2025  
**Purpose:** Show exact patterns for complete agent modernization  
**Scope:** Both MainPC and PC2 agents

---

## **🎯 COMPLETE AGENT STRUCTURE**

### **📝 Template: Perfect Modern Agent**
```python
#!/usr/bin/env python3
"""
[Agent Name] - Modern Implementation
Description: [What this agent does]
"""

# ===== SECTION 1: STANDARD IMPORTS =====
import sys
import os
import logging
import time
import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# ===== SECTION 2: PATH MANAGEMENT (MODERN) =====
# ✅ CORRECT: Use PathManager for all path operations
from common.utils.path_manager import PathManager
from common.utils.path_env import get_main_pc_code, get_project_root

# Add project root to path
PROJECT_ROOT = PathManager.get_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ===== SECTION 3: BASE AGENT & CONFIG =====
# ✅ CORRECT: Import from common/core (not src/core)
from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url

# ===== SECTION 4: COMMUNICATION IMPORTS =====
# For ZMQ communication
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket

# For NATS (modern error bus)
# Note: UnifiedErrorHandler comes from BaseAgent

# ===== SECTION 5: SPECIALIZED IMPORTS =====
# Agent-specific imports here
# Example: redis, numpy, torch, etc.

# ===== SECTION 6: AGENT CLASS DEFINITION =====
class ModernAgent(BaseAgent):
    """
    Modern agent following all best practices
    """
    
    def __init__(self, name: str = "ModernAgent", **kwargs):
        # ✅ CORRECT: Call super().__init__ first
        super().__init__(
            name=name,
            agent_type="modern",
            **kwargs
        )
        
        # Agent-specific initialization
        self.setup_agent_specific_resources()
    
    def setup_agent_specific_resources(self):
        """Setup agent-specific resources"""
        try:
            # Agent-specific setup here
            self.logger.info(f"Setting up {self.name} resources...")
            
        except Exception as e:
            # ✅ CORRECT: Use BaseAgent's error reporting
            self.report_error(f"Resource setup failed: {e}")
    
    async def start(self):
        """Start the agent"""
        try:
            # ✅ CORRECT: Call parent start first
            await super().start()
            
            # Agent-specific startup logic
            self.logger.info(f"{self.name} started successfully")
            
        except Exception as e:
            self.report_error(f"Agent start failed: {e}")
            raise
    
    async def stop(self):
        """Stop the agent"""
        try:
            self.logger.info(f"Stopping {self.name}...")
            
            # Agent-specific cleanup here
            
            # ✅ CORRECT: Call parent stop
            await super().stop()
            
        except Exception as e:
            self.report_error(f"Agent stop failed: {e}")
    
    def cleanup(self):
        """
        ✅ GOLD STANDARD: Cleanup with try...finally guarantee
        """
        self.logger.info(f"🚀 Starting cleanup for {self.name}...")
        cleanup_errors = []
        
        try:
            # Agent-specific cleanup steps
            self.logger.info("Cleaning up agent-specific resources...")
            
            # Example cleanup steps:
            # - Close connections
            # - Save state
            # - Release resources
            
        except Exception as e:
            cleanup_errors.append(f"Agent cleanup error: {e}")
            self.logger.error(f"❌ Agent cleanup failed: {e}")
        
        finally:
            # ✅ CRITICAL: Always call parent cleanup
            self.logger.info("Final Step: Calling BaseAgent cleanup...")
            try:
                super().cleanup()
                self.logger.info("✅ BaseAgent cleanup completed successfully")
            except Exception as e:
                cleanup_errors.append(f"BaseAgent cleanup error: {e}")
                self.logger.error(f"❌ BaseAgent cleanup failed: {e}")
        
        # Report cleanup status
        if cleanup_errors:
            self.logger.warning(f"⚠️ Cleanup completed with {len(cleanup_errors)} error(s)")
            for i, err in enumerate(cleanup_errors):
                self.logger.warning(f"   - Error {i+1}: {err}")
        else:
            self.logger.info(f"✅ Cleanup for {self.name} completed perfectly")

# ===== SECTION 7: MAIN EXECUTION =====
def main():
    """Main execution function"""
    agent = None
    try:
        agent = ModernAgent()
        
        # Run the agent
        import asyncio
        asyncio.run(agent.start())
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Agent interrupted by user")
    except Exception as e:
        print(f"Agent failed: {e}")
    finally:
        if agent:
            agent.cleanup()

if __name__ == "__main__":
    main()
```

---

## **🚨 CRITICAL PATTERNS TO CHECK**

### **✅ PATTERN 1: PATH MANAGEMENT**
```python
# ✅ CORRECT - Modern PathManager approach:
from common.utils.path_manager import PathManager
from common.utils.path_env import get_main_pc_code, get_project_root

PROJECT_ROOT = PathManager.get_project_root()
sys.path.insert(0, str(PROJECT_ROOT))

# ❌ WRONG - Legacy join_path approach:
from common.utils.path_env import join_path
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
```

### **✅ PATTERN 2: BASE AGENT IMPORT**
```python
# ✅ CORRECT - Common core path:
from common.core.base_agent import BaseAgent

# ❌ WRONG - Old src path:
from main_pc_code.src.core.base_agent import BaseAgent
from pc2_code.src.core.base_agent import BaseAgent
```

### **✅ PATTERN 3: SECURE ZMQ HANDLING**
```python
# ✅ CORRECT - Comment out non-existent imports:
# from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled

# If needed, create simple placeholders:
def is_secure_zmq_enabled() -> bool:
    """Placeholder for secure ZMQ check"""
    return False

# ❌ WRONG - Import non-existent modules:
from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled
```

### **✅ PATTERN 4: ERROR REPORTING**
```python
# ✅ CORRECT - Use BaseAgent's UnifiedErrorHandler:
class ModernAgent(BaseAgent):
    def some_method(self):
        try:
            # Some operation
            pass
        except Exception as e:
            # Use inherited error reporting
            self.report_error(f"Operation failed: {e}")

# ❌ WRONG - Custom ZMQ error bus:
class OldAgent:
    def setup_error_bus(self):
        self.error_socket = zmq.Context().socket(zmq.PUSH)
        # ... custom error handling
```

### **✅ PATTERN 5: HEALTH CHECKS**
```python
# ✅ CORRECT - Use BaseAgent's StandardizedHealthChecker:
class ModernAgent(BaseAgent):
    # Health checking is automatic via BaseAgent
    pass

# ❌ WRONG - Custom Redis health system:
class OldAgent:
    def setup_health_check(self):
        self.redis_client = redis.Redis(...)
        # ... custom health implementation
```

### **✅ PATTERN 6: CLEANUP PATTERN**
```python
# ✅ GOLD STANDARD - try...finally pattern:
def cleanup(self):
    cleanup_errors = []
    try:
        # Agent-specific cleanup
        pass
    except Exception as e:
        cleanup_errors.append(f"Agent cleanup: {e}")
    finally:
        # ALWAYS call parent cleanup
        try:
            super().cleanup()
        except Exception as e:
            cleanup_errors.append(f"BaseAgent cleanup: {e}")

# ❌ WRONG - No guaranteed parent cleanup:
def cleanup(self):
    # Agent cleanup
    super().cleanup()  # Could be skipped if error above
```

---

## **🔍 INSPECTION CHECKLIST**

### **📋 For MainPC Agents:**
```bash
✅ Check: from common.utils.path_manager import PathManager
✅ Check: from common.core.base_agent import BaseAgent
✅ Check: No "from main_pc_code.src.core.base_agent"
✅ Check: No "from main_pc_code.src.network.secure_zmq"
✅ Check: No ".as_posix()" on string objects
✅ Check: No custom ZMQ error bus setup
✅ Check: class [Agent](BaseAgent): inheritance
✅ Check: super().__init__ in constructor
✅ Check: try...finally in cleanup method
✅ Check: super().cleanup() in finally block
```

### **📋 For PC2 Agents:**
```bash
✅ Check: from common.utils.path_manager import PathManager
✅ Check: from common.core.base_agent import BaseAgent
✅ Check: No legacy join_path usage
✅ Check: No custom error bus implementation
✅ Check: Modern config loading patterns
✅ Check: Proper BaseAgent inheritance
✅ Check: Standard health check integration
✅ Check: Gold standard cleanup pattern
```

---

## **🧪 TESTING PATTERNS**

### **✅ IMPORT TEST:**
```python
# Test agent can be imported
import importlib.util
spec = importlib.util.spec_from_file_location("agent_name", "path/to/agent.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print("✅ Import successful")
```

### **✅ INSTANTIATION TEST:**
```python
# Test agent can be instantiated
agent_class = getattr(module, "AgentClassName")
agent = agent_class()
print("✅ Instantiation successful")
```

### **✅ BASIC FUNCTIONALITY TEST:**
```python
# Test basic agent methods
agent.setup_agent_specific_resources()
# await agent.start()  # For async agents
agent.cleanup()
print("✅ Basic functionality working")
```

---

## **🎯 SUCCESS CRITERIA**

### **✅ COMPLETE MODERN AGENT:**
```bash
📋 Imports: All modern imports present
🔧 Patterns: All 6 critical patterns correct
🧪 Testing: Passes import + instantiation + basic functionality
📊 Quality: No legacy patterns or anti-patterns
🎯 Result: Ready for production deployment
```

### **🚨 INCOMPLETE AGENT:**
```bash
❌ Import failures (ModuleNotFoundError, ImportError)
❌ Legacy patterns (join_path, src/core imports)
❌ Missing BaseAgent inheritance
❌ No proper cleanup pattern
❌ Custom error bus instead of UnifiedErrorHandler
```

---

## **💡 QUICK DIAGNOSTIC COMMANDS**

### **🔍 Check Agent Status:**
```bash
# Test single agent
python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('agent', 'path/to/agent.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print('✅ Agent working')
"
```

### **🔍 Check Patterns:**
```bash
# Check for legacy patterns
grep -n "join_path\|src/core\|src/network" agent_file.py
grep -n "class.*BaseAgent" agent_file.py
grep -n "super().__init__\|super().cleanup" agent_file.py
```

**YAN ANG COMPLETE PATTERNS na dapat makita sa modernized agent! 🎯** 