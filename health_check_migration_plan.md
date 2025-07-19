# HEALTH CHECK MIGRATION PLAN

**Target**: Remove duplicate health check implementations  
**Scope**: 41+ agent files with custom `_health_check_loop`  
**Expected Result**: 3,350+ lines eliminated, standardized health checks  
**Risk**: LOW (BaseAgent implementation already exists and tested)

---

## 🎯 **MIGRATION STRATEGY**

### **Phase 1: Safe Migrations (Agents that inherit BaseAgent)**
**Target**: Agents with `class AgentName(BaseAgent)` + custom `_health_check_loop`  
**Action**: Simply remove the custom implementation  
**Risk**: VERY LOW (BaseAgent will handle health checks automatically)

### **Phase 2: Class Definition Updates** 
**Target**: Agents with custom health loops but not inheriting BaseAgent  
**Action**: Update class definition + remove custom implementation  
**Risk**: LOW (well-tested pattern)

---

## 📋 **IMPLEMENTATION STEPS**

### **Step 1: Identify Safe Migration Targets**
```bash
# Find agents that inherit BaseAgent AND have custom health loops
grep -l "class.*BaseAgent" main_pc_code/agents/*.py pc2_code/agents/*.py > baseagent_inheritors.txt
grep -l "_health_check_loop" main_pc_code/agents/*.py pc2_code/agents/*.py > custom_health_agents.txt
comm -12 <(sort baseagent_inheritors.txt) <(sort custom_health_agents.txt) > safe_migration_targets.txt
```

### **Step 2: Validate Current Health Check Pattern**
For each safe target:
1. Confirm it inherits from BaseAgent
2. Confirm it has custom `_health_check_loop` method
3. Remove the custom implementation
4. Test health endpoint still works

### **Step 3: Create Migration Script**
```python
#!/usr/bin/env python3
"""
Health Check Migration Script
Removes duplicate _health_check_loop implementations from agents that inherit BaseAgent
"""

import re
import os
from pathlib import Path

def remove_custom_health_loop(file_path):
    """Remove custom _health_check_loop method from file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match custom health check loop method
    pattern = r'\n    def _health_check_loop\(self\):.*?(?=\n    def |\n\nclass |\nif __name__|\Z)'
    
    # Remove the custom implementation
    modified_content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # Write back if changed
    if content != modified_content:
        with open(file_path, 'w') as f:
            f.write(modified_content)
        return True
    return False

def main():
    safe_targets = []
    
    # Read safe migration targets
    with open('safe_migration_targets.txt', 'r') as f:
        safe_targets = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(safe_targets)} safe migration targets")
    
    for target in safe_targets:
        print(f"Migrating: {target}")
        if remove_custom_health_loop(target):
            print(f"  ✅ Removed custom health loop")
        else:
            print(f"  ⏭️  No changes needed")

if __name__ == "__main__":
    main()
```

---

## 🚨 **VALIDATION CHECKLIST**

Before migration:
- [ ] Agent inherits from BaseAgent
- [ ] Agent has custom `_health_check_loop` method
- [ ] Health endpoint currently works: `curl http://localhost:PORT/health`

After migration:
- [ ] Custom `_health_check_loop` method removed
- [ ] Health endpoint still works: `curl http://localhost:PORT/health`
- [ ] No compilation/import errors
- [ ] Agent starts successfully

---

## 📊 **EXPECTED RESULTS**

**Per Agent**:
- Remove ~80-120 lines of duplicate code
- Eliminate custom health check thread management
- Standardize health response format

**System-wide**:
- 3,350+ total lines eliminated
- Single health check implementation to maintain
- Consistent health monitoring across all agents
- Foundation for further optimizations

---

**Next Action**: Execute Step 1 to identify safe migration targets 