# AGENT STARTUP ANALYSIS

## 1. Current Status
* Running `main_pc_code/scripts/start_system.py` results in **0 startup phases**; no agents are launched.
* All 85 agents therefore crash / never start.
* Health-check verification script (`verify_all_health_checks.py`) also extracts **0 agents** from the same configuration.

## 2. Issues Identified
1. **Configuration parser skips every agent**  
   The `DependencyResolver.extract_agents()` loop only processes top-level YAML keys that are *lists*:
   ```python
               if not isinstance(section_data, list):
                   continue
   ```
   In `startup_config.yaml` agents are nested under `agent_groups -> <category> -> <agent>`, i.e. **dictionary of dictionaries**. As a result `extract_agents()` never sees any agent definitions.
2. **Demo-mode bypass**  
   Even if phases were detected, the script is permanently in `demo_mode = True`, so only phase-1 agents would run.
3. **Health-check verifier has the same list-only assumption** causing 0 agents to be analysed.
4. **Silent failure path**  
   With an empty dependency graph the script prints "0 phases" and exits without error – masking the real root cause.

## 3. Root Causes
* **Schema mismatch** between the startup script (expects `List[dict]` at the top level) and the actual MainPC YAML schema (nested dictionaries).
* Lack of validation: no guard clause warns about "no agents detected".

## 4. Impact Assessment
| Impact | Description |
|--------|-------------|
| 🔴 Critical | No MainPC agents start at all. Entire system unavailable. |
| 🔴 Critical | Down-stream PC2 agents that depend on MainPC services can never become healthy. |
| 🟠 High | Health-check tooling mis-reports success because it processes zero agents. |

## 5. Recommendations
1. **Unify the parser**: Refactor `extract_agents()` (and the health-check script) to recursively walk nested dictionaries so both schemas are supported.
2. **Add validation**: After parsing, assert that at least one agent was found; abort with clear error otherwise.
3. **Remove hard-coded `demo_mode`** flag or make it command-line configurable.
4. **Unit tests**: Add tests that load the real YAML and confirm that the expected 58 agents are discovered.
5. **Logging improvements**: Emit a warning if a referenced `script_path` does not exist before attempting launch.
