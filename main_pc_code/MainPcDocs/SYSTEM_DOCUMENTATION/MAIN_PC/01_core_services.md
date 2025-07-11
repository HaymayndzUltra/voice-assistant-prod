# Group: Core Services

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: SystemDigitalTwin
- **Main Class:** `SystemDigitalTwinAgent`
- **Host Machine:** Main PC
- **Role:** Digital twin ng buong system; central service-registry at real-time metrics collector.
- **🎯 Responsibilities:** Mangolekta ng CPU, RAM, VRAM, network-latency metrics; mag-maintain ng metrics history; mag-expose ng ZMQ API para health/status, agent registration & discovery; i-push metrics sa Prometheus; mag-relay ng error reports sa Error-Bus.
- **🔗 Interactions:** Lahat ng agents (service registry), Prometheus, Redis (optional), secure-ZMQ handshake.
- **🧬 Technical Deep Dive:** Main ZMQ REP `tcp://0.0.0.0:7120`; Health REP `tcp://0.0.0.0:8120`; metrics thread `_collect_metrics_loop()`, in-memory registry (`self.service_registry`); error publishing via ZMQ PUB (`ERROR:` topic).
- **⚠️ Panganib:** Single point of failure para sa discovery; metric drift kapag down ang Prometheus/Redis; potensyal na resource overhead sa napakaraming updates.
- **📡 Communication Details:** 
  - **🔌 Health Port:** 8120
  - **🛰️ Port:** 7120
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `ENABLE_PROMETHEUS`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `SECURE_ZMQ`
  - **📑 Sample Request:**
    ```json
    { "action": "register_agent", "data": { "name": "ExampleAgent", "ip": "127.0.0.1", "port": 5000 } }
    ```
  - **📊 Resource Footprint (baseline):** ~100 MB RAM, <5 % CPU idle.
  - **🔒 Security & Tuning Flags:** `SECURE_ZMQ=true`, `ENABLE_PROMETHEUS=true`.

---
### 🧠 AGENT PROFILE: RequestCoordinator
- **Main Class:** `RequestCoordinator`
- **Host Machine:** Main PC
- **Role:** Central task dispatcher at dynamic priority-queue manager para sa lahat ng user requests.
- **🎯 Responsibilities:** Tumatanggap ng text/audio/vision requests; nag-prioritize at nag-dispatch sa MemoryOrchestrator, StreamingTTSAgent, ChainOfThoughtAgent, GOT_TOTAgent; nag-monitor at nag-log ng metrics; sumusubscribe sa StreamingInterruptHandler; nag-publish ng errors sa Error-Bus.
- **🔗 Interactions:** Service discovery via `utils.service_discovery_client`; Proactive suggestion channel (`tcp://*:5591`); SUB connection sa Speech/Language Analyzer.
- **🧬 Technical Deep Dive:** Main ZMQ REP `tcp://0.0.0.0:26002`; Health REP `tcp://0.0.0.0:26003`; extra REP on 5591; circuit-breaker per downstream service; metrics file `logs/request_coordinator_metrics.json`.
- **⚠️ Panganib:** Queue overflow ➜ latency spikes; mis-configured circuit breaker ➜ unnecessary cut-offs; security risk kung disabled ang secure-ZMQ.
- **📡 Communication Details:** 
  - **🔌 Health Port:** 26003
  - **🛰️ Port:** 26002
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `PC2_IP`, `SECURE_ZMQ`, `queue_max_size`, `enable_dynamic_prioritization`
  - **📑 Sample Request:**
    ```json
    { "type": "text", "data": "Hello world", "context": {}, "metadata": {} }
    ```
  - **📊 Resource Footprint (baseline):** ~150 MB RAM, <10 % CPU with moderate queue.
  - **🔒 Security & Tuning Flags:** `SECURE_ZMQ`, circuit-breaker thresholds.

---
### 🧠 AGENT PROFILE: UnifiedSystemAgent
- **Main Class:** `UnifiedSystemAgent`
- **Host Machine:** Main PC
- **Role:** Central orchestrator / command center para sa service discovery, lifecycle management, at maintenance.
- **🎯 Responsibilities:** Mag-expose ng ROUTER socket para sa control commands; mag-monitor at mag-restart ng services; mag-maintain ng consolidated registry; lumikha ng readiness file; magbigay ng system maintenance utilities.
- **🔗 Interactions:** Lahat ng MainPC agents – registration at health-queries; external management consoles via ZMQ ROUTER.
- **🧬 Technical Deep Dive:** ROUTER `tcp://0.0.0.0:5568`; Health REP `tcp://0.0.0.0:5569`; background threads `_initialize_background`, `_monitor_services`; thread-safe `self.services` dict; port ranges ZMQ 5500-5600, HTTP 8000-8100.
- **⚠️ Panganib:** High-privilege agent (risk kapag compromised); CPU overhead kung mis-tuned monitoring loops; single-point failure tulad ng SystemDigitalTwin.
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5569
  - **🛰️ Port:** 5568
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `SYSTEM_AGENT_PORT`, `HEALTH_CHECK_PORT`, `SECURE_ZMQ`
  - **📑 Sample Request:**
    ```json
    { "action": "get_system_info" }
    ```
  - **📊 Resource Footprint (baseline):** ~120 MB RAM, <7 % CPU; peaks during restarts.
  - **🔒 Security & Tuning Flags:** `SECURE_ZMQ`, port ranges (`ZMQ_PORT_RANGE`, `HTTP_PORT_RANGE`).

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| SystemDigitalTwin | ✓ | |
| RequestCoordinator | ✓ | |
| UnifiedSystemAgent | ✓ | |
