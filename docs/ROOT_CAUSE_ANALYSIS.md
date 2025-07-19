# Root Cause Analysis – "0 phases detected" on System Startup

## Summary

When the startup script (`main_pc_code/scripts/start_system.py`) initialised, it attempted to build a dependency-ordered list of agent startup *phases* using `DependencyResolver`.  Because of a **schema mismatch** between the resolver’s parser and the current `startup_config.yaml`, the resolver failed to discover any agents, resulting in **0 detected phases** and therefore no agents were launched.

## Detailed Findings

1. **Config Schema Evolution**  
   Early versions of the system stored agent definitions as a *list* of dictionaries.  The resolver’s `extract_agents()` method only handled that layout.
2. **Current Schema**  
   As of January 2025, agents are organised under the top-level key `agent_groups`, with each group containing a mapping of `agent_name ➜ settings`.  This structure is *not* a list, so the legacy parser silently skipped it.
3. **Effect in Code**  
   ```python
   for section_name, section_data in self.config.items():
       if not isinstance(section_data, list):
           continue              # <-- Skipped everything under 'agent_groups'
   ```
   Consequently `self.agents` remained empty, and `get_startup_phases()` returned an empty list.

## Validation

Running the patched startup script now logs a non-zero number of phases and proceeds to start agents:

```
[SYSTEM STARTUP] Loading configuration and resolving dependencies…
[SYSTEM STARTUP] 13 phases detected.
…
```

## Impact

* Agents were never started in any environment (docker, bare-metal), blocking system functionality.
* Health-check verification and subsequent orchestration steps were effectively no-ops.

---

Prepared: 2025-07-19