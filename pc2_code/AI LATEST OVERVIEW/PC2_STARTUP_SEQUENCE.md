# PC2 Startup Sequence (Updated)

This document outlines the recommended startup sequence for PC2 agents to ensure proper system initialization. The sequence considers dependencies between agents, with "server" agents starting before "client" agents that connect to them, and ensuring fallback mechanisms are available before primary services.

## Startup Groups

The startup process is organized into sequential groups. Each group should be started and verified before proceeding to the next group.

### Group 1: Core Model Services

These services provide the fundamental LLM capabilities required by other agents:

1. **NLLB Translation Adapter** (5581)
   - Specialized translation service used as a fallback by Translator Agent
   - No dependencies on other PC2 agents
   - Command: `python nllb_translation_adapter.py --server`

2. **TinyLlama Service** (5615)
   - Lightweight LLM fallback service
   - No dependencies on other PC2 agents
   - Command: `python tinyllama_service.py --server`

### Group 2: Memory and Context Management

These agents provide memory services required by higher-level agents:

1. **Memory Agent (Base)** (5590)
   - Core memory management functionality
   - No dependencies on other PC2 agents
   - Command: `python memory.py --server`

2. **Contextual Memory Agent** (5596)
   - **CONSOLIDATED**: Now handles both context management and advanced summarization 
   - Integrated functionality from context_summarizer_agent.py (now deprecated)
   - Depends on Memory Agent for base functionality
   - Command: `python contextual_memory_agent.py --server`

3. **Digital Twin Agent** (5597)
   - User modeling and behavioral analysis
   - No critical dependencies
   - Command: `python digital_twin_agent.py --server`

4. **Jarvis Memory Agent** (5598)
   - Long-term memory services (scheduled for future consolidation)
   - No critical dependencies
   - Command: `python jarvis_memory_agent.py --server`

5. **Learning Mode Agent** (5599)
   - System adaptation and continuous learning
   - No critical dependencies
   - Command: `python learning_mode_agent.py --server`

6. **Error Pattern Memory** (5611)
   - Tracks error patterns and solutions
   - No critical dependencies
   - Command: `python error_pattern_memory.py --server`

### Group 3: Core Processing Agents

These agents provide critical infrastructure for the PC2 system:

1. **Remote Connector Agent (RCA)** (5557)
   - Direct gateway to model services
   - Depends on model services from Group 1
   - Command: `python remote_connector_agent.py --server`

2. **Chain of Thought Agent (CoT)** (5612)
   - Multi-step reasoning capability
   - Depends on Remote Connector Agent
   - Command: `python chain_of_thought_agent.py --server`

3. **Self-Healing Agent** (5614/5616)
   - System health monitoring and recovery
   - Should start early to monitor other services as they come online
   - Command: `python self_healing_agent.py --server`

> **Note**: Model Manager Agent (MMA) has been removed as AI services now implement self-managed on-demand loading and idle unloading.

### Group 4: Specialized Assistants

These agents provide specialized capabilities:

1. **Enhanced Web Scraper** (5602)
   - Web content retrieval
   - No critical dependencies on other PC2 agents
   - Command: `python enhanced_web_scraper.py --server`

2. **Autonomous Web Assistant** (5604)
   - Web-based research and tasks
   - May depend on Enhanced Web Scraper
   - Command: `python autonomous_web_assistant.py --server`

3. **Filesystem Assistant Agent** (5606)
   - File operations and management
   - No critical dependencies
   - Command: `python filesystem_assistant_agent.py --server`

### Group 5: Central Routing and Translation

The Enhanced Model Router should be started before the Translator Agent as the latter depends on it:

1. **Enhanced Model Router (EMR)** (7602/7701)
   - **CONSOLIDATED & ENHANCED**: Central intelligence hub 
   - Integrated functionality from task_router_agent.py (now deprecated)
   - Depends on:
     - Contextual Memory Agent

     - Chain of Thought Agent
     - Remote Connector Agent
   - Command: `python enhanced_model_router.py --server`

2. **Translator Agent (PC2)** (5563/5561, health check: 5559)
   - **ENHANCED**: Advanced tiered translation with dual socket architecture:
     - REP socket (5563): Direct communication with Main PC's fixed_streaming_translation.py
     - SUB socket (5561): For PUB-SUB interactions with other components
   - Depends on:
     - NLLB Translation Adapter (for fallback)
     - Enhanced Model Router (for output routing)
   - Command: `python translator_agent.py --server`

## Startup Verification

After starting each group, verify that the agents are running properly:

1. **Health Check**: For agents with health check endpoints (e.g., Translator Agent on port 5559), you can send a request to verify they're responsive:

   ```python
   # Example health check for Translator Agent
   import zmq
   import json
   import time

   context = zmq.Context()
   health_socket = context.socket(zmq.REQ)
   health_socket.connect("tcp://localhost:5559")
   
   health_socket.send_json({"action": "health_check", "request_id": str(time.time())})
   response = health_socket.recv_json()
   print(f"Health status: {response['status']}")
   print(f"Stats: {response['stats']}")
   ```

