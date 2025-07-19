# CONFIGURATION VALIDATION

## 1. Schema Overview
| Machine | Top-level key | Structure |
|---------|--------------|-----------|
| MainPC  | `agent_groups` | Dict ⟶ *category* ⟶ *agent_name* ⟶ properties |
| PC2     | `pc2_services` | **List** ⟶ Dict (one per agent) |

Additional shared sections:
* MainPC: `global_settings`
* PC2: `environment`, `resource_limits`, `pc2_network`, `core_services`, `error_bus_port`

## 2. Validation Results
### 2.1 MainPC (`startup_config.yaml`)
* **Total agents detected:** 58
* **Validation**
  * ⚠️ *Parser incompatibility* — existing tooling expects a list; categories are dictionaries.
  * ✅ No duplicate ports found (scripted scan).
  * ✅ All agents declare `script_path` & `port`.
  * ⚠️ *Broken path references* (sampling):
    * `phase1_implementation/consolidated_agents/observability_hub/backup_observability_hub/observability_hub.py` does not exist.
    * Several `FORMAINPC/*.py` files point to legacy paths – verify presence.

### 2.2 PC2 (`startup_config.yaml`)
* **Total agents detected:** 27
* **Validation**
  * ✅ Schema is flat list – already compatible with tooling that expects list.
  * ✅ No duplicate ports in range 7100-7199.
  * ⚠️ Two agents (`SystemHealthManager`, `PerformanceLoggerAgent`) have circular-break comments – indicates previous dependency loop.

### 2.3 Cross-machine Port Map
* **Conflict scan:** none detected between MainPC and PC2 allocated ports — ranges are disjoint (MainPC 2xxxx/5xxx/7xxx; PC2 71xx).

## 3. Issues Identified
1. **Schema Divergence** prevents a single parser from consuming both YAMLs.
2. **Mixed path conventions** (`main_pc_code/...`, relative paths, deep phase folders) raise risk of file-not-found at runtime.
3. **Inline circular-dependency notes** suggest manual edits; automated validation unaware of them.

## 4. Recommendations
1. **Introduce unified schema v3** with machine-specific grouping but common node definition (e.g. top-level `agents: List[Agent]` + optional `machine` field).
2. Extend config loader to **support both legacy schemas** during migration:
   * Recursively walk dicts → flatten to list.
   * Preserve category as `group` metadata.
3. **Schema validation** (pydantic / jsonschema) enforced in CI.
4. **Path sanity check**: verify every `script_path` exists before startup; fail fast otherwise.
