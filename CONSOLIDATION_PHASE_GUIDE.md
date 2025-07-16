# AGENT CONSOLIDATION PHASE-BY-PHASE GUIDE
## Para sa 100% Accurate Implementation ng PLAN_A.md

---

## COMPLETE PLAN_A CONSOLIDATIONS:

### 1. **HealthSuite** (pc2)
- PredictiveHealthMonitor (main_pc)
- HealthMonitor, SystemHealthManager, PerformanceMonitor, PerformanceLoggerAgent (pc2)

### 2. **MemoryProxy** (main_pc) + **UnifiedMemoryOrchestrator** (pc2)
- UnifiedMemoryOrchestrator (main_pc) → MemoryProxy
- UnifiedMemoryOrchestrator (pc2) → authoritative instance

### 3. **TaskRouter** (pc2)
- RequestCoordinator (main_pc)
- TaskScheduler, AdvancedRouter, AsyncProcessor, ResourceManager, TieredResponder (pc2)

### 4. **VisionService** (main_pc)
- FaceRecognitionAgent (main_pc)
- VisionProcessingAgent (pc2)

### 5. **UtilityHub** (pc2)
- UnifiedUtilsAgent, SystemToolkitAgent, StreamingInterruptHandler

### 6. **SecondaryModelService** (fix duplication)
- Remove duplicate deployment

---

## PHASE 1: ANALYSIS & EXTRACTION (1 Week)

### Day 1-2: Core Infrastructure Extraction

**UTOS #1:**
```
"Extract all logic from HealthSuite agents: PredictiveHealthMonitor, HealthMonitor, SystemHealthManager, PerformanceMonitor, PerformanceLoggerAgent. Show me complete analysis of each."
```

**UTOS #2:**
```
"Extract all logic from Memory agents: UnifiedMemoryOrchestrator (both main_pc and pc2), MemoryClient, SessionMemoryAgent, KnowledgeBase. Map their differences."
```

**UTOS #3:**
```
"Extract all logic from TaskRouter agents: RequestCoordinator, TaskScheduler, AdvancedRouter, AsyncProcessor, ResourceManager, TieredResponder. Create comparison table."
```

### Day 3-4: Sensory & Utility Extraction

**UTOS #4:**
```
"Extract all logic from Vision agents: FaceRecognitionAgent and VisionProcessingAgent. Compare their model families and GPU usage."
```

**UTOS #5:**
```
"Extract all logic from Utility agents: UnifiedUtilsAgent, SystemToolkitAgent, StreamingInterruptHandler. Map their helper functions."
```

### Day 5-7: Port & Dependency Analysis

**UTOS #6:**
```
"Fix port conflicts: EmotionEngine (5590) vs SecondaryModelService. Map all port usage and create resolution plan."
```

**UTOS #7:**
```
"Create complete dependency graph for all agents to be consolidated. Show direct and indirect dependencies."
```

---

## PHASE 2: IMPLEMENTATION (3 Weeks)

### Week 1: Core Infrastructure

**UTOS #8:**
```
"Implement HealthSuite on pc2 combining ALL logic from the 5 health agents. Preserve all original functionality."
```

**UTOS #9:**
```
"Implement MemoryProxy on main_pc and consolidate UMO on pc2. Ensure all memory operations work correctly."
```

### Week 2: Task Routing & Vision

**UTOS #10:**
```
"Implement TaskRouter on pc2 with ALL logic from the 6 routing agents. Include GPU-aware scheduling."
```

**UTOS #11:**
```
"Implement VisionService on main_pc combining FaceRecognitionAgent and VisionProcessingAgent. Use GPU affinity flags."
```

### Week 3: Utilities & Cleanup

**UTOS #12:**
```
"Implement UtilityHub on pc2 consolidating all utility agents. Split into modules within same process."
```

**UTOS #13:**
```
"Fix SecondaryModelService duplication. Keep only one instance and update all references."
```

---

## PHASE 3: TESTING (1 Week)

