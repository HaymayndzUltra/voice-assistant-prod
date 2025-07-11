# Group: Utilities Support

Ito ang mga agents na kabilang sa grupong ito:

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
- **Main Class:** `TinyLlamaService`
- **Host Machine:** Main PC (GPU preferred)
- **Role:** Serve TinyLlama language-model generation with smart resource management.
- **🎯 Responsibilities:** Handles `generate`, `ensure_loaded`, `request_unload`, `resource_stats`, and health requests; dynamically tunes batch-size & quantisation; reports to Error Bus.
- **🔗 Interactions:**
  - Error Bus (`tcp://PC2_IP:7150`)
  - Other generating agents via ZMQ `REQ` pattern
- **🧬 Technical Deep Dive:** ZMQ `REP` on 5615, health `REP` on 6615, uses `ResourceManager` to adapt batch size/quantisation, supports CUDA & CPU fallback, calls PyTorch, and runs resource monitor thread.
- **⚠️ Panganib:** VRAM spikes during load, prolonged GPU hold if unload fails, potential OOM on CPU fallback.
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
- **Main Class:** `NLLBTranslationAdapter`
- **Host Machine:** Main PC (GPU optional)
- **Role:** Lightweight on-demand translator using Meta NLLB-200 model with idle-unload.
- **🎯 Responsibilities:** Translate text via `translate` action, self-load/unload model, expose health, watch resource usage, publish errors.
- **🔗 Interactions:**
  - Other translation pipelines (e.g., `TranslationService`) over ZMQ
  - Error Bus (`tcp://PC2_IP:7150`)
- **🧬 Technical Deep Dive:** Binds `REP` on 5581 (fallback to localhost if 0.0.0.0 fails), health `REP` on 5582, background monitor thread unloads model after idle timeout, supports dynamic quantisation.
- **⚠️ Panganib:** Large model memory load, translation latency spikes on cold-start, port bind failures.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5582
  - **🛰️ Port:** 5581

---
