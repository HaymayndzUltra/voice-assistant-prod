# PC2 SYSTEM SOURCE OF TRUTH (FINAL)
**Date: June 2, 2025**

This document serves as the definitive source of truth for all essential PC2 services monitored by the Main PC Model Manager Agent (MMA). This represents the final state after memory agent consolidation and translator service fixes.

## Essential PC2 Services (11)

### 1. Primary Translator
- **Official Service Name / Model ID**: `translator-agent-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/agents/translator_simple.py`
- **Final Confirmed ZMQ Port Number**: 5563 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Primary Filipino/English bidirectional translator with caching
- **Notes**: Uses Google Translate API with fallback to pattern matching. Requires internet connection for best results.

### 2. Fallback Translator
- **Official Service Name / Model ID**: `fallback-translator-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/quick_translator_fix.py`
- **Final Confirmed ZMQ Port Number**: 5564 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Backup/fallback translator service with basic pattern matching capabilities
- **Notes**: Runs when primary translator fails. Simple pattern-based translator that works without internet.

### 3. NLLB Translation Adapter
- **Official Service Name / Model ID**: `nllb-adapter-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/nllb_adapter.py`
- **Final Confirmed ZMQ Port Number**: 5581 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Neural machine translation using Facebook's NLLB model
- **Notes**: Uses Hugging Face transformers and the NLLB-200-distilled-600M model. Requires ~2GB VRAM.

### 4. TinyLlama Service
- **Official Service Name / Model ID**: `tinyllama-service-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/agents/tinyllama_service_enhanced.py`
- **Final Confirmed ZMQ Port Number**: 5615 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Lightweight LLM for fast responses and fallbacks
- **Notes**: Uses TinyLlama-1.1B-Chat-v1.0 model, optimized for speed and low VRAM usage (~1.5GB).

### 5. Memory Agent (Consolidated)
- **Official Service Name / Model ID**: `memory-agent-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/agents/memory.py`
- **Final Confirmed ZMQ Port Numbers**: 
  - Main Port: 5590 (REP) - for memory operations
  - Health Port: 5598 (REP) - for health checks
  - PUB Port: 5595 (PUB) - for proactive reminder broadcasting
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload to Port 5598**: `{"action": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Core memory management including user profiles, reminders, and proactive broadcasting
- **Notes**: Consolidated from previous `jarvis_memory_agent.py` and `memory_agent.py`. Proactive reminder broadcasting can be toggled via `memory.proactive_reminder_broadcast` in `system_config.py`.

### 6. Contextual Memory Agent
- **Official Service Name / Model ID**: `contextual-memory-agent-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/agents/contextual_memory_agent.py`
- **Final Confirmed ZMQ Port Number**: 5596 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Advanced context management and summarization
- **Notes**: Incorporates previous Context Summarizer functionality. Uses LLM to maintain conversation context.

### 7. Digital Twin Agent
- **Official Service Name / Model ID**: `digital-twin-agent-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/agents/digital_twin_agent.py`
- **Final Confirmed ZMQ Port Number**: 5597 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: User modeling and behavioral analysis
- **Notes**: Maintains user preferences, habits, and long-term memory patterns.

### 8. Error Pattern Memory
- **Official Service Name / Model ID**: `error-pattern-memory-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/agents/error_pattern_memory.py`
- **Final Confirmed ZMQ Port Number**: 5611 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Tracks error patterns and solutions
- **Notes**: Used for system self-healing and recurrent issue detection.

### 9. Context Summarizer Agent
- **Official Service Name / Model ID**: `context-summarizer-agent-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/agents/context_summarizer_agent.py`
- **Final Confirmed ZMQ Port Number**: 5610 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Provides summarization of conversation context
- **Notes**: Works in conjunction with Contextual Memory Agent to maintain coherent conversation flow.

### 10. Chain of Thought Agent (PC2 CoT)
- **Official Service Name / Model ID**: `cot-agent-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/agents/chain_of_thought_agent.py`
- **Final Confirmed ZMQ Port Number**: 5612 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "breakdown", "request": "health_check"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Provides multi-step reasoning for complex tasks
- **Notes**: Used for breaking down complex problems into simpler steps. Different health check payload format.

### 11. Remote Connector Agent (RCA)
- **Official Service Name / Model ID**: `rca-agent-pc2`
- **Script Filename & Path**: `d:/DISKARTE/Voice Assistant/agents/remote_connector_agent.py`
- **Final Confirmed ZMQ Port Number**: 5557 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"request_type": "check_status", "model": "phi3"}`
  - **Expected Healthy Response**: `{"status": "success", ...}`
- **Role**: Manages direct model inference and caching
- **Notes**: Unique health check payload format with "request_type" instead of "action".

## Deprecated or Non-Essential Services

The following services exist but are not part of the essential PC2 services monitored by the Main PC MMA:

### Bark TTS Agent
- **Status**: Deprecated, functionality moved to Main PC XTTS
- **Former Port**: 5562
- **Notes**: Text-to-speech capabilities now centralized on Main PC

### Filesystem Assistant Agent
- **Status**: Non-essential
- **Port**: 5594
- **Notes**: Not currently part of essential MMA-monitored services

### Jarvis Memory Agent
- **Status**: Deprecated, consolidated into memory.py
- **Former Port**: 5598
- **Notes**: Functionality fully merged into the consolidated Memory Agent

---

## Health Check Summary

To verify all services are running properly, use the `health_check_pc2.py` script or check each service individually using the appropriate ZMQ payload.

## Starting Essential Services

For consistent PC2 service startup, use the `start_essential_pc2_services.bat` script which launches all essential services with the correct parameters.
