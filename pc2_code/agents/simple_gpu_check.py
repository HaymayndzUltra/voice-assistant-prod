print("Starting GPU check...")
try:
    import torch
    except ImportError as e:
        print(f"Import error: {e}")
    print("PyTorch imported successfully")
    print("CUDA Available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("Device count:", torch.cuda.device_count())
        print("Device name:", torch.cuda.get_device_name(0))
    else:
        print("No CUDA devices detected")
except Exception as e:
    print(f"Error: {e}")
    
print("GPU check complete")
