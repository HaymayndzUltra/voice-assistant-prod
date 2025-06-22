import torch
import os

print("=" * 50)
print("PyTorch CUDA Checker")
print("=" * 50)

# Basic PyTorch info
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

# Environment variables
print("\nEnvironment Variables:")
cuda_path = os.environ.get('CUDA_PATH', 'Not set')
cuda_home = os.environ.get('CUDA_HOME', 'Not set')
print(f"CUDA_PATH: {cuda_path}")
print(f"CUDA_HOME: {cuda_home}")

# Compiled with CUDA?
if hasattr(torch, 'version') and hasattr(torch.version, 'cuda'):
    print(f"\nPyTorch compiled with CUDA: {torch.version.cuda}")
else:
    print("\nPyTorch CUDA version information not available.")

# Try to initialize CUDA
try:
    if torch.cuda.is_available():
        device_count = torch.cuda.device_count()
        print(f"\nCUDA Device Count: {device_count}")
        
        for i in range(device_count):
            device_name = torch.cuda.get_device_name(i)
            capability = torch.cuda.get_device_capability(i)
            print(f"Device {i}: {device_name}, Capability: {capability[0]}.{capability[1]}")
            
            # Create a simple tensor on the GPU
            print("Attempting to create a tensor on the GPU...")
            x = torch.tensor([1.0, 2.0, 3.0], device=f'cuda:{i}')
            print(f"Tensor created successfully on cuda:{i}: {x}")
    else:
        print("\nCUDA is not available. PyTorch will run on CPU only.")
        print("\nPossible reasons:")
        print("1. NVIDIA drivers not installed or outdated")
        print("2. CUDA Toolkit not installed")
        print("3. PyTorch installed without CUDA support")
        print("4. CUDA version mismatch between PyTorch and installed drivers")
except Exception as e:
    print(f"\nError initializing CUDA: {e}")

print("\n" + "=" * 50)
print("Recommendations:")
print("1. Check if NVIDIA drivers are installed: nvidia-smi")
print("2. Verify CUDA Toolkit installation")
print("3. Reinstall PyTorch with CUDA support:")
print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
print("   (Replace cu118 with your CUDA version if needed)")
print("=" * 50)
