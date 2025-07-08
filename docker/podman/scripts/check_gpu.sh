#!/bin/bash
# Script to check GPU status in the container

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== GPU Status Check =====${NC}"

# Check if nvidia-smi is available
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}Error: nvidia-smi not found. NVIDIA drivers may not be installed or accessible.${NC}"
    echo -e "${YELLOW}Make sure the container has access to NVIDIA devices and runtime.${NC}"
    exit 1
fi

# Check GPU information
echo -e "${GREEN}GPU Information:${NC}"
nvidia-smi

# Check CUDA version
echo -e "\n${GREEN}CUDA Version:${NC}"
if command -v nvcc &> /dev/null; then
    nvcc --version
else
    echo -e "${YELLOW}nvcc not found. Only runtime CUDA libraries may be installed.${NC}"
    
    # Try to get CUDA version from nvidia-smi
    CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}')
    if [ -n "$CUDA_VERSION" ]; then
        echo -e "CUDA Runtime Version: $CUDA_VERSION"
    fi
fi

# Check PyTorch CUDA support
echo -e "\n${GREEN}PyTorch CUDA Support:${NC}"
python3 -c "
import sys
try:
    import torch
    print(f'PyTorch version: {torch.__version__}')
    print(f'CUDA available: {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'CUDA version: {torch.version.cuda}')
        print(f'CUDA device count: {torch.cuda.device_count()}')
        print(f'CUDA device name: {torch.cuda.get_device_name(0)}')
        print(f'CUDA device capability: {torch.cuda.get_device_capability(0)}')
        
        # Test CUDA computation
        print('\nTesting CUDA computation...')
        x = torch.rand(5, 3).cuda()
        y = torch.rand(5, 3).cuda()
        z = x + y
        print(f'CUDA computation successful: {z.device}')
except ImportError:
    print('PyTorch not installed or CUDA support not available')
except Exception as e:
    print(f'Error testing PyTorch CUDA support: {e}')
"

# Check llama-cpp-python CUDA support
echo -e "\n${GREEN}llama-cpp-python CUDA Support:${NC}"
python3 -c "
import sys
try:
    from llama_cpp import Llama
    print('llama-cpp-python is installed')
    
    # Check if CUDA methods are available
    has_cuda = hasattr(Llama, 'n_gpu_layers')
    print(f'CUDA support available: {has_cuda}')
    
    if has_cuda:
        print('llama-cpp-python was built with CUDA support')
except ImportError:
    print('llama-cpp-python not installed')
except Exception as e:
    print(f'Error testing llama-cpp-python CUDA support: {e}')
"

# Check GPU memory usage
echo -e "\n${GREEN}GPU Memory Usage:${NC}"
nvidia-smi --query-gpu=memory.used,memory.total,memory.free --format=csv

echo -e "\n${GREEN}===== GPU Status Check Complete =====${NC}" 