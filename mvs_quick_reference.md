# MVS Quick Reference Guide

## System Transformation Summary

### Before vs After
| Metric | Current System | MVS |
|--------|---------------|-----|
| Total Agents | 77 | 13 |
| MainPC Agents | 54 | 8 |
| PC2 Agents | 23 | 5 |
| Startup Time | ~5 minutes | <30 seconds |
| Memory Usage | ~8GB | ~2.5GB |
| Dependency Depth | 6+ levels | 4 levels |

### Essential Agents (13)

#### MainPC (8)
1. ServiceRegistry - Service discovery
2. SystemDigitalTwin - State management
3. RequestCoordinator - Request routing
4. ModelManagerSuite - Model management
5. MemoryClient - Memory interface
6. STTService - Speech-to-text
7. TTSService - Text-to-speech
8. ObservabilityHub - Monitoring

#### PC2 (5)
1. MemoryOrchestratorService - Memory coordination
2. ResourceManager - Resource allocation
3. AsyncProcessor - Async processing
4. CacheManager - Caching layer
5. ObservabilityHub - PC2 monitoring

### Startup Order
```
Phase 0: ServiceRegistry
Phase 1: SystemDigitalTwin, ObservabilityHub, MemoryOrchestratorService
Phase 2: RequestCoordinator, ModelManagerSuite, ResourceManager
Phase 3: MemoryClient, AsyncProcessor, CacheManager
Phase 4: STTService, TTSService
```

### Key Consolidations
- **Monitoring**: 4 agents → 1 ObservabilityHub
- **Emotion**: 6 agents → Future: 1 EmotionService
- **Translation**: 3 agents → Future: 1 TranslationService
- **Learning**: 5 agents → Future: 1 LearningOrchestrator

### Hybrid LLM Routing
- **Heavy Tasks** → Cloud API
  - Complex reasoning
  - Code generation
  - Multi-step planning
- **Light Tasks** → Local LLM
  - Simple Q&A
  - Command parsing
  - Basic translation

### Quick Commands

Start MVS:
```bash
python /workspace/scripts/start_mvs.py --config /workspace/config/mvs_startup_config.yaml
```

Check Health:
```bash
curl http://localhost:9000/health/all
```

Monitor Metrics:
```bash
http://localhost:9090/metrics
```

### Rollback Command
```bash
python /workspace/scripts/rollback_to_legacy.py --backup /workspace/backups/pre-optimization/
```