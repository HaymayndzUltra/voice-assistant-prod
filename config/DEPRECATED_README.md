# Deprecated Configuration Files Notice

## ⚠️ **IMPORTANT: Configuration Migration Complete**

This directory and its subdirectories contain **legacy configuration files** that have been **superseded by the v3 Unified Configuration System**.

### **Current Production Configuration**
Use this file for all deployments:
```
config/startup_config.v3.yaml  # ✅ PRODUCTION READY
```

### **Deprecated Files**
The following files are **NO LONGER USED** in production:

#### Legacy MainPC Config
- `main_pc_code/config/startup_config.yaml` ❌ **DEPRECATED**
- `main_pc_code/config/*.yaml` ❌ **DEPRECATED**

#### Legacy PC2 Config  
- `pc2_code/config/startup_config.yaml` ❌ **DEPRECATED**
- `pc2_code/config/*.yaml` ❌ **DEPRECATED**

#### Old Include-based Configs
- Any config files using `include:` directives ❌ **DEPRECATED**

### **Migration Benefits**
The v3 system provides:
- ✅ **77 agents** in single configuration file
- ✅ **Machine-aware filtering** (MainPC: 63 agents, PC2: 39 agents)  
- ✅ **Override system** for MainPC/PC2/Docker environments
- ✅ **Zero duplication** - single source of truth
- ✅ **Environment variable support**
- ✅ **Dependency resolution** with proper batching

### **How to Use v3 Config**
```bash
# MainPC deployment (63 agents)
export MACHINE_TYPE=mainpc
python3 main_pc_code/system_launcher.py --config config/startup_config.v3.yaml

# PC2 deployment (39 agents)  
export MACHINE_TYPE=pc2
python3 main_pc_code/system_launcher.py --config config/startup_config.v3.yaml

# Docker deployment
export CONFIG_OVERRIDE=docker  
python3 main_pc_code/system_launcher.py --config config/startup_config.v3.yaml
```

### **Legacy Support**
Legacy configs are kept for backward compatibility during transition period only.
**DO NOT USE** for new deployments.

---
**Date:** 2025-01-16  
**Migration Status:** ✅ COMPLETE  
**Confidence:** 95% - Production ready with comprehensive testing 