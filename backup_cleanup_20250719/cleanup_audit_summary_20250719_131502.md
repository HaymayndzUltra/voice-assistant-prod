# Codebase Cleanup Audit Summary

Generated: 2025-07-19T13:15:02.230131

## Summary Statistics

- **Test Files**: 223
- **Temp Files**: 9
- **Script Files In Root**: 96
- **Config Files**: 70
- **Documentation Files**: 312
- **Duplicate Groups**: 92
- **Potentially Unused Files**: 0

## Recommendations

### Temporary Files
**Action**: DELETE
**Reason**: These appear to be temporary files that can be safely removed
**Files**:
- `template_agent.py`
- `temp.hex`
- `scripts/template_compliant_agent.py`
- `scripts/temp_pc2_port_scanner.py`
- `main_pc_code/agents/_trash_2025-06-13/archive/web/unified_web_agent_old.py`
- ... and 4 more

### Test Files in Root
**Action**: MOVE
**Reason**: Test files should be organized in a tests/ directory
**Files**:
- `test_memory_health.py`
- `cleanup_imports_script.py`
- `test_service_discovery.py`
- `test_stability_improvements.py`
- `fix_mood_tracker.py`
- ... and 46 more

### Duplicate Files
**Action**: REVIEW
**Reason**: Multiple files with similar names detected - review for consolidation
**Groups**:
- **test_service_discovery**:
  - `test_service_discovery.py`
  - `scripts/test_service_discovery.py`
- **run_memory_client**:
  - `run_memory_client.py`
  - `containerization_package/scripts/run_memory_client.py`
- **path_manager**:
  - `path_manager.py`
  - `common/utils/path_manager.py`
  - `main_pc_code/utils/path_manager.py`
- **launch_mvs**:
  - `launch_mvs.py`
  - `main_pc_code/NEWMUSTFOLLOW/launch_mvs.py`
- **run_pc2_health_monitor**:
  - `run_pc2_health_monitor.py`
  - `containerization_package/scripts/run_pc2_health_monitor.py`

### Archive Directories
**Action**: DELETE
**Reason**: Old archive directories that can likely be removed
**Directories**:
- `main_pc_code/agents/_archive`
- `main_pc_code/agents/_trash_2025-06-13`

