# Memory-Bank Module

This folder contains the design history, decisions and implementation notes for
the system-wide **Memory Orchestration** layer.  The memory system is now fully
aligned with the v3 unified configuration loader and the cross-machine agent
groups described in `config/startup_config.v3.yaml`.

## Active Components (as of 2025-01-16)

| Agent / Service | Location | Purpose |
|-----------------|----------|---------|
| **MemoryOrchestratorService** | `pc2_code/agents/memory_orchestrator_service.py` | Single source of truth for session & knowledge stores; runs on PC2 |
| **MemoryClient** | `main_pc_code/agents/memory_client.py` | Thin RPC layer used by MainPC agents |
| **SessionMemoryAgent** | `main_pc_code/agents/session_memory_agent.py` | Handles per-conversation short-term memories |
| **KnowledgeBase** | `main_pc_code/agents/knowledge_base.py` | Long-term semantic store |

Configuration for these services now derives from:

* `config/startup_config.v3.yaml`  – base graph
* `config/overrides/mainpc.yaml`   – MainPC tweaks
* `config/overrides/pc2.yaml`      – PC2 tweaks

The legacy `memory-bank/*/*.yaml` config fragments have been removed (see
CHANGELOG below).

## Removed / Archived Items

Old agent prototypes and per-machine memory YAMLs were superseded by the v3
schema.  They have been archived under `memory-bank/archive/` for reference.

## Local Development Tips

```bash
# Dry-run launch just the memory related agents
python main_pc_code/system_launcher.py --dry-run \
    --config main_pc_code/config/startup_config.yaml \
    | grep -E "Memory|SessionMemory|KnowledgeBase"
```

## Migration Note

As of 2025-01-16 all memory-related configuration must go through the unified
loader.  Import paths that reference the old `memory_bank.config` module will
raise `DeprecationWarning` and will be removed in the next major release.