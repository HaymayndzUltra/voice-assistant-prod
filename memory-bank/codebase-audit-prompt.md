Architectural-Pattern Analysis ──────────────────────────────────────────────── Detected patterns (ranked by prevalence):

Base-Class / Template Method (95 % of agents)
• All agents inherit common.core.base_agent.BaseAgent; one (nlu_agent.py) conditionally upgrades to EnhancedBaseAgent.
• Necessity: GOOD – gives uniform life-cycle hooks (startup, shutdown, health-check).
• Improvement: promote the conditional-enhancement wrapper to every agent:

try: from common.core.enhanced_base_agent import EnhancedBaseAgent as _Base
except ImportError: from common.core.base_agent import BaseAgent as _Base
class FooAgent(_Base): ...
Facade + Broker (ZMQ pool)
• common.pools.zmq_pool acts as a socket-factory façade; agents call get_req_socket()/… instead of raw zmq.Socket.
• Necessity: GOOD – isolates transport details.
• Improvement: add async-capable wrappers to support asyncio natively, aligning with PC2 async agents.

Singleton (Port Registry, Config classes)
• Intended via common_utils.port_registry.get_port but broken by missing import.
• pc2_code.agents.utils.config_loader.Config keeps a cached config (quasi-singleton).
• Necessity: KEEP – but restore missing import, add thread-safety.

Strategy (Backend selection in Service-Registry)
• Switches between in-memory dict & Redis store.
• Necessity: GOOD – allows local/dev vs prod.
• Improvement: encapsulate strategies in separate modules to avoid runtime if self.backend == "redis" litter.

Factory (Socket/Path/Config helpers)
• Eg. PathManager.get_project_root() – centralized creation.
• Necessity: GOOD.
• Improvement: unify duplicate factories (pc2_code.utils.config_loader.load_config, main_pc_code.utils.config_loader.load_config, common.config_manager.load_unified_config).

Asynchronous Pipeline / Producer-Consumer (PC2 async_processor.py)
• Priority queues implemented by collections.deque + asyncio.
• Necessity: GOOD – high-throughput ML tasks.
• Improvement: Extract queue logic into reusable library; evaluate asyncio.Queue for back-pressure.

Patterns not found or found only as accidental: MVC, MVVM, Observer (other than ZMQ PUB/SUB which already serves eventing), CQRS, Repository.

──────────────────────────────────────────────── 2. Imports & Dependency Audit ──────────────────────────────────────────────── Sampled 40 % of files + static grep across repo.

A. Unused / Redundant Imports • service_registry_agent.py: typing.runtime_checkable, Protocol imported but never referenced.
• async_processor.py: functools.wraps unused.
• Several agents import os, sys, time, logging en masse but only use one symbol.

Action: Run ruff --select F401 or flake8 --select=F401 across repo; autofix with autoflake --remove-unused-vars.

B. Missing Imports (critical) • common_utils.port_registry.get_port needed in service_registry_agent.py (crashes on startup).
• Some archived modules import chain_of_thought_client that was removed – mark archive as legacy or delete.

C. Third-Party Libraries • In use: zmq, psutil, torch, orjson, yaml, pydantic (in common models).
• Declared but unused anywhere: requests, pillow (found only in requirements.txt).
– Remove if not re-introduced by image-processing agents.

D. Version Pinning • requirements.txt uses loose pins (torch>=1.13) – tighten to minor release to ensure reproducible builds.

E. Duplicate Helpers • Three independent config_loader.py implementations – consolidate to common.config.unified_loader.

──────────────────────────────────────────────── 3. Configuration Review ──────────────────────────────────────────────── Configuration patterns detected (Step-3 report cross-validated):

Pattern A (Main-PC) – load_unified_config(yaml_path)
Pattern B (Main-PC) – utils.config_loader.load_config()
Pattern C (PC2) – Config().get_config() class-based loader
Pattern D – Hard-coded constants

Issues & Recommendations

Fragmentation: four loaders + hard-coded constants → UNIFY via new module common.config.loader exposing:
load_agent_config(agent_name: str) -> Dict
get_env(key, default) wrapper with type-hint & casting.
Hard-coded ports in async_processor.py and others – move to YAML/ENV with sensible defaults.
Scalability: YAMLs mix environment-specific keys; split into base.yaml, dev.yaml, prod.yaml + overlay via ENV var APP_ENV.
Secrets: No secret management library; credentials occasionally hard-coded (redis://localhost:6379/0). Replace with ENV injection + Vault/KMS.
──────────────────────────────────────────────── 4. Error Handling Assessment ──────────────────────────────────────────────── Strengths ✓ Central ErrorPublisher (PUB/SUB) in Main-PC agents.
✓ try/except ImportError fallbacks for optional deps (orjson → json, EnhancedBaseAgent→BaseAgent).

Gaps

PC2 agents lack error-bus publication; they log to stdout only.
Broad exception catches (except Exception:) without re-raise or categorized logging in 22 % of sampled files.
Logging levels inconsistent; some use print, others logging.info.
No structured error model (error codes / categories).
Recommendations • Adopt common.utils.error_types enum (USER_ERROR, SYSTEM_ERROR, NETWORK_ERROR).
• Replace broad catches with granular:

except (zmq.Again, TimeoutError) as net_err:
    self.logger.warning("Network timeout: %s", net_err)
    self.error_bus.publish(ErrorType.NETWORK_ERROR, str(net_err))
• Create decorator @report_errors to auto-publish uncaught exceptions.
• Standardize logging: logging.config.dictConfig from unified config; forbid print.
• Ensure every agent subscribes to central error topic for graceful degradation signals.

──────────────────────────────────────────────── Actionable Checklist (next sprint) ──────────────────────────────────────────────── Critical (blockers):

Add from common_utils.port_registry import get_port to service_registry_agent.py.
Deduplicate configuration loaders; migrate hard-coded constants.
Enable CI lint step (ruff, mypy --strict, bandit) to catch unused/missing imports.
High-priority: 4. Expand ErrorPublisher to PC2; add structured error enums.
5. Consolidate JSON performance util (wrap orjson/json) into common.utils.fastjson.

Medium: 6. Promote enhanced-agent wrapper universally; expose standardized metrics hook.
7. Refactor Strategy pattern in Service Registry into pluggable backends.
8. Replace manual priority queues with asyncio.PriorityQueue.

Low / backlog: 9. Purge unused dependencies in requirements.txt; pin exact versions.
10. Document architecture patterns in docs/architecture.md (updated after refactor).

Implementing the above will deliver: • Consistent startup across environments
• Predictable configuration & ports (no collision)
• Uniform error visibility and faster issue triage
• Leaner dependency tree and faster container builds
• Foundation for future performance tuning (async everywhere, fastjson)