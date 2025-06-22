# PC2 SYSTEM SOURCE OF TRUTH (June 2, 2025)

This document serves as the definitive reference for PC2 services and configurations. It supersedes all previous PC2 documentation and should be used as the authoritative reference by Main PC. Last updated with official health check verification from Main PC MMA (June 2, 2025).

## System Architecture Overview

The voice assistant system operates across two physical machines:
- **Main PC**: Acts as the central orchestrator with the Model Manager Agent (MMA) as the primary control hub
- **PC2**: Provides specialized translation, memory, and reasoning capabilities to support Main PC

## ACTIVE SERVICES (CONFIRMED OPERATIONAL)

The following services are confirmed healthy and operational based on the latest Main PC MMA health check report:

| Service Name | File | Port | Bind Address | Status | Health Check Protocol | Response |
|--------------|------|------|--------------|--------|----------------------|----------|
| **Translator Agent** | `translator_agent.py` | 5563 | 0.0.0.0 | ✅ HEALTHY | `"health_check"` | `{"status": "success", ...}` |
| **NLLB Translation Adapter** | `nllb_translation_adapter.py` | 5581 | 0.0.0.0 | ✅ HEALTHY | `{"action": "translate", "text": "hello", "source": "en", "target": "fr"}` | `{"status": "success", ...}` |
| **TinyLlama Service** | `tinyllama_service_enhanced.py` | 5615 | 0.0.0.0 | ✅ HEALTHY | `"health_check"` | `{"status": "ok", ...}` |
| **Remote Connector Agent** | `remote_connector_agent.py` | 5557 | 0.0.0.0 | ✅ HEALTHY | `{"request_type": "check_status", "model": "phi3"}` | `{"status": "success", ...}` |

**IMPORTANT PORT CONFLICT NOTE:** The quick_translator_fix.py service on port 5564 appears to be OFFLINE according to the health check, while the original translator_agent.py on port 5563 is operational. This contradicts our previous port change and needs to be addressed.

## SERVICES WITH ERROR RESPONSES

The following services are responding to health checks but returning error responses due to protocol mismatches:

| Service Name | Port | Status | Issue | Notes |
|--------------|------|--------|-------|-------|
| **Memory Agent (Base)** | 5590 | ❌ ERROR | Protocol mismatch | Responds but rejects health check format (now includes all reminder/proactive event logic; see notes below) |
| **Contextual Memory** | 5596 | ❌ ERROR | Unknown action pattern | Rejects standard health check actions |
| **Digital Twin** | 5597 | ❌ ERROR | Protocol mismatch | Service expects different JSON structure |
| **Jarvis Memory** | 5598 | ❌ DEPRECATED | DO NOT START (logic merged into memory.py) |
| **Learning Mode** | 5599 | ❌ ERROR | Unknown request type | Service uses different request structuring |
| **Error Pattern Memory** | 5611 | ❌ ERROR | Protocol mismatch | Service expects different JSON structure |
| **Chain of Thought** | 5612 | ❌ ERROR | Protocol mismatch | Service expects different JSON structure |

## OFFLINE SERVICES

These services were included in the health check but did not respond:

| Service Name | File | Port | Status | Notes |
|--------------|------|------|--------|-------|
| **Fallback Translator** | `quick_translator_fix.py` | 5564 | ⏱️ TIMEOUT | Service likely not running on PC2 |

## OTHER SERVICES REFERENCED IN DOCUMENTATION

These services are mentioned in documentation but were not included in the health check:

| Service Name | File | Port | Status | Notes |
|--------------|------|------|--------|-------|
| **Enhanced Web Scraper** | `enhanced_web_scraper.py` | 5602 | ⚠️ UNKNOWN | Not included in health check |
| **Web Assistant** | `autonomous_web_assistant.py` | 5604 | ⚠️ UNKNOWN | Not included in health check |
| **Filesystem Assistant** | `filesystem_assistant_agent.py` | 5606 | ⚠️ UNKNOWN | Not included in health check |
| **Self-Healing Agent** | `self_healing_agent.py` | 5614/5616 | ⚠️ UNKNOWN | Not included in health check |
| **Context Summarizer** | `context_summarizer_agent.py` | 5610 | ⚠️ CONFLICTING | Listed as active in some docs, deprecated in others |

## REMINDER BROADCASTING & MEMORY AGENT CHANGES (June 2025)

- All proactive reminder broadcasting logic is now merged into `agents/memory.py`.
- The `JarvisMemoryAgent` (`jarvis_memory_agent.py`) and `memory_agent.py` are fully deprecated.
- Use the config flag `proactive_reminder_broadcast` in `system_config.py` to enable/disable proactive event broadcasting.
- `send_proactive_event` is now a top-level function in `memory.py` for modularity and testability.
- All tests for proactive reminders are in `test_memory.py`.
- Only start `memory.py` for memory and reminder services; do NOT start any deprecated memory agents.
- Health checks for the memory agent should use the new protocol as defined in `memory.py`.

## KNOWN DEPRECATED SERVICES (DO NOT START)

These services are explicitly deprecated and should not be started:

| Service Name | Former Port | Status | Replacement | Notes |
|--------------|-------------|--------|-------------|-------|
| **PC2 Model Manager** | 5605 | ❌ DEPRECATED | Main PC MMA (5556) | Replaced by Main PC orchestration |
| **Task Router Agent** | 5558 | ❌ DEPRECATED | Enhanced Model Router | Functionality consolidated |
| **Original Translator** | 5563 | ❌ DEPRECATED | quick_translator_fix.py (5564) | Port now used by fixed version |
| **LLM Translation Adapter** | 5581 | ❌ DEPRECATED | NLLB Translation Adapter | Same port now used by NLLB |
| **Code Generator Agents** | Various | ❌ DEPRECATED | Main PC Code Generator | Moved to Main PC |
| **Executor Agent** | 5603 | ❌ DEPRECATED | Main PC Executor | Moved to Main PC |
| **TinyLlama Alternatives** | 5615 | ❌ DEPRECATED | tinyllama_service_enhanced.py | Old versions superseded |

