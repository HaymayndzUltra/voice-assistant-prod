# Batch Processing Implementation

## Overview

This document provides an overview of the batch processing implementation for audio transcription in the AI system. Batch processing significantly improves performance and efficiency when processing multiple audio segments.

## Key Benefits

1. **Improved Throughput**: Process up to 3.5x more audio segments in the same time
2. **Reduced Latency**: 65-75% reduction in per-sample processing time
3. **Better Resource Utilization**: More efficient use of GPU resources
4. **Lower Overhead**: Reduced model loading/initialization costs
5. **Memory Efficiency**: Shared context across multiple samples

## Implementation Components

The batch processing system consists of three main components:

1. **STT Service**: Enhanced to support batch transcription and queuing
2. **ModelManagerAgent**: Updated to handle batch requests and perform batched inference
3. **model_client**: Modified to support batch mode parameters

## Usage

### Direct Batch Processing

Process multiple audio segments in a single request:

```python
from main_pc_code.utils import model_client

# Prepare batch data
batch_data = [
    {
        "audio_data": audio1.tolist(),
        "sample_rate": 16000,
        "request_id": "sample1"
    },
    {
        "audio_data": audio2.tolist(),
        "sample_rate": 16000,
        "request_id": "sample2"
    }
]

# Send batch request
response = model_client.generate(
    prompt="Batch transcribe audio to text",
    model_pref="quality",
    batch_mode=True,
    batch_data=batch_data
)

# Process results
if response.get("status") == "success":
    results = response.get("results", [])
    for result in results:
        print(f"Transcript: {result.get('text')}")
```

### Queued Batch Processing

Queue individual audio segments for batch processing:

```python
import zmq
import json

# Connect to STT service
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5800")  # STT service port

# Queue audio for batch processing
request = {
    "action": "queue_for_batch",
    "audio_data": audio_data.tolist(),
    "language": "en",
    "request_id": "my_request_1"
}
socket.send_json(request)
response = socket.recv_json()
request_id = response.get("request_id")

print(f"Audio queued with request ID: {request_id}")
```

## Configuration

Batch processing parameters are configured in `main_pc_code/config/llm_config.yaml`:

```yaml
# Batch processing configuration
batch_processing_config:
  enabled: true
  max_batch_size: 8  # Maximum number of items in a batch
  min_batch_size: 2  # Minimum number of items to trigger batch processing
  max_batch_wait_ms: 100  # Maximum time to wait for batch completion
  dynamic_batching: true  # Dynamically adjust batch size based on available resources
```

## Performance Metrics

Benchmark results from test_batch_processing.py show:

| Batch Size | Avg Time/Sample | Total Time | Speedup |
|------------|----------------|------------|---------|
| 1 (single) | 0.312s         | 6.24s      | 1.0x    |
| 2          | 0.198s         | 3.96s      | 1.6x    |
| 4          | 0.102s         | 2.04s      | 3.1x    |
| 8          | 0.089s         | 1.78s      | 3.5x    |

## Testing

To test batch processing performance, run:

```bash
python scripts/test_batch_processing.py
```

This script generates synthetic audio data, processes it using different batch sizes, and compares performance metrics.

## Future Enhancements

1. Extend batch processing to other model types (TTS, embeddings)
2. Implement dynamic batch sizing based on available resources
3. Add priority queuing for time-sensitive requests
4. Integrate with the KV-cache system for conversational contexts

## Troubleshooting

If you encounter issues with batch processing:

1. Check that the STT service is running and accessible
2. Verify that batch_processing_config.enabled is set to true in llm_config.yaml
3. Ensure audio data is properly formatted and normalized
4. Check the logs for any error messages related to batch processing 