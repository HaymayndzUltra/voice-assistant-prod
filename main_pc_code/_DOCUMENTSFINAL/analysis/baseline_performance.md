# Voice Assistant Performance Baseline

This document outlines the key performance metrics we will be tracking to establish a baseline for the Voice Assistant system. The instrumentation has been implemented using a standardized log format (`PERF_METRIC`) across critical components.

## Standardized Logging Format

All performance metrics are logged using the following standardized format for easy parsing:

```
PERF_METRIC: [AgentName] - [StageName] - Duration: {duration_ms:.2f}ms
```

## Key Performance Metrics

### Audio Pipeline Latency

The total estimated time from raw audio capture to the final transcript being published by ASR (Automatic Speech Recognition).

| Component                  | Metric               | Description                                                                      |
| -------------------------- | -------------------- | -------------------------------------------------------------------------------- |
| NoiseReductionAgent        | AudioChunkProcessing | Time to process one audio chunk through the noise reduction pipeline             |
| StreamingSpeechRecognition | AudioToTranscript    | Time from receiving an audio chunk to outputting a transcript segment            |
| StreamingSpeechRecognition | AudioProcessing      | Time to process the audio buffer, including language detection and transcription |

**Total Audio Pipeline Latency** = Sum of all component latencies in the audio processing chain.

Critical factors affecting Audio Pipeline Latency:

- Audio chunk size and sampling rate
- Complexity of noise reduction algorithms
- ASR model size and complexity
- Hardware capabilities (CPU/GPU availability)
- Network latency for model inference (if applicable)

### Text Processing Time

The estimated time from the Coordinator receiving a transcript to a response being ready for TTS (Text-to-Speech).

| Component           | Metric             | Description                                                       |
| ------------------- | ------------------ | ----------------------------------------------------------------- |
| CoordinatorAgent    | TaskClassification | Time to classify intent and route a task                          |
| EnhancedModelRouter | RequestRouting     | Time from receiving a request to sending it to a downstream model |

**Total Text Processing Time** = Coordinator classification time + Model routing time + Model inference time + Response generation time

Critical factors affecting Text Processing Time:

- Task complexity
- Model selection accuracy
- LLM inference speed
- Context window size
- Network latency between components

### Memory Retrieval Latency

The estimated time for a typical query to the `SessionMemoryAgent`.

| Component          | Metric        | Description                                  |
| ------------------ | ------------- | -------------------------------------------- |
| SessionMemoryAgent | DatabaseRead  | Time to retrieve context from the database   |
| SessionMemoryAgent | DatabaseWrite | Time to write an interaction to the database |

**Memory Operation Latency** = Time for database read/write operations

Critical factors affecting Memory Retrieval Latency:

- Database size and complexity
- Context window size
- Query complexity
- Storage medium performance (SSD vs HDD)
- Database optimization level

### Cross-Machine Round-Trip Time (RTT)

The estimated time for a request to travel from `mainPC` to `PC2` and receive a response.

This is measured by tracking the full processing chain from Coordinator to Bridge to PC2 services and back.

| Component           | Metric             | Description                            |
| ------------------- | ------------------ | -------------------------------------- |
| CoordinatorAgent    | TaskClassification | Includes ZMQ bridge communication time |
| EnhancedModelRouter | RequestRouting     | Time to route requests on PC2          |

**Cross-Machine RTT** = Time from request initiation on mainPC to response receipt

Critical factors affecting Cross-Machine RTT:

- Network bandwidth and latency between machines
- ZMQ message serialization/deserialization overhead
- Load on each machine
- Message size (particularly for audio/model data)
- Bridge queue depth

## Performance Optimization Targets

Based on these metrics, we can establish the following performance optimization targets:

1. **Audio Pipeline Latency**: Target < 500ms for real-time responsiveness
2. **Text Processing Time**: Target < 1000ms for simple queries, < 5000ms for complex ones
3. **Memory Retrieval Latency**: Target < 100ms for typical queries
4. **Cross-Machine RTT**: Target < 150ms network overhead

## Monitoring and Analysis

The performance logs will be collected and analyzed to:

1. Establish baseline performance across different hardware configurations
2. Identify performance bottlenecks in the system
3. Measure the impact of optimization efforts
4. Set realistic performance expectations for different types of interactions

Future enhancements may include a real-time performance monitoring dashboard and automated alerts for performance degradation.
