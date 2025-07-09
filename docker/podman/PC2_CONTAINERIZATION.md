# PC2 System Containerization with Podman in WSL2

## Overview

This document describes the containerization solution for the PC2 components of the AI System using Podman in a WSL2 environment. The containerization approach is aligned with the existing documentation and container grouping strategies defined in the PC2 configuration.

## Container Groups

Based on the `container_grouping.yaml` file and our implementation, PC2 agents are organized into the following container groups:

1. **pc2-core-services**
   - SystemHealthManager, HealthMonitor, ResourceManager, PerformanceMonitor, PerformanceLoggerAgent
   - Essential infrastructure services that other containers depend on

2. **pc2-security-services**
   - AuthenticationAgent, UnifiedUtilsAgent, AgentTrustScorer
   - Security and authentication services

3. **pc2-memory-services**
   - CacheManager, ContextManager, ExperienceTracker, ProactiveContextMonitor, UnifiedMemoryReasoningAgent
   - Memory management and context services

4. **pc2-task-services**
   - TieredResponder, AsyncProcessor, TaskScheduler, AdvancedRouter, RemoteConnectorAgent
   - Task processing and routing services

5. **pc2-ai-services**
   - DreamWorldAgent, DreamingModeAgent, TutorAgent, TutoringServiceAgent, TutoringAgent
   - Specialized AI services (requires GPU)

6. **pc2-web-services**
   - FileSystemAssistantAgent, UnifiedWebAgent, VisionProcessingAgent
   - Web and filesystem services

## Architecture

The containerization architecture consists of:

1. **Base Container Image**:
   - `Dockerfile.wsl2`: CUDA-enabled base image specifically optimized for WSL2
   - Support for GPU acceleration via NVIDIA runtime

2. **Dynamic Agent Management**:
   - `container_startup.py`: Launches appropriate agents based on container group
   - Handles PC2-specific agent configurations and dependencies
   - Creates placeholders for missing agent implementations

3. **Cross-Machine Communication**:
   - PC2 containers communicate with MainPC services via ZMQ
   - Host networking mode for simplified communication

## Setup and Deployment

### Prerequisites

- WSL2 with Ubuntu 22.04+
- NVIDIA GPU with CUDA 11.8+ drivers installed on Windows host
- Podman installed in WSL2

### Building Container Images

1. Use the same base image as MainPC:
```bash
./build_wsl2_container.sh
```

### Running PC2 Containers

1. Start the core-services container first:
```bash
./scripts/launch_pc2_container.sh pc2-core-services
```

2. Launch other containers as needed:
```bash
./scripts/launch_pc2_container.sh pc2-security-services
./scripts/launch_pc2_container.sh pc2-memory-services
./scripts/launch_pc2_container.sh pc2-task-services
./scripts/launch_pc2_container.sh pc2-ai-services
./scripts/launch_pc2_container.sh pc2-web-services
```

## Configuration Files

### Container Groups

The container groups are defined in `pc2_code/config/container_grouping.yaml`. This file specifies:
- Which agents belong to which container groups
- Agent priorities and requirements
- Script paths and port configurations

### Startup Configuration

The PC2 agent startup configuration is defined in `pc2_code/config/startup_config.yaml`. This file contains:
- Agent configurations including ports and health check ports
- Dependencies between agents
- Required vs. optional agents

## Agent Dependencies

PC2 agents have dependencies on both local PC2 services and remote MainPC services:

1. **Local PC2 Dependencies**:
   - These are handled normally within the container startup system
   - Proper startup order is ensured based on dependencies

2. **MainPC Dependencies**:
   - The container startup system identifies dependencies on MainPC services
   - Warnings are logged when starting agents with MainPC dependencies
   - Agents will attempt to connect to MainPC services based on network configuration

## Testing and Validation

### Testing Individual Agents

Use the provided runner scripts to test individual PC2 agents:

```bash
./run_pc2_health_monitor.py
```

### Testing Container Startup

To test the container startup system with PC2 agents:

```bash
PC2_MODE=true CONTAINER_GROUP=pc2-core-services python docker/podman/scripts/container_startup.py
```

## Troubleshooting

### Common Issues

1. **MainPC Dependency Issues**:
   - If PC2 agents fail due to missing MainPC services, ensure MainPC containers are running
   - Check network configuration to ensure PC2 can reach MainPC services

2. **Agent Script Not Found**:
   - The container startup system will create placeholder scripts for missing agents
   - Check logs for warnings about missing agent scripts

3. **Port Conflicts**:
   - Ensure no port conflicts between PC2 and MainPC services
   - Use different port ranges for PC2 and MainPC services

## Next Steps

1. **Integration Testing**:
   - Test communication between PC2 and MainPC containers
   - Verify cross-machine functionality

2. **Performance Testing**:
   - Test PC2 containers under load
   - Monitor resource usage and adjust container limits as needed

3. **Deployment Automation**:
   - Create scripts for automated deployment of all PC2 containers
   - Implement proper startup ordering based on dependencies 