# StreamingAudioCapture Integration

## Overview

The StreamingAudioCapture agent has been successfully integrated into the Minimal Viable System (MVS). This agent provides advanced audio capture capabilities with wake word detection, enabling a more natural and efficient interaction with the AI system.

## Features

### Wake Word Detection

The StreamingAudioCapture agent uses the Whisper model to detect wake words such as "highminds". When a wake word is detected, the system activates for a configurable period (default: 15 seconds), during which it processes all audio input. This provides a natural way to interact with the system without requiring manual activation.

Key components:

- Uses the "small" Whisper model for accurate wake word detection
- Supports multiple wake word variations to handle different pronunciations
- Implements fuzzy matching to handle slight mispronunciations

### Energy-Based Fallback Detection

In addition to wake word detection, the agent includes an energy-based fallback mechanism that activates the system when sustained speech is detected above a certain threshold. This ensures the system responds even when the wake word isn't clearly detected.

Key parameters:

- Energy threshold: 0.15
- Minimum duration: 0.5 seconds
- Cooldown period: 5 seconds

### Real-time Audio Streaming

The agent captures audio in real-time and streams it to downstream components using ZeroMQ (ZMQ). The audio is processed in chunks, allowing for low-latency processing and immediate response to user input.

Technical details:

- Sample rate: 16000 Hz (configurable)
- Channels: 1 (mono)
- Format: 32-bit float
- Chunk duration: 0.2 seconds

### Robust Error Handling

The agent includes comprehensive error handling to ensure stability and reliability:

- Error propagation to downstream components
- Error rate limiting to avoid flooding
- Detailed logging for troubleshooting

## Integration Details

The StreamingAudioCapture agent has been added to the MVS configuration with the following settings:

```yaml
- description: Streams audio chunks in real-time with wake word detection
  file_path: streaming_audio_capture.py
  health_check_port: 5661
  name: StreamingAudioCapture
  port: 5660
```

## Testing

A dedicated test script (`test_streaming_audio.py`) has been created to verify the functionality of the StreamingAudioCapture agent. This script:

1. Launches the agent in a controlled environment
2. Sets up a ZMQ subscriber to listen for messages
3. Monitors the agent's output and reports any errors
4. Verifies that audio chunks and/or wake word events are being published

To run the test:

```bash
./test_streaming_audio.py --dummy  # Run in dummy mode (no actual audio capture)
./test_streaming_audio.py          # Run with actual audio capture
```

## Configuration Options

The StreamingAudioCapture agent supports several configuration options through environment variables:

- `USE_DUMMY_AUDIO`: Set to "true" to run in dummy mode (no actual audio capture)
- `AGENT_PORT`: Override the default port (5660)
- `SECURE_ZMQ`: Set to "1" to enable secure ZMQ connections

## Dependencies

The agent requires the following dependencies:

- Python 3.8+
- PyAudio
- NumPy
- ZeroMQ
- Whisper (for wake word detection)
- PyTorch (for Whisper)

## Next Steps

1. **Fine-tuning**: Adjust wake word detection parameters for optimal performance
2. **Integration testing**: Test the agent with the full MVS
3. **Performance optimization**: Monitor resource usage and optimize as needed
4. **User testing**: Gather feedback on wake word detection accuracy and responsiveness
