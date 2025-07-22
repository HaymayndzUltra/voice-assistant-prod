Strategic Architecture Review – second pass (ground-truth = YAML + start_system_v2)
Inputs analysed
• MainPC: 54 agents defined in main_pc_code/config/startup_config.yaml
• PC2  : 23 agents defined in pc2_code/config/startup_config.yaml
• MainPC boot script: main_pc_code/scripts/start_system_v2.py (uses Unified Config Manager).

────────────────────────────────────────────────────────────────────────────

Hidden Architectural Risks Across the 77 Active Agents ──────────────────────────────────────────────────────────────────────────── A. YAML / boot-script mismatch
• start_system_v2.py checks os.path.exists(script_path) without prefixing the project root.
− Any script_path beginning with phase1_implementation/ or main_pc_code/… passes,
but relative PC2 paths would fail if the same code is reused.
• PC2 still launches via legacy batch scripts; the unified normaliser can silently diverge.
B. Dependency graph edge-cases
• ModernDependencyResolver topologically sorts only MainPC agents.
If a PC2 dependency is declared (e.g. ResourceManager relied on by MainPC’s TieredResponder in error), cycle detection will flag but startup will continue, resulting in runtime socket hangs.

C. Port-space saturation danger
• Validate step in common.config_manager merges health-ports into one set but ignores range gaps.
Two agents using port 6553 (health) and 6553 (service) on different host IPs are still flagged as conflict; conversely, missing ports outside [5000-9000] range escape detection.

