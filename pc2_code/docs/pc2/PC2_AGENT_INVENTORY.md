# PC2 Agent Inventory

This document serves as the authoritative reference for all agents and services related to PC2. It provides a comprehensive inventory, including active services, deprecated components, and moved functionality, to ensure clear system architecture understanding.

*Last Updated: May 31, 2025 - Major architectural update*

## Active Agents & Services (Currently Running on PC2)

### 1. Memory Agent (Consolidated)

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `memory.py` |
| **Primary Responsibility** | All memory-related services including user profiles, reminders, proactive broadcasting, and general memory storage |
| **ZMQ Ports** | 5590 (REP socket for main agent operations)<br>5598 (REP socket for health checks)<br>5595 (PUB socket for proactive event broadcasting) |
| **Bind Address** | 0.0.0.0 (accessible from network) |
| **Key Dependencies** | ZeroMQ, `config/system_config.py` for configuration flags |
| **Config Source** | `config/system_config.py` - `memory.proactive_reminder_broadcast` for enabling/disabling proactive broadcasting |
| **Replaces** | `jarvis_memory_agent.py` (deprecated) and `memory_agent.py` stub (deprecated) |
| **Features** | • User profile management<br>• Reminder storage, listing, and deletion<br>• Proactive event broadcasting (configurable)<br>• Thread-safe operations |

### 2. TranslatorAgent

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `translator_fixed.py` |
| **Primary Responsibility** | Translate Taglish/Filipino commands to English using tiered translation approach (Pattern Matching → NLLB → Google Translate) with confidence scoring |
| **ZMQ Ports** | 5563 (REP socket for Main PC communication) |
| **Bind Address** | 0.0.0.0 (accessible from network) |
| **Key Dependencies** | NLLB Translation Adapter, Google Translate API (fallback) |
| **Config Source** | Primary: `config/system_config.py` - `pc2_settings["model_configs"]["translator-agent-pc2"]`<br>Secondary: Internal constants |
| **GPU Usage** | Indirect (via NLLB adapter) |
| **Confidence Thresholds** | Pattern matching: 0.98<br>NLLB (high): 0.85<br>NLLB (medium): 0.60<br>Low threshold: 0.30<br>Google Translate default: 0.90 |
| **Cache System** | Advanced adaptive caching with hot/warm/cold categorization |
| **Memory Management** | Session-based with compression for inactive sessions |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #17) |

### 2. NLLB Translation Adapter

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `nllb_translation_adapter.py` |
| **Primary Responsibility** | Neural machine translation using Facebook's NLLB model with confidence scores |
| **ZMQ Port** | 5581 (REP) |
| **Bind Address** | 0.0.0.0 (accessible from network) |
| **Key Dependencies** | PyTorch, Transformers, NLLB model (facebook/nllb-200-1.3B) |
| **Config Source** | Primary: `config/system_config.py` - `pc2_settings["model_configs"]["nllb-translation-adapter-pc2"]` |
| **GPU Usage** | Direct (requires CUDA-enabled PyTorch) |
| **Model Size** | ~5GB (facebook/nllb-200-1.3B) |
| **Self-Management** | On-demand loading with idle timeout (configurable, default: 300 seconds) |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #1) |

### 3. TinyLlama Service

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `tinyllama_service_enhanced.py` |
| **Primary Responsibility** | Serve TinyLlama model for lightweight inference tasks |
| **ZMQ Port** | 5615 (REP) |
| **Bind Address** | 0.0.0.0 (accessible from network) |
| **Key Dependencies** | PyTorch, Transformers, TinyLlama model |
| **Config Source** | Primary: `config/system_config.py` - `pc2_settings["model_configs"]["tinyllama-service-pc2"]` |
| **GPU Usage** | Direct (requires CUDA-enabled PyTorch) |
| **Model Size** | ~2.8GB (TinyLlama/TinyLlama-1.1B-Chat-v1.0) |
| **Self-Management** | On-demand loading with idle timeout (configurable) |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #2) |

## Truly Active PC2 Agents

The following agents are also active on PC2 as confirmed by system testing and the PC2_STARTUP_SEQUENCE.md documentation.

