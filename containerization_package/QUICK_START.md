# AI System Containerization Quick Start Guide

This guide provides quick instructions for setting up and running the AI System in containers.

## Setup

1. Run the setup script to make all scripts executable and check prerequisites:

```bash
./setup.sh
```

This script will:
- Make all scripts executable
- Check for Podman installation
- Check for NVIDIA GPU
- Fix GPU device paths if needed
- Check for container image and offer to build it if not found

## Running MainPC Containers

To start all MainPC containers in the correct order:

```bash
./start_mainpc.sh
```

This will start:
1. core-services (SystemDigitalTwin, etc.)
2. memory-system (MemoryOrchestrator, etc.)
3. utility-services
4. ai-models-gpu-services (if GPU available)
5. language-processing (if GPU available)

## Running PC2 Containers

To start all PC2 containers in the correct order:

```bash
./start_pc2.sh
```

This will start:
1. pc2-core-services
2. pc2-security-services
3. pc2-memory-services
4. pc2-task-services
5. pc2-ai-services (if GPU available)
6. pc2-web-services

## Stopping All Containers

To stop all running containers:

```bash
./stop_all.sh
```

## Running Individual Containers

To run specific containers manually:

```bash
# MainPC containers
./scripts/launch_wsl2_container.sh core-services
./scripts/launch_wsl2_container.sh memory-system
./scripts/launch_wsl2_container.sh utility-services
./scripts/launch_wsl2_container.sh ai-models-gpu-services
./scripts/launch_wsl2_container.sh language-processing

# PC2 containers
./scripts/launch_pc2_container.sh pc2-core-services
./scripts/launch_pc2_container.sh pc2-security-services
./scripts/launch_pc2_container.sh pc2-memory-services
./scripts/launch_pc2_container.sh pc2-task-services
./scripts/launch_pc2_container.sh pc2-ai-services
./scripts/launch_pc2_container.sh pc2-web-services
```

## Development Mode

For development, you can mount your local code directory into the container:

```bash
# MainPC containers
./scripts/launch_wsl2_container.sh core-services --dev

# PC2 containers
./scripts/launch_pc2_container.sh pc2-core-services --dev
```

## Testing Individual Agents

For testing individual agents without containers:

```bash
# MainPC agents
./scripts/run_systemdigitaltwin.py
./scripts/run_memory_client.py

# PC2 agents
./scripts/run_pc2_health_monitor.py
```

## Viewing Container Logs

To view logs from a specific container:

```bash
podman logs -f ai-system-core-services
podman logs -f ai-system-pc2-core-services
```

## Additional Documentation

For more detailed information, refer to:
- [Full README](README.md)
- [MainPC Containerization Documentation](docs/CONTAINERIZATION_SOLUTION.md)
- [PC2 Containerization Documentation](docs/PC2_CONTAINERIZATION.md) 