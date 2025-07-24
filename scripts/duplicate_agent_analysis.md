# Duplicate Agent Analysis Report
*Generated for Sprint 2-3 Duplicate Agent Merge*

## Identified Duplicates

### 🔴 **Critical Duplicates** (Same base name, different locations)

#### 1. **tiered_responder.py**
- `main_pc_code/agents/tiered_responder.py` (19KB, 524 lines)
- `pc2_code/agents/tiered_responder.py` (18KB, 502 lines)
- **Status**: Active implementations, different sizes suggest code divergence

#### 2. **remote_connector_agent.py**
- `main_pc_code/agents/remote_connector_agent.py` (20KB, 517 lines)  
- `pc2_code/agents/remote_connector_agent.py` (38KB, 843 lines)
- **Status**: Significant size difference (38KB vs 20KB) - major functionality divergence

#### 3. **tutoring_agent.py / tutor_agent.py**
- `pc2_code/agents/tutoring_agent.py` (17KB, 409 lines)
- `pc2_code/agents/tutor_agent.py` (26KB, 682 lines)  
- **Status**: Similar functionality, different implementations within PC2

#### 4. **unified_memory_reasoning_agent.py**
- `pc2_code/agents/unified_memory_reasoning_agent.py` (35KB, 895 lines)
- `pc2_code/agents/unified_memory_reasoning_agent_simplified.py` (9.3KB, 244 lines)
- **Status**: Full vs simplified versions

### 🟡 **Backup/Version Duplicates** (Same functionality, version control)

#### 5. **Multiple .bak/.backup files**
- `emotion_engine.py` + `emotion_engine.py.bak`
- `face_recognition_agent.py` + `face_recognition_agent.py.bak` 
- `model_manager_agent.py` + `model_manager_agent_test.py` + `model_manager_agent_migrated.py`
- `vram_optimizer_agent.py` + `vram_optimizer_agent_day4_optimized.py`

### 🟢 **Machine-Specific Variants** (Different purpose/config)

#### 6. **Health Monitoring**
- `pc2_code/agents/health_monitor.py` (8.6KB)
- `main_pc_code/agents/predictive_health_monitor.py` (61KB)
- **Status**: Different complexity levels, possibly complementary

#### 7. **Performance Monitoring** 
- `pc2_code/agents/performance_monitor.py` (17KB)
- `pc2_code/agents/PerformanceLoggerAgent.py` (15KB)
- **Status**: Different approaches to performance tracking

## Consolidation Strategy

### **Phase 1: Critical Duplicates**
1. **tiered_responder.py** → Merge to `main_pc_code/agents/tiered_responder.py`
2. **remote_connector_agent.py** → Analyze functionality differences, create unified version
3. **tutoring variants** → Consolidate to single `tutoring_agent.py` with feature flags

### **Phase 2: Backup Cleanup**
1. Remove `.bak` files after confirming current versions work
2. Archive backup files to `backups/` directory
3. Maintain only current production versions

### **Phase 3: Machine-Specific Logic**
1. Add `machine_type` configuration parameter 
2. Use feature flags for PC2-specific behaviors
3. Centralize configuration in `config/` directory

## Next Actions
1. ✅ **Diff Analysis**: Compare duplicate implementations 
2. ✅ **Feature Flag Setup**: Create machine-specific configuration
3. ✅ **Merge Implementation**: Start with tiered_responder.py
4. ✅ **Testing**: Validate unified agents work on both machines 