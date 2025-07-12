# Group: GPU Infrastructure

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: GGUFModelManager
- **Main Class:** `GGUFModelManager`
- **Host Machine:** Main PC
- **Role:** Central manager for local GGUF Llama-cpp models (load/unload, metadata, inference helper).
- **🎯 Responsibilities:**
  • Mag-maintain ng catalogue ng GGUF models (metadata, VRAM estimates).
  • Mag-load at mag-unload ng models on demand via `load_model` / `unload_model`.
  • Mag-provide text generation interface thru `generate_text()`.
  • Mag-track idle models at auto-unload (default 300 s).
  • Mag-publish health & model-status info.
- **🔗 Interactions:**
  • Used by `CodeGeneratorAgent` & `ModelManagerAgent` for generation.
  • Error-Bus PUB (`tcp://192.168.100.17:7150`).
- **🧬 Technical Deep Dive:**
  • ZMQ REP `tcp://0.0.0.0:5575`; health REP `5576` (BaseAgent default).
  • Uses llama-cpp-python (optional; warns if missing).
  • Keeps `loaded_models` dict and `GGUFStateTracker` (port 5576) for VRAM accounting.
  • Model metadata read from `config/system_config.py` (serving_method = gguf_direct).
- **⚠️ Panganib:**
  • High VRAM usage — may fail load if insufficient.
  • Llama-cpp not available ⇒ inability to serve GGUF models.
  • Thread safety issues when parallel load/unload (lock mitigated).
- **📡 Communication Details:**
  - **🔌 Health Port:** 5576
  - **🛰️ Port:** 5575
  - **🔧 Environment Variables:** `PC2_IP`, `SECURE_ZMQ`, `LLAMA_CPP_THREADS`, `MODEL_IDLE_TIMEOUT_SECONDS`
  - **📑 Sample Request:**
    ```json
    { "action": "load_model", "model_id": "codellama" }
    ```
  - **📊 Resource Footprint (baseline):** ~120 MB RAM + VRAM per model; CPU ~3 % idle.
  - **🔒 Security & Tuning Flags:** secure-ZMQ toggle; idle-unload timeout; VRAM budget via VRAMOptimizer.

---
### 🧠 AGENT PROFILE: ModelManagerAgent
- **Main Class:** `ModelManagerAgent`
- **Host Machine:** Main PC
- **Role:** High-level orchestrator for loading, unloading, routing, and monitoring of every model type (LLMs, STT, TTS, Ollama, custom API, GGUF, etc.).
- **🎯 Responsibilities:**
  • Mag-route generation requests to appropriate model.
  • Mag-handle STT (speech-to-text) and TTS (text-to-speech) requests.
  • Mag-manage VRAM via coordination with `VRAMOptimizerAgent`.
  • Auto-unload idle models; maintain cache files.
  • Mag-expose rich JSON API (`load_model`, `unload_model`, `generate`, `status`).
- **🔗 Interactions:**
  • `VRAMOptimizerAgent` (consultation & unload requests).
  • `SystemDigitalTwin` (status updates).
  • `GGUFModelManager` for GGUF models.
  • `STTService` and `TTSService` for audio processing.
  • Error-Bus PUB.
- **🧬 Technical Deep Dive:**
  • ZMQ REP `tcp://0.0.0.0:5570`; health REP `5571`.
  • Handles GPU/CPU detection, VRAM budget (default 80 % of GPU).
  • Log rotation (5 MB x5) at `logs/mma_*.log`.
  • Background threads: VRAM management, health check, model idle checker.
  • Uses `llm_config.yaml` for model routing policies including STT and TTS models.
- **⚠️ Panganib:**
  • Complex concurrency ⇒ race conditions on `models` dict.
  • VRAM mis-estimation ➜ OOM.
  • Large log files if debug enabled.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5571
  - **🛰️ Port:** 5570
  - **🔧 Environment Variables:** `MODEL_MANAGER_PORT`, `PC2_IP`, `SECURE_ZMQ`, `LLM_CONFIG_PATH`, `vram_budget_percentage`
  - **📑 Sample Request:**
    ```json
    { "action": "generate", "model_pref": "quality", "prompt": "Hello, world!" }
    ```
  - **📊 Resource Footprint (baseline):** ~220 MB RAM idle; GPU VRAM varies; CPU <6 % idle.
  - **🔒 Security & Tuning Flags:** secure-ZMQ; VRAM budget %; idle unload timeout.

