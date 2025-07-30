#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PyTorch Installation Script for NLLB Translator
- Installs PyTorch with CUDA support
- Installs transformers library for NLLB model
- Validates the installation
- Provides clear instructions and feedback
"""

import sys
import subprocess
import platform
import argparse
from colorama import init, Fore, Style

# Initialize colorama for colored console output
init()

def print_colored(text, color=Fore.WHITE, style=Style.NORMAL):
    """Print colored text to console"""
    print(f"{style}{color}{text}{Style.RESET_ALL}")

def check_cuda_available():
    """Check if CUDA is available on the system"""
    try:
        # Try to run nvidia-smi to check for CUDA GPUs
        result = subprocess.run(["nvidia-smi"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            # Parse the output to get GPU info
            lines = result.stdout.split('\n')
            gpu_info = []
            for line in lines:
                if "NVIDIA" in line and "%" in line:
                    gpu_info.append(line.strip())
            
            if gpu_info:
                print_colored("✅ CUDA GPUs detected:", Fore.GREEN, Style.BRIGHT)
                for gpu in gpu_info:
                    print_colored(f"   {gpu}", Fore.GREEN)
                return True
            else:
                print_colored("❌ No NVIDIA GPUs detected in nvidia-smi output.", Fore.YELLOW)
                return False
        else:
            print_colored("❌ nvidia-smi command failed. CUDA may not be installed.", Fore.RED)
            return False
    except FileNotFoundError:
        print_colored("❌ nvidia-smi not found. CUDA is not installed or not in PATH.", Fore.RED)
        return False

def install_pytorch(cuda_version="11.8"):
    """Install PyTorch with the specified CUDA version"""
    print_colored("\n=== Installing PyTorch with CUDA support ===", Fore.CYAN, Style.BRIGHT)
    
    # Determine the appropriate PyTorch installation command based on CUDA version
    if cuda_version == "11.8":
        cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu118"]
    elif cuda_version == "12.1":
        cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu121"]
    elif cuda_version == "cpu":
        cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cpu"]
    else:
        print_colored(f"❌ Unsupported CUDA version: {cuda_version}", Fore.RED)
        return False
    
    print_colored(f"Installing PyTorch with CUDA {cuda_version}...", Fore.YELLOW)
    print_colored(f"Command: {' '.join(cmd)}", Fore.BLUE)
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print_colored("✅ PyTorch installation completed successfully.", Fore.GREEN, Style.BRIGHT)
            return True
        else:
            print_colored(f"❌ PyTorch installation failed with error:", Fore.RED)
            print_colored(result.stderr, Fore.RED)
            return False
    except Exception as e:
        print_colored(f"❌ Error during PyTorch installation: {str(e)}", Fore.RED)
        return False

def install_transformers():
    """Install the transformers library for NLLB model"""
    print_colored("\n=== Installing Transformers Library ===", Fore.CYAN, Style.BRIGHT)
    
    cmd = [sys.executable, "-m", "pip", "install", "transformers"]
    
    print_colored("Installing transformers library...", Fore.YELLOW)
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print_colored("✅ Transformers installation completed successfully.", Fore.GREEN, Style.BRIGHT)
            return True
        else:
            print_colored(f"❌ Transformers installation failed with error:", Fore.RED)
            print_colored(result.stderr, Fore.RED)
            return False
    except Exception as e:
        print_colored(f"❌ Error during Transformers installation: {str(e)}", Fore.RED)
        return False

def validate_installation():
    """Validate that PyTorch and transformers are installed correctly"""
    print_colored("\n=== Validating Installation ===", Fore.CYAN, Style.BRIGHT)
    
    # Check PyTorch
    print_colored("Checking PyTorch installation...", Fore.YELLOW)
    try:
        import torch
    except ImportError as e:
        print(f"Import error: {e}")
        print_colored(f"✅ PyTorch {torch.__version__} is installed.", Fore.GREEN)
        
        # Check CUDA availability in PyTorch
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
            print_colored(f"✅ CUDA is available with PyTorch. Found {device_count} device(s).", Fore.GREEN)
            print_colored(f"   Device: {device_name}", Fore.GREEN)
            print_colored(f"   CUDA Version: {torch.version.cuda}", Fore.GREEN)
        else:
            print_colored("⚠️ CUDA is not available with PyTorch. Using CPU only.", Fore.YELLOW)
    except ImportError:
        print_colored("❌ PyTorch is not installed correctly.", Fore.RED)
        return False
    
    # Check transformers
    print_colored("\nChecking transformers installation...", Fore.YELLOW)
    try:
        import transformers
    except ImportError as e:
        print(f"Import error: {e}")
        print_colored(f"✅ Transformers {transformers.__version__} is installed.", Fore.GREEN)
    except ImportError:
        print_colored("❌ Transformers is not installed correctly.", Fore.RED)
        return False
    
    # Try to load a small model to verify everything works
    print_colored("\nTesting model loading capability...", Fore.YELLOW)
    try:
        from transformers import AutoTokenizer
    except ImportError as e:
        print(f"Import error: {e}")
        
        # Load a small tokenizer as a test (much faster than loading a full model)
        print_colored("Loading a test tokenizer...", Fore.BLUE)
        tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M", use_fast=False)
        print_colored("✅ Successfully loaded test tokenizer. Installation is working correctly!", Fore.GREEN, Style.BRIGHT)
        return True
    except Exception as e:
        print_colored(f"❌ Error during model loading test: {str(e)}", Fore.RED)
        return False

def main():
    """Main function to install and validate PyTorch for NLLB"""
    parser = argparse.ArgumentParser(description="Install PyTorch and dependencies for NLLB Translator")
    parser.add_argument("--cuda", choices=["11.8", "12.1", "cpu"], default="11.8", 
                        help="CUDA version to use (11.8, 12.1, or 'cpu' for CPU-only)")
    parser.add_argument("--skip-validation", action="store_true", 
                        help="Skip the validation step")
    args = parser.parse_args()
    
    print_colored("\n" + "="*80, Fore.CYAN)
    print_colored("  NLLB TRANSLATOR - PYTORCH INSTALLATION SCRIPT", Fore.CYAN, Style.BRIGHT)
    print_colored("="*80, Fore.CYAN)
    print_colored(f"System: {platform.system()} {platform.release()}", Fore.WHITE)
    print_colored(f"Python: {sys.version.split()[0]}", Fore.WHITE)
    print_colored(f"CUDA Version: {args.cuda}", Fore.WHITE)
    print_colored("="*80 + "\n", Fore.CYAN)
    
    # Check for CUDA if not using CPU
    if args.cuda != "cpu":
        has_cuda = check_cuda_available()
        if not has_cuda:
            print_colored("\n⚠️ CUDA not detected but CUDA installation requested.", Fore.YELLOW, Style.BRIGHT)
            response = input("Continue with CUDA installation anyway? (y/n): ").lower()
            if response != 'y':
                print_colored("Switching to CPU installation...", Fore.YELLOW)
                args.cuda = "cpu"
    
    # Install PyTorch
    pytorch_success = install_pytorch(args.cuda)
    if not pytorch_success:
        print_colored("\n❌ PyTorch installation failed. Please check the errors above.", Fore.RED, Style.BRIGHT)
        return
    
    # Install transformers
    transformers_success = install_transformers()
    if not transformers_success:
        print_colored("\n❌ Transformers installation failed. Please check the errors above.", Fore.RED, Style.BRIGHT)
        return
    
    # Validate installation
    if not args.skip_validation:
        validation_success = validate_installation()
        if validation_success:
            print_colored("\n✅ Installation completed successfully!", Fore.GREEN, Style.BRIGHT)
            print_colored("\nYou can now run the NLLB Translation Adapter with:", Fore.CYAN)
            print_colored("python agents/llm_translation_adapter.py", Fore.CYAN)
        else:
            print_colored("\n⚠️ Installation completed but validation failed.", Fore.YELLOW, Style.BRIGHT)
            print_colored("Please check the errors above and try to resolve them.", Fore.YELLOW)
    else:
        print_colored("\n⚠️ Validation skipped. Installation may or may not work correctly.", Fore.YELLOW, Style.BRIGHT)
    
    print_colored("\nNote: The first time you run the adapter, it will download the NLLB model (~5GB).", Fore.CYAN)
    print_colored("This may take some time depending on your internet connection.", Fore.CYAN)

if __name__ == "__main__":
    main()
