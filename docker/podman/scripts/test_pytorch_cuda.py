#!/usr/bin/env python3
"""
Test script to verify PyTorch CUDA functionality in a container.
"""

import os
import sys
import time
import platform

def print_separator():
    print("=" * 60)

def print_header(title):
    print_separator()
    print(f" {title} ".center(60, "="))
    print_separator()

def print_section(title):
    print("\n" + "-" * 60)
    print(f" {title} ".center(60, "-"))
    print("-" * 60)

def check_system_info():
    print_section("System Information")
    print(f"Python version: {sys.version}")
    print(f"Platform: {platform.platform()}")
    print(f"Machine: {platform.machine()}")
    print(f"Processor: {platform.processor()}")

def check_environment_variables():
    print_section("Environment Variables")
    for var in ["CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES", "PYTHONPATH", "CUDA_HOME", "LD_LIBRARY_PATH"]:
        print(f"{var}: {os.environ.get(var, 'Not set')}")

def check_cuda_libraries():
    print_section("CUDA Libraries")
    cuda_paths = [
        "/usr/local/cuda",
        "/usr/local/cuda-12.1",
        "/usr/lib/cuda",
    ]
    
    for path in cuda_paths:
        if os.path.exists(path):
            print(f"{path}: Found")
            try:
                import subprocess
                result = subprocess.run(["ls", "-la", path], capture_output=True, text=True)
                print(result.stdout)
            except Exception as e:
                print(f"Error listing directory: {e}")
        else:
            print(f"{path}: Not found")

def check_pytorch_cuda():
    print_section("PyTorch CUDA Support")
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA version: {torch.version.cuda}")
            print(f"CUDA device count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"CUDA device {i} name: {torch.cuda.get_device_name(i)}")
                print(f"CUDA device {i} capability: {torch.cuda.get_device_capability(i)}")
            
            # Test CUDA computation
            print("\nTesting CUDA computation...")
            start_time = time.time()
            
            # Create tensors on GPU
            x = torch.rand(1000, 1000).cuda()
            y = torch.rand(1000, 1000).cuda()
            
            # Perform matrix multiplication
            z = torch.matmul(x, y)
            
            # Ensure computation is complete
            torch.cuda.synchronize()
            
            end_time = time.time()
            print(f"CUDA computation successful on device: {z.device}")
            print(f"Computation time: {end_time - start_time:.4f} seconds")
            
            # Test memory allocation
            print("\nTesting GPU memory allocation...")
            print(f"Memory allocated: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")
            print(f"Memory reserved: {torch.cuda.memory_reserved() / 1024**2:.2f} MB")
            
            # Free memory
            del x, y, z
            torch.cuda.empty_cache()
            print(f"After cleanup - Memory allocated: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")
        else:
            print("CUDA is not available. Check your PyTorch installation and CUDA setup.")
    except ImportError:
        print("PyTorch not installed. Install PyTorch with CUDA support.")
    except Exception as e:
        print(f"Error testing PyTorch CUDA: {e}")

def check_nvidia_smi():
    print_section("NVIDIA-SMI")
    try:
        import subprocess
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"Error running nvidia-smi: {result.stderr}")
    except Exception as e:
        print(f"Error running nvidia-smi: {e}")

def main():
    print_header("PyTorch CUDA Test")
    
    check_system_info()
    check_environment_variables()
    check_cuda_libraries()
    check_nvidia_smi()
    check_pytorch_cuda()
    
    print_header("Test Complete")

if __name__ == "__main__":
    main() 