### Shadow Mode Testing

**UTOS #14:**
```
"Deploy all consolidated agents in shadow mode. Run parallel with old agents for 1 week. Compare all outputs."
```

### Gradual Migration

**UTOS #15:**
```
"Start 5% traffic migration to consolidated agents. Monitor error rates and performance for 48 hours."
```

**UTOS #16:**
```
"Increase to 25% traffic. Monitor for 6 hours. Then 50% for 12 hours. Finally 100% for 24 hours."
```

---

## PHASE 4: VALIDATION & CLEANUP (1 Week)

### Blue/Green Cutover

**UTOS #17:**
```
"Perform blue/green cutover to new configs. Monitor for 48 hours. Expected downtime < 2 minutes."
```

### Legacy Cleanup

**UTOS #18:**
```
"Retire duplicate ports. Update compose files. Run integration tests. Archive legacy code in /archive/legacy_YYYYMMDD."
```

---

## HARDWARE-AWARE PLACEMENT (from PLAN_A):

### Main PC (RTX 4090):
- **GPU inference & training**: ModelManager, VisionService, Learning
- **Audio stack**: TTS/STT (low-latency, GPU accelerated)
- **Cognitive Loop**: ChainOfThought, CognitiveModel, LearningManager

### PC2 (RTX 3060):
- **Memory orchestration**: UnifiedMemoryOrchestrator
- **Health monitoring**: HealthSuite
- **Task routing**: TaskRouter
- **Utilities**: UtilityHub, RemoteConnector, Authentication

---

## PORT ALLOCATION (from PLAN_A):

```
70xx - Gateway/task routing
71xx - Memory & cache  
72xx - Learning
75xx - Health ports
```

---

## CRITICAL TEMPLATES:

### Before Each Consolidation:
```
CHECKLIST:
□ Extracted ALL logic from source agents?
□ Preserved ALL original methods?
□ Mapped ALL dependencies?
□ Created compatibility layer?
□ Tested in shadow mode?
□ Have rollback plan ready?
```

### Success Metrics (from PLAN_A):
```
□ 35% fewer running containers
□ Reduced IPC hops
□ GPU 4090 saturation improves > 10%
□ Clear domains, fewer configs
□ TaskRouter can shard to future nodes
□ Error rate < 0.1%
□ Downtime < 2 minutes
```

---

## ROLLBACK PROCEDURES:

**EMERGENCY UTOS:**
```
"ROLLBACK ALL CONSOLIDATIONS! Switch back to original agents immediately."
```

**Rollback Commands:**
```bash
# Restore original configs
git checkout HEAD~1 -- main_pc_code/config/startup_config.yaml
git checkout HEAD~1 -- pc2_code/config/startup_config.yaml

# Restart services
systemctl restart ai-agents

# Verify rollback
curl http://localhost:7100/health
curl http://localhost:26002/health
```

---

## MGA IMPORTANTENG PAALALA:

### ❌ IWASAN:
1. **HUWAG** implement nang sabay-sabay lahat
2. **HUWAG** kalimutan ang hardware placement
3. **HUWAG** skip ang shadow testing
4. **HUWAG** burahin ang old agents agad

### ✅ GAWIN:
1. **FOLLOW PLAN_A** exactly - 6 consolidations total
2. **RESPECT HARDWARE** placement (4090 vs 3060)
3. **USE CORRECT PORTS** (70xx, 71xx, 72xx, 75xx)
4. **TEST EVERYTHING** in parallel first

---

## COMPLETE PLAN_A IMPLEMENTATION ORDER:

1. **HealthSuite** (lowest risk)
2. **MemoryProxy + UMO** (medium risk)  
3. **TaskRouter** (highest risk)
4. **VisionService** (GPU optimization)
5. **UtilityHub** (cleanup)
6. **SecondaryModelService** (fix duplication)

---

Remember: PLAN_A is comprehensive - implement ALL consolidations, not just the first 3! 