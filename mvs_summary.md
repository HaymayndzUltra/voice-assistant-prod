# Minimal Viable System (MVS) Summary

## Overview

The Minimal Viable System (MVS) consists of 9 healthy agents plus their direct dependencies, creating a small but fully functional core system. This approach allows us to stabilize the essential components before expanding to the full system.

## MVS Agents

### Core Healthy Agents

1. **ModelManagerAgent**
   - Script: `agents/model_manager_agent.py`
   - Port: 5570
   - No dependencies
   - Purpose: Manages AI models, handles loading/unloading, and monitors VRAM usage

2. **ChainOfThoughtAgent**
   - Script: `FORMAINPC/ChainOfThoughtAgent.py`
   - Port: 5612
   - No dependencies
   - Purpose: Implements chain-of-thought reasoning for complex tasks

3. **GOT_TOTAgent**
   - Script: `FORMAINPC/GOT_TOTAgent.py`
   - Port: 5646
   - No dependencies
   - Purpose: Implements graph-of-thought and tree-of-thought reasoning

4. **CoordinatorAgent**
   - Script: `agents/coordinator_agent.py`
   - Port: 26002
   - No dependencies
   - Purpose: Central coordinator for system communication and task routing

5. **SystemDigitalTwin**
   - Script: `agents/system_digital_twin.py`
   - Port: 7120
   - Health Check Port: 8120
   - Dependencies: ModelManagerAgent
   - Purpose: Monitors system resources and provides a digital twin of the system

6. **TinyLlamaService**
   - Script: `FORMAINPC/TinyLlamaServiceEnhanced.py`
   - Port: 5615
   - Dependencies: ModelManagerAgent
   - Purpose: Provides lightweight LLM capabilities using TinyLlama

7. **LearningAdjusterAgent**
   - Script: `FORMAINPC/LearningAdjusterAgent.py`
   - Port: 5643
   - Dependencies: SelfTrainingOrchestrator
   - Purpose: Adjusts learning parameters for training

8. **StreamingInterruptHandler**
   - Script: `agents/streaming_interrupt_handler.py`
   - Port: 5576
   - Dependencies: StreamingSpeechRecognition
   - Purpose: Handles interruptions in speech input

9. **MemoryOrchestrator**
   - Script: `src/memory/memory_orchestrator.py`
   - Port: 5575
   - Dependencies: TaskRouter
   - Purpose: Manages the memory system for storing and retrieving information

### Direct Dependencies

1. **SelfTrainingOrchestrator**
   - Script: `FORMAINPC/SelfTrainingOrchestrator.py`
   - Port: 5644
   - Required by: LearningAdjusterAgent
   - Purpose: Orchestrates self-training cycles for agents

2. **StreamingSpeechRecognition**
   - Script: `agents/streaming_speech_recognition.py`
   - Port: 6580
   - Dependencies: FusedAudioPreprocessor, ModelManagerAgent
   - Required by: StreamingInterruptHandler
   - Purpose: Provides real-time speech-to-text capabilities

3. **FusedAudioPreprocessor**
   - Script: `src/audio/fused_audio_preprocessor.py`
   - Port: 6578
   - Dependencies: AudioCapture
   - Required by: StreamingSpeechRecognition
   - Purpose: Preprocesses audio for speech recognition

4. **AudioCapture**
   - Script: `agents/streaming_audio_capture.py`
   - Port: 6575
   - No dependencies
   - Required by: FusedAudioPreprocessor
   - Purpose: Captures audio from microphone or provides dummy audio

5. **TaskRouter**
   - Script: `src/core/task_router.py`
   - Port: 8571
   - Dependencies: StreamingTTSAgent, StreamingSpeechRecognition, ChainOfThoughtAgent, GOT_TOTAgent
   - Required by: MemoryOrchestrator
   - Purpose: Routes tasks to appropriate agents

6. **StreamingTTSAgent**
   - Script: `agents/streaming_tts_agent.py`
   - Port: 5562
   - Dependencies: CoordinatorAgent, ModelManagerAgent
   - Required by: TaskRouter
   - Purpose: Provides streaming text-to-speech capabilities

## Environment Variables

The MVS requires the following environment variables:

### Machine Configuration
- `MACHINE_TYPE`: Set to "MAINPC" for the main PC
- `PYTHONPATH`: Include the current directory

### Network Configuration
- `MAIN_PC_IP`: IP address of the main PC (default: "localhost")
- `PC2_IP`: IP address of the second PC (default: "localhost")
- `BIND_ADDRESS`: Address to bind services to (default: "0.0.0.0")

### Security Settings
- `SECURE_ZMQ`: Enable/disable secure ZMQ (default: "0" for testing)
- `ZMQ_CERTIFICATES_DIR`: Directory for ZMQ certificates (default: "certificates")

### Service Discovery
- `SYSTEM_DIGITAL_TWIN_PORT`: Port for SystemDigitalTwin (default: "7120")
- `SERVICE_DISCOVERY_ENABLED`: Enable service discovery (default: "1")
- `FORCE_LOCAL_SDT`: Force local SystemDigitalTwin (default: "1")

### Voice Pipeline Ports
- `TASK_ROUTER_PORT`: Port for TaskRouter (default: "8571")
- `STREAMING_TTS_PORT`: Port for StreamingTTSAgent (default: "5562")
- `TTS_PORT`: Port for TTSAgent (default: "5562")
- `INTERRUPT_PORT`: Port for StreamingInterruptHandler (default: "5576")

### Resource Constraints
- `MAX_MEMORY_MB`: Maximum memory usage (default: "2048")
- `MAX_VRAM_MB`: Maximum VRAM usage (default: "2048")

### Logging
- `LOG_LEVEL`: Logging level (default: "INFO")
- `LOG_DIR`: Directory for logs (default: "logs")

### Timeouts and Retries
- `ZMQ_REQUEST_TIMEOUT`: ZMQ request timeout in ms (default: "5000")
- `CONNECTION_RETRIES`: Number of connection retries (default: "3")
- `SERVICE_DISCOVERY_TIMEOUT`: Service discovery timeout in ms (default: "10000")

### Voice Pipeline Settings
- `VOICE_SAMPLE_DIR`: Directory for voice samples (default: "voice_samples")
- `MODEL_DIR`: Directory for models (default: "models")
- `CACHE_DIR`: Directory for cache (default: "cache")

### Agent-Specific Variables
- `MODEL_MANAGER_PORT`: Port for ModelManagerAgent (default: "5570")
- `USE_DUMMY_AUDIO`: Use dummy audio for testing (default: "true")

## Running the MVS

To run the MVS:

1. Ensure all required directories exist:
   - logs/
   - data/
   - models/
   - cache/
   - certificates/

2. Run the `run_mvs.sh` script:
   ```bash
   chmod +x run_mvs.sh
   ./run_mvs.sh
   ```

3. Check the health of the MVS:
   ```bash
   python3 check_mvs_health.py
   ```

## Next Steps

After the MVS is running stably:

1. Fill in actual values for environment variables in `run_mvs.sh`
2. Test each agent's functionality
3. Gradually add more agents to the system
4. Monitor system performance and stability 