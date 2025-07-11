# Group: Vision System

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: FaceRecognitionAgent
- **Main Class:** `FaceRecognitionAgent`
- **Host Machine:** Main PC
- **Role:** Real-time face detection, recognition, emotion analysis, liveness check, and privacy enforcement for the vision pipeline.
- **🎯 Responsibilities:**
  • Detect faces in incoming video frames using InsightFace.
  • Match faces against known database; track with Kalman filters.
  • Analyze emotions via ONNX model and voice features.
  • Perform liveness detection (blink / motion / anti-spoof).
  • Enforce privacy zones and blur unknown faces.
  • Publish events over ZMQ PUB socket (port+1).
- **🔗 Interactions:**
  • Receives frames from upstream vision capture agents.
  • Registers status with `SystemDigitalTwin` (via BaseAgent auto-register).
  • Publishes face events to interested subscribers (e.g., ContextManager).
  • Error-Bus PUB (`tcp://192.168.100.17:7150`).
- **🧬 Technical Deep Dive:**
  • ZMQ REP `tcp://0.0.0.0:5560` (default); PUB on 5561.
  • Async initialization thread loads models and sets `initialization_status` progress flags.
  • Uses CUDA optimizations if GPU available, otherwise CPU.
  • Configurable `blur_unknown`, `privacy_zones`, `data_minimization` with retention cleanup.
- **⚠️ Panganib:**
  • High GPU usage during heavy video; may block other GPU models.
  • Privacy misconfiguration could expose faces.
  • Large memory footprint from multiple models (face, emotion, liveness).
- **📡 Communication Details:**
  - **🔌 Health Port:** 5561
  - **🛰️ Port:** 5560
  - **🔧 Environment Variables:** `BIND_ADDRESS`, `SECURE_ZMQ`, `AGENT_PORT`, `blur_unknown`, `data_minimization.retention_period`
  - **📑 Sample Request:**
    ```json
    { "action": "process_frame", "frame": "<base64-jpeg>", "timestamp": 1720099200 }
    ```
  - **📊 Resource Footprint (baseline):** ~300 MB RAM; GPU VRAM ~1-2 GB for InsightFace; CPU 10-15 % per 30 FPS stream.
  - **🔒 Security & Tuning Flags:** secure-ZMQ; privacy zones list; data minimization enabled.

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| FaceRecognitionAgent | ✓ | |
