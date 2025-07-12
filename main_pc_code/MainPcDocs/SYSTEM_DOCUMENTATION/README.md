# AI System Monorepo

This repository contains the unified codebase for the AI System, including components for both MainPC and PC2.

## Architecture

The system follows a centralized model management architecture, where all AI models (LLMs, STT, TTS) are managed by a dedicated ModelManagerAgent, with lightweight micro-services providing specific functionality.

For detailed architecture documentation, see [system_docs/architecture.md](system_docs/architecture.md).

## Key Components

- **ModelManagerAgent**: Central hub for all AI model operations
- **STT Service**: Lightweight wrapper for speech-to-text functionality
- **TTS Service**: Lightweight wrapper for text-to-speech functionality
- **GGUFModelManager**: Specialized manager for GGUF-format models
- **Model Client**: Standardized interface for agents to request model services

## Performance Optimizations

The system includes several performance optimizations:

### Model Quantization

- **4-bit Quantization**: Applied to Phi-3 models for maximum VRAM savings (~75% reduction)
- **8-bit Quantization**: Applied to GGUF models for balanced performance
- **16-bit Quantization**: Applied to Hugging Face models as default
- **Configuration**: Customizable per model type or specific model in `llm_config.yaml`

### KV-Cache Reuse

- **Conversation Tracking**: Uses conversation IDs to maintain context across requests
- **Cache Management**: Automatically manages cache size and expiration
- **Performance Impact**: Reduces latency by 30-50% for consecutive requests in the same conversation
- **API Support**: Clients can explicitly clear conversation caches when needed

## Configuration

The system uses a configuration-based approach to control behavior:

- **ENABLE_LEGACY_MODELS**: When set to true, allows direct model loading in legacy code paths (default: false)
- **Quantization Settings**: Control quantization levels for different model types
- **KV-Cache Settings**: Configure cache size, timeout, and other parameters
- **Location**: Defined in main_pc_code/config/llm_config.yaml

## Development

### Testing

Run the test suite to ensure code quality:

```bash
python -m pytest main_pc_code/tests/
```

### Performance Benchmarking

Run the performance benchmark to measure system performance:

```bash
python scripts/bench_baseline.py
```

### CI/CD Performance Gate (TODO)

A CI job (e.g., in `.github/workflows/main.yml`) must be configured to perform the following on every Pull Request:
1. Run the baseline performance snapshot: `python scripts/bench_baseline.py`.
2. Store the results as a CI artifact.
3. Compare the new results against the baseline from the `main` branch.
4. Fail the CI check if the new performance is slower than the baseline by more than 15%. 