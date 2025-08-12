# 🗺️ REMAINING AGENTS CONTAINERIZATION ROADMAP

## Current Status: 6/50+ agents containerized

### ✅ COMPLETED (6 services)
1. ModelOpsCoordinator - 8212 ✅
2. RealTimeAudioPipeline - 6557 ✅
3. AffectiveProcessingCenter - 6560 ✅
4. UnifiedObservabilityCenter - 9110 ✅
5. SelfHealingSupervisor - 9008 ✅
6. CentralErrorBus - 8150 ✅

## 🔴 MAINPC AGENTS - TO BE CONTAINERIZED

### Foundation Services (CRITICAL - Phase 1)
- [ ] ServiceRegistry - 8200
- [ ] SystemDigitalTwin - 8220
- [ ] UnifiedSystemAgent - 8201
- [ ] MemoryFusionHub - 6713

### Utility Services
- [ ] HumanAwarenessSystem - 6650
- [ ] DataCacheManager - 6613
- [ ] EventBus - 6606
- [ ] ContextTracker - 6615
- [ ] HotSwapManager - 8125

### GPU Infrastructure
- [ ] GPUCoordinator - 8155

### Reasoning Services
- [ ] ReasoningEngineAgent - 6612
- [ ] ChainOfThoughtAgent - 6646
- [ ] CognitiveAgent - 6641

### Vision Processing
- [ ] VisionAgent - 6610

### Learning & Knowledge
- [ ] AdaptiveLearningOrchestrator - 8202
- [ ] KnowledgeGraph - 6580
- [ ] IncidentCollector - 6638

### Language Processing
- [ ] NLUAgent - 6701
- [ ] CommandProcessor - 6709
- [ ] IntentRouter - 6710
- [ ] ResponseOptimizer - 6711
- [ ] PersonalizationEngine - 6636
- [ ] ResponseGenerator - 6637
- [ ] MiscAgent - 6802
- [ ] PriorityManager - 6706

### Speech Services
- [ ] VoiceToTextAgent - 6800
- [ ] TextToSpeechAgent - 6801
- [ ] SpeechProcessingAgent - 7550
- [ ] VoiceOutputAgent - 7551
- [ ] AudioCaptureAgent - 6576
- [ ] AudioProcessingAgent - 7553
- [ ] AudioCoordinator - 6562
- [ ] SpeechSynthesisAgent - 7552
- [ ] AudioStreamManager - 6579
- [ ] ToneDetector - 6624

### Emotion System
- [ ] EmotionSimulator - 6590
- [ ] SituationalResponder - 6704
- [ ] ActiveHumanityAgent - 6705
- [ ] ToneDetector - 6625
- [ ] VoiceProfilingAgent - 6708
- [ ] EmpathyAgent - 6703

### Translation Services
- [ ] CloudTranslationService - 6592
- [ ] StreamingTranslationProxy - 6596
- [ ] ObservabilityDashboardAPI - 9007

## 🔵 PC2 AGENTS - TO BE CONTAINERIZED

### Core Services
- [ ] MemoryFusionHub - 6713 (PC2 instance)
- [ ] RealTimeAudioPipelinePC2 - 6557 (PC2 instance)

### Async Processing
- [ ] TieredResponder - 8100
- [ ] AsyncProcessor - 8101
- [ ] CacheManager - 8102

### Vision & Dream
- [ ] VisionProcessingAgent - 8160
- [ ] DreamWorldAgent - 8104
- [ ] DreamingModeAgent - 8127

### Resource Management
- [ ] ResourceManager - 8113
- [ ] TaskScheduler - 8115

### Utilities
- [ ] AuthenticationAgent - 8116
- [ ] UnifiedUtilsAgent - 8118
- [ ] ProactiveContextMonitor - 8119
- [ ] AgentTrustScorer - 8122
- [ ] FileSystemAssistantAgent - 8123
- [ ] RemoteConnectorAgent - 8124
- [ ] UnifiedWebAgent - 8126
- [ ] AdvancedRouter - 8129

### Educational
- [ ] TutoringServiceAgent - 8108

### Speech
- [ ] SpeechRelayService - 8130

## 📊 Containerization Strategy

### Phase 1: Critical Foundation (Week 1)
1. ServiceRegistry - Central service discovery
2. SystemDigitalTwin - System state management
3. UnifiedSystemAgent - Core orchestration
4. MemoryFusionHub - Memory management

### Phase 2: Core Processing (Week 2)
1. All Language Processing agents
2. All Speech Services agents
3. GPU Infrastructure agents

### Phase 3: Intelligence Layer (Week 3)
1. Reasoning Services
2. Vision Processing
3. Learning & Knowledge agents

### Phase 4: Support Services (Week 4)
1. Emotion System agents
2. Translation Services
3. Utility Services

### Phase 5: PC2 Agents (Week 5)
1. All PC2-specific agents
2. Backup/redundancy services

## 🔧 Technical Requirements

### For Each Agent:
1. Create `pyproject.toml` for package structure
2. Create multi-stage Dockerfile
3. Set proper health check endpoint
4. Configure correct ports
5. Handle Docker Desktop compatibility
6. Add to deployment scripts

### Base Images Needed:
- GPU agents → `family-torch-cu121` or `family-llm-cu121`
- CPU agents → `base-cpu-pydeps`
- Web agents → `family-web`
- Vision agents → `family-vision-cu121`

### Port Management:
- PORT_OFFSET needs to be resolved (default: 0)
- Each agent has specific health_check_port
- Some use gRPC (port - 1000) and HTTP ports

## 📝 Next Immediate Steps

1. **Create batch containerization script** for foundation services
2. **Template Dockerfile** that can be reused
3. **Automated pyproject.toml generator**
4. **Batch health check validator**

## 🚨 Critical Notes

- Many agents have `${PORT_OFFSET}` which needs resolution
- Some agents have conditional requirements (`${RTAP_ENABLED:-false}`)
- Dependencies between agents need to be respected
- Some agents share the same script but different configs

## 📈 Progress Tracking

Total Agents: ~50+
Containerized: 6 (12%)
Remaining: 44+ (88%)

Estimated Time: 5 weeks at current pace
Recommended: Automate the process to reduce to 1 week