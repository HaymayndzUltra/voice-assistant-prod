# AI SYSTEM MONOREPO – DETAILED IMPLEMENTATION ROADMAP  
(74 Source-of-Truth agents - 52 Main-PC, 23 PC2)

---

## LEGEND  
• 📄 = file • 🔧 = new file • 🛠 = modify code • 🧪 = test step

---

## PHASE 1 CRITICAL FIXES (Week 1)

### 1.1 Fix Fatal Import Error in Service Registry
**Problem** `get_port` not imported → agent crashes at start-up  
**Affected File** 📄 `main_pc_code/agents/service_registry_agent.py`  
**Exact Changes**  
```diff
@@
-import os, time, logging, threading
-from datetime import datetime
-from typing import Dict, Any, Optional, Protocol, runtime_checkable
+# 3rd-party & stdlib …
+from common_utils.port_registry import get_port          # 🛠 line ~18
Implementation Order commit → push → deploy ServiceRegistry before other agents.
Testing 🧪 python service_registry_agent.py --health-check → expect 200 OK on /health.
Rollback delete added import & restore env-var fallbacks.

1.2 Create Unified Config Manager & Migrate Agents
Problem Six different config patterns + hard-coded constants
Deliverables

🔧 common/config/unified_config_manager.py
🔧 common/config/defaults/ (base.yaml, dev.yaml, prod.yaml)
🛠 Update imports in 26 Main-PC and 18 PC2 agents.
Unified API

from common.config.unified_config_manager import Config
cfg = Config.for_agent(__file__)          # cached singleton
port = cfg.int("ports.push", default=7102)
Migration Table (excerpt)

| File | Current Pattern | Lines to Change | |------|-----------------|-----------------| | main_pc_code/agents/nlu_agent.py | load_unified_config(...) | Replace 18-24, 67-72 | | main_pc_code/agents/unified_system_agent.py | load_config() | Replace 65-74 | | pc2_code/agents/async_processor.py | Config().get_config() + constants | Delete constants (96-104), import new Config |

Implementation Order

Scaffold manager + YAMLs → unit-test.
Migrate stateless/utility agents first (no external deps).
Migrate long-running core agents (ServiceRegistry, UnifiedSystem, AsyncProcessor).
Remove legacy loaders after green CI.
Testing
• 🧪 Unit: pytest tests/test_config_manager.py (coverage > 95 %).
• 🧪 Integration: spin up docker-compose with both subsystems → ensure every agent boots with no missing keys.
• 🧪 Performance: compare cold-start times (<+10 ms allowed).

Rollback
git revert the migration commit; YAML defaults remain inert.

1.3 Extend ErrorPublisher to PC2 Subsystem
Problem PC2 agents log locally; no central error bus.
Affected Files 📄 All 23 PC2 agents (starting with async_processor.py, system_coordinator.py, …)
Changes

🛠 Add import: from main_pc_code.agents.error_publisher import ErrorPublisher as EP.
🛠 Inject in __init__: self.error_bus = EP(agent_name=__class__.__name__).
🛠 Wrap top-level asyncio.run(self.main()) with try/except → publish uncaught exceptions:
try:
    await self.main()
except Exception as exc:
    self.error_bus.publish(exc)
    raise
Order integrate into infrastructure-heavy agents first to validate network reachability, then cascade.
Testing
• 🧪 Trigger synthetic ZeroDivisionError; verify received on Main-PC SUB socket.
• 🧪 Check Grafana dashboard shows new PC2 error source.
Rollback stub ErrorPublisher injection block.

1.4 Unused-/Redundant-Import Cleanup (Automated)
Problem Dead imports increase build time & security surface.
Execution

ruff --select F401 --fix .
autoflake --remove-all-unused-imports -ri main_pc_code pc2_code
Validation 🧪 pytest -q passes; CI lint gate green.
Rollback git restore files.

PHASE 2 HIGH-PRIORITY IMPROVEMENTS (Week 2-3)
2.1 Standardized EnhancedBaseAgent Wrapper
Goal Uniform metrics & hooks across all agents.
Design Decorator-based loader:

🔧 common/core/agent_factory.py

def AgentBase():
    try:
        from common.core.enhanced_base_agent import EnhancedBaseAgent as _B
    except ImportError:
        from common.core.base_agent import BaseAgent as _B
    return _B
Usage: class ServiceRegistryAgent(AgentBase()): …

File Impact All 74 agents: change class inheritance line only.
Testing 🧪 Ensure hasattr(agent, 'metrics') true for agents when enhanced base present.

2.2 Centralized FastJSON Utility
Feature Wrap orjson/json once.
🔧 common/utils/fast_json.py

try:
    import orjson as _json
    dumps = _json.dumps; loads = _json.loads
except ImportError:
    import json as _json
    dumps = lambda o: _json.dumps(o, separators=(',', ':')).encode()
    loads = _json.loads
🛠 Replace per-file orjson logic (currently only in ServiceRegistry) with from common.utils.fast_json import dumps, loads.

2.3 Async Socket Wrappers
Goal Give Main-PC agents optional asyncio channels.
🔧 common/pools/async_zmq_pool.py – thin wrappers over zmq.asyncio.
Integration Points unified_system_agent.py, nlu_agent.py.
Testing 🧪 Bench throughput before/after (expect ~15 % latency reduction for burst loads).

2.4 Configuration Validation & Schema
Feature Add JSON-Schema validation to new ConfigManager.
🔧 common/config/schemas/agent_config.schema.json
🛠 ConfigManager validates at load, raises ConfigError.
Docs Update docs/configuration.md.

PHASE 3 MEDIUM-PRIORITY ENHANCEMENTS (Week 4-5)
3.1 Pluggable Backend Strategy for ServiceRegistry
Enhancement Goals Decouple storage strategies.
Implementation
🔧 main_pc_code/agents/backends/memory_backend.py
🔧 main_pc_code/agents/backends/redis_backend.py
🛠 service_registry_agent.py selects backend via factory.

Performance Impact Better unit-test coverage; no runtime if … else.
Compatibility Keep env var SERVICE_REGISTRY_BACKEND; default same.

3.2 Priority-Queue Refactor using asyncio.PriorityQueue
Target 📄 pc2_code/agents/async_processor.py
Changes

Delete manual deque lists.
Implement worker tasks pulling from PriorityQueue.
Metrics Expect 10–12 % drop in context switch overhead (profile with aiomonitor).
3.3 Monitoring & Metrics Expansion
Deliverables
• Prometheus exporter in common/monitoring/metrics.py.
• Add self.metrics.increment('tasks_processed') in AsyncProcessor, NLU, ServiceRegistry.
• Grafana dashboard update (new panels).

3.4 Documentation & Developer-Onboarding
Docs docs/architecture.md, docs/configuration.md, docs/error_handling.md updated to reflect new patterns.

IMPLEMENTATION CHECKLIST
[ ] 1.1 Import fix committed & deployed
[ ] 1.2 Unified ConfigManager merged, all agents migrated
[ ] 1.3 ErrorPublisher integrated into PC2
[ ] 1.4 Ruff/autoflake cleanup completed
[ ] 2.1 EnhancedBaseAgent wrapper applied
[ ] 2.2 fast_json utility adopted
[ ] 2.3 async_zmq_pool released & integrated
[ ] 2.4 Config schema validation live
[ ] 3.1 Pluggable backends shipped
[ ] 3.2 PriorityQueue refactor done
[ ] 3.3 Metrics exporter deployed
[ ] 3.4 Documentation updated
RISK MITIGATION
Git Branching Work on feature/phase-X branches; squash merge.
CI Gates Add lint, unit, integration, schema-validation jobs.
Backups Nightly DB & Redis dumps before each phase deploy.
Canary Deploy Roll out agents to staging cluster first; monitor for 24 h.
Automatic Rollback If health-check fails in deploy script, previous container re-started.
Observability Prometheus alerts for crash-loop, error-rate spikes, config-load failures.
SERVICE RESTART SEQUENCE
Stop celestial traffic (ingress pause).
Restart ServiceRegistryAgent → UnifiedSystemAgent → rest of Main-PC agents.
Restart PC2 agents in order: resource_manager → async_processor → others.
Resume ingress; monitor dashboards.
HEALTH-CHECK VALIDATION
./scripts/check_health.sh --all-agents  # returns HTTP 200 or ZMQ PING OK
Threshold: < 30 seconds for full green status.

Deliver this roadmap to execution teams; track each checklist item in Jira / GitHub Projects with linked PR IDs for traceability.

