# Group: Utility Services

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: CodeGenerator
- **Main Class:** `CodeGeneratorAgent`
- **Host Machine:** Main PC
- **Role:** AI code-generation service that converts natural-language prompts into executable code snippets using local LLMs (GGUF models) or Ollama back-end.
- **🎯 Responsibilities:** 
  • I-load / i-unload ang GGUF models on-demand.
  • Mag-generate ng code via GGUF or forward to external Ollama endpoint.
  • Mag-maintain ng model cache w/ idle-timeout (600 s).
  • Mag-expose health/ping + model status endpoints.
  • Mag-report ng errors sa Error-Bus.
- **🔗 Interactions:** 
  • `GGUFModelManager` for local model management.
  • Error-Bus PUB (`tcp://192.168.100.17:7150`).
  • Downstream dev/automation agents na humihingi ng code.
- **🧬 Technical Deep Dive:** 
  • ZMQ REP `tcp://0.0.0.0:5708`; Health REP `5709` (BaseAgent default).
  • JSON API actions: `generate`, `load_gguf_model`, `unload_gguf_model`, `list_gguf_models`, `generate_with_gguf`, `get_gguf_status`, `ping`, `health_check`.
  • Timeout = 5 s (`zmq_request_timeout`), auto-reconnect not needed (server-side).
  • Logging → `logs/code_generator_agent.log`.
- **⚠️ Panganib:** 
  • High VRAM/RAM usage kapag sabay-sabay na models ang naka-load.
  • Latency spikes kapag cold-load ng large model.
  • Security risk kung arbitrary code prompts ay hindi na-sanitize.
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5709
  - **🛰️ Port:** 5708
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `PC2_IP`, `SECURE_ZMQ`, `ENABLE_PROMETHEUS`, `AGENT_PORT`, `AGENT_NAME`
  - **📑 Sample Request:**
    ```json
    { "action": "generate_with_gguf", "model_id": "codellama", "prompt": "Write a bubble sort in Python" }
    ```
  - **📊 Resource Footprint (baseline):** ~250 MB RAM idle; +VRAM per loaded model (~2-6 GB); <8 % CPU idle.
  - **🔒 Security & Tuning Flags:** secure-ZMQ toggle; `MODEL_IDLE_TIMEOUT`; request timeout (5 s).

---
### 🧠 AGENT PROFILE: SelfTrainingOrchestrator
- **Main Class:** `SelfTrainingOrchestrator`
- **Host Machine:** Main PC
- **Role:** Scheduler at resource-aware orchestrator para sa automated self-training / fine-tuning cycles ng iba’t-ibang AI agents/models.
- **🎯 Responsibilities:** 
  • Mag-queue at mag-prioritize ng training cycles w/ resource constraints.
  • Mag-allocate CPU/GPU/MEMORY/NETWORK resources per cycle.
  • Mag-monitor ng progress, mag-update ng SQLite DB, at mag-release ng resources.
  • Mag-expose control API: create cycle, start/pause/stop, get status.
  • Health watchdog via dedicated REP socket; mag-publish errors sa Error-Bus.
- **🔗 Interactions:** 
  • Local SQLite DB (`data/self_training.db`).
  • Error-Bus PUB (`tcp://192.168.100.17:7150`).
  • Other agents (e.g., ActiveLearningMonitor) that request new training cycles.
- **🧬 Technical Deep Dive:** 
  • Main ZMQ REP `tcp://0.0.0.0:5644`; Health REP `5645`.
  • Uses `PriorityQueue` to schedule cycles; resource limits: CPU 100 %, GPU 100 %, RAM 16 GB.
  • Threads: `_run_cycle_manager`, `_health_check_loop`.
  • ENV-configurable via `AGENT_PORT`, `HEALTH_CHECK_PORT`, `PROJECT_ROOT`.
- **⚠️ Panganib:** 
  • Resource starvation kapag mali ang limits ➜ system slow-down.
  • Possible DB corruption sa abnormal shutdown.
  • Long-running cycles might hog GPU kung walang pre-emption.
- **📡 Communication Details:** 
  - **🔌 Health Port:** 5645
  - **🛰️ Port:** 5644
  - **🔧 Environment Variables:** `AGENT_NAME`, `AGENT_PORT`, `HEALTH_CHECK_PORT`, `PROJECT_ROOT`, `PC2_IP`, `SECURE_ZMQ`
  - **📑 Sample Request:**
    ```json
    { "action": "create_training_cycle", "agent_id": "VisionModel1", "config": {"epochs": 3}, "priority": 2 }
    ```
  - **📊 Resource Footprint (baseline):** ~180 MB RAM idle; CPU ~5 %; GPU usage depends on cycles.
  - **🔒 Security & Tuning Flags:** secure-ZMQ; `resource_limits` dict; `ZMQ_REQUEST_TIMEOUT`.

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| CodeGenerator | ✓ | |
| SelfTrainingOrchestrator | ✓ | |
