# Group: Pc2 Core Agents

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: DreamWorldAgent
- **Main Class:** `DreamWorldAgent` (`pc2_code/agents/DreamWorldAgent.py`)
- **Host Machine:** PC-2
- **Role:** Scenario-simulation agent that runs Monte-Carlo-Tree-Search (MCTS) “dream worlds” for strategy & planning.
- **🎯 Responsibilities:**
  • Load scenario templates from SQLite.  • Run MCTS simulations (`run_simulation`) to evaluate actions.  • Persist results and causal analysis.  • Provide create / update / history API.
- **🔗 Interactions:**
  • Stores episode data in `dream_world.db`.  • May query UnifiedMemoryReasoningAgent for context.  • Sends error reports to Error Bus.
- **🧬 Technical Deep Dive:** Inherits `BaseAgent`; ROUTER **7104**, dedicated REP health **7105**. Background `_initialize_background` loads DB & templates. ThreadPoolExecutor for parallel simulations.
- **⚠️ Panganib:** Long simulations CPU heavy; health socket duplication with BaseAgent default; DB corruption.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7105 (REP)
  - **🛰️ Port:** 7104 (ROUTER/REQ-REP)

---
### 🧠 AGENT PROFILE: UnifiedMemoryReasoningAgent
- **Main Class:** `UnifiedMemoryReasoningAgent` (`pc2_code/agents/unified_memory_reasoning_agent.py`)
- **Host Machine:** PC-2
- **Role:** Consolidated memory, context and reasoning service (merges ContextualMemory, ErrorPatternMemory, etc.).
- **🎯 Responsibilities:**
  • Store/retrieve context, errors, twins.  • Provide summarisation and conflict resolution.  • Coordinate memory agents via ZMQ.
- **🔗 Interactions:** Various memory agents on 55xx ports; Remote models.  Error Bus.
- **🧬 Technical Deep Dive:** BaseAgent REP **7105**, health REP **7106**. Uses JSON stores (`memory_store.json`, etc.), ContextManager helper, priority levels.
- **⚠️ Panganib:** Large JSON files, potential race on file writes.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7106 (REP)
  - **🛰️ Port:** 7105 (REP)

---
### 🧠 AGENT PROFILE: TutorAgent
- **Main Class:** `TutorAgent` (`pc2_code/agents/tutor_agent.py`)
- **Host Machine:** PC-2 (GPU optional)
- **Role:** Adaptive AI tutor providing personalised lessons and feedback.
- **🎯 Responsibilities:**
  • Manage `StudentProfile`, lessons, progress tracking.  • Adjust difficulty via NN (`AdaptiveLearningEngine`).
- **🔗 Interactions:** Reads lesson files; may use TinyLlama/NLLB for generation; Error Bus.
- **🧬 Technical Deep Dive:** Port from config (`tutor.port`, default **5605**); BaseAgent health **5606** (default). Uses PyTorch & sklearn models.
- **⚠️ Panganib:** GPU memory spikes during model use; missing health socket if config changes.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5606 (BaseAgent default)
  - **🛰️ Port:** 5605 (REP)

---
### 🧠 AGENT PROFILE: TutoringServiceAgent
- **Main Class:** `TutoringServiceAgent` (`pc2_code/agents/tutoring_service_agent.py`)
- **Host Machine:** PC-2
- **Role:** Lightweight facade exposing tutoring operations to external callers.
- **🎯 Responsibilities:** Simple CRUD interface, forward heavy work to TutorAgent.
- **🔗 Interactions:** TutorAgent (internal call), Error Bus.
- **🧬 Technical Deep Dive:** BaseAgent REP **5604**, health default **5605** handled via same socket (no dedicated health REP).
- **⚠️ Panganib:** Health monitoring limited; no auth on API.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5605 (default, not separately bound)
  - **🛰️ Port:** 5604 (REP)

