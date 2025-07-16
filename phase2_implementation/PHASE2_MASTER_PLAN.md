# PHASE 2: DATA & MODEL BACKBONE IMPLEMENTATION PLAN
**Target Reduction: 23 agents → 6 agents**

## CRITICAL REQUIREMENTS FOR O3

### 1. MEMORY HUB CONSOLIDATION
**Target Service:** `MemoryHub`
**Port:** 7010 | **Health Port:** 7110
**Hardware:** PC2 (RAM + light CPU)

#### Source Agents to Consolidate:
```
MemoryClient (5713)
SessionMemoryAgent (5574) 
KnowledgeBase (5715)
MemoryOrchestratorService (7140)
UnifiedMemoryReasoningAgent (7105)
ContextManager (7111)
ExperienceTracker (7112) 
CacheManager (7102)
```

#### Required Implementation Features:
1. **Unified Redis + SQLite Layer**
   - Multi-database Redis setup (db0=cache, db1=sessions, db2=knowledge)
   - SQLite for persistent storage with tables: `memories`, `sessions`, `knowledge_base`, `contexts`
   - Connection pooling and retry logic

2. **Neuro-Symbolic Search**
   - Vector embeddings storage and retrieval
   - Semantic similarity search
   - Context-aware memory retrieval

3. **Session Store Management**
   - Session lifecycle management
   - TTL-based cleanup
   - Cross-session context bridging

4. **API Endpoints Structure:**
   ```
   /kv/{key}           - Key-value operations
   /doc/{doc_id}       - Document storage/retrieval
   /embedding/{query}  - Semantic search
   /session/{session_id} - Session management
   /context/{context_id} - Context operations
   ```

5. **Logic Merger Strategy:**
   - Import legacy modules as sub-apps
   - Namespace collision prevention (session:, kb:, cache:)
   - Backward compatibility routes

#### Dependencies:
- CoreOrchestrator (startup priority 2)
- SecurityGateway (for auth)

---

### 2. MODEL MANAGER SUITE CONSOLIDATION
**Target Service:** `ModelManagerSuite`
**Port:** 7011 | **Health Port:** 7111
**Hardware:** MainPC (RTX 4090)

#### Source Agents to Consolidate:
```
GGUFModelManager (5575)
ModelManagerAgent (5570)
PredictiveLoader (5617)
ModelEvaluationFramework (7220)
```

#### Required Implementation Features:
1. **Quantized Model Registry**
   - GGUF model catalog with metadata
   - Model versioning and checksums
   - Hot-swap capability with locking

2. **Dynamic Model Loader**
   - Predictive pre-loading based on usage patterns
   - Memory-efficient model swapping
   - GPU memory management integration

3. **Evaluation Framework**
   - Automated model evaluation pipelines
   - Performance benchmarking
   - A/B testing infrastructure

4. **API Endpoints Structure:**
   ```
   /models             - List available models
   /models/{id}/load   - Load specific model
   /models/{id}/unload - Unload model
   /evaluate/{model_id} - Run evaluation
   /predict/{model_id}  - Model inference
   ```

5. **GPU Resource Management:**
   - Integration with ResourceManagerSuite
   - VRAM quota enforcement
   - Lockfile mechanism for GPU hot-swaps

#### Dependencies:
- MemoryHub (for model metadata storage)
- ResourceManagerSuite (for GPU management)

---

### 3. ADAPTIVE LEARNING SUITE CONSOLIDATION
**Target Service:** `AdaptiveLearningSuite`
**Port:** 7012 | **Health Port:** 7112
**Hardware:** MainPC (RTX 4090)

#### Source Agents to Consolidate:
```
SelfTrainingOrchestrator (5660)
LocalFineTunerAgent (5642)
LearningManager (5580)
LearningOrchestrationService (7210)
LearningOpportunityDetector (7200)
ActiveLearningMonitor (5638)
LearningAdjusterAgent (5643)
```

#### Required Implementation Features:
1. **Continual Learning Scheduler**
   - Automated training pipeline orchestration
   - Learning opportunity detection and prioritization
   - Resource-aware scheduling

2. **LoRA Fine-Tuner**
   - Low-Rank Adaptation implementation
   - Incremental model updates
   - Checkpoint management

3. **Auto-Evaluation Loop**
   - Performance monitoring and feedback
   - Adaptive learning rate adjustment
   - Model quality assessment

4. **API Endpoints Structure:**
   ```
   /training/start     - Start training job
   /training/{id}/stop - Stop training job
   /training/{id}/status - Check training status
   /opportunities      - List learning opportunities
   /evaluate/performance - Performance evaluation
   ```

