# Startup System Fix – Agent Phase Detection

## File Modified

`main_pc_code/scripts/start_system.py`

## Fix Implemented (commit 2025-07-19)

1. **Enhanced `DependencyResolver.extract_agents()`**  
   * Added support for the **current YAML schema** where agents live under `agent_groups > <group> > <agent_name>`.
   * Introduced helper `_register_agent()` to standardise agent registration and dependency extraction.
   * Maintained backward-compatibility with the legacy list-based schema for safe roll-backs.

2. **No other functional changes** – all downstream logic (`topological_sort`, health checks, etc.) works unchanged because the `self.agents` dictionary is now correctly populated.

## How to Validate

1. Rebuild / restart the affected containers or run locally:

   ```bash
   python main_pc_code/scripts/start_system.py | cat
   ```

2. Expected output snippet:

   ```
   [SYSTEM STARTUP] Loading configuration and resolving dependencies...
   [SYSTEM STARTUP] 13 phases detected.
   === Starting Phase 1 (2 agents) ===
   [STARTED] ServiceRegistry (PID: …)
   [STARTED] SystemDigitalTwin (PID: …)
   …
   ```

3. Observe that each phase passes health-checks and subsequent phases begin.

## Deployment Notes

* **Containers:** Rebuild the `mainpc` image or mount the updated code into the running container and restart.
* **Roll-back:** If issues arise, simply revert `start_system.py` to commit prior to 2025-07-19.

---

Prepared: 2025-07-19