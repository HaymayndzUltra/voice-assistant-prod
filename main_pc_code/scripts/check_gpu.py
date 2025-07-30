#!/usr/bin/env python3
"""
GPU checker script to verify RTX 4090 is properly configured for the AI System
"""

import os
import sys
import subprocess
import logging
from typing import Dict, List, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gpu_checker")

def run_command(cmd: List[str]) -> Tuple[str, str, int]:
    """Run a command and return stdout, stderr, and the return code."""
    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode
    except Exception as e:
        return "", str(e), 1

def check_nvidia_smi() -> Tuple[bool, Dict[str, Any]]:
    """Check if nvidia-smi is available and get GPU information."""
    stdout, stderr, returncode = run_command(["nvidia-smi", "--query-gpu=name,memory.total,driver_version,cuda_version", "--format=csv,noheader"])
    
    if returncode != 0:
        logger.error(f"Failed to run nvidia-smi: {stderr}")
        return False, {}
    
    # Parse the output to get GPU info
    try:
        gpu_info = {}
        parts = stdout.strip().split(',')
        if len(parts) >= 4:
            gpu_info["name"] = parts[0].strip()
            gpu_info["memory"] = parts[1].strip()
            gpu_info["driver_version"] = parts[2].strip()
            gpu_info["cuda_version"] = parts[3].strip()
            
            # Check if this is an RTX 4090
            "4090" in gpu_info["name"]
            
            return True, gpu_info
        else:
            logger.error("Failed to parse nvidia-smi output")
            return False, {}
    except Exception as e:
        logger.error(f"Error parsing nvidia-smi output: {e}")
        return False, {}

def check_pytorch_cuda() -> Tuple[bool, str]:
    """Check if PyTorch can access CUDA."""
    code = """
import torch
print(f"CUDA Available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA Device Count: {torch.cuda.device_count()}")
    print(f"CUDA Device Name: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Device Capability: {torch.cuda.get_device_capability(0)}")
    print(f"CUDA Version: {torch.version.cuda}")
"""
    
    with open(str(PathManager.get_temp_dir() / "check_pytorch.py"), "w") as f:
        f.write(code)
    
    stdout, stderr, returncode = run_command(["python", str(PathManager.get_temp_dir() / "check_pytorch.py")])
    
    if returncode != 0:
        logger.error(f"Failed to check PyTorch CUDA support: {stderr}")
        return False, stderr
    
    return "CUDA Available: True" in stdout, stdout

def check_llama_cpp_cuda() -> Tuple[bool, str]:
    """Check if llama-cpp-python is built with CUDA support."""
    code = """
from llama_cpp import Llama

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
print("Attempting to load llama_cpp...")
try:
    print(f"CUDA Support: {Llama.args_info()}")
    print("Successfully loaded llama_cpp with CUDA")
    has_cuda = "n_gpu_layers" in dir(Llama) and "prefer_small_models" in dir(Llama)
    print(f"Has GPU acceleration capabilities: {has_cuda}")
except Exception as e:
    print(f"Error: {e}")
"""
    
    with open(str(PathManager.get_temp_dir() / "check_llama_cpp.py"), "w") as f:
        f.write(code)
    
    stdout, stderr, returncode = run_command(["python", str(PathManager.get_temp_dir() / "check_llama_cpp.py")])
    
    if returncode != 0:
        logger.error(f"Failed to check llama-cpp CUDA support: {stderr}")
        return False, stderr
    
    return "Successfully loaded llama_cpp with CUDA" in stdout, stdout

def check_podman_nvidia() -> Tuple[bool, str]:
    """Check if podman can use NVIDIA runtime."""
    stdout, stderr, returncode = run_command(["podman", "info"])
    
    if returncode != 0:
        logger.error(f"Failed to run podman info: {stderr}")
        return False, stderr
    
    # Check if nvidia runtime is available
    has_nvidia = "nvidia" in stdout
    
    return has_nvidia, stdout

