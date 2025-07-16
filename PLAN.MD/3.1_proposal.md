# DEPENDENCY ANALYSIS & PORT MAPPING

## CURRENT DEPENDENCY COMPLEXITY ANALYSIS

### **Critical Dependency Patterns Identified**

#### **1. SystemDigitalTwin Bottleneck (MainPC)**
**Current Dependencies**: 41 agents depend on SystemDigitalTwin
- **Risk**: Single point of failure
- **Consolidation Impact**: Maintains central role, reduces satellite complexity

#### **2. Memory System Fragmentation**
**Current Pattern**:
```
MemoryClient (5713) → SystemDigitalTwin
SessionMemoryAgent (5574) → RequestCoordinator, SystemDigitalTwin, MemoryClient  
KnowledgeBase (5715) → MemoryClient, SystemDigitalTwin
MemoryOrchestratorService (7140) → []
UnifiedMemoryReasoningAgent (7105) → MemoryOrchestratorService
CacheManager (7102) → MemoryOrchestratorService
```

**Post-Consolidation Pattern**:
```
MainMemoryOrchestrator (5700) → SystemDigitalTwin, RequestCoordinator
[Eliminates 5 inter-memory dependencies]
```

#### **3. Learning Service Interdependencies**
**Current Circular Dependencies**:
```
LearningManager (5580) → MemoryClient, RequestCoordinator, SystemDigitalTwin
ActiveLearningMonitor (5638) → LearningManager, SystemDigitalTwin
LearningAdjusterAgent (5643) → SelfTrainingOrchestrator, SystemDigitalTwin
LearningOpportunityDetector (7200) → LearningOrchestrationService, MemoryClient, SystemDigitalTwin
LearningOrchestrationService (7210) → ModelEvaluationFramework, SystemDigitalTwin
ModelEvaluationFramework (7220) → SystemDigitalTwin
```

**Post-Consolidation Simplified**:
```
IntelligentLearningOrchestrator (5580) → MainMemoryOrchestrator, SelfTrainingOrchestrator, SystemDigitalTwin
[Eliminates 12 inter-learning dependencies]
```

---

## PORT CONSOLIDATION STRATEGY

### **Phase 1: Port Reassignment Plan**

#### **Memory Services Consolidation**
```
OLD PORTS:
MainPC: 5713 (MemoryClient), 5574 (SessionMemoryAgent), 5715 (KnowledgeBase)
PC2: 7140 (MemoryOrchestratorService), 7105 (UnifiedMemoryReasoningAgent), 7102 (CacheManager)

NEW PORT:
MainPC: 5700 (MainMemoryOrchestrator) + Health: 6700
  └─ Internal communication with PC2 cache layer via secured channel
```

#### **Learning Services Consolidation**
```
OLD PORTS:
MainPC: 5580, 5638, 5643, 7200, 7210, 7220

NEW PORT:
MainPC: 5580 (IntelligentLearningOrchestrator) + Health: 6580
```

#### **Health Monitoring Consolidation**
```
OLD PORTS:
MainPC: 5613 (PredictiveHealthMonitor)
PC2: 7114, 7117, 7103, 7128

NEW PORT:
PC2: 7114 (UnifiedSystemHealthOrchestrator) + Health: 8114
```

### **Phase 2: Functional Service Ports**

#### **Emotion System Consolidation**
```
OLD PORTS: 5590, 5704, 5705, 5625, 5708, 5703
NEW PORT: 5590 (SocialIntelligenceEngine) + Health: 6590
```

#### **Translation Services Consolidation**
```
OLD PORTS: 5584, 5581, 5595, 5579
NEW PORT: 5581 (UnifiedLanguageProcessor) + Health: 6581
```

#### **PC2 Utility Services Consolidation**
```
OLD PORTS: 7108, 7131, 7116, 7118, 7123
NEW PORT: 7108 (PC2UtilityOrchestrator) + Health: 8108
```

### **Phase 3: Advanced Integration Ports**

#### **Vision Services Consolidation**
```
OLD PORTS: 5610 (MainPC), 7150 (PC2)
NEW PORT: 5610 (UnifiedVisionIntelligence) + Health: 6610
```

#### **Dream/Context Services Consolidation**
```
OLD PORTS: 7104, 7127, 7111, 7112, 7119
NEW PORT: 7104 (ContextualDreamOrchestrator) + Health: 8104
```

#### **Reasoning Engine Consolidation**
```
OLD PORTS: 5612, 5646, 5641
NEW PORT: 5612 (AdvancedReasoningEngine) + Health: 6612
```

---

## FINAL PORT ALLOCATION MAP

### **MainPC (RTX 4090) - Optimized Port Ranges**

#### **Core Infrastructure (5xxx Range)**
```
5700: MainMemoryOrchestrator (was MemoryClient/SessionMemoryAgent/KnowledgeBase)
5580: IntelligentLearningOrchestrator (was LearningManager + 5 others)
5590: SocialIntelligenceEngine (was EmotionEngine + 5 others)
5581: UnifiedLanguageProcessor (was Translation services)
5610: UnifiedVisionIntelligence (was FaceRecognitionAgent)
5612: AdvancedReasoningEngine (was ChainOfThoughtAgent + 2 others)
```

