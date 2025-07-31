# Docker Group Structure Design
## Optimized for Production Deployment

**Design Date**: 2025-07-30  
**Target Environment**: Docker Swarm / Kubernetes

---

## 1. MainPC Docker Groups (RTX 4090 System)

### Group 1: cascade-core
**Purpose**: Foundation services that must start first

```yaml
services:
  cascade-core:
    image: cascade/core:latest
    deploy:
      replicas: 1  # Single instance for state consistency
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 10
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    
    agents:
      - name: ServiceRegistry
        port: 7200
        health_port: 8200
        startup_order: 1
        health_check:
          test: ["CMD", "curl", "-f", "http://localhost:8200/health"]
          interval: 10s
          timeout: 5s
          retries: 5
          start_period: 30s
      
      - name: SystemDigitalTwin
        port: 7220
        health_port: 8220
        startup_order: 2
        depends_on: [ServiceRegistry]
        volumes:
          - unified_memory:/data/unified_memory.db
          - redis_data:/data/redis
      
      - name: ObservabilityHub
        port: 9000
        health_port: 9001
        startup_order: 3
        depends_on: [SystemDigitalTwin]
        environment:
          PROMETHEUS_ENABLED: "true"
          PARALLEL_HEALTH_CHECKS: "true"
      
      - name: UnifiedSystemAgent
        port: 7201
        health_port: 8201
        startup_order: 4
        depends_on: [SystemDigitalTwin]
```

### Group 2: cascade-ai-engine
**Purpose**: GPU-intensive AI model services

```yaml
services:
  cascade-ai-engine:
    image: cascade/ai-engine:latest
    deploy:
      replicas: 1  # Single instance for GPU access
      placement:
        constraints:
          - node.labels.gpu == rtx4090
      resources:
        limits:
          cpus: '8.0'
          memory: 32G
        reservations:
          cpus: '4.0'
          memory: 16G
          generic_resources:
            - discrete_resource_spec:
                kind: 'gpu'
                value: 1
    
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
      - CUDA_VISIBLE_DEVICES=0
      - VRAM_BUDGET_PERCENTAGE=80
      - MODEL_CACHE_DIR=/models
    
    volumes:
      - model_cache:/models
      - model_configs:/configs
    
    agents:
      - name: ModelManagerSuite
        port: 7211
        health_port: 8211
        startup_order: 1
        memory_limit: 8G
        environment:
          HYBRID_INFERENCE_ENABLED: "true"
          IDLE_TIMEOUT: "300"
      
      - name: VRAMOptimizerAgent
        port: 5572
        health_port: 6572
        startup_order: 2
        memory_limit: 512M
      
      - name: ModelOrchestrator
        port: 7213
        health_port: 8213
        startup_order: 3
        memory_limit: 2G
      
      - name: STTService
        port: 5800
        health_port: 6800
        startup_order: 4
        memory_limit: 4G
      
      - name: TTSService
        port: 5801
        health_port: 6801
        startup_order: 5
        memory_limit: 4G
      
      - name: FaceRecognitionAgent
        port: 5610
        health_port: 6610
        startup_order: 6
        memory_limit: 2G
```

### Group 3: cascade-request-handler
**Purpose**: Stateless request processing pipeline

```yaml
services:
  cascade-request-handler:
    image: cascade/request-handler:latest
    deploy:
      replicas: 3  # Horizontal scaling for load
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    
    agents:
      - name: RequestCoordinator
        port: 26002
        health_port: 27002
        load_balanced: true
      
      - name: NLUAgent
        port: 5709
        health_port: 6709
      
      - name: IntentionValidatorAgent
        port: 5701
        health_port: 6701
      
      - name: GoalManager
        port: 7205
        health_port: 8205
      
      - name: AdvancedCommandHandler
        port: 5710
        health_port: 6710
      
      - name: Responder
        port: 5637
        health_port: 6637
```

### Group 4: cascade-memory-learning
**Purpose**: Persistent memory and learning services

