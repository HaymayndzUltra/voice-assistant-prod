# AI System Containerization Solution

## Overview

This document describes the containerization solution implemented for the AI System using Podman in a WSL2 environment. The solution enables running various agent groups in isolated containers with proper GPU support and dynamic agent launching.

## Architecture

The containerization architecture consists of:

1. **Base Container Images**:
   - `Dockerfile.wsl2`: CUDA-enabled base image specifically optimized for WSL2
   - Support for GPU acceleration via NVIDIA runtime

2. **Agent Group Containers**:
   - Organized by functionality (core-services, memory-system, utility-services, etc.)
   - Each container runs multiple related agents

3. **Dynamic Agent Management**:
   - `container_startup.py`: Launches appropriate agents based on container group
   - Handles missing agent scripts by creating placeholders
   - Monitors and restarts failed agents

4. **WSL2-CUDA Integration**:
   - Special configuration for WSL2 GPU passthrough
   - Scripts to fix device path issues in WSL2 environment

## Container Groups

The system is divided into these primary container groups:

1. **core-services**: Essential system agents (SystemDigitalTwin, RequestCoordinator)
2. **memory-system**: Memory-related agents (MemoryOrchestrator, MemoryClient)  
3. **utility-services**: Support services (LoggingService, ConfigManager)
4. **ai-models-gpu-services**: GPU-accelerated model services
5. **language-processing**: NLP and translation services

## Setup and Deployment

### Prerequisites

- WSL2 with Ubuntu 22.04+
- NVIDIA GPU with CUDA 11.8+ drivers installed on Windows host
- Podman installed in WSL2

### Building Container Images

1. Use the `build_wsl2_container.sh` script to build the base CUDA-enabled image:
```bash
./build_wsl2_container.sh
```

2. For faster rebuilds during development, use:
```bash
./build_wsl2_container_fast.sh
```

### Running Containers

1. Start the core-services container first:
```bash
./scripts/launch_wsl2_container.sh core-services
```

2. Launch other containers as needed:
```bash
./scripts/launch_wsl2_container.sh memory-system
./scripts/launch_wsl2_container.sh ai-models-gpu-services
```

## WSL2-Specific Considerations

### GPU Support

GPU support in WSL2 requires special handling due to how device paths are managed. The `fix_wsl2_gpu.sh` script ensures NVIDIA devices are properly accessible within containers by:

1. Checking for NVIDIA devices in the WSL2 environment
2. Creating proper device nodes if needed
3. Setting up appropriate permissions

### Networking

WSL2 containers use host networking mode to avoid issues with CNI networks in the WSL2 environment. This allows agents to communicate across containers without complex networking setup.

## Agent Startup System

The `container_startup.py` script provides these key features:

1. **Configuration Loading**: Reads agent configuration from `main_pc_code/config/startup_config.yaml`
2. **Dynamic Agent Discovery**: Launches agents based on container group assignment
3. **Dependency Management**: Checks for required services and handles missing dependencies
4. **Placeholder Creation**: Generates placeholder scripts for missing agents
5. **Process Monitoring**: Restarts crashed agents and logs their output

## Testing and Validation

### Testing GPU Access

Use these scripts to verify GPU access:

1. `scripts/test_host_cuda.sh`: Tests CUDA availability in the WSL2 host
2. `scripts/test_gpu_container.sh`: Verifies CUDA functionality within containers
3. `scripts/test_pytorch_cuda.py`: Tests PyTorch GPU acceleration

### Agent Validation

To test individual agents without containers:

1. Use wrapper scripts like `run_systemdigitaltwin.py` for simpler testing
2. Monitor agent logs in the `logs/` directory
3. Use `agent_health_check_validator.py` to verify agent health endpoints

## Troubleshooting

### Common Issues

1. **GPU Not Detected in Container**: 
   - Run `fix_wsl2_gpu.sh` to fix device paths
   - Verify NVIDIA drivers are properly installed on Windows host

2. **Agent Fails to Start**:
   - Check if agent implementation exists
   - Verify Python path includes necessary directories
   - Check for dependency issues in logs

3. **Agent Crashes with Import Errors**:
   - Use wrapper scripts that set proper PYTHONPATH
   - Create symlinks for shared modules if needed

4. **Communication Issues Between Containers**:
   - Verify all containers use host networking mode
   - Ensure required services are running (SystemDigitalTwin, etc.)
   - Check network ports are not blocked by firewalls

## Next Steps

1. **PC2 Integration**: Set up proper communication with PC2 machine agents
2. **Orchestration**: Add docker-compose or Kubernetes configuration for multi-machine deployment
3. **CI/CD**: Integrate container builds into CI/CD pipeline
4. **Monitoring**: Add container health monitoring and alerting

## Conclusion

This containerization approach provides a flexible, isolated environment for running the AI System's agents with proper GPU acceleration in WSL2. The dynamic agent management system handles agent dependencies, monitors processes, and ensures the system runs reliably even with missing components. 