2. **Self-Healing Agent Status**: The Self-Healing Agent monitors other agents and can provide a comprehensive status overview.

3. **Log Files**: Check agent log files for successful startup messages and any error reports.

## Consolidated Startup Script

Here's a PowerShell script to automate the startup sequence:

```powershell
# PC2 Agents Startup Script
# Usage: Run from the Voice Assistant root directory

$agentsDir = "D:\DISKARTE\Voice Assistant\agents"
$logDir = "D:\DISKARTE\Voice Assistant\logs"

# Ensure log directory exists
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir
}

# Helper function to start agent
function Start-Agent {
    param (
        [string]$name,
        [string]$args = "--server"
    )
    
    Write-Host "Starting $name..." -ForegroundColor Green
    $logFile = Join-Path $logDir "$name.log"
    Start-Process -FilePath "python" -ArgumentList "$name.py $args" -WorkingDirectory $agentsDir -RedirectStandardOutput $logFile -RedirectStandardError "$logFile.error"
    
    # Wait briefly to ensure process starts
    Start-Sleep -Seconds 3
    Write-Host "$name started. Logs at $logFile" -ForegroundColor Cyan
}

# Group 1: Core Model Services
Write-Host "\nStarting Group 1: Core Model Services..." -ForegroundColor Yellow
Start-Agent "nllb_translation_adapter"
Start-Agent "tinyllama_service"

# Group 2: Memory and Context Management
Write-Host "\nStarting Group 2: Memory and Context Management..." -ForegroundColor Yellow
Start-Agent "memory"
Start-Agent "contextual_memory_agent"
Start-Agent "digital_twin_agent"
Start-Agent "jarvis_memory_agent"
Start-Agent "learning_mode_agent"
Start-Agent "error_pattern_memory"

# Group 3: Core Processing Agents
Write-Host "\nStarting Group 3: Core Processing Agents..." -ForegroundColor Yellow
Start-Agent "remote_connector_agent"
Start-Agent "chain_of_thought_agent"
Start-Agent "self_healing_agent"

# Note: Model Manager Agent removed as AI services now implement self-managed loading/unloading

# Group 4: Specialized Assistants
Write-Host "\nStarting Group 4: Specialized Assistants..." -ForegroundColor Yellow
Start-Agent "enhanced_web_scraper"
Start-Agent "autonomous_web_assistant"
Start-Agent "filesystem_assistant_agent"

# Group 5: Central Routing and Translation
Write-Host "\nStarting Group 5: Central Routing and Translation..." -ForegroundColor Yellow
Start-Agent "enhanced_model_router"
Start-Agent "translator_agent"

Write-Host "\nAll PC2 agents started successfully." -ForegroundColor Green
Write-Host "Run Self-Healing Agent status check to verify all services." -ForegroundColor Yellow
```

## Troubleshooting

If an agent fails to start:

1. Check the agent's log file for error messages
2. Verify that all dependent agents are running
3. Ensure ports are not in use by other applications
4. Restart the agent and its dependencies if necessary

## Deprecated Components

The following components have been deprecated and should not be started:

- **task_router_agent.py** (formerly port 5558): Functionality consolidated into Enhanced Model Router
- **context_summarizer_agent.py** (formerly port 5610): Features merged into contextual_memory_agent.py
- **translator_agent.py (Main PC)** (formerly port 8044): Replaced by enhanced PC2 Translator Agent

## Port Reference (Updated)

| Component | REP/SUB Port | PUB/Health Port | Dependencies |
|-----------|---------|---------|------------|
| Enhanced Model Router (EMR) | 7602 (REP) | 7701 (PUB) | RCA, Contextual Memory, CoT |
| Remote Connector Agent (RCA) | 5557 (REP) | - | Model Services |
| Chain of Thought Agent (CoT) | 5612 (REP) | - | RCA |
| Translator Agent (PC2) | 5563 (REP for Main PC), 5561 (SUB) | 5559 (Health) | NLLB, EMR |
| Contextual Memory Agent | 5596 (REP) | - | Memory Agent |
| Digital Twin Agent | 5597 (REP) | - | - |
| Jarvis Memory Agent | 5598 (REP) | - | - |
| Learning Mode Agent | 5599 (REP) | - | - |
| Error Pattern Memory | 5611 (REP) | - | - |
| Memory Agent (Base) | 5590 (REP) | - | - |
| NLLB Translation Adapter | 5581 (REP) | - | - |
| TinyLlama Service | 5615 (REP) | - | - |
| Autonomous Web Assistant | 5604 (REP) | - | - |
| Enhanced Web Scraper | 5602 (REP) | - | - |
| Filesystem Assistant Agent | 5606 (REP) | - | - |
| Self-Healing Agent | 5614 (REP) | 5616 (PUB) | - |

## Shutdown Sequence

For controlled shutdown, reverse the startup sequence to prevent errors from agents attempting to connect to services that are no longer available.

## Troubleshooting

If an agent fails to start:

1. Check log files for error messages
2. Verify that all dependent agents are running
3. Ensure the required port is available and not blocked
4. Check system resources (memory, CPU) are sufficient
5. Restart the failed agent and its dependencies if necessary