```yaml
services:
  cascade-memory-learning:
    image: cascade/memory-learning:latest
    deploy:
      replicas: 2  # Active-passive for data consistency
      resources:
        limits:
          cpus: '4.0'
          memory: 16G
        reservations:
          cpus: '2.0'
          memory: 8G
    
    volumes:
      - memory_data:/data/memory
      - learning_data:/data/learning
      - training_checkpoints:/data/checkpoints
    
    agents:
      - name: MemoryClient
        port: 5713
        health_port: 6713
        persistent: true
      
      - name: SessionMemoryAgent
        port: 5574
        health_port: 6574
      
      - name: KnowledgeBase
        port: 5715
        health_port: 6715
      
      - name: LearningOrchestrationService
        port: 7210
        health_port: 8212
      
      - name: LearningManager
        port: 5580
        health_port: 6580
      
      - name: ActiveLearningMonitor
        port: 5638
        health_port: 6638
      
      - name: SelfTrainingOrchestrator
        port: 5660
        health_port: 6660
        gpu_access: optional
      
      - name: LocalFineTunerAgent
        port: 5642
        health_port: 6642
        gpu_access: optional
```

### Group 5: cascade-audio-realtime
**Purpose**: Real-time audio processing

```yaml
services:
  cascade-audio-realtime:
    image: cascade/audio-realtime:latest
    deploy:
      replicas: 1  # Single instance for audio device
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    
    devices:
      - /dev/snd:/dev/snd  # Audio device access
    
    cap_add:
      - SYS_ADMIN  # For real-time priority
    
    agents:
      - name: AudioCapture
        port: 6550
        health_port: 7550
        realtime_priority: true
      
      - name: FusedAudioPreprocessor
        port: 6551
        health_port: 7551
      
      - name: WakeWordDetector
        port: 6552
        health_port: 7552
      
      - name: StreamingSpeechRecognition
        port: 6553
        health_port: 7553
      
      - name: StreamingTTSAgent
        port: 5562
        health_port: 6562
      
      - name: StreamingInterruptHandler
        port: 5576
        health_port: 6576
      
      - name: StreamingLanguageAnalyzer
        port: 5579
        health_port: 6579
```

### Group 6: cascade-personality
**Purpose**: Emotion and personality modeling

```yaml
services:
  cascade-personality:
    image: cascade/personality:latest
    deploy:
      replicas: 2  # Redundancy for consistency
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    
    agents:
      - name: EmotionEngine
        port: 5590
        health_port: 6590
        state_sync: true
      
      - name: MoodTrackerAgent
        port: 5704
        health_port: 6704
      
      - name: HumanAwarenessAgent
        port: 5705
        health_port: 6705
      
      - name: ToneDetector
        port: 5625
        health_port: 6625
      
      - name: VoiceProfilingAgent
        port: 5708
        health_port: 6708
      
      - name: EmpathyAgent
        port: 5703
        health_port: 6703
      
      - name: EmotionSynthesisAgent
        port: 5706
        health_port: 6706
      
      - name: DynamicIdentityAgent
        port: 5802
        health_port: 6802
```

### Group 7: cascade-auxiliary
**Purpose**: Optional specialized services

```yaml
services:
  cascade-auxiliary:
    image: cascade/auxiliary:latest
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    
    agents:
      - name: TranslationService
        port: 5595
        health_port: 6595
        optional: true
      
      - name: FixedStreamingTranslation
        port: 5584
        health_port: 6584
      
      - name: NLLBAdapter
        port: 5582
        health_port: 6582
      
      - name: CodeGenerator
        port: 5650
        health_port: 6650
      
      - name: Executor
        port: 5606
        health_port: 6606
      
      - name: ProactiveAgent
        port: 5624
        health_port: 6624
      
      - name: ChitchatAgent
        port: 5711
        health_port: 6711
      
      - name: FeedbackHandler
        port: 5636
        health_port: 6636
```

---

## 2. PC2 Docker Groups (RTX 3060 System)

### Group 1: cascade-pc2-core
**Purpose**: PC2 foundation services

```yaml
services:
  cascade-pc2-core:
    image: cascade/pc2-core:latest
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.system == pc2
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    
    agents:
      - name: ObservabilityHub
        port: 9100
        health_port: 9110
        config:
          scope: "pc2_agents"
          mainpc_hub_endpoint: "http://mainpc:9000"
      
      - name: MemoryOrchestratorService
        port: 7140
        health_port: 8140
      
      - name: ResourceManager
        port: 7113
        health_port: 8113
      
      - name: AsyncProcessor
        port: 7101
        health_port: 8101
      
      - name: CacheManager
        port: 7102
        health_port: 8102
```

