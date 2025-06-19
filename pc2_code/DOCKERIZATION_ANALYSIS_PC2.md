# PC2 Dockerization Analysis

## System Overview

PC2 serves as the Cognitive/Memory Hub of the AI system, hosting multiple specialized agents that handle memory, learning, and cognitive processing tasks. The system communicates with PC1 (Sensory/Interface Hub) at IP `192.168.1.27`.

## Agent Inventory

### Core Infrastructure Agents
1. **Enhanced Model Router** (Port: 5598)
   - Dependencies: pyzmq, torch, transformers
   - Communication: Intra-PC2 (all agents), Inter-PC1 (ModelManagerAgent)

2. **Advanced Router** (Port: N/A)
   - Dependencies: pyzmq, networkx
   - Communication: Intra-PC2 (all agents)

### Memory and Learning Agents
3. **Unified Memory Reasoning Agent** (Port: 5596)
   - Dependencies: pyzmq, torch, transformers, chromadb
   - Communication: Intra-PC2 (all agents)

4. **Memory Decay Manager** (Port: N/A)
   - Dependencies: pyzmq, numpy, pandas
   - Communication: Intra-PC2 (Unified Memory Reasoning Agent)

5. **Episodic Memory Agent** (Port: N/A)
   - Dependencies: pyzmq, torch, transformers
   - Communication: Intra-PC2 (Unified Memory Reasoning Agent)

### Cognitive and Learning Agents
6. **Cognitive Model Agent** (Port: N/A)
   - Dependencies: pyzmq, torch, transformers
   - Communication: Intra-PC2 (all agents)

7. **Learning Adjuster Agent** (Port: N/A)
   - Dependencies: pyzmq, torch, transformers
   - Communication: Intra-PC2 (Cognitive Model Agent)

8. **Self Training Orchestrator** (Port: N/A)
   - Dependencies: pyzmq, torch, transformers
   - Communication: Intra-PC2 (Learning Adjuster Agent)

### Dream World and Trust Agents
9. **Dream World Agent** (Port: 5599)
   - Dependencies: pyzmq, torch, transformers
   - Communication: Intra-PC2 (all agents)

10. **Dreaming Mode Agent** (Port: N/A)
    - Dependencies: pyzmq, torch, transformers
    - Communication: Intra-PC2 (Dream World Agent)

11. **Agent Trust Scorer** (Port: N/A)
    - Dependencies: pyzmq, numpy, pandas
    - Communication: Intra-PC2 (all agents)

### Service and Utility Agents
12. **TinyLLaMA Service** (Port: 5615)
    - Dependencies: pyzmq, torch, transformers, llama-cpp-python
    - Communication: Intra-PC2 (all agents)

13. **Self Healing Agent** (Port: 5611)
    - Dependencies: pyzmq, psutil
    - Communication: Intra-PC2 (all agents)

14. **Performance Logger Agent** (Port: N/A)
    - Dependencies: pyzmq, psutil, prometheus-client
    - Communication: Intra-PC2 (all agents)

### Interface and Communication Agents
15. **Unified Web Agent** (Port: 5604)
    - Dependencies: pyzmq, fastapi, uvicorn, playwright
    - Communication: Intra-PC2 (all agents), Inter-PC1 (Web Interface)

16. **Remote Connector Agent** (Port: 5557)
    - Dependencies: pyzmq, requests
    - Communication: Inter-PC1 (all services)

17. **Consolidated Translator** (Port: 5563)
    - Dependencies: pyzmq, torch, transformers
    - Communication: Intra-PC2 (all agents)

18. **Filesystem Assistant Agent** (Port: 5606)
    - Dependencies: pyzmq
    - Communication: Intra-PC2 (all agents)

19. **Tutoring Service Agent** (Port: 5568)
    - Dependencies: pyzmq, sympy, wolframalpha
    - Communication: Intra-PC2 (all agents), Inter-PC1 (TaskRouter)

## Communication Map

### Intra-PC2 Communication
- All agents communicate with each other through ZMQ
- Enhanced Model Router serves as the central message broker
- Memory agents form a sub-network for memory operations
- Learning agents form a sub-network for learning operations

### Inter-PC1 Communication
- Remote Connector Agent handles all communication with PC1
- Target PC1 Services:
  - TaskRouter (192.168.1.27)
  - HealthMonitor (192.168.1.27)
  - AudioCapture (192.168.1.27)
  - ModelManagerAgent (192.168.1.27)

## Volume Requirements

1. **Model Storage**
   - Path: `/app/models`
   - Purpose: Store TinyLLaMA and other model files
   - Type: Persistent

2. **Memory Storage**
   - Path: `/app/data/memory`
   - Purpose: Store memory databases and caches
   - Type: Persistent

3. **Log Storage**
   - Path: `/app/logs`
   - Purpose: Store agent logs
   - Type: Persistent

4. **Cache Storage**
   - Path: `/app/cache`
   - Purpose: Store temporary caches
   - Type: Ephemeral

## Environment Variables

1. **System Configuration**
   - `PC1_IP_ADDRESS`: IP address of PC1 (192.168.1.27)
   - `PYTHONPATH`: Set to `/app`

2. **Agent Configuration**
   - `ENHANCED_MODEL_ROUTER_HOST`: Service name or IP
   - `DREAM_WORLD_HOST`: Service name or IP
   - `TRANSLATOR_HOST`: Service name or IP
   - `TUTORING_HOST`: Service name or IP
   - `MEMORY_HOST`: Service name or IP
   - `REMOTE_CONNECTOR_HOST`: Service name or IP
   - `WEB_AGENT_HOST`: Service name or IP
   - `FILESYSTEM_HOST`: Service name or IP
   - `HEALTH_CHECK_HOST`: Service name or IP
   - `CHAIN_OF_THOUGHT_HOST`: Service name or IP
   - `TINYLLAMA_HOST`: Service name or IP

## GPU Requirements

Most agents require GPU access for optimal performance:
- Enhanced Model Router
- Unified Memory Reasoning Agent
- Cognitive Model Agent
- Dream World Agent
- TinyLLaMA Service
- Consolidated Translator

## Network Configuration

1. **Internal Network**
   - Name: `pc2_network`
   - Type: Bridge
   - Purpose: Inter-agent communication

2. **External Network**
   - Type: Host
   - Purpose: Communication with PC1

## Security Considerations

1. **Volume Permissions**
   - All volumes should be owned by non-root user
   - Read-only where possible
   - Proper SELinux/AppArmor profiles

2. **Network Security**
   - Internal network isolation
   - Firewall rules for PC1 communication
   - ZMQ authentication

3. **Resource Limits**
   - CPU limits per container
   - Memory limits per container
   - GPU memory limits 