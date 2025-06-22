# Modular Streaming Component Routing & Communication Architecture

## Communication Protocols & Patterns

### ZeroMQ (ZMQ) Streaming Pipeline Logic

The voice assistant implements a streamlined pipeline for processing audio input and generating responses in its modular streaming architecture, implementing several messaging patterns:

| Pattern | Description | Primary Use Cases |
|---------|-------------|-------------------|
| **REQ/REP** | Synchronous request-reply | Command execution, queries requiring immediate response |
| **PUB/SUB** | Asynchronous publish-subscribe | Status updates, broadcasts, event notifications |
| **PUSH/PULL** | Pipeline distribution | Distributing tasks to worker agents, load balancing |
| **DEALER/ROUTER** | Advanced asynchronous patterns | Complex routing scenarios, multi-step workflows |

### Network Transport

- **TCP Transport**: Primary transport mechanism (`tcp://ip:port`)
  - Internal communication on `127.0.0.1` (localhost) for all streaming components
  - Optimized for low-latency data streaming between pipeline stages
  - Configurable buffer sizes and processing settings in each component

- **Data Streaming**: Optimized for real-time audio and text processing
  - Audio chunks streaming (8000 samples per chunk @ 16kHz)
  - Partial text transcripts for low-latency response
  - Interrupt signal propagation for natural conversation flow

## Port Assignments & Streaming Pipeline

### Modular Streaming Components

| Component | Input Port | Output Port | Pattern | Connected To |
|-----------|-----------|------------|---------|---------------|
| streaming_audio_capture.py | - | 5570 | PUB | streaming_speech_recognition.py |
| streaming_speech_recognition.py | 5570 | 5571 | SUB/PUB | From audio_capture to language_analyzer/partial_transcripts |
| streaming_partial_transcripts.py | 5571 | 5575 | SUB/PUB | From speech_recognition to interrupt_handler |
| streaming_interrupt_handler.py | 5575 | 5576 | SUB/PUB | From partial_transcripts to xtts_agent (for interruption) |
| streaming_language_analyzer.py | 5571 | 5572 | SUB/PUB | From speech_recognition to translation |
| fixed_streaming_translation.py | 5572 | 5573 | SUB/PUB | From language_analyzer to text_processor |
| streaming_text_processor.py | 5573 | 5574 | SUB/PUB | From translation to tts_connector |
| tts_connector.py | 5574 | 5562 | SUB/REQ | From text_processor to xtts_agent |
| xtts_agent.py | 5562 | - | REP | Responds to tts_connector requests |
| coordinator.py | 5560 | 5561/5597 | SUB/PUB | All components (receives on 5560, health monitoring on 5597) |

### STREAMING PIPELINE EXAMPLES

1. **Basic Voice Command Processing**:
   ```
   streaming_audio_capture → streaming_speech_recognition 
   → streaming_language_analyzer → streaming_text_processor 
   → tts_connector → xtts_agent
   ```

2. **Translation Pipeline**:
   ```
   streaming_audio_capture → streaming_speech_recognition 
   → streaming_language_analyzer → fixed_streaming_translation 
   → streaming_text_processor → tts_connector → xtts_agent
   ```

3. **Interrupt Handling**:
   ```
   streaming_audio_capture → streaming_speech_recognition 
   → streaming_partial_transcripts → streaming_interrupt_handler 
   → xtts_agent (STOP signal)
   ```

## Optimized Streaming Patterns

1. **Partial Transcript Processing**: Enables early response before full processing
   ```
   streaming_speech_recognition → streaming_partial_transcripts → tts_connector
   (parallel to) → streaming_language_analyzer → streaming_text_processor
   ```

2. **TTS Streaming**: When implementing XTTS for improved responsiveness
   ```
   streaming_text_processor → tts_connector → streaming_tts_agent
   (sentence-by-sentence streaming) → audio output
   ```

3. **Multi-Language Processing**: For handling Tagalog/Taglish commands
   ```
   streaming_language_analyzer (detects Filipino) → fixed_streaming_translation 
   → llm_translation_adapter (on PC2, port 5581) → Ollama (NLLB) 
   → fixed_streaming_translation → streaming_text_processor → response generation
   ```

## Security & Reliability Features

- **Heartbeat Monitoring**: Regular health checks between machines (10-second interval)
- **Automatic Reconnection**: Exponential backoff retry on connection failures
- **Message Serialization**: JSON-based message format with validation
- **Error Handling**: Comprehensive error reporting and recovery mechanisms

## Message Format & Protocol

### Standard Message Structure

```json
{
  "request_id": "unique-request-identifier",
  "sender": "originating-agent",
  "timestamp": "ISO-8601-timestamp",
  "request_type": "command-type",
  "priority": 1-5,
  "payload": {
    // Command-specific data
  },
  "metadata": {
    // Optional context information
  }
}
```

### Common Request Types

| Request Type | Description | Example Payload |
|--------------|-------------|------------------|
| `query` | Information request | `{"query": "current_time"}` |
| `command` | Action execution | `{"command": "generate_code", "language": "python"}` |
| `status` | Status update | `{"status": "ready", "load": 0.5}` |
| `health` | Health check | `{"uptime": 3600, "memory_usage": 0.4}` |
| `error` | Error report | `{"error_code": 404, "message": "Resource not found"}` |

## Load Balancing & Failover

### Resource-Based Load Balancing

- System monitors CPU, memory, and GPU usage on both machines
- Tasks are routed to the machine with more available resources
- Configuration in `distributed_config.json`: `load_balancing.strategy = "resource_based"`

### Agent Failover Mechanisms

1. **Primary Detection**: Orchestrator or Self-Healing Agent detects failure through:
   - Missed heartbeats
   - Socket timeouts
   - Error responses

2. **Recovery Actions**:
   - Automatic agent restart (up to 3 attempts with exponential backoff)
   - Routing to backup agent if available
   - Degraded mode operation if recovery fails

## Configuration Management

All routing settings are centrally defined in `distributed_config.json` with the following key sections:

```json
{
  "machines": {
    "main_pc": {
      "ip": "192.168.1.27",
      "agents": ["listener", "trigger_word_detector", "streaming_speech_recognition", "streaming_language_analyzer", "fixed_streaming_translation", "streaming_text_processor", "tts_connector", "xtts_agent"]
    },
    "second_pc": {
      "ip": "192.168.1.2",
      "agents": ["llm_translation_adapter", "model_manager_agent", "code_generator_agent"]
    }
  },
  "ports": {
    "model_manager_agent": 5556,
    "remote_connector_agent": 5557,
    ...
  },
  "communication": {
    "use_tcp": true,
    "timeout": 5000,
    "retry_attempts": 3
  }
}
```

## Debugging & Monitoring

### Communication Logging

- All inter-agent messages are logged centrally
- Log format includes timestamp, sender, receiver, message type, and status
- Configurable log levels (INFO, DEBUG, ERROR)
- Logs stored in `logs/communication.log`

### Visualization Tools

- Dashboard provides real-time visualization of message flow
- Agent connection status displayed with latency metrics
- Message volume statistics and bottleneck identification

---

For detailed agent capabilities, see [CAPABILITIES.md](CAPABILITIES.md).
For complete system workflow, see [WORKFLOW.md](WORKFLOW.md).
