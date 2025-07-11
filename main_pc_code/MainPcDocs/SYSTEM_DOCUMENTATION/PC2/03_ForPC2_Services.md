# Group: Forpc2 Services

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: AuthenticationAgent
- **Main Class:** `AuthenticationAgent` (`pc2_code/agents/ForPC2/AuthenticationAgent.py`)
- **Host Machine:** PC-2
- **Role:** Central authentication / session-token service for all PC-2 agents.
- **🎯 Responsibilities:**
  • Handle registration, login, logout.  • Issue & validate JWT-like tokens (`_generate_token`, `_validate_token`).  • Hash & store passwords.  • Clean up expired sessions (background thread).  • Report auth errors to Error Bus.
- **🔗 Interactions:**
  • Receives auth requests via `REP` 7116.  • Publishes `ERROR` events to Error Bus (`PUB` 7150).  • Optionally connects to Main-PC services for user data.
- **🧬 Technical Deep Dive:** BaseAgent REP 7116, health REP 8116; network config overrides via env vars (`AUTH_PORT`, `AUTH_HEALTH_PORT`).  Session dict stored in-memory; expiry 24 h; cleanup every 5 min.
- **⚠️ Panganib:** Memory leak if session cleanup fails; brute-force attacks (add rate-limit); health socket duplication if config drifts.
- **📡 Communication Details:**
  - **🔌 Health Port:** 8116 (REP)
  - **🛰️ Port:** 7116 (REP)

---
### 🧠 AGENT PROFILE: SystemHealthManager
- **Main Class:** `SystemHealthManager` (`pc2_code/agents/ForPC2/system_health_manager.py`)
- **Host Machine:** PC-2
- **Role:** Top-level health aggregator for PC-2 memory subsystem (orchestrator & scheduler).
- **🎯 Responsibilities:**
  • Periodically ping MemoryOrchestratorService (7140) & MemoryScheduler (7142).  • Emit consolidated status & push errors to Error Bus.  • Expose `get_system_status` API.
- **🔗 Interactions:**
  • ZMQ `REQ` to orchestrator & scheduler.  • Error Bus `PUB` 7150.  • Health REP 8121.
- **🧬 Technical Deep Dive:** BaseAgent REP 7121, health REP 8121. `_run_health_checks` thread every 60 s; timeouts 5 s.  Uses `_report_error()` helper.
- **⚠️ Panganib:** False negatives if sub-services slow; error-bus overload on repeated failures.
- **📡 Communication Details:**
  - **🔌 Health Port:** 8121 (REP)
  - **🛰️ Port:** 7121 (REP)

---
### 🧠 AGENT PROFILE: UnifiedUtilsAgent
- **Main Class:** `UnifiedUtilsAgent` (`pc2_code/agents/ForPC2/unified_utils_agent.py`)
- **Host Machine:** PC-2
- **Role:** Maintenance & housekeeping utilities (temp/log cache cleanup, disk cleanup, browser cache).
- **🎯 Responsibilities:**
  • Expose actions `cleanup_temp_files`, `cleanup_logs`, `cleanup_cache`, `cleanup_browser_cache`.  • Provide system cleanup orchestration.  • Report issues to Error Bus.
- **🔗 Interactions:**
  • Exposed via `REP` 7118.  • Error `PUB` 7150.
- **🧬 Technical Deep Dive:** BaseAgent REP 7118, health REP 8118. Platform-aware cleanup paths; measures bytes freed.
- **⚠️ Panganib:** Deleting wrong files; OS permission errors; long-running disk cleanup.
- **📡 Communication Details:**
  - **🔌 Health Port:** 8118 (REP)
  - **🛰️ Port:** 7118 (REP)

---
### 🧠 AGENT PROFILE: ProactiveContextMonitor
- **Main Class:** `ProactiveContextMonitor` (`pc2_code/agents/ForPC2/proactive_context_monitor.py`)
- **Host Machine:** PC-2
- **Role:** Background context analyzer that triggers proactive prompts/actions.
- **🎯 Responsibilities:**
  • Maintain `context_history`.  • Accept `add_context` events.  • Analyze context every 10 s in thread; trigger future proactive actions (TBD).
- **🔗 Interactions:** Error Bus `PUB` 7150; may connect to Main-PC services dynamically.
- **🧬 Technical Deep Dive:** BaseAgent REP 7119, health REP 8119. Background analysis thread; context stored in list; health reflects history length.
- **⚠️ Panganib:** Context history growth; analysis loop exceptions; missing proactive action handlers.
- **📡 Communication Details:**
  - **🔌 Health Port:** 8119 (REP)
  - **🛰️ Port:** 7119 (REP)

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| AuthenticationAgent | ✓ | |
| SystemHealthManager | ✓ | |
| UnifiedUtilsAgent | ✓ | |
| ProactiveContextMonitor | ✓ | |
