# System Architecture

## Overview

This document describes the final system architecture after the completion of the LLM Unification project. The architecture follows a centralized model management approach, where all AI models (LLMs, STT, TTS) are managed by a dedicated ModelManagerAgent, with lightweight micro-services providing specific functionality.

## Core Architectural Principles

1. **Centralized Model Management**: All AI models are loaded, managed, and accessed through the ModelManagerAgent.
2. **Micro-Service Architecture**: Lightweight, specialized services handle specific tasks (e.g., STT, TTS).
3. **Decoupled Components**: Services communicate via well-defined interfaces, reducing dependencies.
4. **Resource Optimization**: Intelligent model loading/unloading based on usage patterns and available resources.
5. **Unified Error Handling**: Standardized error reporting and recovery mechanisms.
6. **Performance Optimization**: Quantization and KV-cache reuse for improved VRAM usage and latency.

## Key Components

### ModelManagerAgent

The ModelManagerAgent serves as the central hub for all AI model operations:

- **Model Loading**: Loads models on demand based on requests from other agents.
- **Resource Management**: Monitors VRAM usage and implements intelligent model unloading.
- **Model Routing**: Routes requests to the appropriate model based on task requirements.
- **Model Versioning**: Tracks model versions and ensures compatibility.
- **Health Monitoring**: Reports model health and performance metrics.
- **Quantization Management**: Applies appropriate quantization levels based on model type.
- **Conversation Management**: Tracks conversation context for KV-cache reuse.

### STT Service

The Speech-to-Text service provides a lightweight wrapper around the ModelManagerAgent for transcription:

- **Audio Processing**: Receives audio data from streaming sources.
- **Model Client**: Uses model_client to request transcription from ModelManagerAgent.
- **Format Conversion**: Handles audio format conversion and normalization.
- **Result Publishing**: Publishes transcription results to subscribers.

### TTS Service

The Text-to-Speech service provides a lightweight wrapper around the ModelManagerAgent for speech synthesis:

- **Text Processing**: Receives text data from various sources.
- **Model Client**: Uses model_client to request speech synthesis from ModelManagerAgent.
- **Audio Formatting**: Handles audio format conversion and normalization.
- **Result Publishing**: Publishes synthesized speech to subscribers.

### GGUFModelManager

Specialized manager for GGUF-format models:

- **GGUF Loading**: Handles loading and initialization of GGUF models.
- **Quantization Support**: Supports various quantization levels (int4, int8, float16).
- **Inference Optimization**: Implements optimizations specific to GGUF models.
- **Resource Monitoring**: Tracks VRAM usage and model performance.
- **KV-Cache Management**: Stores and reuses KV caches for improved inference speed.

### Model Client

Provides a standardized interface for agents to request model services:

- **Request Formatting**: Standardizes request format for different model types.
- **Error Handling**: Handles connection errors and retries.
- **Load Balancing**: Distributes requests across available model instances.
- **Result Parsing**: Standardizes model outputs for consistent handling.
- **Conversation Tracking**: Maintains conversation IDs for context continuity.

## Communication Flow

1. **Agent Needs Model Inference**:
   - Agent creates a request using model_client
   - Request is sent to ModelManagerAgent

2. **ModelManagerAgent Processes Request**:
   - Identifies the appropriate model for the task
   - Loads the model if not already loaded
   - Performs inference (using KV-cache if available)
   - Returns results to the requesting agent

3. **Resource Management**:
   - ModelManagerAgent monitors VRAM usage
   - Unloads idle models when resources are needed
   - Prioritizes models based on usage patterns
   - Applies quantization based on model type and configuration

## Performance Optimizations

### Model Quantization

The system supports various quantization levels for models to reduce memory usage while maintaining acceptable quality. The quantization system is implemented in the ModelManagerAgent and supports:

1. **4-bit Quantization**: Primarily for Phi-3 models, reducing VRAM usage by ~75%
2. **8-bit Quantization**: For general models, reducing VRAM usage by ~50%
3. **16-bit Quantization**: For precision-sensitive models, reducing VRAM usage by ~25%

Quantization is configured per-model in the llm_config.yaml file, with appropriate defaults based on model type and size.

### KV-Cache Reuse

For conversational models, the system implements KV-cache reuse to significantly reduce latency in multi-turn conversations:

1. **Conversation Tracking**: Uses conversation_id to maintain context across requests
2. **Cache Management**: Implements timeout and size limits for caches
3. **Memory Efficiency**: Reduces redundant computation for repeated context

The KV-cache system is primarily implemented in the GGUF model manager and provides 30-50% latency reduction for consecutive requests in the same conversation.

### Batch Processing

The system implements batch processing for audio transcription to improve throughput and efficiency:

1. **Batched Inference**: Processes multiple audio segments in a single model forward pass
2. **Dynamic Batching**: Automatically collects and batches requests based on configurable thresholds
3. **Asynchronous Processing**: Background thread for batch management with timeout controls

Batch processing provides significant performance benefits:
- Up to 3.5x higher throughput with batch sizes of 4-8
- 65-75% reduction in per-sample latency
- More efficient GPU utilization and reduced overhead

The batch processing system is implemented in the STT service and ModelManagerAgent, with configuration in llm_config.yaml.

## Legacy Code Support

To facilitate a smooth transition to the new architecture, a configuration flag has been implemented:

- **ENABLE_LEGACY_MODELS**: When set to true, allows direct model loading in legacy code paths.
- **Default Value**: false (direct model loading is disabled)
- **Location**: Defined in main_pc_code/config/llm_config.yaml

This flag is checked by the test_no_direct_model_load.py guardrail test, which enforces the use of the centralized model management architecture when the flag is disabled.

## Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Agent 1       │     │   Agent 2       │     │   Agent 3       │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │                       │                       │
         │     ┌─────────────────▼─────────────────┐     │
         │     │                                   │     │
         └────►│          model_client            ◄─────┘
               │                                   │
               └─────────────────┬─────────────────┘
                                 │
                                 │
               ┌─────────────────▼─────────────────┐
               │                                   │
               │        ModelManagerAgent          │
               │                                   │
               └───┬─────────────┬────────────┬───┘
                   │             │            │
       ┌───────────▼───┐ ┌───────▼───────┐ ┌──▼─────────────┐
       │               │ │               │ │                │
       │  LLM Models   │ │  STT Models   │ │  TTS Models    │
       │               │ │               │ │                │
       └───────────────┘ └───────────────┘ └────────────────┘
```

## Future Optimization Opportunities

1. **Flash Attention 2**: Enable Flash Attention 2 for transformer models.
2. **Docker Build Optimization**: Implement multi-stage Docker builds.
3. **Batch Processing**: Implement batched processing for audio transcription.
4. **Speculative Decoding**: Implement speculative decoding for faster inference.
5. **Continuous Batching**: Implement continuous batching for higher throughput.

## Conclusion

The unified architecture provides a clean, maintainable, and resource-efficient approach to AI model management. By centralizing model loading and inference, we've reduced code duplication, improved resource utilization, and created a more scalable system. The addition of quantization and KV-cache reuse further enhances performance while reducing resource requirements. 