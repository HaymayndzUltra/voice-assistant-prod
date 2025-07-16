# O3 PHASE 2 IMPLEMENTATION COMMANDS
**Execute these commands in exact order - DO NOT SKIP ANY STEP**

## STEP 1: CREATE DIRECTORY STRUCTURE
```bash
mkdir -p phase2_implementation/consolidated_agents/memory_hub
mkdir -p phase2_implementation/consolidated_agents/model_manager_suite  
mkdir -p phase2_implementation/consolidated_agents/adaptive_learning_suite
mkdir -p phase2_implementation/configs
mkdir -p phase2_implementation/tests
mkdir -p phase2_implementation/scripts
```

## STEP 2: IMPLEMENT MEMORY HUB (Port 7010)
Create these files with COMPLETE implementations:

1. `phase2_implementation/consolidated_agents/memory_hub/__init__.py`
2. `phase2_implementation/consolidated_agents/memory_hub/memory_hub.py` - Main FastAPI service
3. `phase2_implementation/consolidated_agents/memory_hub/redis_manager.py` - Multi-DB Redis handler
4. `phase2_implementation/consolidated_agents/memory_hub/sqlite_manager.py` - Persistent storage
5. `phase2_implementation/consolidated_agents/memory_hub/search_engine.py` - Vector embeddings
6. `phase2_implementation/consolidated_agents/memory_hub/session_manager.py` - Session lifecycle

**REQUIRED FEATURES:**
- FastAPI with routes: `/kv/{key}`, `/doc/{doc_id}`, `/embedding/{query}`, `/session/{session_id}`, `/context/{context_id}`
- Redis multi-database setup (db0=cache, db1=sessions, db2=knowledge)
- SQLite tables: memories, sessions, knowledge_base, contexts
- Health endpoint on port 7110
- Prometheus metrics integration
- Error handling with ErrorBusSuite
- All legacy agent compatibility layers

## STEP 3: IMPLEMENT MODEL MANAGER SUITE (Port 7011) 
Create these files with COMPLETE implementations:

1. `phase2_implementation/consolidated_agents/model_manager_suite/__init__.py`
2. `phase2_implementation/consolidated_agents/model_manager_suite/model_manager_suite.py` - Main service
3. `phase2_implementation/consolidated_agents/model_manager_suite/gguf_manager.py` - GGUF model handling
4. `phase2_implementation/consolidated_agents/model_manager_suite/predictive_loader.py` - Smart pre-loading
5. `phase2_implementation/consolidated_agents/model_manager_suite/evaluation_framework.py` - Model evaluation

**REQUIRED FEATURES:**
- FastAPI with routes: `/models`, `/models/{id}/load`, `/models/{id}/unload`, `/evaluate/{model_id}`, `/predict/{model_id}`
- GGUF model registry with metadata
- GPU resource coordination with ResourceManagerSuite
- Lockfile mechanism for hot-swaps
- Health endpoint on port 7111
- VRAM quota enforcement
- All legacy agent compatibility (GGUFModelManager, ModelManagerAgent, PredictiveLoader, ModelEvaluationFramework)

## STEP 4: IMPLEMENT ADAPTIVE LEARNING SUITE (Port 7012)
Create these files with COMPLETE implementations:

1. `phase2_implementation/consolidated_agents/adaptive_learning_suite/__init__.py`
2. `phase2_implementation/consolidated_agents/adaptive_learning_suite/adaptive_learning_suite.py` - Main service
3. `phase2_implementation/consolidated_agents/adaptive_learning_suite/training_orchestrator.py` - Training pipeline
4. `phase2_implementation/consolidated_agents/adaptive_learning_suite/lora_finetuner.py` - LoRA implementation
5. `phase2_implementation/consolidated_agents/adaptive_learning_suite/learning_monitor.py` - Performance tracking

**REQUIRED FEATURES:**
- FastAPI with routes: `/training/start`, `/training/{id}/stop`, `/training/{id}/status`, `/opportunities`, `/evaluate/performance`
- LoRA/QLoRA fine-tuning capability
- Continual learning scheduler
- GPU resource coordination
- Health endpoint on port 7112
- All legacy agent compatibility (7 agents consolidated)

