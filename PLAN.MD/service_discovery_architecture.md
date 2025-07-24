# SERVICE DISCOVERY ARCHITECTURE

## 1. Current Design
1. **SystemDigitalTwin** (MainPC) acts as central registry.
2. All agents inherit `BaseAgent`; during construction they invoke `_register_with_digital_twin()` (definition around line 503 in `common/core/base_agent.py`).  
   ```python
   def _register_with_digital_twin(self) -> None:
       """Register this agent with the SystemDigitalTwin for service discovery."""
   ```
3. Registration message is pushed via ZeroMQ using the helper `send_event()` method to the Digital Twin (default host `localhost`, port derived from config or fallback 7220/8220).
4. Agents discover **other** agents at runtime by calling `get_agent_endpoint()` which queries the Digital Twin (`/get_agent` action) and caches the `(host, port)` pair (see lines ~547-580 in the same file).

## 2. Observations / Issues
| # | Issue | Evidence | Impact |
|---|-------|----------|--------|
| 1 | **Registration never happens** because construction crashes before reaching `_register_with_digital_twin()` (see BaseAgent report). | Constructor error; no ZMQ message emitted. | 🔴 Central registry empty → discovery fails across both machines. |
| 2 | **Port hard-coding** — Digital Twin port is fixed in configs at 7220/8220 (MainPC) and referenced verbatim on PC2; if changed, code must be rebuilt. | Search for `7220` shows direct literals in several agents. | 🟠 Limits flexibility, risk of mismatch. |
| 3 | **No PC2 fallback** — PC2 agents register to *local* Digital Twin only if their config overrides host/port; default assumes `localhost`. | Default args in `_register_with_digital_twin()` | 🟠 Cross-machine discovery breaks when processes live on different hosts. |
| 4 | **Missing heartbeat** — After initial registration there is no keep-alive; stale entries accumulate. | No periodic call in BaseAgent. | 🟡 Could lead to routing to dead agents. |

## 3. Recommendations
1. **Fix startup path first** so registration code executes.
2. Introduce a **Service Registry HA layer** shared between machines (could be Redis-backed as hinted in configs) so PC2 can query MainPC services without direct host/port assumptions.
3. Add **heartbeat / TTL** in Digital Twin; agents should renew every N seconds.
4. Externalise registry address via env vars (`SERVICE_REGISTRY_HOST/PORT`) consumed by BaseAgent.
5. Provide **graceful deregistration** in `cleanup()` to prevent stale entries.
