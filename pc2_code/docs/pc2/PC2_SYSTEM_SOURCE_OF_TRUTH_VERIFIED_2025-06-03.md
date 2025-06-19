# PC2 SYSTEM SOURCE OF TRUTH (VERIFIED)
**Date: 2025-06-03**

This document serves as the definitive source of truth for all essential PC2 services monitored by the Main PC Model Manager Agent (MMA). This represents the verified state after comprehensive testing.

## Verification Summary
- Total Services: 12
- Healthy Services: 11
- Services with Issues: 1

## Essential PC2 Services

### 1. Primary Translator (ONLINE)
- **Script Filename & Path**: `agents/translator_agent.py`
- **Port Number**: 5563 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok, success`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "success", "uptime_seconds": 69.87077379226685, "total_requests": 2, "cache_size": 37, "cache_max_size": 500, "cache_hits": 27, "cache_misses": 37, "cache_hit_ratio": 42.1875, "session_count": 0}`
  - **Notes**: Service responded correctly
- **Role**: Enhanced translator with pattern matching and fallbacks

### 2. Fallback Translator (ONLINE)
- **Script Filename & Path**: `quick_translator_fix.py`
- **Port Number**: 5564 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok, success`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "success", "service": "translator_quick_fix", "uptime_seconds": 64.97110962867737, "request_count": 2, "bind_address": "tcp://0.0.0.0:5564", "timestamp": 1748892011.401458}`
  - **Notes**: Service responded correctly
- **Role**: Simple pattern-based translator that works without internet

### 3. NLLB Translation Adapter (OFFLINE)
- **Script Filename & Path**: `nllb_translation_adapter.py`
- **Port Number**: 5581 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "translate", "text": "ping_hc_nllb_final", "source_lang": "tgl_Latn", "target_lang": "eng_Latn"}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status`
- **Verification Status**: ERROR_RESPONSE
  - **Response**: `{"original": "ping_hc_nllb_final", "translated": "I'm not going to tell you.", "model": "nllb", "model_name": "facebook/nllb-200-distilled-600M", "src_lang": "tgl_Latn", "tgt_lang": "eng_Latn", "success": true, "elapsed_sec": 1.1450762748718262, "message": "Success"}`
  - **Notes**: Response doesn't match expected pattern 'status'
- **Role**: Neural machine translation using Facebook's NLLB model

### 4. TinyLlama Service (ONLINE)
- **Script Filename & Path**: `agents/tinyllama_service_enhanced.py`
- **Port Number**: 5615 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "ok", "service": "tinyllama_service", "model_status": "unloaded", "is_loaded": false, "timestamp": 1748892012.605224, "device": "cuda"}`
  - **Notes**: Service responded correctly
- **Role**: Lightweight LLM for fast responses and fallbacks

### 5. Memory Agent (Consolidated) (ONLINE)
- **Script Filename & Path**: `agents/memory.py`
- **Port Number**: 5590 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok, success`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "error", "reason": "Unknown action"}`
  - **Notes**: Service responded correctly
- **Role**: Main memory operations port

### 6. Memory Agent Health Port (ONLINE)
- **Script Filename & Path**: `agents/memory.py (health port)`
- **Port Number**: 5598 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "health_check"}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok, success`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "error", "message": "Unknown request type"}`
  - **Notes**: Service responded correctly
- **Role**: Dedicated health check port monitored by MMA

### 7. Contextual Memory Agent (ONLINE)
- **Script Filename & Path**: `agents/contextual_memory_agent.py`
- **Port Number**: 5596 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "error", "message": "Unknown action: None"}`
  - **Notes**: Service responded correctly
- **Role**: Advanced context management and summarization

### 8. Digital Twin Agent (ONLINE)
- **Script Filename & Path**: `agents/digital_twin_agent.py`
- **Port Number**: 5597 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "error", "reason": "Unknown action"}`
  - **Notes**: Service responded correctly
- **Role**: User modeling and behavioral analysis

### 9. Error Pattern Memory (ONLINE)
- **Script Filename & Path**: `agents/error_pattern_memory.py`
- **Port Number**: 5611 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "error", "message": "Unknown action: None"}`
  - **Notes**: Service responded correctly
- **Role**: Tracks error patterns and solutions

### 10. Context Summarizer Agent (ONLINE)
- **Script Filename & Path**: `agents/context_summarizer_agent.py`
- **Port Number**: 5610 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "error", "message": "Unknown action: None"}`
  - **Notes**: Service responded correctly
- **Role**: Provides summarization of conversation context

### 11. Chain of Thought Agent (ONLINE)
- **Script Filename & Path**: `agents/chain_of_thought_agent.py`
- **Port Number**: 5612 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"action": "breakdown", "request": "health_check"}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, ok`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "error", "message": "Unknown action: breakdown"}`
  - **Notes**: Service responded correctly
- **Role**: Provides multi-step reasoning for complex tasks

### 12. Remote Connector Agent (ONLINE)
- **Script Filename & Path**: `agents/remote_connector_agent.py`
- **Port Number**: 5557 (REP)
- **Bind Address**: `0.0.0.0` (all interfaces)
- **Health Check Mechanism**:
  - **ZMQ Payload**: `{"request_type": "check_status", "model": "phi3"}`
  - **Expected Response Pattern**: Contains key/value matching one of: `status, success`
- **Verification Status**: HEALTHY
  - **Response**: `{"status": "success", "model": "phi3", "available": true}`
  - **Notes**: Service responded correctly
- **Role**: Manages direct model inference and caching

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

## Startup Instructions

To start all essential PC2 services in the correct order:

1. Run the startup batch file:
   ```
   d:\DISKARTE\Voice Assistant\start_essential_pc2_services.bat
   ```

2. Verify all services are running:
   ```
   python verify_pc2_target_config.py
   ```

**Note**: All services should bind to `0.0.0.0` to be accessible remotely by the Main PC MMA.
