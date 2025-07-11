# Group: Memory System

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: MemoryClient
- **Main Class:** `MemoryClient`
- **Host Machine:** Main PC
- **Role:** Thin client interface to the central MemoryOrchestratorService (PC2) for memory CRUD operations.
- **🎯 Responsibilities:** Kumonekta sa MemoryOrchestratorService; gumawa/magbura/maghahanap ng memories at sessions; mag-implement ng circuit-breaker para sa resilience; mag-relay ng error reports sa Error-Bus; mag-auto-reconnect kapag naputol.
- **🔗 Interactions:** MemoryOrchestratorService (PC2) via ZMQ REQ/REP; Error-Bus PUB socket (`tcp://192.168.100.17:7150`); ginagamit ng iba pang MainPC agents bilang internal library.
- **🧬 Technical Deep Dive:** Nagbubukas pa rin ng sariling ZMQ REP socket (port `5713`) bilang BaseAgent; health-check REP sa `5714`; REQ socket kumokonekta sa service-discovery address ng orchestrator; 5 s timeout; 10 s retry interval; CircuitBreaker class para i-gate requests.
- **⚠️ Panganib:** Dependency sa PC2 availability; kapag nag-OPEN ang circuit-breaker, lahat ng memory calls ay fail; security risk kung walang secure-ZMQ; overload kung sobrang daming parallel requests.
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5714
  - **🛰️ Port:** 5713
  - **🔧 Environment Variables:** `PC2_IP`, `ERROR_BUS_HOST`, `ERROR_BUS_PORT`, `SECURE_ZMQ`, `connection_retry_interval`, `request_timeout`
  - **📑 Sample Request:**
    ```json
    { "action": "create_session", "data": { "user_id": "U123", "session_type": "conversation" } }
    ```
  - **📊 Resource Footprint (baseline):** ~80 MB RAM, <4 % CPU.
  - **🔒 Security & Tuning Flags:** Circuit-breaker thresholds, secure-ZMQ toggle.

---
### 🧠 AGENT PROFILE: SessionMemoryAgent
- **Main Class:** `SessionMemoryAgent`
- **Host Machine:** Main PC
- **Role:** Tagapamahala ng session-level memory at conversational context.
- **🎯 Responsibilities:** Lumikha at mag-expire ng sessions; mag-store ng interactions; mag-provide ng context windows; mag-cleanup ng expired sessions; mag-publish ng error events; gumamit ng MemoryClient para sa persistent storage.
- **🔗 Interactions:** MemoryClient → MemoryOrchestratorService; Error-Bus PUB (`tcp://192.168.100.17:7150`); tumatanggap ng requests mula sa voice pipeline at iba pang agents.
- **🧬 Technical Deep Dive:** ZMQ REP socket bound to `5574`; health REP `6583`; constants: MAX_SESSIONS 100, SESSION_TIMEOUT 3600 s, MAX_CONTEXT_TOKENS 2000; background cleanup thread; request routing sa `process_request` method.
- **⚠️ Panganib:** Memory growth kapag hindi na-cleanup; failure kapag down ang central memory; race conditions sa simultaneous session access; exposure sa network kung hindi secured.
- **📡 Communication Details:** 
  - **🔌 Health Port:** 6583
  - **🛰️ Port:** 5574
  - **🔧 Environment Variables:** `PC2_IP`, `ERROR_BUS_HOST`, `ERROR_BUS_PORT`, `SECURE_ZMQ`, `MAX_SESSIONS`, `SESSION_TIMEOUT`
  - **📑 Sample Request:**
    ```json
    { "action": "get_context", "session_id": "S456", "limit": 20 }
    ```
  - **📊 Resource Footprint (baseline):** ~90 MB RAM, <6 % CPU; memory grows with active sessions.
  - **🔒 Security & Tuning Flags:** `MAX_CONTEXT_TOKENS`, secure-ZMQ toggle.

---
### 🧠 AGENT PROFILE: KnowledgeBase
- **Main Class:** `KnowledgeBase`
- **Host Machine:** Main PC
- **Role:** Knowledge-management agent para sa long-term factual data ng system.
- **🎯 Responsibilities:** Mag-add, mag-retrieve, mag-update at mag-search ng knowledge facts; gumamit ng semantic at text search; mag-publish ng errors; i-expose health endpoint.
- **🔗 Interactions:** MemoryClient / MemoryOrchestratorService; Error-Bus PUB (`tcp://192.168.100.17:7150`); callers na nangangailangan ng factual lookup.
- **🧬 Technical Deep Dive:** Default ZMQ REP port `5715` (env-configurable); health REP `6715`; gumagamit ng MemoryClient semantic_search at search_memory; nagta-track ng `request_count`; nag-log via standard logger.
- **⚠️ Panganib:** Stale or inaccurate data kapag hindi na-update; dependency sa MemoryClient connectivity; maaaring ma-DOS kung walang rate-limit; security issues sa open REP socket.
- **📡 Communication Details:** 
  - **🔌 Health Port:** 6715
  - **🛰️ Port:** 5715
  - **🔧 Environment Variables:** `KNOWLEDGE_BASE_PORT`, `KNOWLEDGE_BASE_HEALTH_PORT`, `ERROR_BUS_HOST`, `ERROR_BUS_PORT`, `SECURE_ZMQ`
  - **📑 Sample Request:**
    ```json
    { "action": "search_facts", "query": "project timeline", "limit": 5 }
    ```
  - **📊 Resource Footprint (baseline):** ~110 MB RAM, <5 % CPU.
  - **🔒 Security & Tuning Flags:** secure-ZMQ toggle, semantic search limit (`k`).

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| MemoryClient | ✓ | |
| SessionMemoryAgent | ✓ | |
| KnowledgeBase | ✓ | |
