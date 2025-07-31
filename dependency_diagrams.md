# Dependency Mapping Diagrams
## Docker Production Deployment

**Created**: 2025-07-30  
**Purpose**: Visual representation of agent dependencies for Docker deployment

---

## 1. MainPC System Dependency Diagram

### 1.1 High-Level Group Dependencies

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MainPC System                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐                                               │
│  │ core_platform   │ ◄─── All other groups depend on this          │
│  │ (Critical)      │                                               │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ├────────┬────────┬────────┬────────┬────────┐          │
│           ▼        ▼        ▼        ▼        ▼        ▼          │
│  ┌─────────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ ai_engine   │ │ request_ │ │ memory_  │ │ audio_   │ │persona │││
│  │ (High)      │ │processing│ │ learning │ │ realtime │ │lity    │││
│  └─────────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘│
│           │             │            │                              │
│           └─────────────┴────────────┴──────────────────────┐      │
│                                                             ▼      │
│                                                    ┌──────────────┐ │
│                                                    │ auxiliary    │ │
│                                                    │ (Low)        │ │
│                                                    └──────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Detailed Agent Dependencies - Core Platform

```
ServiceRegistry (Port 7200)
    │
    └──► SystemDigitalTwin (Port 7220)
              │
              ├──► ObservabilityHub (Port 9000)
              │
              └──► UnifiedSystemAgent (Port 7201)
```

### 1.3 Detailed Agent Dependencies - AI Engine

```
SystemDigitalTwin ──► ModelManagerSuite (Port 7211)
                           │
                           ├──► VRAMOptimizerAgent (Port 5572)
                           │
                           ├──► ModelOrchestrator (Port 7213)
                           │
                           ├──► STTService (Port 5800)
                           │
                           ├──► TTSService (Port 5801)
                           │
                           └──► FaceRecognitionAgent (Port 5610)
```

### 1.4 Detailed Agent Dependencies - Request Processing

```
SystemDigitalTwin ──► RequestCoordinator (Port 26002)
    │                      │
    │                      ├──► IntentionValidatorAgent (Port 5701)
    │                      │
    │                      ├──► GoalManager (Port 7205)
    │                      │    └── Also depends on:
    │                      │        - ModelOrchestrator
    │                      │        - MemoryClient
    │                      │
    └──► NLUAgent ◄───────┤
         (Port 5709)      │
              │           │
              └──► AdvancedCommandHandler (Port 5710)
                         │    └── Also depends on:
                         │        - CodeGenerator
                         │
                         └──► Responder (Port 5637)
                              └── Also depends on:
                                  - EmotionEngine
                                  - FaceRecognitionAgent
                                  - StreamingTTSAgent
                                  - TTSService
```

### 1.5 Cross-Group Dependencies Matrix

| From Group | To Group | Agent Dependencies |
|------------|----------|-------------------|
| request_processing | ai_engine | GoalManager → ModelOrchestrator |
| request_processing | ai_engine | Responder → FaceRecognitionAgent, TTSService |
| request_processing | memory_learning | GoalManager → MemoryClient |
| request_processing | audio_realtime | Responder → StreamingTTSAgent |
| request_processing | personality | Responder → EmotionEngine |
| request_processing | auxiliary | AdvancedCommandHandler → CodeGenerator |
| memory_learning | ai_engine | LearningOrchestrationService → ModelManagerSuite |
| memory_learning | ai_engine | SelfTrainingOrchestrator → ModelManagerSuite |
| memory_learning | request_processing | SessionMemoryAgent → RequestCoordinator |
| memory_learning | request_processing | LearningManager → RequestCoordinator |
| audio_realtime | request_processing | StreamingSpeechRecognition → RequestCoordinator |
| audio_realtime | ai_engine | StreamingSpeechRecognition → STTService |
| audio_realtime | ai_engine | StreamingTTSAgent → TTSService |
| audio_realtime | auxiliary | StreamingLanguageAnalyzer → TranslationService |
| personality | request_processing | EmotionSynthesisAgent → RequestCoordinator |
| personality | ai_engine | EmotionSynthesisAgent → ModelManagerSuite |
| personality | audio_realtime | EmpathyAgent → StreamingTTSAgent |
| auxiliary | ai_engine | CodeGenerator → ModelManagerSuite |
| auxiliary | ai_engine | FixedStreamingTranslation → ModelManagerSuite |
| auxiliary | request_processing | ProactiveAgent → RequestCoordinator |

---

## 2. PC2 System Dependency Diagram

### 2.1 High-Level Group Dependencies

```
┌─────────────────────────────────────────────────────────────────────┐
│                           PC2 System                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐                                               │
│  │ core_services   │ ◄─── Foundation for all PC2 operations        │
│  │ (Critical)      │                                               │
│  └────────┬────────┘                                               │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────────────────────────────────────────┐          │
│  │ application_services                                  │          │
│  │ (Medium)                                             │          │
│  │                                                      │          │
│  │ • Request Processing    • Memory & Learning          │          │
│  │ • Tutoring & Education  • Context Management         │          │
│  │ • Security & Auth       • Utility Services           │          │
│  │ • External Connectivity • Vision Processing          │          │
│  └──────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Services Dependencies

```
ObservabilityHub (Port 9100) [No dependencies]
    │
    ├──► ResourceManager (Port 7113)
    │         │
    │         └──► AsyncProcessor (Port 7101)
    │
    └──► UnifiedUtilsAgent (Port 7118)

MemoryOrchestratorService (Port 7140) [No dependencies]
    │
    └──► CacheManager (Port 7102)
```

### 2.3 Application Services Dependencies

```
Request Processing:
    ResourceManager ──► TieredResponder (Port 7100)
    AsyncProcessor ──► TaskScheduler (Port 7115)
                            │
                            └──► AdvancedRouter (Port 7129)