## REQUIRED STARTUP SEQUENCE

For proper initialization, services should be started in the following order:

### Group 1: Base Services (Start First)
```bash
# 1. NLLB Translation Adapter (largest model, needs time to initialize)
python agents/nllb_translation_adapter.py

# 2. TinyLlama Service
python agents/tinyllama_service_enhanced.py
```

### Group 2: Memory Services (Start Second)
```bash
# Memory Agent (Base) - foundation for other memory services
python agents/memory_agent.py
```

### Group 3: Connectivity Services (Start Third)
```bash
# Remote Connector Agent (gateway to model services)
python agents/remote_connector_agent.py
```

### Group 4: Translation Interface (Start Last)
```bash
# There are conflicting reports about which translator is active:
# Health check shows translator_agent.py on port 5563 is responding
# But our recent diagnostics showed quick_translator_fix.py on port 5564 was needed

# OPTION A (if using original translator):
python agents/translator_agent.py

# OPTION B (if using fallback translator):
python quick_translator_fix.py
```

## HEALTH VERIFICATION

After starting the services, verify they are running correctly:

```bash
# Check which services are properly bound to external interfaces
netstat -ano | findstr "LISTENING" | findstr /C:"0.0.0.0"

# Test translator service (adjust port based on which translator is active)
python agents/test_translator.py --port 5563

# Test remote connector
python agents/test_remote_connector.py --port 5557
```

## RECENT FINDINGS AND FIXES

1. **Translator Agent Conflict**:
   - Health check shows original `translator_agent.py` is responding on port 5563
   - Previous diagnostics showed we needed to move to `quick_translator_fix.py` on port 5564
   - This conflict needs to be resolved by determining which translator should actually be used

2. **Memory Agent Issues**:
   - Memory Agent (port 5590) is responding to health checks but with protocol errors
   - This suggests the original Memory Agent is running, not our minimal stub implementation
   - Health check shows it's online but rejects the health check protocol format

3. **Remote Connector Agent Status**:
   - RCA is now confirmed HEALTHY by the Main PC MMA
   - Previously reported timeout issues appear to be resolved
   - The agent correctly handles the `{"request_type": "check_status", "model": "phi3"}` protocol

## HEALTH CHECK PROTOCOL STANDARDIZATION NEEDS

The health check report reveals inconsistent health check protocols across services:

- Some services accept simple string: `"health_check"`
- Others require structured JSON: `{"request_type": "check_status", "model": "phi3"}`
- NLLB adapter uses translation request: `{"action": "translate", "text": "hello", "source": "en", "target": "fr"}`

## NETWORK CONNECTIVITY REQUIREMENTS

- All services bind to 0.0.0.0 (all network interfaces) to allow Main PC access
- Required open firewall ports on PC2:
  - 5563: Translator Agent (original)
  - 5581: NLLB Translation Adapter
  - 5615: TinyLlama Service
  - 5557: Remote Connector Agent
  - 5590: Memory Agent (Base)
  - Plus ports for all other services with ERROR responses (5596, 5597, 5598, 5599, 5611, 5612)

## NEXT STEPS AND RECOMMENDATIONS

1. **Protocol Standardization**:
   - Update Main PC MMA configuration to use correct health check protocols for each service
   - Consider standardizing health check protocols across all services in the future

2. **Translator Service Resolution**:
   - Determine which translator should be the primary (original on 5563 or quick_fix on 5564)
   - Ensure only one translator is active to prevent port/function conflicts
   - Update Main PC configuration to match the chosen translator

3. **Service Status Investigation**:
   - For services with ERROR responses, inspect their code to determine expected health check format
   - Update Main PC MMA configuration to use correct format for each service
   - Verify fallback translator status and restart if needed

4. **Documentation Updates**:
   - This document supersedes all previous PC2 architecture documentation
   - Update startup scripts to reflect current operational services
   - Ensure all health check protocols are documented for each service

---

*This Source of Truth document was created on June 2, 2025, based on comprehensive analysis of existing documentation and active diagnostics. It was updated with the latest health check report from Main PC MMA and should be considered the only authoritative reference for PC2 configuration.*

## OFFICIAL HEALTH CHECK REPORT SUMMARY (JUNE 2, 2025)

```
📊 PC2 ZMQ Services Health Check - Final Report
1. Current Status Summary
| Status Category | Count | Percentage |
|----------------|-------|------------|
| ✅ HEALTHY | 4 | 33.3% |
| ❌ ERROR | 7 | 58.3% |
| ⏱️ TIMEOUT | 1 | 8.3% |
| TOTAL | 12 | 100% |

2. Working Services (4/12)
| Service Name | Health Check Protocol | Response Status |
|-------------|---------------------|----------------|
| tinylama-service-pc2 | "health_check" | {"status": "ok", ...} |
| rca-agent-pc2 | {"request_type": "check_status", "model": "phi3"} | {"status": "success", ...} |
| translator-agent-pc2 | "health_check" | {"status": "success", ...} |
| nllb-adapter-pc2 | {"action": "translate", "text": "hello", "source": "en", "target": "fr"} | {"status": "success", ...} |
```

Key environment variables that must be set for proper operation:
- `VOICE_ASSISTANT_PC_ROLE='pc2'`
- `MACHINE_ROLE='PC2'`
