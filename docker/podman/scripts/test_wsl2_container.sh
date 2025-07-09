#!/bin/bash
# Script to test a container in WSL2 environment

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== Testing Container in WSL2 Environment =====${NC}"

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    echo -e "${RED}Error: podman not found. Please install podman first.${NC}"
    exit 1
fi

# Check if nvidia-smi is available on the host
echo -e "${GREEN}Host GPU Information:${NC}"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
else
    echo -e "${RED}Error: nvidia-smi not found on the host.${NC}"
    exit 1
fi

# Create a simple Python script for environment testing
cat > /tmp/env_check.py << 'EOF'
#!/usr/bin/env python3
import os
import sys
import platform
import subprocess

print("Container Environment Check")
print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")

# Check environment variables
print("\nEnvironment Variables:")
for var in ["PYTHONPATH", "NVIDIA_VISIBLE_DEVICES", "CUDA_VISIBLE_DEVICES"]:
    print(f"{var}: {os.environ.get(var, 'Not set')}")

# List directories
print("\nDirectory Listing:")
for dir_path in ["/app", "/home"]:
    try:
        print(f"\nContents of {dir_path}:")
        print(subprocess.check_output(["ls", "-la", dir_path], stderr=subprocess.STDOUT).decode())
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Error listing {dir_path}: {e}")

print("\nContainer Check Complete")
EOF

chmod +x /tmp/env_check.py

echo -e "\n${GREEN}Running container test in WSL2 environment...${NC}"
echo -e "${YELLOW}This will pull a small Python container and test the environment.${NC}"

# Create a test directory and file
mkdir -p /tmp/test_mount
echo "Hello from the host!" > /tmp/test_mount/test.txt

# Run a simple container to test environment
podman run --rm \
    -e PYTHONPATH=/app \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -v /tmp/env_check.py:/env_check.py \
    -v /tmp/test_mount:/app/test_mount \
    docker.io/python:3.10-slim /env_check.py

echo -e "\n${GREEN}===== Test Complete =====${NC}" 