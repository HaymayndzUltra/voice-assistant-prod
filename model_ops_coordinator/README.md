# ModelOps Coordinator

Central GPU resource management and model lifecycle hub for AI System.

## Features

- GPU resource management and VRAM optimization
- Model lifecycle management (load/unload/inference)
- Learning job orchestration
- Goal-driven task management
- Circuit breaker resiliency patterns
- **Hybrid Inference Routing (Local ⇄ Cloud)**

## Hybrid Inference Architecture

The ModelOps Coordinator includes a sophisticated hybrid inference system that intelligently routes requests between local models and cloud providers.

### Key Features

- **Local-First Strategy** (STT/Reasoning): Prioritizes local models with intelligent fallback to cloud
- **Cloud-First Strategy** (TTS/Translation): Prioritizes cloud providers with local fallback
- **Hedged Requests**: Launches parallel requests when latency or quality thresholds aren't met
- **Circuit Breakers**: Automatic failure detection and recovery for each provider
- **Policy-Driven**: Configurable thresholds and provider priorities via YAML

### Configuration

Configure hybrid routing in `config/hybrid_policy.yaml`:

```yaml
services:
  stt:
    strategy: local_first
    providers:
      local:
        - name: whisper_local
      cloud:
        - name: openai_stt
    fallback_criteria:
      latency_threshold_ms: 500
      confidence_score_threshold: 0.75
```

### API Endpoints

- `POST /v1/stt` - Speech-to-text with hybrid routing
- `POST /v1/tts` - Text-to-speech with hybrid routing  
- `POST /v1/reason` - LLM reasoning with hybrid routing
- `POST /v1/translate` - Translation with hybrid routing

### Environment Variables

Required for cloud providers:
- `OPENAI_API_KEY` - OpenAI API key
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to Google Cloud service account JSON
- `PICOVOICE_ACCESS_KEY` - Picovoice access key for wake word detection

## Architecture

The coordinator uses a micro-kernel architecture with pluggable modules:

- **Kernel**: Core orchestration and initialization
- **GPU Manager**: GPU resource tracking and allocation
- **Lifecycle Module**: Model loading/unloading
- **Inference Module**: Inference execution with bulkhead protection
- **Learning Module**: Fine-tuning and training job management
- **Goal Module**: Goal-driven task orchestration
- **Hybrid Module**: Intelligent local/cloud routing

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```python
from model_ops_coordinator import ModelOpsCoordinator

# Start the coordinator
coordinator = ModelOpsCoordinator(port=7212)
await coordinator.run()
```

## API Documentation

Access the interactive API documentation at `http://localhost:8008/docs` when the service is running.