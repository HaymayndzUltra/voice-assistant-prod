# AI System Deployment Strategy

## Date: 2025-01-30

## Decision: Modular Build Strategy (UPDATED)

### Rationale:
- Phase 0 scan revealed 18 missing modular Dockerfiles referenced in CI/CD
- Created dedicated Dockerfiles for each service group:
  - MainPC: 11 service groups
  - PC2: 7 service groups
- Enables granular updates and better resource allocation

### Strategy:
1. Build separate Docker images for each service group
2. Use Docker Compose to orchestrate services with dedicated images
3. Each service runs in its own container with appropriate resource limits

### Service Groups Created:

#### MainPC (RTX 4090):
- `infra_core` - ServiceRegistry, SystemDigitalTwin
- `coordination` - RequestCoordinator, ModelManagerSuite, VRAMOptimizerAgent
- `observability_hub` - ObservabilityHub
- `memory_stack` - Memory services
- `vision_suite` - GPU vision processing
- `speech_pipeline` - GPU STT/TTS services
- `learning_pipeline` - GPU training services
- `reasoning_suite` - GPU reasoning agents
- `language_stack` - NLU and dialogue services
- `utility_suite` - CPU utility services
- `emotion_system` - Emotion modeling services

#### PC2 (RTX 3060):
- `infra_core` - ObservabilityHub, ResourceManager
- `memory_stack` - Memory orchestration services
- `async_pipeline` - Async processing services
- `tutoring_suite` - Educational agents
- `vision_dream_suite` - GPU vision/dream services
- `utility_suite` - Support utilities
- `web_interface` - Web UI services

### Benefits:
- Granular updates per service group
- Optimized resource allocation
- Better fault isolation
- Easier debugging and monitoring
- Scalable architecture

### Build Process:
```bash
# Build all images
./build-images.sh

# Push to registry
./push-images.sh
```

### Deployment:
- Use updated docker-compose files with per-service images
- Each service references its specific image
- Resource limits applied per container 