---
### 🧠 AGENT PROFILE: VRAMOptimizerAgent
- **Main Class:** `VramOptimizerAgent`
- **Host Machine:** Main PC
- **Role:** Monitors GPU VRAM usage across devices and coordinates model unload/load to stay within budget.
- **🎯 Responsibilities:**
  • Poll `SystemDigitalTwin` & local metrics for VRAM usage.
  • Advise `ModelManagerAgent` whether a new model can be loaded (`can_load_model`).
  • Trigger unload of least-used models when thresholds exceeded.
  • Predictive optimisation (defragmentation, idle tracking).
- **🔗 Interactions:**
  • `ModelManagerAgent` (REQ/REP).
  • `SystemDigitalTwin` (REQ/REP) for global metrics.
  • Error-Bus PUB.
- **🧬 Technical Deep Dive:**
  • Default ZMQ REP `tcp://0.0.0.0:5000`; health REP `5001`.
  • Uses thresholds: critical 0.9, warning 0.75, safe 0.5 (configurable).
  • Background threads: `_monitor_vram`, `_optimize_memory`, `_predict_usage`, `_monitor_idle_models`.
- **⚠️ Panganib:**
  • Incorrect prediction may unload active models ➜ latency.
  • Thresholds too low ⇒ constant churn.
  • Dependency on SystemDigitalTwin availability.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5001
  - **🛰️ Port:** 5000
  - **🔧 Environment Variables:** `PC2_IP`, `SECURE_ZMQ`, `vram_optimizer.*` thresholds
  - **📑 Sample Request:**
    ```json
    { "action": "can_load_model", "model_vram_mb": 8000 }
    ```
  - **📊 Resource Footprint (baseline):** ~140 MB RAM; CPU 4-7 % due to monitoring threads.
  - **🔒 Security & Tuning Flags:** secure-ZMQ; `defragmentation_threshold`; idle timeout.

---
### 🧠 AGENT PROFILE: PredictiveLoader
- **Main Class:** `PredictiveLoader`
- **Host Machine:** Main PC
- **Role:** Forecasts near-future model usage based on historical patterns and preloads models to reduce latency.
- **🎯 Responsibilities:**
  • Collect model usage data (via `record_usage`).
  • Predict upcoming models (`predict_models`) within look-ahead window (default 5 min).
  • Instruct `ModelManagerAgent` to preload required models.
  • Provide health endpoint.
- **🔗 Interactions:**
  • `RequestCoordinator` for usage signals.
  • `ModelManagerAgent` for preload commands.
  • Error-Bus PUB.
- **🧬 Technical Deep Dive:**
  • ZMQ REP `tcp://0.0.0.0:5617`; health REP `5618`.
  • Maintains `model_usage` dict; prediction loop runs every 60 s.
  • Config keys: `prediction_window` (1 h), `lookahead_window` (5 min).
- **⚠️ Panganib:**
  • Wrong predictions waste VRAM.
  • Connection loss with RequestCoordinator.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5618
  - **🛰️ Port:** 5617
  - **🔧 Environment Variables:** `prediction_window`, `lookahead_window`, `PC2_IP`, `SECURE_ZMQ`
  - **📑 Sample Request:**
    ```json
    { "action": "record_usage", "model_id": "gemma-7b" }
    ```
  - **📊 Resource Footprint (baseline):** ~90 MB RAM; CPU 3 %.
  - **🔒 Security & Tuning Flags:** secure-ZMQ; idle monitor intervals.

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| GGUFModelManager | ✓ | |
| ModelManagerAgent | ✓ | |
| VRAMOptimizerAgent | ✓ | |
| PredictiveLoader | ✓ | |

---

### Container Grouping Updates
- This group has been renamed from **ai_models_gpu_services** to **gpu_infrastructure** to better reflect its focus on core GPU resource management.
- The reasoning agents (ChainOfThoughtAgent, GoTToTAgent, CognitiveModelAgent) have been moved to a dedicated **reasoning_services** group.
- This reorganization provides clearer separation between infrastructure services and higher-level reasoning capabilities.
