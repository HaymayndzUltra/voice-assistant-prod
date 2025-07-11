# Group: Learning Knowledge

Ito ang mga agents na kabilang sa grupong ito:

---

### 🧠 AGENT PROFILE: ModelEvaluationFramework
- **Main Class:** `ModelEvaluationFramework`
- **Host Machine:** Main PC
- **Role:** Central hub for model performance logging, evaluation scoring, and feedback into the learning pipeline.
- **🎯 Responsibilities:**
  • Log performance metrics (`log_performance_metric`).
  • Store & retrieve evaluation scores (`log_model_evaluation`).
  • Provide stats API and health endpoint.
  • Register with service discovery; publish errors to Error-Bus.
- **🔗 Interactions:**
  • Receives metrics from `LearningOrchestrationService`, `ModelManagerAgent`, others.
  • Publishes feedback / scores to training agents.
- **🧬 Technical Deep Dive:**
  • ZMQ REP `tcp://0.0.0.0:7220`; health REP `7221`.
  • SQLite DB `data/model_evaluation.db` with two tables (performance_metrics, model_evaluation_scores).
  • Background thread `_main_loop` polling sockets.
- **⚠️ Panganib:** Database corruption on abrupt stop; large metric volume may bloat DB; reliance on downstream services availability.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7221
  - **🛰️ Port:** 7220
  - **🔧 Environment Variables:** `mef_port`, `mef_db_path`, `PC2_IP`, `SECURE_ZMQ`
  - **📑 Sample Request:**
    ```json
    { "action": "log_performance_metric", "metric": {"metric_id":"abc123","agent_name":"CodeGenerator","metric_name":"latency_ms","value":120.5,"timestamp":1720000000}}
    ```
  - **📊 Resource Footprint (baseline):** ~110 MB RAM; CPU ~4 % idle.
  - **🔒 Security & Tuning Flags:** secure-ZMQ; circuit breaker thresholds.

---
### 🧠 AGENT PROFILE: LearningOrchestrationService
- **Main Class:** `LearningOrchestrationService`
- **Host Machine:** Main PC
- **Role:** Scheduler and coordinator for training cycles and resource allocation.
- **🎯 Responsibilities:**
  • Accept learning opportunities; create `TrainingCycle` records.
  • Allocate resources, monitor progress, update SQLite DB.
  • Communicate with `ModelEvaluationFramework` after training.
- **🔗 Interactions:** `LearningOpportunityDetector` (upstream), `ModelEvaluationFramework` (downstream), Error-Bus.
- **🧬 Technical Deep Dive:** ZMQ REP `7210`; health REP `7211`; DB `data/training_cycles.db`; circuit breakers; background main loop.
- **⚠️ Panganib:** Misallocation of resources, DB growth, cascade failures if downstream unavailable.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7211
  - **🛰️ Port:** 7210

---
### 🧠 AGENT PROFILE: LearningOpportunityDetector
- **Main Class:** `LearningOpportunityDetector`
- **Host Machine:** Main PC
- **Role:** Detects valuable user interactions as learning opportunities and scores them.
- **🎯 Responsibilities:** Monitor UMRA & RequestCoordinator streams; analyze and score interactions; save to DB; notify LOS.
- **🔗 Interactions:** Subscribes to UMRA (5701) & Coordinator (5702); REQ to LOS (7210); Error-Bus.
- **🧬 Technical Deep Dive:** ZMQ SUB+REQ; default port 7200 REP for API; health REP 7201; DB `data/learning_opportunities.db`; scoring detectors; buffer size 1000.
- **⚠️ Panganib:** False positives/negatives in scoring; buffer overflow; latency.
- **📡 Communication Details:**
  - **🔌 Health Port:** 7201
  - **🛰️ Port:** 7200

---
### 🧠 AGENT PROFILE: LearningManager
- **Main Class:** `LearningManager`
- **Host Machine:** Main PC
- **Role:** Oversees learning sessions, tunes hyper-parameters, and broadcasts health info.
- **🎯 Responsibilities:** Create/manage learning sessions; adjust learning rate; broadcast health over PUB; store history.
- **🔗 Interactions:** Potentially communicates with LearningAdjusterAgent and LOS; Error-Bus PUB.
- **🧬 Technical Deep Dive:** ZMQ REP `5588`; health PUB `6588`; asynchronous initialization; learning_session dict; adjustable parameters via config.
- **⚠️ Panganib:** Exceeding MAX_LEARNING_SESSIONS; stale sessions; high resource use during training.
- **📡 Communication Details:**
  - **🔌 Health Port:** 6588
  - **🛰️ Port:** 5588

---
### 🧠 AGENT PROFILE: ActiveLearningMonitor
- **Main Class:** `ActiveLearningMonitor`
- **Host Machine:** Main PC
- **Role:** Monitors live interactions to extract high-value samples and trigger fine-tuning jobs.
- **🎯 Responsibilities:** Subscribe to UMRA & Coordinator streams; analyze interactions; save training data; request fine-tune via SelfTrainingOrchestrator.
- **🔗 Interactions:** UMRA SUB 5701, Coordinator SUB 5702, SelfTrainingOrchestrator REQ 5703, Error-Bus PUB.
- **🧬 Technical Deep Dive:** Runs monitoring threads; saves files in `training_data/`; ZMQ REP default port 5700; health via `_get_health_status`.
- **⚠️ Panganib:** Disk growth from saved data; mis-classification of value; orchestrator unavailability.
- **📡 Communication Details:**
  - **�� Health Port:** 5639  
  - **��️ Port:** 5638

---
### 🧠 AGENT PROFILE: LearningAdjusterAgent
- **Main Class:** `LearningAdjusterAgent`
- **Host Machine:** Main PC
- **Role:** Dynamically adjusts learning hyper-parameters based on performance metrics.
- **🎯 Responsibilities:** Register & track parameters; record performance; optimize parameters; expose API to adjust.
- **🔗 Interactions:** SQLite DB `data/learning_adjuster.db`; Error-Bus PUB; may receive metrics from ModelEvaluationFramework.
- **🧬 Technical Deep Dive:** ZMQ REP `5643`; health REP `5644` (port+1); enums for ParameterType; optimization algorithms over history window.
- **⚠️ Panganib:** Over-tuning causing instability; DB write latency; requires performance metrics availability.
- **📡 Communication Details:**
  - **🔌 Health Port:** 5644
  - **🛰️ Port:** 5643

---
### Pattern Compliance Checklist
| Agent | Tugma sa Pattern? | Reason (kung X) |
|-------|-------------------|-----------------|
| ModelEvaluationFramework | ✓ | |
| LearningOrchestrationService | ✓ | |
| LearningOpportunityDetector | ✓ | |
| LearningManager | ✓ | |
| ActiveLearningMonitor | ✓ | |
| LearningAdjusterAgent | ✓ | |
