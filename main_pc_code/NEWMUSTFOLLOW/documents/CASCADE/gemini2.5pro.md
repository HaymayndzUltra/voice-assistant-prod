# Project Log: Operation Build Lean MainPC Docker Environment

## Task: Generate Definitive MainPC Build Context via Active Agent Dependency Tracing

**Date:** 2025-07-12

**Objective:** To generate the definitive, final, and minimal list of all required directories for the MainPC Docker build by performing a recursive dependency trace starting only from the active agents defined in the MainPC startup configuration.

**Summary of Execution:**

1.  **Identified Active Agents:** Parsed the `main_pc_code/config/startup_config.yaml` file to extract the full list of agent script paths, forming the initial set for analysis.
2.  **Recursive Dependency Trace:** Executed a custom Python script (`dependency_tracer.py`) that uses Python's `ast` module for static analysis. This script recursively traced all `import` statements from the initial agent set to identify all dependent local modules and files.
3.  **Generated Directory List:** Consolidated the exhaustive list of required files into a minimal set of parent directories necessary for the Docker build context.

**Results:**

The analysis produced a definitive list of directories required for the `COPY` instructions in the Dockerfile, ensuring a lean and efficient build.

### Final MainPC Build Context Report

**Analyzed Active Agent Scripts:**
- `main_pc_code/agents/system_digital_twin.py`
- `main_pc_code/agents/request_coordinator.py`
- `main_pc_code/agents/unified_system_agent.py`
- `main_pc_code/agents/memory_client.py`
- `main_pc_code/agents/session_memory_agent.py`
- `main_pc_code/agents/knowledge_base.py`
- `main_pc_code/agents/code_generator.py`
- `main_pc_code/FORMAINPC/SelfTrainingOrchestrator.py`
- `main_pc_code/agents/predictive_health_monitor.py`
- `main_pc_code/agents/fixed_streaming_translation.py`
- `main_pc_code/agents/executor.py`
- `main_pc_code/FORMAINPC/TinyLlamaServiceEnhanced.py`
- `main_pc_code/FORMAINPC/LocalFineTunerAgent.py`
- `main_pc_code/FORMAINPC/NLLBAdapter.py`
- `main_pc_code/agents/gguf_model_manager.py`
- `main_pc_code/agents/model_manager_agent.py`
- `main_pc_code/agents/vram_optimizer_agent.py`
- `main_pc_code/agents/predictive_loader.py`
- `main_pc_code/FORMAINPC/ChainOfThoughtAgent.py`
- `main_pc_code/FORMAINPC/GOT_TOTAgent.py`
- `main_pc_code/FORMAINPC/CognitiveModelAgent.py`
- `main_pc_code/agents/face_recognition_agent.py`

**Definitive List of Required Directories (Copy-Friendly):**
```
common/core
common/utils
common_utils
main_pc_code/FORMAINPC
main_pc_code/agents
main_pc_code/config
main_pc_code/src/core
main_pc_code/utils
utils
```

**Next Step:** Proceed with creating the lean Dockerfile for the MainPC environment using this verified build context.