### Group 2: cascade-pc2-apps
**Purpose**: PC2 application services

```yaml
services:
  cascade-pc2-apps:
    image: cascade/pc2-apps:latest
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
    
    agents:
      - name: DreamWorldAgent
        port: 7104
        health_port: 8104
      
      - name: UnifiedMemoryReasoningAgent
        port: 7105
        health_port: 8105
      
      - name: TutorAgent
        port: 7108
        health_port: 8108
      
      - name: ContextManager
        port: 7111
        health_port: 8111
      
      - name: ExperienceTracker
        port: 7112
        health_port: 8112
      
      - name: TaskScheduler
        port: 7115
        health_port: 8115
      
      - name: AuthenticationAgent
        port: 7116
        health_port: 8116
      
      - name: UnifiedUtilsAgent
        port: 7118
        health_port: 8118
      
      - name: ProactiveContextMonitor
        port: 7119
        health_port: 8119
      
      - name: AgentTrustScorer
        port: 7122
        health_port: 8122
      
      - name: FileSystemAssistantAgent
        port: 7123
        health_port: 8123
      
      - name: RemoteConnectorAgent
        port: 7124
        health_port: 8124
      
      - name: UnifiedWebAgent
        port: 7126
        health_port: 8126
      
      - name: DreamingModeAgent
        port: 7127
        health_port: 8127
      
      - name: AdvancedRouter
        port: 7129
        health_port: 8129
      
      - name: VisionProcessingAgent
        port: 7150
        health_port: 8150
      
      - name: TieredResponder
        port: 7100
        health_port: 8100
```

---

## 3. Inter-Group Communication

### Network Architecture
```yaml
networks:
  cascade-internal:
    driver: overlay
    internal: true
    attachable: true
    ipam:
      config:
        - subnet: 172.20.0.0/16
  
  cascade-external:
    driver: overlay
    attachable: true
```

### Service Discovery
- Internal DNS: `<agent_name>.<group_name>.cascade`
- Load balancing for replicated services
- Health-check based routing

### Communication Patterns
1. **Sync Communication**: Direct ZMQ connections
2. **Async Communication**: Redis pub/sub
3. **Bulk Data**: Shared volumes
4. **Metrics**: Prometheus scraping

---

## 4. Deployment Strategy

### Phase 1: Core Services
```bash
docker stack deploy -c cascade-core.yml cascade
# Wait for health checks
docker stack deploy -c cascade-ai-engine.yml cascade
```

### Phase 2: Application Services
```bash
docker stack deploy -c cascade-request-handler.yml cascade
docker stack deploy -c cascade-memory-learning.yml cascade
```

### Phase 3: Supporting Services
```bash
docker stack deploy -c cascade-audio-realtime.yml cascade
docker stack deploy -c cascade-personality.yml cascade
docker stack deploy -c cascade-auxiliary.yml cascade
```

### Phase 4: PC2 Deployment
```bash
# On PC2 node
docker stack deploy -c cascade-pc2-core.yml cascade
docker stack deploy -c cascade-pc2-apps.yml cascade
```

---

## 5. Resource Allocation Summary

### MainPC (RTX 4090)
- **Total CPU**: 32 cores allocated
- **Total Memory**: 80GB allocated
- **GPU**: 1x RTX 4090 (80% VRAM for models)

### PC2 (RTX 3060)
- **Total CPU**: 16 cores allocated
- **Total Memory**: 32GB allocated
- **GPU**: Used via MainPC inference

---

## 6. Scaling Strategies

### Horizontal Scaling
- Request handlers: 1-5 replicas
- Memory services: 2 replicas (active-passive)
- Personality services: 2 replicas

### Vertical Scaling
- AI Engine: Scale up for larger models
- Memory services: Increase for more history

### Auto-scaling Rules
```yaml
deploy:
  replicas: 3
  update_config:
    parallelism: 1
  restart_policy:
    condition: any
  resources:
    limits:
      cpus: '4.0'
    reservations:
      cpus: '2.0'
```

---

## Next Steps
1. Create specific YAML configurations
2. Define health check endpoints
3. Setup monitoring dashboards
4. Create deployment scripts