# PHASE 0 - GROUP 2: RESOURCE & SCHEDULING LAYER
**Consolidation Group: Resource & Scheduling Layer (7 agents → 2)**

## 🎯 TARGET SERVICES

### ResourceManagerSuite (Port 9001, PC2)
**Source Agents:**
- ResourceManager
- TaskScheduler
- AsyncProcessor  
- VRAMOptimizerAgent

**Notes:**
- Controls MainPC via NVML
- PC2 controls MainPC GPU resources

### ErrorBus (Port 9002, PC2)
**Source Agents:**
- ErrorBus (retains NATS)

**Notes:**
- Becomes side-car in ResourceManagerSuite
- Maintains NATS on port 9002

## ⚠️ RISKS & MITIGATIONS
- **Risk:** GPU over-commit on RTX 4090 under concurrent infer/fine-tune
- **Mitigation:** ResourceManager enforces semaphore; VRAMOptimizer thread inside ModelManagerSuite

## 📁 STATUS: PLACEHOLDER - IMPLEMENTATION GUIDE NEEDED 