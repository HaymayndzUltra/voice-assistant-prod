# AI System Containerization Package

## Overview

This package contains all the necessary scripts and documentation to run the AI System in containers using Podman in a WSL2 environment. It supports both MainPC and PC2 components with proper GPU acceleration.

## Directory Structure

```
containerization_package/
├── scripts/                    # Container and agent scripts
│   ├── container_startup.py    # Main script for starting agents in containers
│   ├── launch_wsl2_container.sh # Script to launch MainPC containers
│   ├── launch_pc2_container.sh # Script to launch PC2 containers
│   ├── fix_wsl2_gpu.sh         # Script to fix GPU device paths in WSL2
│   ├── run_systemdigitaltwin.py # Script to run SystemDigitalTwin agent directly
│   ├── run_memory_client.py    # Script to run MemoryClient agent directly
│   └── run_pc2_health_monitor.py # Script to run PC2 HealthMonitor agent directly
└── docs/                       # Documentation
    ├── CONTAINERIZATION_SOLUTION.md # MainPC containerization documentation
    └── PC2_CONTAINERIZATION.md # PC2 containerization documentation
```

## Quick Start Guide

### Prerequisites

1. WSL2 with Ubuntu 22.04+
2. NVIDIA GPU with CUDA 11.8+ drivers installed on Windows host
3. Podman installed in WSL2

### Installation

1. Install Podman in WSL2:
```bash
sudo apt-get update
sudo apt-get install -y podman
```

2. Build the container image:
```bash
cd /path/to/AI_System_Monorepo
./docker/podman/build_wsl2_container.sh
```

### Running MainPC Containers

1. Start the core-services container first:
```bash
cd /path/to/AI_System_Monorepo
./containerization_package/scripts/launch_wsl2_container.sh core-services
```

2. Start other MainPC containers:
```bash
./containerization_package/scripts/launch_wsl2_container.sh memory-system
./containerization_package/scripts/launch_wsl2_container.sh utility-services
./containerization_package/scripts/launch_wsl2_container.sh ai-models-gpu-services
./containerization_package/scripts/launch_wsl2_container.sh language-processing
```

### Running PC2 Containers

1. Start the PC2 core-services container first:
```bash
cd /path/to/AI_System_Monorepo
./containerization_package/scripts/launch_pc2_container.sh pc2-core-services
```

2. Start other PC2 containers:
```bash
./containerization_package/scripts/launch_pc2_container.sh pc2-security-services
./containerization_package/scripts/launch_pc2_container.sh pc2-memory-services
./containerization_package/scripts/launch_pc2_container.sh pc2-task-services
./containerization_package/scripts/launch_pc2_container.sh pc2-ai-services
./containerization_package/scripts/launch_pc2_container.sh pc2-web-services
```

### Running Individual Agents (For Testing)

You can run individual agents directly without containers for testing:

1. Run SystemDigitalTwin agent:
```bash
cd /path/to/AI_System_Monorepo
./containerization_package/scripts/run_systemdigitaltwin.py
```

2. Run MemoryClient agent:
```bash
./containerization_package/scripts/run_memory_client.py
```

3. Run PC2 HealthMonitor agent:
```bash
./containerization_package/scripts/run_pc2_health_monitor.py
```

## Development Mode

To mount your local code directory into the container for development:

```bash
# For MainPC containers
./containerization_package/scripts/launch_wsl2_container.sh core-services --dev

# For PC2 containers
./containerization_package/scripts/launch_pc2_container.sh pc2-core-services --dev
```

## Container Groups

### MainPC Container Groups

1. **core-services**: SystemDigitalTwin, RequestCoordinator
2. **memory-system**: MemoryOrchestrator, MemoryClient
3. **utility-services**: LoggingService, ConfigManager
4. **ai-models-gpu-services**: GPU-accelerated model services
5. **language-processing**: NLP and translation services

### PC2 Container Groups

1. **pc2-core-services**: SystemHealthManager, HealthMonitor, ResourceManager, PerformanceMonitor, PerformanceLoggerAgent
2. **pc2-security-services**: AuthenticationAgent, UnifiedUtilsAgent, AgentTrustScorer
3. **pc2-memory-services**: CacheManager, ContextManager, ExperienceTracker, ProactiveContextMonitor, UnifiedMemoryReasoningAgent
4. **pc2-task-services**: TieredResponder, AsyncProcessor, TaskScheduler, AdvancedRouter, RemoteConnectorAgent
5. **pc2-ai-services**: DreamWorldAgent, DreamingModeAgent, TutorAgent, TutoringServiceAgent, TutoringAgent
6. **pc2-web-services**: FileSystemAssistantAgent, UnifiedWebAgent, VisionProcessingAgent

## Troubleshooting

### GPU Issues

If you encounter GPU issues in WSL2:

```bash
# Fix GPU device paths
./containerization_package/scripts/fix_wsl2_gpu.sh

# Test GPU access in container
podman run --rm --device nvidia.com/gpu=all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
```

### Agent Startup Issues

If agents fail to start:

1. Check if the agent script exists
2. Verify Python path includes necessary directories
3. Check for dependency issues in logs

### Communication Issues Between Containers

If containers can't communicate:

1. Verify all containers use host networking mode
2. Ensure required services are running (SystemDigitalTwin, etc.)
3. Check network ports are not blocked by firewalls

## Additional Documentation

For more detailed information, refer to:

- [MainPC Containerization Documentation](docs/CONTAINERIZATION_SOLUTION.md)
- [PC2 Containerization Documentation](docs/PC2_CONTAINERIZATION.md) 