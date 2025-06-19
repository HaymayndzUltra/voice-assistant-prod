import torch
import sys

print("Python version:", sys.version)
print("PyTorch version:", torch.__version__)
print("CUDA Available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("CUDA Device Count:", torch.cuda.device_count())
    print("CUDA Device Name:", torch.cuda.get_device_name(0))
    props = torch.cuda.get_device_properties(0)
    print("Total Memory:", props.total_memory / 1024 / 1024 / 1024, "GB")
    print("CUDA Capability:", f"{props.major}.{props.minor}")
else:
    print("No CUDA device available")
