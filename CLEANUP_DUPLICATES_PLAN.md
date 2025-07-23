# 🧹 DUPLICATE LOGIC & IMPORT PATH CLEANUP PLAN

## 🎯 **EXECUTION ORDER** (Critical: Follow exactly!)

### **PHASE 1: CLASS DUPLICATES REMOVAL**

#### **1.1 ModelManagerSuite Cleanup**
```bash
# KEEP: main_pc_code/11.py (this is your working version)
# DELETE: phase1_implementation/group_02_model_manager_suite/
# DELETE: phase1_implementation/consolidated_agents/model_manager_suite/
```

#### **1.2 ResourceManagerSuite Cleanup**
```bash
# ANALYZE FIRST: Check which version is being used
# phase0_implementation/group_02_resource_scheduling/resource_manager_suite/ (2 classes)
# phase1_implementation/consolidated_agents/resource_manager_suite/ (2 classes)
# DELETE: older/unused implementation
```

#### **1.3 ErrorBusSuite Cleanup**
```bash
# KEEP: phase1_implementation/consolidated_agents/error_bus/ (newer)
# DELETE: phase0_implementation/group_02_resource_scheduling/error_bus/
```

### **PHASE 2: IMPORT PATH STANDARDIZATION**

#### **2.1 BaseAgent Import Unification**
```python
# STANDARD PATTERN (use everywhere):
from common.core.base_agent import BaseAgent

# REMOVE these patterns:
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.agents.base_agent import BaseAgent
```

#### **2.2 Path Setup Standardization**
```python
# STANDARD PATH SETUP (use everywhere):
import sys
import os
from pathlib import Path
from common.utils.path_env import get_main_pc_code

MAIN_PC_CODE_DIR = get_main_pc_code()
if str(MAIN_PC_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE_DIR))

# REMOVE all other sys.path.insert patterns
```

### **PHASE 3: FUNCTION DUPLICATES REMOVAL**

#### **3.1 get_main_pc_code() Consolidation**
```bash
# KEEP ONLY: common/utils/path_env.py version
# DELETE all local get_main_pc_code() definitions in:
- main_pc_code/agents/gguf_model_manager.py
- main_pc_code/agents/tone_detector.py
- main_pc_code/11.py
- phase1_implementation/group_02_model_manager_suite/
```

#### **3.2 restore_agent_functionality() Cleanup**
```bash
# KEEP: scripts/restore_functionality.py (main version)
# DELETE duplicates in:
- scripts/pc2_restore_functionality.py
- scripts/restore_all_agents.py
- cot_agent_audit_phase_c.md
```

### **PHASE 4: ARCHITECTURE VIOLATIONS**

#### **4.1 Wrong BaseAgent Inheritance**
```python
# FIX THESE SYNTAX ERRORS:
# WRONG: class PluginEventHandler(BaseAgent)(FileSystemEventHandler):
# RIGHT: class PluginEventHandler(BaseAgent, FileSystemEventHandler):

# Files to fix:
- main_pc_code/agents/plugin_manager.py
- main_pc_code/agents/llm_runtime_tools.py
- main_pc_code/agents/vram_manager copy.py
```

#### **4.2 Import Standardization**
```bash
# Replace config_parser with config_loader everywhere
# Fix incomplete imports like:
- "from main_pc_code.utils.config_loader i" (incomplete)
```

## 🔧 **AUTOMATED CLEANUP SCRIPTS**

### **Script 1: Duplicate Class Remover**
```python
# !/usr/bin/env python3
"""Remove duplicate class definitions safely"""

DUPLICATE_PATHS_TO_DELETE = [
    "phase1_implementation/group_02_model_manager_suite/",
    "phase1_implementation/consolidated_agents/model_manager_suite/backup_model_manager_suite/",
    "phase0_implementation/group_02_resource_scheduling/error_bus/",
]

for path in DUPLICATE_PATHS_TO_DELETE:
    if os.path.exists(path):
        print(f"🗑️  Removing duplicate: {path}")
        shutil.rmtree(path)
```

### **Script 2: Import Path Fixer**
```python
# !/usr/bin/env python3
"""Standardize all import paths"""

def fix_base_agent_imports(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Fix BaseAgent imports
    content = re.sub(
        r'from main_pc_code\.src\.core\.base_agent import BaseAgent',
        'from common.core.base_agent import BaseAgent',
        content
    )

    # Fix config imports
    content = re.sub(
        r'from.*config_parser.*import',
        'from main_pc_code.utils.config_loader import load_config',
        content
    )

    with open(file_path, 'w') as f:
        f.write(content)
```

### **Script 3: sys.path Cleaner**
```python
# !/usr/bin/env python3
"""Remove redundant sys.path statements"""

def clean_sys_path(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Remove redundant sys.path.insert lines
    cleaned_lines = []
    path_insert_found = False

    for line in lines:
        if 'sys.path.insert' in line and path_insert_found:
            continue  # Skip duplicate
        elif 'sys.path.insert' in line:
            path_insert_found = True
            cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(cleaned_lines)
```

## 📋 **MANUAL VERIFICATION CHECKLIST**

### **Critical Files to Check After Cleanup:**
- [ ] `main_pc_code/agents/model_manager_agent.py` (ensure no conflicts)
- [ ] `common.core.base_agent` (verify single source of truth)
- [ ] All startup configs point to correct agent paths
- [ ] No circular imports created
- [ ] Docker configs updated if needed

### **Test After Each Phase:**
```bash
# Test import resolution
python -c "from common.core.base_agent import BaseAgent; print('✅ BaseAgent import OK')"

# Test agent instantiation
python -c "from main_pc_code.agents.model_manager_agent import ModelManagerAgent; print('✅ Agent import OK')"

# Test path resolution
python -c "from common.utils.path_env import get_main_pc_code; print('✅ Path utils OK')"
```

## 🚨 **CRITICAL WARNINGS**

1. **BACKUP FIRST**: Create full backup before any deletion
2. **TEST INCREMENTALLY**: Test after each phase
3. **CHECK DOCKER**: Update Dockerfiles if paths change
4. **VERIFY CONFIGS**: Ensure startup configs still work
5. **CHECK DEPENDENCIES**: Some agents may depend on "duplicate" paths

## 📊 **SUCCESS METRICS**

After cleanup, you should have:
- **Single BaseAgent** source of truth
- **No duplicate class definitions**
- **Standardized import patterns**
- **Clean sys.path management**
- **Working final system ready for Docker**

---
**Next Step**: Execute Phase 1 (Class Duplicates) first, then test before proceeding.