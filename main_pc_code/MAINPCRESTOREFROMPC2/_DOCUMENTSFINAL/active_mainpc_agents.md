# Active Main PC Agents

> This document lists the **currently active / production-ready agents running on the _Main PC_ (192.168.1.27)**.
> Use it together with `component_inventory.csv`, `port_registry.csv`, and `system_config.py` when debugging or onboarding.

---

### [STREAMING AUDIO CAPTURE]
- **File:** `streaming_audio_capture.py`
- **Purpose:** Captures raw microphone audio and publishes it via ZMQ.
- **Key Features:** Real-time PCM stream, device selection, timestamping.
- **Integration Points:**
  - **PUB socket:** `tcp://*:6575`
  - **Health status:** `tcp://*:6576`
- **Dependencies:** None
- **Notes:** Root of the audio pipeline.

### [FUSED AUDIO PREPROCESSOR]
- **File:** `fused_audio_preprocessor.py`
- **Purpose:** Optimized audio preprocessing combining noise reduction and voice activity detection.
- **Key Features:** 
  - Real-time noise reduction with adaptive profiles
  - Silero VAD model integration
  - Adaptive threshold adjustment
  - Spectral gating and stationary noise reduction
  - Performance monitoring and metrics
- **Integration Points:**
  - **Subscribes:** `tcp://localhost:6575` (raw audio)
  - **PUB sockets:** 
    - `tcp://*:6578` (clean audio)
    - `tcp://*:6579` (VAD events)
  - **Health status:** `tcp://*:6581`
- **Dependencies:** `streaming_audio_capture.py`
- **Notes:** Replaces separate noise_reduction_agent.py and vad_agent.py for improved performance and reduced latency.

### [WAKE WORD DETECTOR]
- **File:** `wake_word_detector.py`
- **Purpose:** Triggers system on recognised wake word.
- **Key Features:** Porcupine models, threshold auto-tune.
- **Integration Points:**
  - **Subscribes:** `tcp://localhost:6575` (raw) & `tcp://localhost:6579` (VAD)
  - **PUB socket:** `tcp://*:6577` (wake events)
- **Dependencies:** `streaming_audio_capture.py`, `fused_audio_preprocessor.py`

### [STREAMING SPEECH RECOGNITION]
- **File:** `streaming_speech_recognition.py`
- **Purpose:** Converts speech → text using Whisper local model.
- **Key Features:** Chunked inference, interim results, language auto-detect.
- **Integration Points:**
  - **Subscribes:** `tcp://localhost:6578` (clean audio)
  - **PUB socket:** `tcp://*:5580` (final transcript)
  - **Health:** `tcp://*:6581`
- **Dependencies:** `fused_audio_preprocessor.py`

### [LANGUAGE & TRANSLATION COORDINATOR]
- **File:** `language_and_translation_coordinator.py`
- **Purpose:** Performs light NLP, optional translation, and routing.
- **Key Features:** Language-id, Tagalog↔English translation via TranslatorAgent.
- **Integration Points:**
  - **Subscribes:** `tcp://localhost:5580`
  - **PUB socket:** `tcp://*:5564` (processed text)
- **Dependencies:** `streaming_speech_recognition.py`

### [COORDINATOR AGENT]
- **File:** `coordinator_agent.py`
- **Purpose:** Classifies user intent and dispatches to downstream agents.
- **Integration Points:**
  - **REP socket:** `tcp://*:5590`
  - **Consumes:** messages from Language & Translation Coordinator
- **Dependencies:** `language_and_translation_coordinator.py`

### [CHITCHAT AGENT]
- **File:** `chitchat_agent.py`
- **Purpose:** Handles casual conversation.
- **Integration:** Registered service with CoordinatorAgent.
- **Ports:** `tcp://*:5573` (REP), `tcp://*:6582` (health PUB)
- **Dependencies:** `coordinator_agent.py`

### [SESSION MEMORY AGENT]
- **File:** `session_memory_agent.py`
- **Purpose:** Short-term conversational context store.
- **Ports:** `tcp://*:5574` (REP), `tcp://*:6583` (health PUB)
- **Dependencies:** `coordinator_agent.py`

