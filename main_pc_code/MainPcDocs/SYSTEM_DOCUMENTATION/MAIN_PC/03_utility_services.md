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
- **Role:** Scheduler at resource-aware orchestrator para sa automated self-training / fine-tuning cycles ng iba't-ibang AI agents/models.
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
### 🧠 AGENT PROFILE: PredictiveHealthMonitor
- **Main Class:** `PredictiveHealthMonitor`
- **Host Machine:** Main PC (primary orchestration node)
- **Role:** Centralised predictive health monitor and resource optimiser
- **🎯 Responsibilities:** Monitors runtime metrics of all Main-PC agents, runs ML-based failure prediction, triggers recovery via Self-Healing Agent, publishes errors to the Error Bus, and exposes health/status over ZMQ.
- **🔗 Interactions:**
  - Self-Healing Agent (`REQ/REP` on port 5606)
  - Distributed Discovery Service (if enabled) via ZMQ REP/REQ
  - Publishes `ERROR:` topic to Error Bus (`PUB` → tcp://PC2_IP:7150)
  - Receives health queries from other services (`REP` on port 5605)
- **🧬 Technical Deep Dive:** Utilises `psutil` for system stats, stores metrics in SQLite (`health_monitor.sqlite`), loads an optional `failure_predictor.pkl`, maintains per-agent subprocesses with restart cooldown, and runs optimisation threads for memory/disk.
- **⚠️ Panganib:** High CPU usage while aggregating metrics, mis-predicting failures leading to unnecessary restarts, single-point failure if DB corrupts, socket bind issues (undefined `HEALTH_CHECK_PORT`).
- **📡 Communication Details:**
  - **🔌 Health Port:** 5606 (should be defined as `HEALTH_CHECK_PORT`; currently missing → runtime error). Primary health REP socket exposed on **5605**.
  - **🛰️ Port:** 5605 (command/monitor channel)
  - **🔧 Environment Variables:** `PC2_IP`, `SELF_HEALING_HOST`, optional ZMQ overrides
  - **📑 Sample Request:** `{ "action": "health" }`  → tcp://<host>:5605  (expects `{ "status": "ok", ... }`)
  - **📊 Resource Footprint (baseline):** ~30-80 MB RAM, <5 % CPU idle (varies with number of agents)
  - **🔒 Security & Tuning Flags:** ZMQ time-outs (RCVTIMEO/SNDTIMEO = 5000 ms), restart cooldown = 60 s

---
### 🧠 AGENT PROFILE: FixedStreamingTranslation
- **Main Class:** `FixedStreamingTranslation`
- **Host Machine:** Main PC
- **Role:** Primary high-throughput streaming translator with intelligent fallback
- **🎯 Responsibilities:** Provides real-time translation, maintains performance metrics, adaptive time-outs, local cache, Google-Translate fallback, and forwards errors to Error Bus.
- **🔗 Interactions:**
  - Connects to PC-2 translator (`tcp://PC2_IP:5595` default)
  - Publishes errors to Error Bus (`tcp://PC2_IP:7150`)
  - Internal helper components: `PerformanceMonitor`, `TranslationCache`, `AdvancedTimeoutManager`
- **🧬 Technical Deep Dive:** ZMQ `REP` on port 5584, separate health `REP` on 6584. Uses threads for queue processing and health updates, caches translations with TTL, monitors p95 latency, exposes metrics.
- **⚠️ Panganib:** GPU/CPU memory pressure due to model loading, external dependency (Google API), queue buildup can raise latency.
- **📡 Communication Details:**
  - **🔌 Health Port:** 6584
  - **🛰️ Port:** 5584

---
### 🧠 AGENT PROFILE: Executor
- **Main Class:** `ExecutorAgent`
- **Host Machine:** Main PC (Windows-centric command executor)
- **Role:** Executes OS-level commands mapped from verbal/text commands.
- **🎯 Responsibilities:** Receives command requests over ZMQ, validates user permissions, launches OS processes, and emits feedback/logs.
- **🔗 Interactions:**
  - Sends usage/log events to central log collector (`PUB` → port 5600)
  - Feedback `PUB` socket on port 5710
  - Publishes errors to Error Bus
- **🧬 Technical Deep Dive:** ZMQ `REP` binds `tcp://<bind_addr>:5709`; command map uses `subprocess`. Hot-reload watcher monitors mapping file. Authentication via local `user_profile.json`.
- **⚠️ Panganib:** High privilege operations (shutdown, lock). Incorrect permission config can lead to abuse. Windows-only commands limit portability.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5710 (auto-bound via BaseAgent default; note: port conflict with feedback PUB socket on same port — recommend separating).
  - **🛰️ Port:** 5709 (command REP)

---
### 🧠 AGENT PROFILE: TinyLlamaServiceEnhanced
- **Main Class:** `TinyLlamaServiceEnhanced`
- **Host Machine:** Main PC
- **Role:** Lightweight LLM service using TinyLlama models for fast inference
- **🎯 Responsibilities:** Provides fast inference using TinyLlama models, exposes simple API, and integrates with ModelManagerAgent
- **🔗 Interactions:**
  - ModelManagerAgent for model loading/unloading
  - Error Bus for error reporting
- **🧬 Technical Deep Dive:** Uses ZMQ REP socket on port 5615, health check on port 6615, integrates with ModelManagerAgent for efficient resource usage
- **⚠️ Panganib:** Model loading failures, memory pressure during inference
- **📡 Communication Details:**
  - **🔌 Health Port:** 6615
  - **🛰️ Port:** 5615

---
### 🧠 AGENT PROFILE: LocalFineTunerAgent
- **Main Class:** `LocalFineTunerAgent`
- **Host Machine:** Main PC (GPU recommended)
- **Role:** Manages on-device fine-tuning jobs for LLMs and stores resulting artefacts.
- **🎯 Responsibilities:** Queue/manage tuning jobs, utilise PEFT/LoRA via HuggingFace Transformers, log metrics to SQLite, publish errors.
- **🔗 Interactions:** Error Bus, local SQLite `local_fine_tuner.db`, uses `Trainer` for training.
- **🧬 Technical Deep Dive:** ZMQ `REP` socket inherited from `BaseAgent` on port 5000, job manager thread processes queue, stores artefacts under `artifacts/`, supports few-shot trigger model.
- **⚠️ Panganib:** High GPU/CPU utilisation during training, disk bloat from checkpoints, dataset path issues.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5001 (auto-bound via BaseAgent default).
  - **🛰️ Port:** 5000

---
### 🧠 AGENT PROFILE: NLLBAdapter
- **Main Class:** `NLLBAdapter`
- **Host Machine:** Main PC
- **Role:** Neural machine translation service using NLLB models
- **🎯 Responsibilities:** Provides translation services between multiple languages, integrates with ModelManagerAgent
- **🔗 Interactions:**
  - ModelManagerAgent for model management
  - Error Bus for error reporting
- **🧬 Technical Deep Dive:** Uses ZMQ REP socket on port 5581, health check on port 6581, supports multiple language pairs
- **⚠️ Panganib:** High memory usage during translation, model loading failures
- **📡 Communication Details:**
  - **🔌 Health Port:** 6581
  - **🛰️ Port:** 5581

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| CodeGenerator | ✓ | |
| SelfTrainingOrchestrator | ✓ | |
| PredictiveHealthMonitor | ✓ | |
| FixedStreamingTranslation | ✓ | |
| Executor | ✓ | |
| TinyLlamaServiceEnhanced | ✓ | |
| LocalFineTunerAgent | ✓ | |
| NLLBAdapter | ✓ | |

---

### Container Grouping Updates
- This group has been enhanced with additional utility agents moved from the former utilities_support group.
- The reorganization provides better logical grouping of utility services that support the system's operation.
- All agents in this group now use the centralized ModelManagerAgent for model inference when needed, improving resource utilization.
