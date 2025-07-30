# Step 2: Imports & Class Mapping
## AI System Monorepo Agent Analysis - Imports and Class Structure

**Analysis Date:** 2025-07-31T01:49:30+08:00  
**Analyzer:** CASCADE AI Assistant  
**Task:** Step 2 from active tasks queue - Imports & Class Mapping

---

## COMPREHENSIVE IMPORTS & CLASS MAPPING

### **1. MAIN PC CODE AGENTS**

#### **NLU Agent (`main_pc_code/agents/nlu_agent.py`)**

**Standard Library Imports:**
```python
import os
import sys
import json
import time
import logging
import threading
import traceback
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
```

**Project Common Imports:**
```python
from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url, load_unified_config
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
from common.utils.path_manager import PathManager
```

**Enhanced Capabilities (Conditional):**
```python
try:
    from common.core.enhanced_base_agent import EnhancedBaseAgent, PerformanceMetrics
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False
```

**Agent-Specific Imports:**
```python
from main_pc_code.agents.error_publisher import ErrorPublisher
from remote_api_adapter.adapter import RemoteApiAdapter
```

**Class Definition:**
```python
# Class name not shown in analyzed snippet, but likely:
class NLUAgent(BaseAgent):  # or EnhancedBaseAgent if available
    # Implementation details not shown
```

**Parent Class:** `BaseAgent` (with conditional `EnhancedBaseAgent`)

---

#### **Service Registry Agent (`main_pc_code/agents/service_registry_agent.py`)**

**Standard Library Imports:**
```python
import argparse
import logging
import os
import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Protocol, runtime_checkable
```

**Performance JSON (Conditional):**
```python
try:
    import orjson as _json
    _dumps = _json.dumps
    _loads = _json.loads
except ImportError:
    import json as _json
    # Custom wrapper functions for consistency
```

**Project Common Imports:**
```python
from common.core.base_agent import BaseAgent
from common.utils.data_models import AgentRegistration
from common.env_helpers import get_env
from common.pools.redis_pool import get_redis_client_sync
```

**Missing/Commented Imports:**
```python
# from common_utils.port_registry import get_port  # MISSING - Commented out
```

**HTTP Server (Built-in):**
```python
from http.server import BaseHTTPRequestHandler, HTTPServer
```

**Class Definition:**
```python
class ServiceRegistryAgent(BaseAgent):
    # Service registry implementation
```

**Parent Class:** `BaseAgent`

---

#### **Unified System Agent (`main_pc_code/agents/unified_system_agent.py`)**

**Standard Library Imports:**
```python
import sys
import os
import json
import logging
import yaml
from pathlib import Path
```

**Project Common Imports:**
```python
from common.core.base_agent import BaseAgent
from common.utils.path_manager import PathManager
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
```

**Agent-Specific Imports:**
```python
from main_pc_code.utils.config_loader import load_config
```

**Class Definition:**
```python
class UnifiedSystemAgent(BaseAgent):
    # Central command center implementation
```

**Parent Class:** `BaseAgent`

---

### **2. PC2 CODE AGENTS**

#### **Async Processor (`pc2_code/agents/async_processor.py`)**

**Standard Library Imports:**
```python
import os
import sys
import json
import time
import logging
import threading
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from datetime import datetime
from collections import deque, defaultdict
```

**Third-party Imports:**
```python
import zmq
import yaml
import psutil
import torch
```

**Project Common Imports:**
```python
from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
```

**PC2-Specific Imports:**
```python
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.utils.config_loader import Config
```

**Class Definition:**
```python
class AsyncProcessor(BaseAgent):
    # Async processing implementation with priority queues
```

**Parent Class:** `BaseAgent`

---

## DETAILED CLASS INHERITANCE ANALYSIS

### **Inheritance Patterns**

| **Agent File** | **Class Name** | **Parent Class** | **Enhanced Capabilities** | **Additional Interfaces** |
|---|---|---|---|---|
| `nlu_agent.py` | `NLUAgent` (implied) | `BaseAgent` / `EnhancedBaseAgent` | ✅ Conditional | Hybrid LLM, Error Bus |
| `service_registry_agent.py` | `ServiceRegistryAgent` | `BaseAgent` | ❌ None | HTTP health endpoint |
| `unified_system_agent.py` | `UnifiedSystemAgent` | `BaseAgent` | ❌ None | System orchestration |
| `async_processor.py` | `AsyncProcessor` | `BaseAgent` | ❌ None | Async processing, ML integration |

### **Base Agent Usage Analysis**

**Standard BaseAgent Pattern:**
```python
from common.core.base_agent import BaseAgent

class AgentName(BaseAgent):
    def __init__(self):
        super().__init__()
        # Agent-specific initialization
```

**Enhanced BaseAgent Pattern (NLU only):**
```python
try:
    from common.core.enhanced_base_agent import EnhancedBaseAgent, PerformanceMetrics
    ENHANCED_AVAILABLE = True
    BaseClass = EnhancedBaseAgent
except ImportError:
    ENHANCED_AVAILABLE = False
    BaseClass = BaseAgent

class NLUAgent(BaseClass):
    # Gets enhanced capabilities when available
```

---

## IMPORT DEPENDENCY ANALYSIS

### **Core Dependencies (Universal)**

**Base Agent System:**
```python
from common.core.base_agent import BaseAgent  # All agents ✅
```

**ZMQ Communication:**
```python
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
# Used by: nlu_agent, unified_system_agent ✅
# Missing from: service_registry_agent, async_processor ⚠️
```

### **Configuration Dependencies (Inconsistent)**