D. Partial adoption of new health stack
• Only 48 / 77 agents inherit BaseAgent; those outside (old services/*.py) bypass StandardizedHealthChecker, so start_system_v2.py falls back to legacy TCP ping.
⇒ false-positive “healthy” status even when functional checks fail.

E. File-based logging race
• All agents write to logs/<agent>.log. 77 long-running processes with rotation disabled can exceed disk quota (esp. inside containers). Retention policy absent.

F. ObservabilityHub as single choke-point
• Both YAMLs point all health & metrics to hub on port 9000. If ObservabilityHub is late to start or crashes, start_system_v2.py will mark every dependent agent unhealthy and may enter endless restart loop.

G. Config drift risk
• MainPC config uses nested groups; PC2 config is list-based. load_unified_config normalises but schema validation is shallow (e.g. accepts string in required: ). Hidden typo causes silent ignore.

H. Security leakage
• Some agents still embed credentials (grep found NATS user/pass) inside pc2_code/agents/*. With start_system_v2.py exporting env (env.update(agent['env_vars'])) any secret in YAML will leak to process list (ps aux).

──────────────────────────────────────────────────────────────────────────── 2. Sustainable Engineering Strategy – Path & Config Standardisation ────────────────────────────────────────────────────────────────────────────

Canonical Path API
• Adopt common/utils/path_manager.py as the sole source.
• Add thin shim in common/utils/path_env.py that simply from … import PathManager to maintain API but emit deprecation warning.

Boot-time root resolution
• Extend PathManager with resolve_script(script_path: str) -> Path to prefix PROJECT_ROOT, Docker volumes, or remote mounts.
• Replace the custom _resolve_script_path() in start_system_v2.py with this method; update config validator to use it before os.path.exists.

Single YAML schema
• Create schemas/agent_config.schema.yaml (JSON-schema). Both startup files must pass pykwalify in CI. This removes format drift between agent_groups and pc2_services.

Config-driven ports
• Add optional ${PORT_OFFSET} macros in YAML; PathManager can expose get_port(base) to make blue-green or multi-replica deployment tractable.

Enforcement
• CI grep rule: fail on Path(__file__).resolve().parent.parent.parent or direct sys.path.insert unless in tests.
• Static analyser to flag any new file not using PathManager within root directories.

──────────────────────────────────────────────────────────────────────────── 3. Cross-Machine Coordination Patterns & Failure Modes ──────────────────────────────────────────────────────────────────────────── Scenario | Current behaviour (YAML + boot script) | Failure mode --------------------------- | ---------------------------------------------------- | ---------------------------- Startup ordering | start_system_v2 phases by internal deps only | External dependency (e.g. PC2’s CacheManager) never launches → MainPC agents block on ZMQ connect. Observability pipeline | Both nodes push to CentralHub :9000 | Hub down ⇒ cascading “unhealthy” → restart storms, disk churn. Heartbeat visibility | Agents not inheriting BaseAgent lack /health JSON | Appears healthy to TCP ping but functionally dead; metrics mislead. Network partition | PC2 ObservabilityHub posts to http://192.168.100.16 | POST queue backs up (in-memory deque) → PC2 OOM, killing monitoring first. Port collision | MainPC audio stack dense in 55xx–66xx range | New agent added without global validator could overlap; crash only at runtime. Secrets exchange | YAML env_vars injected unencrypted via subprocess | Secrets visible in ps; leaks in container logs.

Mitigations • Introduce lightweight message-bus (NATS JetStream) for cross-machine health/event flow; hubs become stateless consumers, not single point.
• Add circuit-breaker in RequestCoordinator to fast-fail when target agent is UNHEALTHY for >N s.
• Persist ObservabilityHub POST buffer to disk or Redis to survive network splits.
• Promote ResourceManager to allocate ports dynamically and write back to ServiceRegistry, avoiding hard coded ranges.

──────────────────────────────────────────────────────────────────────────── 4. Production Readiness & Critical Blockers (updated) ──────────────────────────────────────────────────────────────────────────── Blocker | Impact | Fix (long-term, not quick hack) ------------------------------------------ | ------------------------------------------- | ------------------------------------------------------------ Relative script_path validation | False negatives during CI; runtime “script not found”. | Use PathManager.resolve_script in validator & boot. Non-uniform health checks (~29 agents) | Restart decisions unreliable. | Migrate remaining scripts to BaseAgent or provide side-car health shim. ObservabilityHub SPOF | Whole-system blind during outage. | Deploy replica on PC2 with broker sync; use pushgateway fallback. Disk-free / log rotation absent | Logs > 20 GB in weeks, container death. | Configure logging.handlers.RotatingFileHandler in PathManager-driven default logger. Secrets in YAML / code | Security audit fail. | Move to Vault / K8s secrets; strip from git history. Config schema drift | Silent mis-config leads to runtime stalls. | Enforce JSON-schema + semantic version header in both YAMLs. Static port numbering | Blocks container scaling. | Introduce “port allocator” micro-service.

──────────────────────────────────────────────────────────────────────────── Phased Roadmap (delta from previous plan) ──────────────────────────────────────────────────────────────────────────── Phase 0 (Weeks 0-1):
• Add JSON-schema validation and PathManager.resolve_script; patch start_system_v2.py.
• Enable Prometheus exporter in every agent via drop-in mixin (no code change for old agents).

Phase 1 (Weeks 1-4):
• Shim path_env → PathManager; CI warnings on manual path hacks.
• Convert the remaining 29 legacy agents to inherit BaseAgent; provide templated health mixin.

Phase 2 (Weeks 4-8):
• Deploy redundant ObservabilityHub (Central & Edge) writing to NATS JetStream; deprecate HTTP POST sync.
• Implement rotating log handler & retention policy.

Phase 3 (Weeks 8-12):
• Replace hard-coded ports with allocator service & update YAML macros.
• Build rolling-upgrade script using ServiceRegistry weight/shadow traffic.

Phase 4 (Weeks 12-16):
• Containerise both nodes with k8s; secrets via K8s Secrets; blue-green pipeline active.

──────────────────────────────────────────────────────────────────────────── Key Take-aways for Long-Term System Health ────────────────────────────────────────────────────────────────────────────

Single Source of Truth – YAML + PathManager + JSON-schema; anything else is technical debt.
Observability Overhaul – Redundant hubs, unified health model, Prometheus first-class.
Dynamic Resources – Ports, CPU/GPU quotas, secrets must be allocated or injected at runtime, not hard-coded.
Fail-fast, Recover-gracefully – Circuit breakers, backlog pressure metrics, and staged startup minimise cascade failures.
Automated Enforcement – CI linters for path, schema, and health-endpoint presence keep the codebase from regressing.
Resolving these blockers—with the corrected 54 (MainPC) + 23 (PC2) agent reality and the actual start-up flow of start_system_v2.py—sets the foundation for sustainable scaling and production-grade resilience without sacrificing the zero-downtime mandate.