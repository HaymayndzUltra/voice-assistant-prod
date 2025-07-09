#!/bin/bash
# Script to test a minimal container with basic GPU detection

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== Testing Minimal Container =====${NC}"

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    echo -e "${RED}Error: podman not found. Please install podman first.${NC}"
    exit 1
fi

# Create a simple Python script for GPU detection
cat > /tmp/gpu_check.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import subprocess

print("Python GPU Detection Script")
print(f"Python version: {sys.version}")

# Check environment variables
print("\nEnvironment Variables:")
for var in ["NVIDIA_VISIBLE_DEVICES", "CUDA_VISIBLE_DEVICES"]:
    print(f"{var}: {os.environ.get(var, 'Not set')}")

# Check if nvidia-smi is available
print("\nChecking for nvidia-smi:")
try:
    output = subprocess.check_output(["which", "nvidia-smi"], stderr=subprocess.STDOUT).decode().strip()
    print(f"nvidia-smi found at: {output}")
    
    # Try to run nvidia-smi
    try:
        nvidia_output = subprocess.check_output(["nvidia-smi"], stderr=subprocess.STDOUT).decode()
        print("\nnvidia-smi output:")
        print(nvidia_output)
    except subprocess.CalledProcessError as e:
        print(f"Error running nvidia-smi: {e}")
except subprocess.CalledProcessError:
    print("nvidia-smi not found")

# Check device access
print("\nChecking NVIDIA device files:")
nvidia_devices = ["/dev/nvidia0", "/dev/nvidiactl", "/dev/nvidia-uvm"]
for device in nvidia_devices:
    if os.path.exists(device):
        print(f"{device}: Exists")
    else:
        print(f"{device}: Not found")

print("\nGPU Detection Complete")
EOF

chmod +x /tmp/gpu_check.py

echo -e "\n${GREEN}Running minimal container test...${NC}"
echo -e "${YELLOW}This will pull a small Python container and test GPU detection.${NC}"

# Run a simple container to test GPU detection
podman run --rm \
    --device /dev/nvidia0:/dev/nvidia0 \
    --device /dev/nvidiactl:/dev/nvidiactl \
    --device /dev/nvidia-uvm:/dev/nvidia-uvm \
    --security-opt=label=disable \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -v /tmp/gpu_check.py:/gpu_check.py \
    docker.io/python:3.10-slim /gpu_check.py

echo -e "\n${GREEN}===== Test Complete =====${NC}" 