def check_environment_variables() -> Dict[str, str]:
    """Check relevant environment variables for GPU/CUDA configuration."""
    variables = [
        "NVIDIA_VISIBLE_DEVICES", "NVIDIA_DRIVER_CAPABILITIES",
        "CUDA_VISIBLE_DEVICES", "LD_LIBRARY_PATH"
    ]
    
    result = {}
    for var in variables:
        result[var] = os.environ.get(var, "Not set")
    
    return result

def main():
    """Main entry point for the GPU checker script."""
    print("\n" + "="*50)
    print("RTX 4090 GPU CONFIGURATION CHECKER")
    print("="*50 + "\n")
    
    # Check NVIDIA SMI
    print("1. Checking NVIDIA driver and GPU...")
    has_nvidia, gpu_info = check_nvidia_smi()
    
    if has_nvidia:
        print(f"✓ NVIDIA GPU detected: {gpu_info.get('name', 'Unknown')}")
        print(f"✓ GPU Memory: {gpu_info.get('memory', 'Unknown')}")
        print(f"✓ Driver Version: {gpu_info.get('driver_version', 'Unknown')}")
        print(f"✓ CUDA Version: {gpu_info.get('cuda_version', 'Unknown')}")
        
        if "4090" in gpu_info.get('name', ''):
            print("✓ RTX 4090 confirmed!")
        else:
            print("⚠ This is not an RTX 4090. Using alternative GPU.")
    else:
        print("✗ NVIDIA GPU not detected or drivers not installed properly.")
    
    print("\n" + "-"*50)
    
    # Check PyTorch CUDA
    print("\n2. Checking PyTorch CUDA support...")
    pytorch_cuda, pytorch_output = check_pytorch_cuda()
    
    if pytorch_cuda:
        print("✓ PyTorch can access CUDA:")
        for line in pytorch_output.split('\n'):
            if line.strip():
                print(f"  {line.strip()}")
    else:
        print("✗ PyTorch cannot access CUDA:")
        print(pytorch_output)
    
    print("\n" + "-"*50)
    
    # Check llama-cpp-python CUDA
    print("\n3. Checking llama-cpp-python CUDA support...")
    llama_cuda, llama_output = check_llama_cpp_cuda()
    
    if llama_cuda:
        print("✓ llama-cpp-python has CUDA support:")
        for line in llama_output.split('\n'):
            if line.strip() and "Error" not in line:
                print(f"  {line.strip()}")
    else:
        print("✗ llama-cpp-python does not have CUDA support or is not installed:")
        print(llama_output)
    
    print("\n" + "-"*50)
    
    # Check Podman NVIDIA support
    print("\n4. Checking Podman NVIDIA support...")
    podman_nvidia, _ = check_podman_nvidia()
    
    if podman_nvidia:
        print("✓ Podman has NVIDIA runtime support.")
    else:
        print("✗ Podman does not have NVIDIA runtime support.")
        print("  This is required to use GPU in containers.")
        print("  Install podman-nvidia package or configure nvidia-container-runtime.")
    
    print("\n" + "-"*50)
    
    # Check environment variables
    print("\n5. Environment variables:")
    env_vars = check_environment_variables()
    
    for var, value in env_vars.items():
        print(f"  {var}: {value}")
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    if has_nvidia and pytorch_cuda and llama_cuda and podman_nvidia:
        print("\n✓ SUCCESS: RTX 4090 / GPU is properly configured for the AI System.")
        print("  All LLM dependencies should work properly with GPU acceleration.")
        return 0
    else:
        print("\n⚠ WARNING: Some GPU configuration issues were detected.")
        print("  Review the output above and fix any issues marked with ✗.")
        if not has_nvidia:
            print("  - NVIDIA driver issue: Install proper NVIDIA drivers for your GPU.")
        if not pytorch_cuda:
            print("  - PyTorch CUDA issue: Reinstall PyTorch with CUDA support.")
        if not llama_cuda:
            print("  - llama-cpp-python issue: Reinstall with CMAKE_ARGS=\"-DLLAMA_CUBLAS=on\".")
        if not podman_nvidia:
            print("  - Podman NVIDIA issue: Install nvidia-container-runtime and configure Podman.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 