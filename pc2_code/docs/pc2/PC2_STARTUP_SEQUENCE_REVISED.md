# PC2 Startup Sequence (Revised May 31, 2025)

This document outlines the proper startup sequence for PC2 services following the architectural streamlining decisions made on May 31, 2025.

## Overview

The startup sequence has been significantly simplified to focus only on essential PC2 services. All code generation, execution, and orchestration services have been moved to Main PC, resulting in a more streamlined architecture.

## Essential Services Startup Order

The recommended startup order ensures that dependencies are properly satisfied and services initialize correctly:

### 1. Translation Services

These services should be started first as they have the fewest dependencies:

```bash
# 1. Start NLLB Translation Adapter (has largest model, needs time to initialize)
python agents/nllb_translation_adapter.py

# 2. Start TinyLlama Service (fallback model)
python agents/tinyllama_service_enhanced.py

# 3. Start Translator Agent (depends on both services above)
python quick_translator_fix.py  # Uses the simplified reliable implementation
```

### 2. Memory Services

These services form the memory infrastructure and should be started next:

```bash
# 1. Start Memory Agent (Base) - foundation for other memory services
python agents/memory.py

# 2. Start specialized memory agents
python agents/contextual_memory_agent.py
python agents/digital_twin_agent.py
python agents/jarvis_memory_agent.py
python agents/error_pattern_memory.py
```

### 3. Reasoning Services

These services provide reasoning capabilities:

```bash
# 1. Start Context Summarizer Agent
python agents/context_summarizer_agent.py

# 2. Start Chain of Thought Agent
python agents/chain_of_thought_agent.py
```

## Automated Startup

For convenience, a batch script has been created to automate the startup of all essential services in the correct order:

```bash
# Launches all essential services in the correct order
.\start_essential_pc2_services.bat
```

## Verifying Services

After starting the services, verify they are running correctly:

```bash
# Check which services are properly bound to external interfaces
netstat -ano | findstr "LISTENING" | findstr /C:"0.0.0.0"

# Run health check on essential services
python pc2_health_check.py --essential
```

## Troubleshooting

If services fail to start or bind properly:

1. **Check Port Availability**: Ensure no other processes are using the required ports
   ```bash
   netstat -ano | findstr /C:"5563" /C:"5581" /C:"5590"
   ```

2. **Kill Conflicting Processes**: If needed, terminate processes holding required ports
   ```bash
   # Find PID using port
   netstat -ano | findstr /C:"5563"
   
   # Kill process by PID
   taskkill /F /PID <process_id>
   ```

3. **Verify External Binding**: All services must bind to 0.0.0.0 (not 127.0.0.1) to be accessible from Main PC
   ```bash
   # Check binding addresses
   netstat -ano | findstr "LISTENING" | findstr /C:"0.0.0.0"
   ```

4. **Restart in Correct Order**: If needed, stop all services and restart them in the recommended order

## Deprecated Services

The following services have been deprecated and moved to the `deprecated_agents` folder:

- Model Manager Agent (Port 5605)
- Code Generator Agent (Port 5602)
- Executor Agent (Port 5603)
- Progressive Code Generator (Port 5604)
- Web Scraper Agent (Port 5601)

**Do not start these services.** Their functionality has been moved to Main PC or is no longer needed according to the architectural decisions made on May 31, 2025.

---

*This document was created as part of the PC2 architecture streamlining effort on May 31, 2025.*
