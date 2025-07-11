# Group: Reasoning Services

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: ChainOfThoughtAgent
- **Main Class:** `ChainOfThoughtAgent` (`main_pc_code/FORMAINPC/ChainOfThoughtAgent.py`)
- **Host Machine:** Main PC
- **Role:** Multi-step Chain-of-Thought reasoning agent for breaking complex user requests into logical sub-steps and orchestrating LLM calls.
- **🎯 Responsibilities:**
  • Generate numbered reasoning steps for a task (`generate_problem_breakdown`).
  • Call Remote Connector (LLM router) for each step (`send_to_llm`).
  • Verify and refine partial solutions, then assemble a final answer (`generate_with_cot`).
  • Track metrics (requests, success/fail) and publish errors to Error Bus.
- **🔗 Interactions:**
  • **RemoteConnectorAgent** on port 5557 (`REQ/REP`) for model inference.
  • Publishes `ERROR:` topic to central Error Bus (`tcp://PC2_IP:7150`).
- **🧬 Technical Deep Dive:**
  • Inherits from `BaseAgent` → ZMQ REP bound to **5612**; explicit health REP **6612**.
  • Uses helper regex parsing to extract steps; fallback extraction if LLM output malformed.
  • Keeps `total_requests / successful_requests / failed_requests` counters; uptime via `start_time`.
- **⚠️ Panganib:** LLM time-outs (30 s poll); over-long prompts; RemoteConnector unavailability; high CPU during large step lists.
- **📡 Communication Details:**
  - **🔌 Health Port:** 6612
  - **🛰️ Port:** 5612
  - **🔧 Environment Variables:** `PC2_IP`, optional config keys `chain_of_thought_port`, `health_check_port`
  - **📑 Sample Request:** `{ "action": "generate_with_cot", "user_request": "Write unit tests for merge sort" }`
  - **📊 Resource Footprint (baseline):** ~150 MB RAM; CPU 3-5 % idle.
  - **🔒 Security & Tuning Flags:** ZMQ time-outs (5 s); RemoteConnector circuit-breaker logic.

---
### 🧠 AGENT PROFILE: GoTToTAgent
- **Main Class:** `GoTToTAgent` (`main_pc_code/FORMAINPC/GOT_TOTAgent.py`)
- **Host Machine:** Main PC
- **Role:** Graph/Tree-of-Thought reasoning agent that explores multiple reasoning branches to select the best solution path.
- **🎯 Responsibilities:**
  • Build reasoning tree up to `max_steps` (5) × `max_branches` (3).
  • Score paths and return best/alternative paths (`reason`).
  • Load local or HF model for step generation (`_load_reasoning_model`).
  • Expose simple API `{ "action": "reason", "prompt": … }`.
- **🔗 Interactions:**
  • Local/remote HF model (Phi-2 or local GGUF).
  • Publishes errors to Error Bus (commented lines indicate future wiring).
- **🧬 Technical Deep Dive:**
  • ZMQ REP bound to **5646**; inherits health REP **5647** via BaseAgent.
  • Threaded `_process_loop` with poller; request/response in JSON.
- **⚠️ Panganib:** Missing health socket may violate monitoring; model load failure falls back to limited mode; high VRAM during model load.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5647 (BaseAgent default; auto-bound)
  - **🛰️ Port:** 5646

---
### 🧠 AGENT PROFILE: CognitiveModelAgent
- **Main Class:** `CognitiveModelAgent` (`main_pc_code/FORMAINPC/CognitiveModelAgent.py`)
- **Host Machine:** Main PC
- **Role:** Belief-system manager that stores, queries, and reasons over a directed graph of beliefs.
- **🎯 Responsibilities:**
  • Maintain `networkx.DiGraph` of beliefs/relations.
  • Provide API to add beliefs, query consistency, and retrieve full graph.
  • Connect to Remote Connector (PC2) for advanced reasoning where needed.
  • Update `health_status` dict and serve requests via ZMQ.
- **🔗 Interactions:**
  • Remote Connector (`tcp://PC2_IP:5557`) via REQ.
  • Publishes errors to Error Bus (marked for future wiring).
- **🧬 Technical Deep Dive:**
  • Inherits `BaseAgent`; ZMQ ROUTER bound to **5641**; health REP **5642** via BaseAgent.
  • Uses helper `_initialize_belief_system()` to seed core beliefs; performs DAG checks for consistency.
- **⚠️ Panganib:** Graph can become cyclic (inconsistency); absent health port limits observability; heavy graph ops may spike CPU.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5642 (BaseAgent default; auto-bound)
  - **🛰️ Port:** 5641
  - **🔧 Environment Variables:** `PC2_IP`, config keys `COGNITIVE_MODEL_PORT`, `REMOTE_CONNECTOR_PORT`

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| ChainOfThoughtAgent | ✓ | |
| GoTToTAgent | ✓ | |
| CognitiveModelAgent | ✓ | |

---