## STEP 5: UPDATE STARTUP CONFIGURATIONS

### Update MainPC config:
File: `main_pc_code/config/startup_config.yaml`
Add Phase 2 services section:
```yaml
# Phase 2 Services
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
```

### Update PC2 config:
File: `pc2_code/config/startup_config.yaml`
Add Phase 2 services section:
```yaml
# Phase 2 Services  
memory_hub:
  enabled: true
  port: 7010
  health_port: 7110
  startup_order: 2
  dependencies: ["core_orchestrator", "security_gateway"]
```

## STEP 6: CREATE CONFIGURATION FILES
1. `phase2_implementation/configs/memory_hub_config.yaml` - Redis/SQLite settings
2. `phase2_implementation/configs/model_manager_config.yaml` - Model registry settings
3. `phase2_implementation/configs/learning_suite_config.yaml` - Training parameters

## STEP 7: CREATE MIGRATION SCRIPTS
1. `phase2_implementation/scripts/migrate_legacy_data.py` - Data migration from legacy agents
2. `phase2_implementation/scripts/verify_migration.py` - Migration verification
3. `phase2_implementation/scripts/rollback_migration.py` - Rollback capability

## STEP 8: CREATE HEALTH CHECK ENDPOINTS
Each service MUST have:
- `/health` endpoint returning status
- `/metrics` endpoint for Prometheus
- `/version` endpoint with service info
- Proper HTTP status codes (200, 503, etc.)

## STEP 9: ADD ERROR HANDLING INTEGRATION
- Import ErrorBusSuite client in each service
- Send errors to NATS on port 9003
- Implement retry logic with exponential backoff
- Add structured logging

## STEP 10: CREATE BACKWARD COMPATIBILITY LAYERS
Each consolidated service MUST maintain:
- Original REST endpoints from legacy agents
- Same response formats
- Compatible authentication
- Graceful degradation

## CRITICAL IMPLEMENTATION REQUIREMENTS:

### IMPORTS TO INCLUDE:
```python
# Standard libraries
import asyncio, json, logging, sqlite3, redis, uuid, threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# FastAPI and related
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

# ML/AI libraries  
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer
import sentence_transformers

# Monitoring
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Database
import sqlalchemy
from sqlalchemy.orm import sessionmaker
```

### ERROR HANDLING TEMPLATE:
```python
try:
    # Implementation logic
    pass
except Exception as e:
    logger.error(f"Error in {operation}: {str(e)}")
    await error_bus.publish_error(
        service="memory_hub",
        error_type=type(e).__name__,
        message=str(e),
        context={"operation": operation}
    )
    raise HTTPException(status_code=500, detail=str(e))
```

### HEALTH CHECK TEMPLATE:
```python
@app.get("/health")
async def health_check():
    try:
        # Check database connections
        redis_ok = await redis_client.ping()
        sqlite_ok = sqlite_connection.execute("SELECT 1").fetchone() is not None
        
        if redis_ok and sqlite_ok:
            return {"status": "healthy", "timestamp": datetime.utcnow()}
        else:
            return {"status": "unhealthy"}, 503
    except Exception as e:
        return {"status": "error", "message": str(e)}, 503
```

## SUCCESS CRITERIA CHECKLIST:
- [ ] All 3 services start on correct ports
- [ ] Health endpoints return 200 OK
- [ ] Database connections established
- [ ] Legacy API compatibility maintained
- [ ] Error reporting functional
- [ ] Prometheus metrics exposed
- [ ] Resource management integrated
- [ ] All original functionality preserved

**TOTAL ESTIMATED CODE:** ~3500+ lines
**CONSOLIDATION TARGET:** 23 agents → 3 services
**PORTS:** 7010 (MemoryHub), 7011 (ModelManagerSuite), 7012 (AdaptiveLearningSuite)

## FINAL VERIFICATION COMMAND:
After implementation, run comprehensive health check across all Phase 2 services to ensure 100% functionality preservation. 