**Main PC Configuration:**
```python
# Pattern 1: Unified Config (nlu_agent)
from common.config_manager import load_unified_config

# Pattern 2: Custom Loader (unified_system_agent)  
from main_pc_code.utils.config_loader import load_config

# Pattern 3: Environment + Registry (service_registry_agent)
from common.env_helpers import get_env
# from common_utils.port_registry import get_port  # MISSING
```

**PC2 Configuration:**
```python
# Pattern 4: Mixed approach (async_processor)
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.utils.config_loader import Config
from common.config_manager import get_service_ip, get_service_url, get_redis_url
```

### **Utility Dependencies (Selective Usage)**

**Path Management:**
```python
from common.utils.path_manager import PathManager
# Used by: nlu_agent ✅, unified_system_agent ✅
# Missing from: service_registry_agent ⚠️, async_processor ⚠️
```

**Data Models:**
```python
from common.utils.data_models import AgentRegistration
# Used by: service_registry_agent ✅ (unique)
```

**Redis Integration:**
```python
from common.pools.redis_pool import get_redis_client_sync
# Used by: service_registry_agent ✅ (unique)
```

**Error Management:**
```python
from main_pc_code.agents.error_publisher import ErrorPublisher
# Used by: nlu_agent ✅ (Main PC only)
```

---

## IMPORT INCONSISTENCIES

### **🔴 CRITICAL MISSING IMPORTS**

1. **Service Registry Agent - Port Registry:**
```python
# MISSING: from common_utils.port_registry import get_port
# IMPACT: Agent will crash on startup
```

### **🟡 INCONSISTENT PATTERNS**

1. **ZMQ Pool Usage:**
```python
# Present in: nlu_agent, unified_system_agent
# Missing in: service_registry_agent, async_processor
# IMPACT: Inconsistent communication capabilities
```

2. **Path Management:**
```python
# PathManager used: nlu_agent, unified_system_agent
# Custom path logic: async_processor
# No path management: service_registry_agent
# IMPACT: Deployment environment issues
```

3. **Configuration Loading:**
```python
# 4 different patterns across 4 agents
# IMPACT: Configuration management complexity
```

---

## THIRD-PARTY DEPENDENCY ANALYSIS

### **Performance Libraries**

**JSON Performance:**
```python
# service_registry_agent.py
try:
    import orjson as _json  # High-performance JSON
except ImportError:
    import json as _json  # Fallback
```

**Machine Learning:**
```python
# async_processor.py
import torch  # PyTorch for ML capabilities
```

**System Monitoring:**
```python
# async_processor.py  
import psutil  # System resource monitoring
```

**Async Processing:**
```python
# async_processor.py
import asyncio  # Python async capabilities
```

### **Communication Libraries**

**ZeroMQ:**
```python
# async_processor.py
import zmq  # Direct ZMQ usage (not using pool)
```

**HTTP Server:**
```python
# service_registry_agent.py
from http.server import BaseHTTPRequestHandler, HTTPServer  # Health endpoint
```

---

## SPECIALIZED IMPORTS ANALYSIS

### **Agent-Specific Capabilities**

**NLU Agent - Hybrid LLM:**
```python
from remote_api_adapter.adapter import RemoteApiAdapter
# Advanced AI capability for cloud/local hybrid inference
```

**Service Registry - Data Models:**
```python
from common.utils.data_models import AgentRegistration
# Structured data for agent registration
```

**Async Processor - ML Integration:**
```python
import torch
# Machine learning framework integration
```

### **System Integration Imports**

**Error Management:**
```python
from main_pc_code.agents.error_publisher import ErrorPublisher
# Event-driven error reporting system
```

**Environment Helpers:**
```python
from common.env_helpers import get_env
# Environment variable utilities
```

**Redis Integration:**
```python
from common.pools.redis_pool import get_redis_client_sync
# Redis connection management
```

---

## IMPORT STANDARDIZATION RECOMMENDATIONS

### **🎯 REQUIRED FIXES**

1. **Add Missing Port Registry Import:**
```python
# service_registry_agent.py
from common_utils.port_registry import get_port
```

2. **Standardize ZMQ Pool Usage:**
```python
# All agents should use:
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
```

3. **Standardize Path Management:**
```python
# All agents should use:
from common.utils.path_manager import PathManager
```

### **🎯 ENHANCEMENT OPPORTUNITIES**

1. **Extend Enhanced BaseAgent:**
```python
# Apply conditional enhancement pattern to all agents
try:
    from common.core.enhanced_base_agent import EnhancedBaseAgent, PerformanceMetrics
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False
```

2. **Standardize Performance JSON:**
```python
# Apply orjson optimization to all agents
try:
    import orjson
    # Performance JSON utilities
except ImportError:
    import json
    # Fallback utilities
```

3. **Extend Error Management:**
```python
# Apply to PC2 agents:
from common.utils.error_publisher import ErrorPublisher  # Updated location
```

---

## IMPORT DEPENDENCY MAP

```
common.core.base_agent
├── BaseAgent (All agents ✅)
└── EnhancedBaseAgent (NLU only ⚠️)

common.pools
├── zmq_pool (Main PC agents ✅, PC2 missing ⚠️)
└── redis_pool (Service Registry only ⚠️)

common.config_manager
├── load_unified_config (NLU only ⚠️)
├── get_service_* (Mixed usage ⚠️)

common.utils
├── path_manager (Main PC agents ✅, PC2 missing ⚠️)
├── data_models (Service Registry only ⚠️)
└── error_publisher (NLU only ⚠️)

MISSING:
└── common_utils.port_registry (Service Registry 🔴)
```

---

**Analysis Status:** ✅ COMPLETED for Step 2  
**Next Step:** Step 1 - File Inventory  
**Critical Issues Found:** 1 missing import, multiple inconsistent patterns  
**Import Patterns Identified:** 4 different configuration approaches, selective utility usage