### [TTS CONNECTOR]
- **File:** `tts_connector.py`
- **Purpose:** Queues and streams TTS requests to `streaming_tts_agent.py`.
- **Integration:** Subscribes to text from Language & Translation Coordinator.
- **Dependencies:** `language_and_translation_coordinator.py`

### [STREAMING TEXT PROCESSOR]
- **File:** `streaming_text_processor.py`
- **Purpose:** Detects code-generation intents and forwards to MMA.
- **Key Features:** Regex/LLM intent detection, prompt shaping.
- **Dependencies:** `coordinator_agent.py`

### [MODEL MANAGER AGENT]
- **File:** `model_manager_agent.py`
- **Purpose:** Manages local models & communicates with PC2 for remote ones.
- **Port:** `tcp://*:5570` (REP)
- **Internal Outbound:** `tcp://localhost:5571` (connects to Task Router)
- **Dependencies:** None
- **Notes:** Health logs in `mma_main_debug_output.log`.

### [HEALTH MONITOR AGENT]
- **File:** `health_monitor.py`
- **Purpose:** Monitors health of all agents/services and publishes status.
- **Port:** `tcp://*:5584` (REP)
- **Status PUB:** `tcp://*:5585` (broadcasts health JSON)
- **Dependencies:** Reads config, connects to Task Router (`tcp://localhost:5571`)
- **Notes:** Replaces legacy health-check logic previously embedded in MMA.

### [TASK ROUTER AGENT]
- **File:** `task_router.py`
- **Purpose:** Central router for model/translation requests; implements circuit-breaker.
- **Port:** `tcp://*:5571` (REP)
- **Outgoing:** Connects to Model Manager (`tcp://localhost:5570`) and PC2 services (`5598`, `5563`).
- **Dependencies:** None (top-level dispatcher)
- **Notes:** Handles work formerly managed by MMA; keeps track of service availability.

### [CODE GENERATOR AGENT]
- **File:** `code_generator_agent.py`
- **Purpose:** Generates code (GGUF & GPU models).
- **Port:** `tcp://*:5604` (REP)
- **Dependencies:** `model_manager_agent.py`

### [PROGRESSIVE GENERATOR]
- **File:** `progressive_generator.py`
- **Purpose:** Chain-of-thought code generation refinement.
- **Port:** `[TBD – likely 6002]`
- **Dependencies:** `model_manager_agent.py`

### [AUTO FIXER]
- **File:** `auto_fixer.py`
- **Purpose:** Automatically patches compilation/runtime errors.
- **Port:** `tcp://*:5605` (REP)
- **Dependencies:** `progressive_generator.py`

### [EXECUTOR]
- **File:** `executor.py`
- **Purpose:** Secure sandbox execution of generated code.
- **Port:** `tcp://*:5613` (REP) *(updated per 2025-05-28 change)*
- **Dependencies:** `auto_fixer.py`

### [TEST GENERATOR]
- **File:** `test_generator.py`
- **Purpose:** Generates unit/integration tests for produced code.
- **Port:** `[TBD – 6004]`
- **Dependencies:** `executor.py`

### [MONITORING DASHBOARD]
- **File:** `monitoring_dashboard.py`
- **Purpose:** Web UI for system health & metrics.
- **Dependencies:** `performance_metrics_collector.py`, various PUB sockets.

### [ADVANCED TIMEOUT MANAGER]
- **File:** `advanced_timeout_manager.py`
- **Purpose:** Centralised time-out & cancellation service.
- **Dependencies:** None

### [PERFORMANCE METRICS COLLECTOR]
- **File:** `performance_metrics_collector.py`
- **Purpose:** Collects and exposes system metrics.
- **Dependencies:** None

### [CONSOLIDATED TRANSLATOR AGENT]  <!-- Remote on PC2 but documented here for clarity -->
- **File:** `consolidated_translator.py`
- **Purpose:** Multi-engine translation service (NLLB, Phi-3 fallback, Google Translate).
- **Port:** `tcp://192.168.1.2:5563` (REP)
- **Dependencies:** NLLB Adapter (`tcp://192.168.1.2:5581`) and Translator Adapter Phi3 (`tcp://192.168.1.2:5562`).
- **Notes:** Although hosted on PC2, Main PC components (Language & Translation Coordinator, Task Router) rely on this endpoint; listed here to keep a single reference sheet.

---

*Last updated: 2025-06-13 08:44 PHT*
