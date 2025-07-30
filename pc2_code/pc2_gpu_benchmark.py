#!/usr/bin/env python
"""
PC2 GPU Performance Test
- Verifies PyTorch CUDA availability
- Tests basic tensor operations
- Measures computation time for matrix multiplication
- Includes both CPU and GPU comparisons
"""
import torch
import time
import psutil
import platform
from datetime import datetime

def print_fancy_header(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def get_system_info():
    """Get basic system information"""
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "total_memory_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "available_memory_gb": round(psutil.virtual_memory().available / (1024 ** 3), 2),
        "date_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def print_system_info(info):
    print(f"System: {info['platform']}")
    print(f"Processor: {info['processor']}")
    print(f"Python Version: {info['python_version']}")
    print(f"Total Memory: {info['total_memory_gb']} GB")
    print(f"Available Memory: {info['available_memory_gb']} GB")
    print(f"Date/Time: {info['date_time']}")

def check_cuda():
    """Check if CUDA is available and print device info"""
    print("\n== CUDA Information ==")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        device_count = torch.cuda.device_count()
        print(f"CUDA Device Count: {device_count}")
        
        for i in range(device_count):
            print(f"\nCUDA Device {i}:")
            print(f"  Name: {torch.cuda.get_device_name(i)}")
            print(f"  Capability: {torch.cuda.get_device_capability(i)}")
            
            # Get memory info
            torch.cuda.set_device(i)
            torch.cuda.empty_cache()
            memory_allocated = torch.cuda.memory_allocated(i) / (1024 ** 2)
            memory_reserved = torch.cuda.memory_reserved(i) / (1024 ** 2)
            
            print(f"  Memory Allocated: {memory_allocated:.2f} MB")
            print(f"  Memory Reserved: {memory_reserved:.2f} MB")
            
            # PyTorch version
            print(f"\nPyTorch Version: {torch.__version__}")

def run_benchmark(sizes=[1000, 2000, 4000]):
    """Run matrix multiplication benchmark on CPU and GPU"""
    print("\n== Performance Benchmark ==")
    print(f"{'Size':<10} {'Device':<8} {'Time (ms)':<12} {'GFLOPS':<10}")
    print("-" * 40)
    
    for size in sizes:
        # Compute FLOPS for matrix multiplication (2*n^3 - n^2)
        flops = 2 * (size ** 3) - (size ** 2)
        
        # CPU test
        a_cpu = torch.randn(size, size)
        b_cpu = torch.randn(size, size)
        
        start = time.time()
        torch.matmul(a_cpu, b_cpu)
        cpu_time = (time.time() - start) * 1000  # ms
        cpu_gflops = (flops / (cpu_time / 1000)) / 1e9
        
        print(f"{size:<10} {'CPU':<8} {cpu_time:.2f} ms     {cpu_gflops:.2f}")
        
        # GPU test if available
        if torch.cuda.is_available():
            a_gpu = torch.randn(size, size, device='cuda')
            b_gpu = torch.randn(size, size, device='cuda')
            
            # Warmup
            torch.matmul(a_gpu, b_gpu)
            torch.cuda.synchronize()
            
            start = time.time()
            torch.matmul(a_gpu, b_gpu)
            torch.cuda.synchronize()
            gpu_time = (time.time() - start) * 1000  # ms
            gpu_gflops = (flops / (gpu_time / 1000)) / 1e9
            
            print(f"{size:<10} {'GPU':<8} {gpu_time:.2f} ms     {gpu_gflops:.2f}")
            
            # Calculate speedup
            speedup = cpu_time / gpu_time
            print(f"{'':<10} {'Speedup':<8} {speedup:.2f}x")
        
        print("-" * 40)

def main():
    print_fancy_header("PC2 GPU PERFORMANCE TEST")
    
    # Print system info
    system_info = get_system_info()
    print_system_info(system_info)
    
    # Check CUDA
    check_cuda()
    
    # Run benchmarks
    run_benchmark()
    
    print("\n== Test Complete ==")
    if torch.cuda.is_available():
        print("✅ GPU is working correctly with PyTorch")
        print(f"✅ Using device: {torch.cuda.get_device_name(0)}")
    else:
        print("❌ CUDA is not available. PyTorch is running on CPU only.")
        print("   Please check CUDA installation and PyTorch version.")

if __name__ == "__main__":
    main()
