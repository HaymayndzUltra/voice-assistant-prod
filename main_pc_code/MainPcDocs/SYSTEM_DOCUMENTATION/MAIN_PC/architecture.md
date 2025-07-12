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
7. **Containerization**: Logical grouping of agents based on resource needs, communication patterns, and failure domains.

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

## Container Grouping Strategy

The system is organized into logical container groups based on three key criteria:

1. **Resource Profile & Co-location**: Agents with similar resource needs are grouped together
2. **Coupling and Communication Patterns**: Frequently communicating agents are placed in the same group
3. **Scalability and Failure Domain**: Agents that need independent scaling are separated

### Container Groups

1. **core_services**: Essential system services that provide core functionality
   - SystemDigitalTwin, RequestCoordinator, ErrorBusService

2. **memory_system**: Memory management and storage services
   - MemoryOrchestrator, MemoryClient, ContextSummarizerAgent, MemoryPruningAgent

3. **utility_services**: Support services for system operation
   - LoggingService, ConfigManager, NetworkMonitor, HealthCheckManager, PerformanceTracker

4. **ai_models_gpu_services**: GPU-accelerated AI model services
   - ModelRouter, DeepLearningAgent, ImageGenerationAgent, VideoProcessingAgent, ChainOfThoughtAgent, CognitiveModelAgent, GoTToTAgent

5. **language_processing**: Natural language processing services
   - TranslationAgent, ConsolidatedTranslator, NLLBTranslator, EmotionSynthesisAgent

6. **speech_services**: Speech processing services
   - STTService, TTSService

7. **audio_interface**: Audio streaming and processing services
   - StreamingSpeechRecognition, StreamingTTSAgent, StreamingInterruptHandler

8. **vision_processing**: Computer vision services
   - FaceRecognitionAgent

9. **emotion_system**: Emotion processing and analysis services
   - EmotionEngine, MoodTrackerAgent, HumanAwarenessAgent, ToneDetector, VoiceProfilingAgent, EmpathyAgent

### Grouping Rationale

- **GoTToTAgent** moved to ai_models_gpu_services due to high VRAM usage (similar to other GPU-intensive models)
- **Speech services** separated into a dedicated group for better resource management and scaling
- **Audio interface** agents grouped together due to tight coupling and streaming data flow
- **EmotionSynthesisAgent** moved to language_processing as it primarily processes text with emotional context
- **Vision processing** separated to isolate GPU-intensive computer vision workloads

## Performance Optimizations

### Model Quantization

The system now supports multiple quantization levels for different model types:

- **4-bit Quantization (int4)**: Applied to Phi-3 models for maximum VRAM savings (~75% reduction).
- **8-bit Quantization (int8)**: Applied to GGUF models for balanced performance.
- **16-bit Quantization (float16)**: Applied to Hugging Face models as default.

Quantization is configured in `main_pc_code/config/llm_config.yaml` and can be customized per model type or specific model.

### KV-Cache Reuse

For conversational use cases, the system implements KV-cache reuse:

- **Conversation Tracking**: Uses conversation IDs to maintain context across requests.
- **Cache Management**: Automatically manages cache size and expiration.
- **Performance Impact**: Reduces latency by 30-50% for consecutive requests in the same conversation.
- **API Support**: Clients can explicitly clear conversation caches when needed.

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

## Container Deployment Diagram

```
┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│                        │  │                        │  │                        │
│    core-services       │  │    memory-system       │  │    utility-services    │
│                        │  │                        │  │                        │
└────────────────────────┘  └────────────────────────┘  └────────────────────────┘

┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│                        │  │                        │  │                        │
│ ai-models-gpu-services │  │  language-processing   │  │    speech-services     │
│                        │  │                        │  │                        │
└────────────────────────┘  └────────────────────────┘  └────────────────────────┘

┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│                        │  │                        │  │                        │
│    audio-interface     │  │   vision-processing    │  │     emotion-system     │
│                        │  │                        │  │                        │
└────────────────────────┘  └────────────────────────┘  └────────────────────────┘
```

## Future Optimization Opportunities

1. **Flash Attention 2**: Enable Flash Attention 2 for transformer models.
2. **Docker Build Optimization**: Implement multi-stage Docker builds.
3. **Batch Processing**: Implement batched processing for audio transcription.
4. **Speculative Decoding**: Implement speculative decoding for faster inference.
5. **Continuous Batching**: Implement continuous batching for higher throughput.
6. **Container Resource Limits**: Fine-tune container resource limits based on group requirements.

## Conclusion

The unified architecture provides a clean, maintainable, and resource-efficient approach to AI model management. By centralizing model loading and inference, we've reduced code duplication, improved resource utilization, and created a more scalable system. The addition of quantization, KV-cache reuse, and logical container grouping further enhances performance while reducing resource requirements. 