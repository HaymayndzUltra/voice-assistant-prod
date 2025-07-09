# PC2 Container Instructions for Cascade

## Prerequisites
- WSL2 with Ubuntu 22.04 installed
- CUDA drivers properly installed on Windows host
- Podman installed in WSL2

## Quick Start

1. Make sure you are in the AI_System_Monorepo directory:
   ```bash
   cd /path/to/AI_System_Monorepo
   ```

2. Run the setup script first (only needed once):
   ```bash
   ./containerization_package/setup.sh
   ```

3. Start the PC2 container:
   ```bash
   ./containerization_package/start_pc2.sh
   ```

## Container Details

The PC2 container includes the following agent groups:
- pc2-core-services
- pc2-security-services
- pc2-memory-services
- pc2-task-services
- pc2-ai-services
- pc2-web-services

## Troubleshooting

If you encounter GPU issues:
1. Check that CUDA is working on the host:
   ```bash
   ./containerization_package/scripts/test_host_cuda.sh
   ```

2. If the container fails to access the GPU, try running:
   ```bash
   ./containerization_package/scripts/fix_wsl2_gpu.sh
   ```

3. Verify container GPU access:
   ```bash
   podman exec pc2-container nvidia-smi
   ```

## Stopping the Container

To stop the PC2 container:
```bash
./containerization_package/stop_all.sh
```

## Advanced Configuration

You can modify agent groupings in:
```
pc2_code/config/container_grouping.yaml
```

## Testing Individual Agents

To test the PC2 health monitor outside the container:
```bash
python run_pc2_health_monitor.py
``` 