Memory & Learning:
    MemoryOrchestratorService ──┬──► DreamWorldAgent (Port 7104)
                                │          │
                                │          └──► DreamingModeAgent (Port 7127)
                                │
                                ├──► UnifiedMemoryReasoningAgent (Port 7105)
                                │
                                ├──► TutorAgent (Port 7108)
                                │
                                ├──► TutoringAgent (Port 7131)
                                │
                                ├──► ContextManager (Port 7111)
                                │          │
                                │          └──► ProactiveContextMonitor (Port 7119)
                                │
                                └──► ExperienceTracker (Port 7112)

Security & Authentication:
    UnifiedUtilsAgent ──┬──► AuthenticationAgent (Port 7116)
                        │
                        └──► FileSystemAssistantAgent (Port 7123)

External Connectivity:
    AdvancedRouter ──► RemoteConnectorAgent (Port 7124)
    
    FileSystemAssistantAgent ┐
    MemoryOrchestratorService ┴──► UnifiedWebAgent (Port 7126)

Vision & Monitoring:
    CacheManager ──► VisionProcessingAgent (Port 7150)
    ObservabilityHub ──► AgentTrustScorer (Port 7122)
```

---

## 3. Cross-System Dependencies

### 3.1 PC2 → MainPC Communications

```
┌─────────────────────┐         Network          ┌─────────────────────┐
│      PC2 System     │ ◄─────────────────────► │    MainPC System    │
├─────────────────────┤                          ├─────────────────────┤
│                     │                          │                     │
│ PC2 Agents needing  │         ZMQ/HTTP        │ MainPC Services     │
│ AI inference ──────────────────────────────────► ModelManagerSuite  │
│                     │                          │                     │
│ ObservabilityHub ◄─────── Metrics Sync ──────► ObservabilityHub    │
│ (Port 9100)        │                          │ (Port 9000)         │
│                     │                          │                     │
│ Memory sync ◄──────────── Redis Cluster ─────► SystemDigitalTwin   │
│                     │      (Optional)         │                     │
└─────────────────────┘                          └─────────────────────┘
```

### 3.2 Shared Infrastructure Dependencies

```
                        ┌─────────────────┐
                        │ Shared Services │
                        ├─────────────────┤
                        │                 │
                        │ • Redis Cluster │
                        │ • Prometheus    │
                        │ • Message Queue │
                        │                 │
                        └────────┬────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                                 ▼
        ┌──────────────┐                ┌──────────────┐
        │   MainPC     │                │     PC2      │
        │              │                │              │
        │ - State Mgmt │                │ - Cache Mgmt │
        │ - Metrics    │                │ - Metrics    │
        │ - Events     │                │ - Events     │
        └──────────────┘                └──────────────┘
```

---

## 4. Docker Deployment Order

### 4.1 MainPC Startup Sequence

```
START
  │
  ├─1─► core_platform (ServiceRegistry → SystemDigitalTwin → ObservabilityHub → UnifiedSystemAgent)
  │
  ├─2─► ai_engine (ModelManagerSuite → VRAMOptimizerAgent → Others)
  │
  ├─3─► request_processing (RequestCoordinator → NLUAgent → Others)
  │
  ├─4─► memory_learning (MemoryClient → SessionMemoryAgent → Others)
  │
  ├─5─► audio_realtime (AudioCapture → FusedAudioPreprocessor → Others)
  │
  ├─6─► personality (EmotionEngine → Others)
  │
  └─7─► auxiliary (All optional services)
```

### 4.2 PC2 Startup Sequence

```
START
  │
  ├─1─► core_services (ObservabilityHub → MemoryOrchestratorService → ResourceManager → AsyncProcessor → CacheManager)
  │
  └─2─► application_services (All application agents - can start in parallel within group)
```

---

## 5. Failure Impact Analysis

### 5.1 Critical Path Dependencies

**MainPC Critical Path:**
```
ServiceRegistry ──► SystemDigitalTwin ──► ModelManagerSuite ──► RequestCoordinator
     FAIL              FAIL                    FAIL                   FAIL
      ↓                 ↓                       ↓                      ↓
 System Down      No State Mgmt           No AI Models          No Requests
```

**PC2 Critical Path:**
```
ObservabilityHub ──► ResourceManager ──► AsyncProcessor
     FAIL               FAIL                FAIL
      ↓                  ↓                   ↓
 No Monitoring      No Resource Mgmt    No Async Ops
```

### 5.2 Graceful Degradation Paths

1. **If ai_engine fails**: System continues with cloud API fallbacks
2. **If personality fails**: System continues without emotion modeling
3. **If auxiliary fails**: Core functionality unaffected
4. **If audio_realtime fails**: Text-only interaction remains
5. **If PC2 application_services fail**: MainPC continues independently

---

## 6. Network Topology for Docker

```
Docker Network: cascade-internal (172.20.0.0/16)
├── MainPC Services (172.20.1.0/24)
│   ├── core_platform:     172.20.1.10-19
│   ├── ai_engine:         172.20.1.20-29
│   ├── request_processing: 172.20.1.30-39
│   ├── memory_learning:   172.20.1.40-49
│   ├── audio_realtime:    172.20.1.50-59
│   ├── personality:       172.20.1.60-69
│   └── auxiliary:         172.20.1.70-79
│
└── PC2 Services (172.20.2.0/24)
    ├── core_services:     172.20.2.10-19
    └── application_services: 172.20.2.20-49
```

---

## Next Steps
1. Create Docker Compose files based on these dependencies
2. Implement health check endpoints for each service
3. Setup monitoring dashboards in Prometheus/Grafana
4. Create automated deployment scripts respecting dependency order