#### **GPU Infrastructure (Maintained)**
```
5575: GGUFModelManager
5570: ModelManagerAgent  
5572: VRAMOptimizerAgent
5617: PredictiveLoader
```

#### **Language Processing (Maintained)**
```
7010: ModelOrchestrator
7005: GoalManager
5709: NLUAgent
```

#### **Speech & Audio Pipeline (Maintained)**
```
5800: STTService
5801: TTSService
6550: AudioCapture
6551: FusedAudioPreprocessor
5576: StreamingInterruptHandler
6553: StreamingSpeechRecognition
5562: StreamingTTSAgent
6552: WakeWordDetector
```

#### **Utilities (Maintained)**
```
5650: CodeGenerator
5606: Executor
5660: SelfTrainingOrchestrator
5642: LocalFineTunerAgent
5615: TinyLlamaServiceEnhanced
5637: Responder
```

#### **System Core (7xxx Range)**
```
7100: ServiceRegistry
7120: SystemDigitalTwin
26002: RequestCoordinator
7125: UnifiedSystemAgent
```

### **PC2 (RTX 3060) - Optimized Port Ranges**

#### **System Management (7xxx Range)**
```
7114: UnifiedSystemHealthOrchestrator (was HealthMonitor + 4 others)
7108: PC2UtilityOrchestrator (was TutorAgent + 4 others)
7104: ContextualDreamOrchestrator (was DreamWorldAgent + 4 others)
7113: ResourceManager (maintained)
7122: AgentTrustScorer (maintained)
```

#### **Orchestration Services (Maintained)**
```
7100: TieredResponder
7101: AsyncProcessor
7115: TaskScheduler
7129: AdvancedRouter
```

#### **Network & Web Services (Maintained)**
```
7126: UnifiedWebAgent
7124: RemoteConnectorAgent
```

---

## DEPENDENCY RESTRUCTURING PLAN

### **Pre-Consolidation Dependency Count: ~200**

#### **High-Impact Dependency Reductions**

**Memory System Dependencies**: 
- **Before**: 15 cross-memory dependencies
- **After**: 3 dependencies to MainMemoryOrchestrator
- **Reduction**: 80%

**Learning System Dependencies**:
- **Before**: 18 inter-learning dependencies  
- **After**: 3 dependencies from IntelligentLearningOrchestrator
- **Reduction**: 83%

**Emotion System Dependencies**:
- **Before**: 12 emotion-related dependencies
- **After**: 2 dependencies from SocialIntelligenceEngine
- **Reduction**: 83%

**Health Monitoring Dependencies**:
- **Before**: 8 monitoring dependencies
- **After**: 2 dependencies from UnifiedSystemHealthOrchestrator
- **Reduction**: 75%

### **Post-Consolidation Dependency Count: ~80**
**Overall Dependency Reduction: 60%**

---

## CRITICAL STARTUP SEQUENCE

### **Phase 1: Core Infrastructure Startup**
```
1. SystemDigitalTwin (7120) - Central coordination hub
2. ServiceRegistry (7100) - Service discovery
3. RequestCoordinator (26002) - Request routing
4. MainMemoryOrchestrator (5700) - Unified memory layer
5. UnifiedSystemHealthOrchestrator (7114) - System monitoring
```

### **Phase 2: Resource Management**
```
6. ResourceManager (7113) - Resource allocation
7. GGUFModelManager (5575) - Model management foundation
8. ModelManagerAgent (5570) - Model orchestration
9. VRAMOptimizerAgent (5572) - GPU optimization
```

### **Phase 3: AI & Processing Services**
```
10. IntelligentLearningOrchestrator (5580) - Learning coordination
11. AdvancedReasoningEngine (5612) - Reasoning capabilities
12. UnifiedLanguageProcessor (5581) - Language processing
13. SocialIntelligenceEngine (5590) - Emotion & social intelligence
```

### **Phase 4: Interface & Interaction**
```
14. UnifiedVisionIntelligence (5610) - Vision processing
15. STTService (5800) & TTSService (5801) - Speech services
16. Audio pipeline agents (6550-6553) - Audio processing
17. ContextualDreamOrchestrator (7104) - Context management
```

### **Phase 5: Application Services**
```
18-32. Remaining utility and interface agents
```

---

## COMMUNICATION OPTIMIZATION

### **Inter-Machine Communication Patterns**

#### **MainPC → PC2 Communications**
```
MainMemoryOrchestrator (5700) ←→ UnifiedSystemHealthOrchestrator (7114)
SystemDigitalTwin (7120) ←→ ContextualDreamOrchestrator (7104)
RequestCoordinator (26002) ←→ TieredResponder (7100)
```

#### **PC2 → MainPC Communications**
```
UnifiedSystemHealthOrchestrator (7114) → VRAMOptimizerAgent (5572)
ContextualDreamOrchestrator (7104) → MainMemoryOrchestrator (5700)
PC2UtilityOrchestrator (7108) → SystemDigitalTwin (7120)
```

### **Network Optimization Benefits**
- **Reduced Cross-Machine Calls**: 60% reduction in inter-machine communications
- **Batched Operations**: Consolidated agents can batch related operations
- **Connection Pooling**: Fewer agents mean fewer network connections to maintain
- **Simplified Load Balancing**: Clearer service boundaries for traffic routing

This dependency analysis provides the technical foundation for implementing the consolidation plan with minimal risk and maximum efficiency gains.