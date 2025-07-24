# PRIORITY FIXES ROADMAP

| Priority | Area | Action Item | Owner | Effort | Impact |
|----------|------|-------------|-------|--------|--------|
| P0 | BaseAgent | Remove invalid `super().__init__(*args, **kwargs)` or re-introduce `ABC` inheritance; add unit test. | Core Platform | 30 min | 🔴 System-wide startup crash fix |
| P0 | Startup Script | Refactor `DependencyResolver.extract_agents()` & health-check extractor to handle nested dictionaries; abort if 0 agents parsed. | Platform | 2 h | 🔴 Allows 58 MainPC agents to launch |
| P0 | Config Unification | Provide quick shim: `python -m tools.flatten_config` that converts `agent_groups` → list format for legacy scripts (CI step). | Platform | 1 h | 🔴 Blocks startup until resolved |
| P1 | Service Discovery | Externalise Digital Twin host/port via env vars; update BaseAgent; document in README. | Networking | 3 h | 🟠 Enables cross-machine discovery |
| P1 | Health Checks | Integrate HTTP fallback in agents so `curl` health-check isn’t required; standardise `/health` JSON response. | Observability | 2 h | 🟠 Reliable monitoring |
| P1 | Demo Mode | Make `demo_mode` CLI flag (`--demo`) defaulting to *false*. | Platform | 30 min | 🟠 Removes accidental single-phase launches |
| P2 | Heartbeat | Implement periodic `heartbeat` event in BaseAgent every 30 s; expire registry entries. | Platform | 4 h | 🟡 Prevents stale entries |
| P2 | Port Registry | Generate ports dynamically or validate uniqueness in CI; write to `doc/PORT_REGISTRY.md`. | DevOps | 2 h | 🟡 Avoid future conflicts |
| P3 | CI Schema Validation | Add JSONSchema & lint check for both YAMLs; gate merges. | DevOps | 3 h | 🟢 Long-term safety |
| P3 | Documentation | Update architectural docs to reflect unified config & discovery changes. | Docs | 2 h | 🟢 Handoff clarity |

Legend: **P0** – must fix before any further testing; **P1** – fix in next sprint; **P2** – schedule within the month; **P3** – nice-to-have.