5. **VRAM Management:**
   - Integration with ResourceManagerSuite for GPU quotas
   - Memory-efficient training strategies
   - Gradient accumulation for large models

#### Dependencies:
- ModelManagerSuite (for model access)
- MemoryHub (for training data and checkpoints)
- ResourceManagerSuite (for GPU scheduling)

---

## IMPLEMENTATION DIRECTORY STRUCTURE
```
phase2_implementation/
├── consolidated_agents/
│   ├── memory_hub/
│   │   ├── __init__.py
│   │   ├── memory_hub.py
│   │   ├── redis_manager.py
│   │   ├── sqlite_manager.py
│   │   ├── search_engine.py
│   │   └── session_manager.py
│   ├── model_manager_suite/
│   │   ├── __init__.py
│   │   ├── model_manager_suite.py
│   │   ├── gguf_manager.py
│   │   ├── predictive_loader.py
│   │   └── evaluation_framework.py
│   └── adaptive_learning_suite/
│       ├── __init__.py
│       ├── adaptive_learning_suite.py
│       ├── training_orchestrator.py
│       ├── lora_finetuner.py
│       └── learning_monitor.py
├── configs/
│   ├── memory_hub_config.yaml
│   ├── model_manager_config.yaml
│   └── learning_suite_config.yaml
└── tests/
    ├── test_memory_hub.py
    ├── test_model_manager.py
    └── test_learning_suite.py
```

---

## STARTUP CONFIGURATION UPDATES REQUIRED

### MainPC startup_config.yaml Updates:
```yaml
# Phase 2 Services
services:
  model_manager_suite:
    enabled: true
    port: 7011
    health_port: 7111
    startup_order: 3
    dependencies: ["memory_hub", "resource_manager_suite"]
    
  adaptive_learning_suite:
    enabled: true
    port: 7012
    health_port: 7112
    startup_order: 4
    dependencies: ["model_manager_suite", "memory_hub"]

# Legacy deprecation
deprecated_services:
  - GGUFModelManager
  - ModelManagerAgent
  - PredictiveLoader
  - ModelEvaluationFramework
  - SelfTrainingOrchestrator
  - LocalFineTunerAgent
  - LearningManager
  - LearningOrchestrationService
  - LearningOpportunityDetector
  - ActiveLearningMonitor
  - LearningAdjusterAgent
```

### PC2 startup_config.yaml Updates:
```yaml
# Phase 2 Services
services:
  memory_hub:
    enabled: true
    port: 7010
    health_port: 7110
    startup_order: 2
    dependencies: ["core_orchestrator", "security_gateway"]

# Legacy deprecation
deprecated_services:
  - MemoryClient
  - SessionMemoryAgent
  - KnowledgeBase
  - MemoryOrchestratorService
  - UnifiedMemoryReasoningAgent
  - ContextManager
  - ExperienceTracker
  - CacheManager
```

---

## CRITICAL IMPLEMENTATION NOTES FOR O3

1. **Logic Preservation:** ALL existing functionality must be preserved through facade patterns and compatibility layers.

2. **Database Migration:** Implement schema migration scripts for existing Redis/SQLite data.

3. **API Compatibility:** Maintain backward-compatible REST endpoints for smooth transition.

4. **Error Handling:** Integrate with ErrorBusSuite for centralized error management.

5. **Monitoring:** Add Prometheus metrics for ObservabilityHub integration.

6. **Resource Management:** Coordinate with ResourceManagerSuite for GPU/memory allocation.

7. **Security Integration:** Use SecurityGateway for authentication and authorization.

---

## VERIFICATION CHECKLIST

After O3 implementation, verify:
- [ ] All 3 consolidated services start successfully
- [ ] Health endpoints respond correctly
- [ ] Database migrations complete without data loss
- [ ] Legacy API endpoints maintain compatibility
- [ ] GPU resource allocation works correctly
- [ ] Inter-service communication established
- [ ] Prometheus metrics exposed
- [ ] Error reporting to ErrorBus functional
- [ ] Performance metrics within acceptable ranges
- [ ] All original agent functionality preserved

---

## COMMANDS FOR O3 TO EXECUTE

1. Create directory structure
2. Implement MemoryHub with all required features
3. Implement ModelManagerSuite with GPU management
4. Implement AdaptiveLearningSuite with LoRA training
5. Update both startup_config.yaml files
6. Create database migration scripts
7. Add comprehensive error handling
8. Implement health check endpoints
9. Add Prometheus metrics integration
10. Create backward compatibility layers

**ESTIMATED IMPLEMENTATION SIZE:** ~3000+ lines of code
**EXPECTED COMPLETION TIME:** Full Phase 2 implementation
**SUCCESS CRITERIA:** 23 agents → 6 services with 100% functionality preservation 