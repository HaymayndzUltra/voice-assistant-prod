# Service Registry & Digital-Twin Refactor Roadmap

This file tracks the end-to-end plan to de-risk service discovery, refactor the SystemDigitalTwinAgent, and modernise packaging. Follow each phase in sequence.

---

## PHASE 0 – Bootstrap
1. Create branch: `git checkout -b feat/service-registry`
2. Ensure pytest scaffold exists (`tests/__init__.py`).
3. Commit baseline.

---

## PHASE 1 – Add `ServiceRegistryAgent`
### 1-A  Source code
* File: `main_pc_code/agents/service_registry_agent.py`
* Responsibilities:
  * In-memory dict `self.registry`
  * Actions: `register_agent`, `get_agent_endpoint`, `ping` / `health_check`
  * Default ports: **7100** (main) / **8100** (health)
  * Optional `--persist sqlite.db` flag (stub)

### 1-B  Config
Add to `main_pc_code/config/startup_config.yaml`:
```yaml
core_services:
  ServiceRegistry:
    script_path: main_pc_code/agents/service_registry_agent.py
    host: 0.0.0.0
    port: 7100
    health_check_port: 8100
```

### 1-C  Docker-compose (optional)
```yaml
service-registry:
  build: .
  command: python main_pc_code/agents/service_registry_agent.py
  ports:
    - "7100:7100"
    - "8100:8100"
```

### 1-D  Documentation
Create `MainPcDocs/SYSTEM_DOCUMENTATION/MAIN_PC/00_service_registry.md` with overview, API, ports, curl examples.

### 1-E  Commit message
```
Phase 1: Introduce ServiceRegistryAgent + config + docs
```

---

## PHASE 2 – Delegate Discovery from Digital-Twin
1. Remove internal registry logic from `SystemDigitalTwinAgent`; replace with forwarders to ServiceRegistry.
2. Update `common/core/base_agent.py` discovery defaults (ServiceRegistry host/port).
3. Clean related keys in `startup_config.yaml`.
4. Update docs.
5. Commit message: `Phase 2: Digital-Twin delegates discovery to ServiceRegistry`.

---

## PHASE 3 – Eliminate Digital-Twin Globals
1. Move config, `DB_PATH`, Redis params into `__init__`.
2. Update `startup_config.yaml` under `system_digital_twin:` with new keys.
3. Update docs.
4. Commit.

---

## PHASE 4 – Unit Tests
* `tests/test_service_registry.py`
* `tests/test_system_digital_twin.py`
* Add CI (pytest + ruff).

---

## PHASE 5 – Packaging Modernisation
1. Add `pyproject.toml`; `pip install -e .` workflow.
2. CI gate to block new `sys.path.insert(0, ...)`.
3. Remove inserts directory-by-directory.
4. Add dev-guide markdown.

---

## PHASE 6 – HA / Persistence for ServiceRegistry
Optional: Redis backend, docker-compose integration, config & docs.

---

### Merge Strategy
1. Merge Phases 1+2 together to keep system functional.
2. Follow with Phases 3–4.
3. Packaging epic runs in parallel (Phase 5).

---

_Last updated: 2025-07-12_
