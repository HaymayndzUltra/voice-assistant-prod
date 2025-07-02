# Voice Assistant Error Format Standard

## Overview

This document defines the standardized error message format for inter-agent communication in the Voice Assistant system. Using a consistent error format enables better error tracing, debugging, and recovery throughout the distributed architecture.

## Standard Error Message Format

All error messages passed between agents via ZMQ must adhere to the following JSON structure:

```json
{
  "status": "error",
  "error_type": "ErrorTypeIdentifier",
  "source_agent": "agent_filename.py",
  "message": "Human-readable description of what went wrong",
  "timestamp": "2023-06-12T14:25:36.123Z",
  "trace_id": "optional-trace-identifier",
  "details": {
    "optional": "additional error context"
  }
}
```

## Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `status` | String | Must be "error" to identify this as an error message |
| `error_type` | String | Classification of the error (see Error Types section) |
| `source_agent` | String | Filename of the agent that generated the error |
| `message` | String | Human-readable description of the error |
| `timestamp` | String | ISO 8601 formatted timestamp when the error occurred |

## Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | String | Optional identifier for tracing errors across multiple agents |
| `details` | Object | Optional additional context about the error (can contain nested fields) |

## Error Types

Standardized error types help with error categorization and handling. Use one of the following:

### System-Level Errors

- `SystemError`: General system-level error
- `ConfigurationError`: Error in configuration files or settings
- `ResourceError`: Error related to system resources (memory, disk, etc.)
- `NetworkError`: Network connectivity issues
- `DatabaseError`: Database-related errors

### Audio Processing Errors

- `AudioCaptureError`: Error capturing audio from microphone
- `AudioProcessingError`: Error processing audio data
- `NoiseReductionError`: Specific error in noise reduction
- `VADError`: Voice Activity Detection error
- `WakeWordError`: Wake word detection error
- `TranscriptionError`: Speech-to-text transcription error

### Model Errors

- `ModelLoadError`: Error loading a machine learning model
- `ModelInferenceError`: Error during model inference
- `ModelTimeoutError`: Model took too long to respond

### Communication Errors

- `ZMQError`: ZeroMQ communication error
- `MessageFormatError`: Malformed message received
- `TimeoutError`: Communication timeout
- `BridgeError`: Error in cross-machine bridge

### Agent Errors

- `AgentInitializationError`: Error initializing an agent
- `AgentProcessingError`: General agent processing error
- `AgentShutdownError`: Error during agent shutdown

## Error Handling Guidelines

1. **Catching Exceptions**: Wrap critical code sections in try-except blocks and convert exceptions to standardized error messages.

2. **Propagating Errors**: When an agent receives an error from upstream, it should:
   - Log the error with appropriate context
   - Either attempt recovery or propagate the error downstream with added context

3. **Error Logging**: Always log errors with at least INFO level for normal errors and ERROR level for critical errors.

4. **Recovery Strategy**: Agents should implement appropriate recovery strategies based on error types.

## Example Implementation

```python
try:
    # Critical operation
    result = process_audio_chunk(audio_data)
except Exception as e:
    error_message = {
        "status": "error",
        "error_type": "AudioProcessingError",
        "source_agent": "noise_reduction_agent.py",
        "message": f"Failed to process audio chunk: {str(e)}",
        "timestamp": datetime.now().isoformat(),
        "details": {
            "chunk_size": len(audio_data),
            "sample_rate": sample_rate
        }
    }
    # Log locally
    logger.error(f"Audio processing error: {str(e)}")
    # Publish error message to output socket
    output_socket.send_json(error_message)
```

## Downstream Error Handling Example

```python
# Receive and check message
message = input_socket.recv_json()
if message.get("status") == "error":
    # Log the received error
    logger.error(f"Received error from {message.get('source_agent')}: {message.get('message')}")
    # Take appropriate action based on error type
    if message.get("error_type") == "AudioProcessingError":
        # Implement recovery or propagation strategy
    else:
        # Handle other error types
else:
    # Process normal message
    process_message(message)
```

## PC2 Memory Services

- Unified Memory Reasoning Agent (port 5596)
- DreamWorld Agent (port 5598-PUB)
- Other PC2 memory services 