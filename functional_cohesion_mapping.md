# Functional Cohesion and Failure Domain Mapping
## Docker Production Reorganization Project

**Mapping Date**: 2025-07-30  
**Purpose**: Identify logical agent groupings based on functional cohesion and failure isolation

---

## 1. Functional Cohesion Analysis

### 1.1 Identified Functional Domains

#### Domain A: Core Infrastructure
**Purpose**: Essential services that all other agents depend on  
**Characteristics**: 
- Must start first
- Cannot fail without system-wide impact
- Minimal external dependencies

**Agents**:
- ServiceRegistry (service discovery)
- SystemDigitalTwin (state management)
- ObservabilityHub (system monitoring)

#### Domain B: Request Processing Pipeline
**Purpose**: Handle incoming user requests end-to-end  
**Characteristics**:
- Direct user interaction
- Stateless request handling
- High availability requirement

**Agents**:
- RequestCoordinator (request routing)
- NLUAgent (natural language understanding)
- IntentionValidatorAgent (intent validation)
- GoalManager (goal tracking)
- Responder (response generation)

#### Domain C: AI Model Management
**Purpose**: GPU resource management and model serving  
**Characteristics**:
- GPU-intensive operations
- Shared VRAM pool
- Model lifecycle management

**Agents**:
- ModelManagerSuite (model loading/unloading)
- VRAMOptimizerAgent (VRAM monitoring)
- ModelOrchestrator (inference routing)

#### Domain D: Speech Processing
**Purpose**: Audio input/output processing  
**Characteristics**:
- Real-time processing needs
- Audio stream handling
- GPU acceleration for models

**Agents**:
- AudioCapture
- FusedAudioPreprocessor
- WakeWordDetector
- StreamingSpeechRecognition
- STTService
- TTSService
- StreamingTTSAgent
- StreamingInterruptHandler

#### Domain E: Memory & Knowledge
**Purpose**: Information storage and retrieval  
**Characteristics**:
- Persistent storage
- Database operations
- Cross-session continuity

**Agents**:
- MemoryClient
- SessionMemoryAgent
- KnowledgeBase
- LearningManager
- ExperienceTracker (PC2)
- MemoryOrchestratorService (PC2)

#### Domain F: Reasoning & Learning
**Purpose**: Advanced AI reasoning and self-improvement  
**Characteristics**:
- CPU-intensive algorithms
- Async processing
- Training/fine-tuning operations

**Agents**:
- ChainOfThoughtAgent
- GoTToTAgent
- CognitiveModelAgent
- LearningOrchestrationService
- LearningOpportunityDetector
- ActiveLearningMonitor
- SelfTrainingOrchestrator
- LocalFineTunerAgent

#### Domain G: Emotion & Personality
**Purpose**: Emotional intelligence and personality modeling  
**Characteristics**:
- Stateful behavior tracking
- Real-time emotion processing
- Personality consistency

**Agents**:
- EmotionEngine
- MoodTrackerAgent
- HumanAwarenessAgent
- ToneDetector
- VoiceProfilingAgent
- EmpathyAgent
- EmotionSynthesisAgent
- DynamicIdentityAgent

#### Domain H: Specialized Services
**Purpose**: Domain-specific capabilities  
**Characteristics**:
- Independent functionality
- Optional features
- Specific use cases

**Agents**:
- TranslationService
- FaceRecognitionAgent
- CodeGenerator
- Executor
- ProactiveAgent
- VisionProcessingAgent (PC2)
- DreamWorldAgent (PC2)
- FileSystemAssistantAgent (PC2)

---

## 2. Failure Domain Analysis

### 2.1 Critical Failure Domains

#### Critical Domain 1: Service Discovery
- **Single Point of Failure**: ServiceRegistry
- **Impact**: Complete system failure if down
- **Mitigation**: 
  - Redis-backed persistence
  - Health check priority
  - Fast restart policy

#### Critical Domain 2: State Management  
- **Single Point of Failure**: SystemDigitalTwin
- **Impact**: Loss of system state coordination
- **Mitigation**:
  - Database backups
  - Read replicas
  - Graceful degradation

#### Critical Domain 3: Model Management
- **Failure Point**: ModelManagerSuite
- **Impact**: No AI inference possible
- **Mitigation**:
  - Model cache persistence
  - Fallback to cloud APIs
  - Resource reservation

