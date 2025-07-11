# Agent & Service Groups (from startup_config.yaml)

This document lists all agents and services defined in your system, grouped according to their logical function as configured in `main_pc_code/config/startup_config.yaml`.

---

## core_services
- **SystemDigitalTwin**
  - Path: `main_pc_code/agents/system_digital_twin.py`
  - Port: 7120 | Health: 8120
  - Dependencies: None
- **RequestCoordinator**
  - Path: `main_pc_code/agents/request_coordinator.py`
  - Port: 26002 | Health: 27002
  - Dependencies: SystemDigitalTwin
- **UnifiedSystemAgent**
  - Path: `main_pc_code/agents/unified_system_agent.py`
  - Port: 7125 | Health: 8125
  - Dependencies: SystemDigitalTwin

## memory_system
- **MemoryClient**
  - Path: `main_pc_code/agents/memory_client.py`
  - Port: 5713 | Health: 6713
  - Dependencies: SystemDigitalTwin
- **SessionMemoryAgent**
  - Path: `main_pc_code/agents/session_memory_agent.py`
  - Port: 5574 | Health: 6574
  - Dependencies: RequestCoordinator, SystemDigitalTwin, MemoryClient
- **KnowledgeBase**
  - Path: `main_pc_code/agents/knowledge_base.py`
  - Port: 5715 | Health: 6715
  - Dependencies: MemoryClient, SystemDigitalTwin

## utility_services
- **CodeGenerator**
  - Path: `main_pc_code/agents/code_generator.py`
  - Port: 5650 | Health: 6650
  - Dependencies: None

## language_processing
- **ModelOrchestrator**
  - Path: `main_pc_code/agents/model_orchestrator.py`
  - Port: 7010 | Health: 8010
  - Dependencies: [Details in config]

## emotion_system
- **EmotionEngine**
  - Path: `main_pc_code/agents/emotion_engine.py`
  - Port: 5590 | Health: 6590
  - Dependencies: [Details in config]

---

**Note:**
- This is an initial grouping. For each group, further documentation will be created (communication, roles, config, etc.).
- If you want a more detailed description per agent, let me know or provide agent docstrings/README references.