### 1. Memory Agent (Base)

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `memory.py` |
| **Primary Responsibility** | Core memory management functionality |
| **ZMQ Port** | 5590 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["memory-agent-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #3) |

### 2. Remote Connector Agent (RCA)

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `remote_connector_agent.py` |
| **Primary Responsibility** | Direct gateway to model services |
| **ZMQ Port** | 5557 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["remote-connector-agent-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #10) |

### 3. Task Router Agent

| Property | Value |
|----------|-------|
| **Status** | ⚠️ DEPRECATED - Replaced by Enhanced Model Router |
| **Filename** | `task_router_agent.py` |
| **Former Port** | 5558 (REP) |
| **Former Responsibility** | Route tasks to appropriate models based on task type |
| **Notes** | Listed as deprecated in COMPLETE_AGENTS_LIST.txt. Functionality consolidated in Enhanced Model Router |

### 5. Enhanced Model Router (EMR)

### 6. Chain of Thought Agent (CoT)

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `chain_of_thought_agent.py` |
| **Primary Responsibility** | Multi-step reasoning capability |
| **ZMQ Port** | 5612 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["chain-of-thought-agent-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #11) |

### 7. Memory Agent (Base)

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `memory.py` |
| **Primary Responsibility** | Core memory management functionality |
| **ZMQ Port** | 5590 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["memory-agent-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #3) |

### 8. Contextual Memory Agent

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `contextual_memory_agent.py` |
| **Primary Responsibility** | Context management and advanced summarization |
| **ZMQ Port** | 5596 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["contextual-memory-agent-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #4) |

### 9. Digital Twin Agent

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `digital_twin_agent.py` |
| **Primary Responsibility** | User modeling and behavioral analysis |
| **ZMQ Port** | 5597 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["digital-twin-agent-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #5) |

### 10. Jarvis Memory Agent

| Property | Value |
|----------|-------|
| **Status** | ❌ DEPRECATED - REPLACED BY MEMORY AGENT |
| **Filename** | `jarvis_memory_agent.py` (MOVED TO `agents/Deprecated/`) |
| **Primary Responsibility** | ~~Long-term memory services~~ All functionality consolidated into `memory.py` |
| **ZMQ Port** | ~~5598 (REP)~~ Functionality now on port 5590 with `memory.py` |
| **Config Source** | `config/system_config.py` - Reminder broadcast controlled by `memory.proactive_reminder_broadcast` |
| **Reference in Overview** | This agent is deprecated - see Memory Agent entry |

### 11. Learning Mode Agent

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `learning_mode_agent.py` |
| **Primary Responsibility** | System adaptation and continuous learning |
| **ZMQ Port** | 5599 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["learning-mode-agent-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #7) |

### 12. Error Pattern Memory

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `error_pattern_memory.py` |
| **Primary Responsibility** | Tracks error patterns and solutions |
| **ZMQ Port** | 5611 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["error-pattern-memory-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #8) |

### 13. Self-Healing Agent

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `self_healing_agent.py` |
| **Primary Responsibility** | System health monitoring and recovery |
| **ZMQ Ports** | 5614 (REP), 5616 (PUB) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["self-healing-agent-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #12) |

### 14. Enhanced Web Scraper

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `enhanced_web_scraper.py` |
| **Primary Responsibility** | Web content retrieval |
| **ZMQ Port** | 5602 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["enhanced-web-scraper-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #13) |

### 15. Autonomous Web Assistant

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `autonomous_web_assistant.py` |
| **Primary Responsibility** | Web-based research and tasks |
| **ZMQ Port** | 5604 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["autonomous-web-assistant-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #14) |

### 16. Filesystem Assistant Agent

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE ON PC2 |
| **Filename** | `filesystem_assistant_agent.py` |
| **Primary Responsibility** | File operations and management |
| **ZMQ Port** | 5606 (REP) |
| **Config Source** | `config/system_config.py` - `pc2_settings["model_configs"]["filesystem-assistant-agent-pc2"]` |
| **Reference in Overview** | Listed in PC2_AGENTS_LIST.txt (item #15) |

### 16. Context Summarizer Agent

| Property | Value |
|----------|-------|
| **Status** | ⚠️ DEPRECATED - Legacy component |
| **Filename** | `context_summarizer.py` |
| **Former Port** | 5595 (REP) |
| **Former Responsibility** | Generate summaries of context |
| **Notes** | Functionality merged into Contextual Memory Agent (Port 5596) |

### 17. LLM Translation Adapter

| Property | Value |
|----------|-------|
| **Status** | ⚠️ DEPRECATED - Replaced by NLLB Translation Adapter |
| **Filename** | `llm_translation_adapter.py` |
| **Former Port** | 5581 (REP) |
| **Notes** | Early version of translation adapter. Same port now used by NLLB Translation Adapter |

### 18. Original Translator Agent

| Property | Value |
|----------|-------|
| **Status** | ⚠️ DEPRECATED - Replaced by translator_fixed.py |
| **Filename** | `translator_agent.py` |
| **Former Ports** | 5563 (REP), 5561 (SUB), 5559 (Health) |
| **Former Responsibility** | Original implementation of Taglish translation |
| **Notes** | Replaced by enhanced fixed version (translator_fixed.py) |

### 19. TinyLlama Service Alternatives

| Property | Value |
|----------|-------|
| **Status** | ⚠️ DEPRECATED - Replaced by enhanced version |
| **Filenames** | `tinyllama_service.py`, `tinyllama_service_ollama_backup.py` |
| **Former Port** | 5615 (REP) |
| **Former Responsibility** | Alternative TinyLlama service implementations |
| **Notes** | Replaced by `tinyllama_service_enhanced.py` |

### 20. Code Generator & Executor Agents

| Property | Value |
|----------|-------|
| **Status** | ⚠️ MOVED TO MAIN PC |
| **Filenames** | `code_generator_agent.py`, `executor_agent.py`, `progressive_code_generator.py`, `auto_fixer_agent.py` |
| **Former Ports** | Various (now 6000-6004 on Main PC) |
| **Former Responsibility** | Code generation and execution |
| **Notes** | Developer/Execution agents moved to Main PC as noted in PORTS_CONFIGURATION.md |

## Utility Scripts & Test Files (NOT Agents, but Present in PC2)

### 1. CUDA/GPU Check Utilities

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE UTILITIES |
| **Filenames** | `check_gpu.py`, `check_pytorch_cuda.py`, `simple_gpu_check.py` |
| **Responsibility** | Verify CUDA and GPU availability for PyTorch models |
| **Notes** | Used for diagnostics, not running services |

### 2. Translation Test Utilities

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE UTILITIES |
| **Filenames** | `simple_translator_test.py`, `standalone_translator_test.py`, `pub_translator_test.py` |
| **Responsibility** | Test translation functionality |
| **Notes** | Used for diagnostics and testing, not running services |

### 3. Other Utility Scripts

| Property | Value |
|----------|-------|
| **Status** | ✅ ACTIVE UTILITIES |
| **Filenames** | `agent_utils.py`, `check_llm_adapter.py`, `test_main_pc_socket.py`, `test_self_healing.py`, `test_translator_agent.py`, `translation_normalization.py` |
| **Responsibility** | Various utility functions and test scripts |
| **Notes** | Used for development, testing and maintenance |

## Configuration Sources

All PC2 components now primarily source their configuration from:

1. **Primary Source**: `config/system_config.py` which contains:
   - ZMQ port and bind address information
   - Model paths and parameters
   - Confidence thresholds for translation
   - Resource management settings (timeout, cache limits)

2. **Historical Reference**: `AI LATEST OVERVIEW/PC2_AGENTS_LIST.txt` contains the original intended architecture, much of which has been moved or deprecated.

## Health Check Mechanisms

- All active PC2 services now support the `health_check` action via their main ZMQ ports
- Dedicated health check port (5559) for TranslatorAgent has been DEPRECATED
- Main PC MMA now monitors all PC2 services through their primary ZMQ ports

## Discrepancies Between Documentation and Current State

The significant differences between the architecture described in `AI LATEST OVERVIEW` and the current active components are due to a major restructuring where:

1. Most agents were moved from PC2 to Main PC for centralized control
2. Only three essential services remain active on PC2 (TranslatorAgent, NLLB Adapter, TinyLlama)
3. The health check mechanism was simplified to use main service ports