### 2.2 Isolated Failure Domains

#### Isolated Domain 1: Speech Processing
- **Failure Scope**: Audio features only
- **System Impact**: Text-only interaction remains
- **Recovery**: Independent restart

#### Isolated Domain 2: Learning System
- **Failure Scope**: No new learning
- **System Impact**: Existing capabilities preserved
- **Recovery**: Async rebuild possible

#### Isolated Domain 3: Emotion System
- **Failure Scope**: Reduced empathy
- **System Impact**: Functional but less personalized
- **Recovery**: Stateless restart

---

## 3. Proposed Logical Groupings for Docker

### Group 1: Core Platform Services
**Docker Service Name**: `cascade-core`
**Failure Impact**: CRITICAL
**Resource Profile**: Low CPU/Memory, No GPU
**Agents**:
- ServiceRegistry
- SystemDigitalTwin  
- ObservabilityHub
- UnifiedSystemAgent

**Justification**: Minimal dependencies, must start first, system-wide impact

### Group 2: AI Engine Services  
**Docker Service Name**: `cascade-ai-engine`
**Failure Impact**: HIGH
**Resource Profile**: High GPU/VRAM, High Memory
**Agents**:
- ModelManagerSuite
- VRAMOptimizerAgent
- ModelOrchestrator
- STTService
- TTSService
- FaceRecognitionAgent

**Justification**: GPU resource sharing, coordinated VRAM management

### Group 3: Request Processing Services
**Docker Service Name**: `cascade-request-handler`  
**Failure Impact**: HIGH
**Resource Profile**: Medium CPU, Low GPU
**Agents**:
- RequestCoordinator
- NLUAgent
- IntentionValidatorAgent
- GoalManager
- AdvancedCommandHandler
- Responder

**Justification**: Request pipeline cohesion, stateless scaling

### Group 4: Memory & Learning Services
**Docker Service Name**: `cascade-memory-learning`
**Failure Impact**: MEDIUM  
**Resource Profile**: High Memory, Medium CPU, Low GPU
**Agents**:
- MemoryClient
- SessionMemoryAgent
- KnowledgeBase
- LearningOrchestrationService
- LearningManager
- ActiveLearningMonitor
- All training agents

**Justification**: Shared memory access, learning pipeline

### Group 5: Realtime Audio Services
**Docker Service Name**: `cascade-audio-realtime`
**Failure Impact**: MEDIUM
**Resource Profile**: Medium CPU, Low Memory
**Agents**:
- AudioCapture
- FusedAudioPreprocessor
- WakeWordDetector
- StreamingSpeechRecognition
- StreamingTTSAgent
- StreamingInterruptHandler

**Justification**: Audio stream processing, realtime requirements

### Group 6: Personality Services
**Docker Service Name**: `cascade-personality`  
**Failure Impact**: LOW
**Resource Profile**: Low CPU/Memory
**Agents**:
- EmotionEngine
- All emotion-related agents
- DynamicIdentityAgent

**Justification**: Cohesive personality modeling, graceful degradation

### Group 7: Auxiliary Services
**Docker Service Name**: `cascade-auxiliary`
**Failure Impact**: LOW
**Resource Profile**: Variable
**Agents**:
- Translation services
- Code generation
- Specialized agents

**Justification**: Optional features, independent operation

---

## 4. PC2 System Groupings

### PC2 Group 1: Core Services
**Docker Service Name**: `cascade-pc2-core`
**Agents**:
- ObservabilityHub
- MemoryOrchestratorService
- ResourceManager
- AsyncProcessor
- CacheManager

### PC2 Group 2: Application Services  
**Docker Service Name**: `cascade-pc2-apps`
**Agents**:
- All domain-specific agents
- Web/File agents
- Dream/Vision agents

---

## 5. Benefits of This Grouping

1. **Clear Failure Boundaries**: Each group can fail independently
2. **Resource Optimization**: Groups share similar resource profiles
3. **Simplified Deployment**: Fewer Docker services to manage
4. **Horizontal Scaling**: Groups can scale based on load
5. **Dependency Management**: Minimized cross-group dependencies
6. **Recovery Speed**: Smaller groups restart faster

---

## Next Steps
- Design specific Docker configurations for each group
- Define inter-group communication protocols
- Create health check strategies per group
- Design rollback procedures