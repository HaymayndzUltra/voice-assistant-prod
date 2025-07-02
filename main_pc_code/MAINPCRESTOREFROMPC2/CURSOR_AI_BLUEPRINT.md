```markdown
# CURSOR AI BLUEPRINT: Voice-Assistant-Prod

## 1. Introduction

This document provides a detailed blueprint for building, deploying, and maintaining the Voice-Assistant-Prod system. It is based on a direct analysis of the agent source code and reflects the true, operational architecture.

## 2. System Architecture

The system is distributed across two machines: `MainPC` and `PC2`.

- **MainPC**: Hosts the primary orchestration, reasoning, and user-facing agents.
- **PC2**: Hosts the model management, learning, and resource-intensive services. Communication between the two is handled via ZMQ.

### 2.1. Communication Protocol

- **Transport:** ZeroMQ (ZMQ)
- **Message Format:** JSON
- **Key Sockets:**
    - `REP/REQ`: For standard request/reply interactions.
    - `ROUTER/DEALER`: For more complex, asynchronous communication patterns.

## 3. Agent Inventory and Configuration

This section details each agent, its location, its purpose, and its key dependencies.

### 3.1. MainPC Agents

#### `EnhancedModelRouter`
- **File:** `FORMAINPC/EnhancedModelRouter.py`
- **Purpose:** The central brain of the system. It receives all incoming requests and orchestrates the response.
- **Logic:**
    1.  Uses `advanced_router.py` to classify the task (`code`, `reasoning`, etc.).
    2.  Connects to `ContextualMemoryAgent` to enrich the prompt.
    3.  Delegates to a reasoning agent (`ChainOfThoughtAgent` or `GOT_TOTAgent`).
    4.  Connects to `RemoteConnectorAgent` for final model execution.
- **Dependencies:** `TaskRouter`, `ModelManagerAgent`, `ContextualMemory`, `ChainOfThoughtAgent`, `RemoteConnectorAgent`, `UnifiedUtilsAgent`, `WebAssistant`.

#### `CognitiveModelAgent`
- **File:** `FORMAINPC/CognitiveModelAgent.py`
- **Purpose:** Maintains a consistent "belief system" as a knowledge graph.
- **Architecture:** Standalone agent using a `ZMQ.ROUTER` socket for high-throughput belief management.
- **Dependencies:** `networkx` library.

#### `ChainOfThoughtAgent`
- **File:** `FORMAINPC/ChainOfThoughtAgent.py`
- **Purpose:** Implements a linear, step-by-step reasoning process.
- **Process:**
    1.  Break problem into steps.
    2.  Generate solution for each step.
    3.  Verify and refine solution.
    4.  Combine steps into a final answer.
- **Dependencies:** `RemoteConnectorAgent` (for all model inference).

#### `GOT_TOTAgent`
- **File:** `FORMAINPC/GOT_TOTAgent.py`
- **Purpose:** Implements Graph/Tree-of-Thought reasoning for complex problems.
- **Architecture:** Self-contained agent that loads and runs its own local model (`microsoft/phi-2`).
- **Process:** Explores multiple reasoning paths (branches) simultaneously and scores them to find the best solution.

#### `RemoteConnectorAgent`
- **File:** `agents/_referencefolderpc2/remote_connector_agent.py` (Note: This runs on MainPC despite its folder location)
- **Purpose:** The gateway to all remote model services.
- **Logic:**
    1.  Receives inference requests from other MainPC agents.
    2.  Connects to `ModelManagerAgent` on PC2 (at `192.168.1.27`) to get model recommendations.
    3.  Makes HTTP requests to model APIs (e.g., Ollama, DeepSeek).
- **Features:** Caching, connection monitoring, and asynchronous requests.

### 3.2. PC2 Agents

#### `ModelManagerAgent`
- **File:** `agents/model_manager_agent.py`
- **Purpose:** Manages the practical loading and unloading of AI models.
- **Logic:**
    1.  Maintains a list of available models from `config/model_configs.json`.
    2.  Handles requests to load models, placing them in a queue.
    3.  Implements lazy loading and unloads models that have been idle for a set timeout.
- **Dependencies:** `VRAMManager` (for load approvals).

#### `VRAMManager`
- **File:** `agents/vram_manager.py`
- **Purpose:** Proactively monitors and optimizes GPU VRAM.
- **Logic:**
    1.  Tracks VRAM against `critical`, `warning`, and `safe` thresholds.
    2.  Requests `ModelManagerAgent` to unload idle or large models when VRAM is critical.
    3.  Consults a `SystemDigitalTwinAgent` to simulate and approve large model loads.
- **Features:** Idle model detection, memory defragmentation, predictive preloading.
- **Dependencies:** `GPUtil`, `torch`, `psutil`, `SystemDigitalTwinAgent`.

#### `StreamingSpeechRecognition`
- **File:** `agents/streaming_speech_recognition.py`
- **Purpose:** The core engine of the real-time STT pipeline.
- **Logic:**
    1.  Subscribes to ZMQ events for wake words and voice activity (VAD).
    2.  Manages an audio buffer for continuous transcription.
    3.  Applies noise reduction to the audio stream.
    4.  Requests a model from `DynamicSTTModelManager`.
    5.  Publishes the final transcription text.
- **Features:** Dynamic resource management (batch size, quantization) based on system load.
- **Dependencies:** `DynamicSTTModelManager`, `WakeWordDetector`, `VAD`, `FusedAudioPreprocessor`.

#### `DynamicSTTModelManager`
- **File:** `agents/stt/dynamic_stt_manager.py`
- **Purpose:** Selects and manages different STT (Whisper) models.
- **Logic:**
    1.  Selects the best model based on context (e.g., language, accent).
    2.  Loads models on demand using `whisper.load_model()`.
    3.  Caches loaded models in memory for reuse.
- **Dependencies:** `whisper`.

## 4. Launch and Deployment Instructions

### 4.1. Prerequisites

- Python 3.8+
- `pip install -r requirements.txt` (A `requirements.txt` file should be created).
- ZMQ libraries installed.

### 4.2. Environment Configuration

- A central `config/system_config.py` or `.env` file should define:
    - ZMQ ports for all agents.
    - The IP address of PC2 (`PC2_HOST=192.168.1.27`).
    - API keys and endpoints for model services.

### 4.3. Launch Sequence

1.  **Start PC2 Agents:**
    - Launch the `ModelManagerAgent`.
    - Launch any model servers (Ollama, etc.).

2.  **Start MainPC Agents:**
    - Launch the core services: `RemoteConnectorAgent`, `CognitiveModelAgent`.
    - Launch the reasoning agents: `ChainOfThoughtAgent`, `GOT_TOTAgent`.
    - Launch the main orchestrator: `EnhancedModelRouter`.

## 5. Maintenance and Debugging

- **Logging:** All agents have robust logging. Check the `logs/` directory for detailed operational information.
- **Health Checks:** Most agents implementing `BaseAgent` have a health check endpoint on `port + 1`.
- **ZMQ Monitoring:** Use ZMQ monitoring tools to inspect message flow between agents if issues are suspected.

This blueprint provides a comprehensive guide to the system. It should be kept up-to-date as the system evolves.
```