---
### 🧠 AGENT PROFILE: ContextManager
- **Main Class:** `ContextManager` (`pc2_code/agents/context_manager.py`)
- **Host Machine:** Library / internal (runs inside UnifiedMemoryReasoningAgent)
- **Role:** Advanced conversation context window manager.
- **🎯 Responsibilities:** Add/prune context, adjust window size, calculate importance.
- **🔗 Interactions:** Called by other agents, no external ZMQ.
- **🧬 Technical Deep Dive:** Instantiated without network ports → **Not a standalone agent**.
- **⚠️ Panganib:** Memory leak if importance map grows.
- **📡 Communication Details:**
  - **🔌 Health Port:** N/A (library)
  - **🛰️ Port:** N/A

---
### 🧠 AGENT PROFILE: ExperienceTracker
- **Main Class:** `ExperienceTrackerAgent` (`pc2_code/agents/experience_tracker.py`)
- **Host Machine:** PC-2
- **Role:** Store & retrieve episodic experience memories and forward to EpisodicMemoryAgent.
- **🎯 Responsibilities:** Track experiences, forward to EpisodicMemoryAgent, expose retrieval API.
- **🔗 Interactions:** Connects to EpisodicMemoryAgent (`REQ` dynamic port). Error Bus.
- **🧬 Technical Deep Dive:** REP **7112**, health REP **7113**. Uses helper to load network config and bind sockets.
- **⚠️ Panganib:** Dependency on EpisodicMemoryAgent availability.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7113 (REP)
  - **🛰️ Port:** 7112 (REP)

---
### 🧠 AGENT PROFILE: ResourceManager
- **Main Class:** `ResourceManager` (`pc2_code/agents/resource_manager.py`)
- **Host Machine:** PC-2
- **Role:** Allocate & monitor CPU/GPU/RAM usage, expose stats, handle resource locks.
- **🎯 Responsibilities:** Provide `get_current_stats`, `allocate_resources`, `release_resources`, threshold tuning.
- **🔗 Interactions:** Publishes health; may deny requests from other agents.
- **🧬 Technical Deep Dive:** REP **7113**, health REP **7114**; deque history of stats; GPU via torch.
- **⚠️ Panganib:** Mis-set thresholds causing denial of service.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7114 (REP)
  - **🛰️ Port:** 7113 (REP)

---
### 🧠 AGENT PROFILE: HealthMonitor
- **Main Class:** `HealthMonitorAgent` (`pc2_code/agents/health_monitor.py`)
- **Host Machine:** PC-2
- **Role:** Aggregate health of PC-2 agents and expose status.
- **🎯 Responsibilities:** Maintain `agent_status` dict, answer `get_status`, broadcast health.
- **🔗 Interactions:** Receives health pings from agents; Error Bus.
- **🧬 Technical Deep Dive:** REP **7114**, health REP **7115**. Background init sets agent_status.
- **⚠️ Panganib:** Flood of health messages; dependency on ResourceManager.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7115 (REP)
  - **🛰️ Port:** 7114 (REP)

---
### 🧠 AGENT PROFILE: TaskScheduler
- **Main Class:** `TaskSchedulerAgent` (`pc2_code/agents/task_scheduler.py`)
- **Host Machine:** PC-2
- **Role:** Front-end scheduler that forwards tasks to AsyncProcessor with priority.
- **🎯 Responsibilities:** Schedule task via `schedule_task`, relay to AsyncProcessor, maintain pending count.
- **🔗 Interactions:** Connects to AsyncProcessor (`REQ` 5555), Error Bus.
- **🧬 Technical Deep Dive:** REP **7115**, health REP **7116**; has `_initialize_background` thread.
- **⚠️ Panganib:** AsyncProcessor downtime, queue buildup.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7116 (REP)
  - **🛰️ Port:** 7115 (REP)

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| DreamWorldAgent | ✓ | |
| UnifiedMemoryReasoningAgent | ✓ | |
| TutorAgent | ✓ | Uses BaseAgent, default health port |
| TutoringServiceAgent | ✗ | Health served on same socket, no dedicated health REP |
| ContextManager | N/A | Library/helper, not standalone agent |
| ExperienceTracker | ✓ | |
| ResourceManager | ✓ | |
| HealthMonitor | ✓ | |
| TaskScheduler | ✓ | |
