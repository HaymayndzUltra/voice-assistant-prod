#!/bin/bash
# Script to test using the host's CUDA installation from a container

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== Testing Host CUDA from Container =====${NC}"

# Check if podman is installed
if ! command -v podman &> /dev/null; then
    echo -e "${RED}Error: podman not found. Please install podman first.${NC}"
    exit 1
fi

# Check if CUDA is installed on the host
echo -e "${GREEN}Host CUDA Information:${NC}"
if [ -d "/usr/local/cuda-12.1" ] || [ -d "/usr/lib/cuda" ]; then
    echo "CUDA installation found on host"
    ls -la /usr/local/cuda* || echo "No CUDA in /usr/local"
    ls -la /usr/lib/cuda* || echo "No CUDA in /usr/lib"
    
    # Check nvidia-smi
    if command -v nvidia-smi &> /dev/null; then
        echo -e "\n${GREEN}Host GPU Information:${NC}"
        nvidia-smi
    else
        echo -e "${YELLOW}nvidia-smi not found on host${NC}"
    fi
else
    echo -e "${YELLOW}CUDA installation not found in standard locations${NC}"
    # Check for CUDA libraries
    echo -e "\nChecking for CUDA libraries:"
    find /usr -name "libcuda*.so*" | head -n 5
fi

# Create a simple script to check CUDA in container
cat > /tmp/check_cuda.sh << 'EOF'
#!/bin/bash
echo "Container CUDA Check"
echo "===================="
echo "Checking for NVIDIA driver files:"
ls -la /dev/nvidia* 2>/dev/null || echo "No NVIDIA device files found"

echo -e "\nChecking for CUDA libraries:"
find /usr -name "libcuda*.so*" 2>/dev/null | head -n 5 || echo "No CUDA libraries found"

echo -e "\nChecking for nvidia-smi:"
which nvidia-smi 2>/dev/null || echo "nvidia-smi not found"
nvidia-smi 2>/dev/null || echo "nvidia-smi failed to run"

echo -e "\nChecking environment variables:"
env | grep -i cuda || echo "No CUDA environment variables found"
env | grep -i nvidia || echo "No NVIDIA environment variables found"

echo -e "\nSystem information:"
uname -a
EOF

chmod +x /tmp/check_cuda.sh

echo -e "\n${GREEN}Running container with host CUDA access...${NC}"
echo -e "${YELLOW}This will pull a small Ubuntu container and test CUDA access.${NC}"

# Run a container with host CUDA access
podman run --rm \
    --privileged \
    -e NVIDIA_VISIBLE_DEVICES=all \
    -v /usr/bin/nvidia-smi:/usr/bin/nvidia-smi \
    -v /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1 \
    -v /usr/lib/x86_64-linux-gnu/libnvidia-ml.so.575.57.08:/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.575.57.08 \
    -v /usr/lib/wsl/lib/libnvidia-ml.so.1:/usr/lib/wsl/lib/libnvidia-ml.so.1 \
    -v /tmp/check_cuda.sh:/check_cuda.sh \
    docker.io/ubuntu:22.04 /check_cuda.sh

echo -e "\n${GREEN}===== Test Complete =====${NC}" 