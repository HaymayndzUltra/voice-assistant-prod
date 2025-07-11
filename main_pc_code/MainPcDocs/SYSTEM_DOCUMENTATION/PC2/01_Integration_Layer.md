# Group: Integration Layer

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: TieredResponder
- **Main Class:** `TieredResponder` (`pc2_code/agents/tiered_responder.py`)
- **Host Machine:** PC-2
- **Role:** Tier-based responder that routes text queries to Instant / Fast / Deep handlers.
- **🎯 Responsibilities:**
  • Match query to tier using regex patterns.
  • Invoke corresponding async handler and enqueue responses.
  • Broadcast health & resource stats every 30 s.
- **🔗 Interactions:**
  • Receives queries (`REP` 7101) from Main-PC integration bus.
  • Pushes responses (`PUSH` 7102) back to bus.
  • Publishes health JSON (`PUB` 7103).
  • Reports errors via central Error Bus.
- **🧬 Technical Deep Dive:** Inherits `BaseAgent` (main 7100 / health 7101 default). Overrides with custom sockets (7101/7102/7103). Utilises `ResourceManager` (psutil + torch) and async `deque` queue (`MAX_QUEUE_SIZE = 100`).
- **⚠️ Panganib:** Queue overflow, GPU spike on Deep tier, duplicated health sockets between BaseAgent and custom config.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7103 (PUB JSON)
  - **🛰️ Port:** 7101 (REQ/REP user queries) ‑ main; 7102 (PUSH responses)

---
### 🧠 AGENT PROFILE: AsyncProcessor
- **Main Class:** `AsyncProcessor` (`pc2_code/agents/async_processor.py`)
- **Host Machine:** PC-2
- **Role:** Priority-based asynchronous task dispatcher for background jobs.
- **🎯 Responsibilities:**
  • Accept tasks via `send_task` API and prioritise (high/medium/low).
  • Execute handlers `_handle_*` on worker thread.
  • Monitor resources & queue stats; publish health.
- **🔗 Interactions:**
  • Receives tasks (`REP` 7101).
  • Pushes downstream work (`PUSH` 7102).
  • Publishes health JSON (`PUB` 7103).
  • Error Bus for exception reporting.
- **🧬 Technical Deep Dive:** Built on `TaskQueue` + `ResourceManager`. Background threads: task processor, health monitor (30 s). Decorator `@async_task` lets other modules push into queue without direct ZMQ.
- **⚠️ Panganib:** Starvation of low-priority queue, Redis-size bursts if handlers write cache, duplicate health socket (BaseAgent default 7102).
- **📡 Communication Details:**
  - **🔌 Health Port:** 7103 (PUB)
  - **🛰️ Port:** 7101 (REQ/REP), 7102 (PUSH)

---
### 🧠 AGENT PROFILE: CacheManager
- **Main Class:** `CacheManager` (`pc2_code/agents/cache_manager.py`)
- **Host Machine:** PC-2
- **Role:** Central Redis cache service for NLU, model decisions, memory blobs.
- **🎯 Responsibilities:**
  • CRUD cache entries with TTL/size quotas.
  • Background maintenance every 5 min to evict expired keys.
  • Memory-specific helpers (`cache_memory`, `invalidate_memory_cache`).
- **🔗 Interactions:**
  • Connects to Redis (env `REDIS_HOST|PORT|PWD`).
  • Serves requests from Main-PC & PC-2 via `REP` 7102.
  • Publishes health (`REP` 8102 via BaseAgent health).
  • Error Bus integration.
- **🧬 Technical Deep Dive:** Inherits `BaseAgent` with explicit `health_check_port=8102`. Uses Redis `ping()` at init. Maintenance thread checks `ResourceMonitor` memory_percent and calls `flush_cache` on threshold.
- **⚠️ Panganib:** Redis outage, high memory if MAX_CACHE_SIZE mis-tuned, TTL misconfiguration.
- **📡 Communication Details:**
  - **🔌 Health Port:** 8102 (REQ/REP)
  - **🛰️ Port:** 7102 (REQ/REP)

---
### 🧠 AGENT PROFILE: PerformanceMonitor
- **Main Class:** `PerformanceMonitor` (`pc2_code/agents/performance_monitor.py`)
- **Host Machine:** PC-2
- **Role:** System-wide performance metrics collector and alert broadcaster.
- **🎯 Responsibilities:**
  • Track CPU, RAM, queue sizes, response times.
  • Publish metrics every 5 s (`PUB` 5619).
  • Broadcast health at same cadence (`PUB` 5620).
  • Raise alerts when thresholds exceeded.
- **🔗 Interactions:**
  • Subscribers: Dashboard, Self-Healing Agent.
  • Error Bus for anomaly reports.
- **🧬 Technical Deep Dive:** Uses `ResourceMonitor` deque history (1 000 samples). Calculates averages & error rate. BaseAgent main port 7103 (unused externally).
- **⚠️ Panganib:** Metric spam if PUB unbounded; high CPU from numpy mean over large deque.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5620 (PUB JSON)
  - **🛰️ Port:** 5619 (PUB metrics) + BaseAgent REP 7103 (internal)

---
### 🧠 AGENT PROFILE: VisionProcessingAgent
- **Main Class:** `VisionProcessingAgent` (`pc2_code/agents/VisionProcessingAgent.py`)
- **Host Machine:** PC-2 (GPU optional)
- **Role:** Process images sent by VisionCaptureAgent and generate descriptions.
- **🎯 Responsibilities:**
  • Decode Base64 images, optionally save for audit.
  • Produce description (placeholder or model inference).
  • Provide health report with uptime & system metrics.
- **🔗 Interactions:**
  • Receives image requests via BaseAgent `REP` 7150.
  • Sends error events to Error Bus.
- **🧬 Technical Deep Dive:** Inherits `BaseAgent` port 7150; no explicit health socket—relies on `health_check()` method invoked via same `REP`.
- **⚠️ Panganib:** Large image memory, missing GPU leads to slow model, absence of dedicated health socket.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7151 (BaseAgent default, **not bound**; health served by same REP)
  - **🛰️ Port:** 7150 (REQ/REP)

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| TieredResponder | ✓ | |
| AsyncProcessor | ✓ | |
| CacheManager | ✓ | Explicit `health_check_port` set (8102) |
| PerformanceMonitor | ✓ | Uses PUB for health but BaseAgent health REP unused |
| VisionProcessingAgent | ✗ | Walang dedicated `health_socket` (relies on same REP) |

