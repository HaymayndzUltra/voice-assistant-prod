
---

### [2025-07-12] Operation: Build Lean MainPC Docker Environment – Phase 1: Definitive Build Context

**Summary:**  
Performed a full dependency trace starting from all active agent scripts as defined in `startup_config.yaml`. Recursively resolved all Python imports, including shared and utility modules. Produced a minimal, explicit list of directories required for the Docker build context. This ensures the forthcoming Docker image will be lean, self-contained, and robust.

**Final Required Directories for Docker Build:**
```
main_pc_code/agents/
main_pc_code/FORMAINPC/
main_pc_code/services/
main_pc_code/config/
common/
common/core/
common/utils/
common_utils/
src/
src/core/
src/analysis/
src/bridge/
src/database/
src/detection/
src/memory_new/
src/network/
utils/
```

---

**Next Step:**  
Proceed to create the Dockerfile using only the above directories as the build context for a lean, correct MainPC container.

---

### Copy-Friendly Output Block

```
main_pc_code/agents/
main_pc_code/FORMAINPC/
main_pc_code/services/
main_pc_code/config/
common/
common/core/
common/utils/
common_utils/
src/
src/core/
src/analysis/
src/bridge/
src/database/
src/detection/
src/memory_new/
src/network/
utils/
```

---

If you require a machine-readable JSON or YAML version of this list, let me know!

---
