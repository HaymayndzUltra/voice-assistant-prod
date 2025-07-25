# Memory-Bank Module

This folder contains the design history, decisions and implementation notes for
the system-wide **Memory Orchestration** layer.  The memory system is now fully
aligned with the v3 unified configuration loader and the cross-machine agent
groups described in `config/startup_config.v3.yaml`.

## Current System Status (2025-01-16)

### ✅ **Unified Configuration v3.0 - WORKING**
- **Total Agents**: 77 agents across MainPC (54) and PC2 (23)
- **Configuration**: `config/startup_config.v3.yaml` with include-based delegation
- **Loader**: `common/utils/unified_config_loader.py` with include processing
- **Status**: ✅ Fully functional with dependency resolution and health checks

### ✅ **Memory Architecture - ACTIVE**
| Agent / Service | Location | Purpose | Status |
|-----------------|----------|---------|---------|
| **MemoryOrchestratorService** | `pc2_code/agents/memory_orchestrator_service.py` | Single source of truth for session & knowledge stores | ✅ Active |
| **MemoryClient** | `main_pc_code/agents/memory_client.py` | Thin RPC layer used by MainPC agents | ✅ Active |
| **SessionMemoryAgent** | `main_pc_code/agents/session_memory_agent.py` | Handles per-conversation short-term memories | ✅ Active |
| **KnowledgeBase** | `main_pc_code/agents/knowledge_base.py` | Long-term semantic store | ✅ Active |

### ✅ **Recent Fixes Applied**
- **Import Issue**: Fixed `ModuleNotFoundError` in system launcher
- **Include Processing**: Added support for `include` directive in unified config loader
- **Agent Consolidation**: Fixed type errors in agent processing
- **Port Validation**: Working port uniqueness validation

## Configuration Sources

Configuration for these services now derives from:

* `config/startup_config.v3.yaml`  – base graph with include delegation
* `config/overrides/mainpc.yaml`   – MainPC tweaks (placeholder)
* `config/overrides/pc2.yaml`      – PC2 tweaks (placeholder)

The legacy `memory-bank/*/*.yaml` config fragments have been removed (see
CHANGELOG below).

## Removed / Archived Items

Old agent prototypes and per-machine memory YAMLs were superseded by the v3
schema.  They have been archived under `memory-bank/archive/` for reference.

## Local Development Tips

```bash
# Test unified configuration (77 agents total)
python3 main_pc_code/system_launcher.py --dry-run

# Test legacy MainPC config (54 agents)
python3 main_pc_code/system_launcher.py --dry-run --config main_pc_code/config/startup_config.yaml

# Test legacy PC2 config (23 agents)  
python3 main_pc_code/system_launcher.py --dry-run --config pc2_code/config/startup_config.yaml
```

## Migration Note

As of 2025-01-16 all memory-related configuration must go through the unified
loader.  Import paths that reference the old `memory_bank.config` module will
raise `DeprecationWarning` and will be removed in the next major release.

## Known Issues

- **Machine Detection**: "Could not auto-detect machine type, defaulting to 'mainpc'" - needs environment variable setup
- **Group Filtering**: "No enabled groups found for machine mainpc" - machine profiles need configuration
- **Override Files**: Placeholder override files need actual configuration content