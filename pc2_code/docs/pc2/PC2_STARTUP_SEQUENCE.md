# PC2 Startup Sequence

This document outlines the recommended startup sequence for active PC2 components. Following this sequence ensures proper initialization and dependency resolution.

## Pre-Startup Check

### 1. Verify CUDA Availability

```bash
python agents/check_pytorch_cuda.py
```

This script verifies that PyTorch can access CUDA GPU resources, which are required for optimal performance of the translation and language model services.

**Expected Output:** Should confirm CUDA is available and show the GPU device(s) available for use.

## Complete PC2 Startup Sequence

### Group 1: Base Services (Start First)

#### 1. NLLB Translation Adapter

```bash
python agents/nllb_translation_adapter.py
```

**Rationale:** The NLLB Translation Adapter should be started first because:
- It has no dependencies on other PC2 services
- It requires significant time for initial model loading (~5GB model)
- The TranslatorAgent depends on it for high-quality translations

**Verification:** Wait until you see the log message: `"NLLB Translation Adapter bound to tcp://0.0.0.0:5581"` followed by model loading completion message.

#### 2. TinyLlama Service

```bash
python agents/tinyllama_service_enhanced.py
```

**Rationale:** The TinyLlama Service should be started second because:
- It has no dependencies on other PC2 services
- It's used independently from the TranslatorAgent
- It serves as a complementary AI service for PC2

**Verification:** Wait until you see the log message: `"TinyLlama Service bound to tcp://0.0.0.0:5615"` and any initial model loading messages if it's configured to pre-load the model.

### Group 2: Memory Services (Start Second)

#### 3. Memory Agent (Base)

```bash
python agents/memory.py
```

**Rationale:** The base Memory Agent provides core memory services needed by other memory-related agents.

**Verification:** Confirm successful binding to port 5590.

#### 4. Memory Agent (Consolidated)

```bash
python agents/memory.py
```

**Verification:** 
- Confirm successful binding to port 5590 (main REP socket)
- Confirm successful binding to port 5598 (health check socket) 
- Confirm successful binding to port 5595 (proactive event PUB socket)

> **Note:** Jarvis Memory Agent (`jarvis_memory_agent.py`) is DEPRECATED. All reminder functionality and proactive broadcasting has been consolidated into the Memory Agent (`memory.py`).

#### 5. Contextual Memory Agent

```bash
python agents/contextual_memory_agent.py
```

**Verification:** Confirm successful binding to port 5596.

#### 6. Digital Twin Agent

```bash
python agents/digital_twin_agent.py
```

**Verification:** Confirm successful binding to port 5597.

#### 7. Error Pattern Memory

```bash
python agents/error_pattern_memory.py
```

**Verification:** Confirm successful binding to port 5611.

### Group 3: Router and Core Services (Start Third)

#### 8. Enhanced Model Router

```bash
python agents/enhanced_model_router.py
```

**Rationale:** The Enhanced Model Router is a central hub for routing requests to appropriate agents.

**Verification:** Confirm successful binding to ports 7602 (REP) and 7701 (PUB).

#### 9. Remote Connector Agent

```bash
python agents/remote_connector_agent.py
```

**Verification:** Confirm successful binding to port 5557.

#### 10. Chain of Thought Agent

```bash
python agents/chain_of_thought_agent.py
```

**Verification:** Confirm successful binding to port 5612.

### Group 4: Utility Services (Start Fourth)

#### 11. Learning Mode Agent

```bash
python agents/learning_mode_agent.py
```

**Verification:** Confirm successful binding to port 5599.

#### 12. Enhanced Web Scraper

```bash
python agents/enhanced_web_scraper.py
```

**Verification:** Confirm successful binding to port 5602.

#### 13. Autonomous Web Assistant

```bash
python agents/autonomous_web_assistant.py
```

**Verification:** Confirm successful binding to port 5604.

#### 14. Filesystem Assistant Agent

```bash
python agents/filesystem_assistant_agent.py
```

**Verification:** Confirm successful binding to port 5606.

### Group 5: Monitoring Services (Start Fifth)

#### 15. Self-Healing Agent

```bash
python agents/self_healing_agent.py
```

**Verification:** Confirm successful binding to ports 5614 (REP) and 5616 (PUB).

### Group 6: Translation Interface (Start Last)

#### 16. TranslatorAgent

```bash
python agents/translator_fixed.py
```

**Rationale:** The TranslatorAgent should be started last because:
- It depends on the NLLB Translation Adapter
- It integrates multiple translation services
- It's the primary interface for Main PC communication

**Verification:** Wait until you see the log message: `"TranslatorAgent bound to tcp://0.0.0.0:5563"` and `"TranslatorAgent initialized successfully"`.

### Automated Startup Script

To simplify the startup process, you can use the following script:

```bash
python scripts/start_pc2_services.py
```

This script will start all services in the correct order and verify their proper initialization.

## Health Check Verification

After starting all services, you should verify their health from Main PC using the Model Manager Agent's health check functionality:

```bash
# Run this on Main PC
python scripts/check_pc2_services.py
```

All services should report "healthy" status. Alternatively, you can manually test each service by sending health check requests to their respective ZMQ ports.

## Important Notes

1. **DO NOT start any truly deprecated agents** - The following agents should NOT be started on PC2 as they are truly deprecated or replaced:
   - PC2 Model Manager Agent (replaced by Main PC MMA)
   - Original Translator Agent (replaced by translator_fixed.py)
   - Context Summarizer Agent (functionality merged into Contextual Memory Agent)
   - Original TinyLlama Service variants (replaced by enhanced version)
   - LLM Translation Adapter (replaced by NLLB Translation Adapter)
   
   NOTE: All other agents in the PC2_AGENTS_LIST.txt are ACTIVE and should be started according to their dependency groups

2. **On-Demand Loading:** Both the NLLB Adapter and TinyLlama Service implement on-demand loading of their AI models, so they may not load their models until the first request. The first translation or inference request will take longer to process.

3. **Idle Timeout:** Both model services have idle timeout features to unload models after periods of inactivity (default: 600 seconds). This is normal behavior to conserve GPU memory.

4. **Configuration Source:** All services now read their configuration from `config/system_config.py`. Modify this file if you need to change ports, bind addresses, or other settings.

5. **Network Connectivity:** All services now bind to 0.0.0.0 (all network interfaces) to allow Main PC to connect to them over the network. Ensure firewall settings allow traffic on the necessary ports (5563, 5581, 5615).
