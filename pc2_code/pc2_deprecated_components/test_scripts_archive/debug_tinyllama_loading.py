"""
Diagnostic script for TinyLlama model loading issues
Tests different loading approaches to isolate "Cannot copy out of meta tensor" error
"""
import sys
import os
import logging
import torch
import traceback
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TinyLlamaDebug")

def print_environment_info():
    """Print detailed environment information to help diagnose the issue"""
    logger.info("=== Environment Information ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"PyTorch version: {torch.__version__}")
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"CUDA version: {torch.version.cuda}")
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    
    try:
        import transformers
        logger.info(f"Transformers version: {transformers.__version__}")
    except ImportError:
        logger.info("Transformers not installed")
    
    try:
        import accelerate
        logger.info(f"Accelerate version: {accelerate.__version__}")
    except ImportError:
        logger.info("Accelerate not installed")

def test_load_approach1():
    """Test basic model loading approach (standard from_pretrained)"""
    logger.info("\n=== Testing Approach 1: Standard Loading ===")
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading tokenizer from {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        logger.info(f"Loading model from {model_name} to {device}")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        )
        
        # Move model to device
        logger.info(f"Moving model to {device}")
        model.to(device)
        
        # Test tokenization
        logger.info("Testing tokenization")
        test_input = "Hello, world!"
        tokens = tokenizer(test_input, return_tensors="pt").to(device)
        logger.info(f"Tokenized input shape: {tokens['input_ids'].shape}")
        
        # Test simple generation
        logger.info("Testing generation")
        with torch.no_grad():
            output = model.generate(tokens["input_ids"], max_new_tokens=10)
        
        # Decode output
        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        logger.info(f"Generated text: {decoded}")
        
        logger.info("Approach 1: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"Approach 1 failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_load_approach2():
    """Test loading with device_map='auto' approach"""
    logger.info("\n=== Testing Approach 2: Using device_map='auto' ===")
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        
        logger.info(f"Loading tokenizer from {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        logger.info(f"Loading model with device_map='auto'")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        
        # Test tokenization
        logger.info("Testing tokenization")
        test_input = "Hello, world!"
        tokens = tokenizer(test_input, return_tensors="pt")
        if torch.cuda.is_available():
            tokens = tokens.to("cuda:0")
        logger.info(f"Tokenized input shape: {tokens['input_ids'].shape}")
        
        # Test simple generation
        logger.info("Testing generation")
        with torch.no_grad():
            output = model.generate(tokens["input_ids"], max_new_tokens=10)
        
        # Decode output
        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        logger.info(f"Generated text: {decoded}")
        
        logger.info("Approach 2: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"Approach 2 failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_load_approach3():
    """Test loading without low_cpu_mem_usage"""
    logger.info("\n=== Testing Approach 3: Without low_cpu_mem_usage ===")
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading tokenizer from {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        
        logger.info(f"Loading model without low_cpu_mem_usage")
        # Explicitly NOT using low_cpu_mem_usage
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            # No low_cpu_mem_usage parameter
        )
        
        # Move model to device
        logger.info(f"Moving model to {device}")
        model.to(device)
        
        # Test tokenization
        logger.info("Testing tokenization")
        test_input = "Hello, world!"
        tokens = tokenizer(test_input, return_tensors="pt").to(device)
        logger.info(f"Tokenized input shape: {tokens['input_ids'].shape}")
        
        # Test simple generation
        logger.info("Testing generation")
        with torch.no_grad():
            output = model.generate(tokens["input_ids"], max_new_tokens=10)
        
        # Decode output
        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        logger.info(f"Generated text: {decoded}")
        
        logger.info("Approach 3: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"Approach 3 failed: {e}")
        logger.error(traceback.format_exc())
        return False

def test_load_approach4():
    """Test loading with trust_remote_code=True"""
    logger.info("\n=== Testing Approach 4: With trust_remote_code=True ===")
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading tokenizer from {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        logger.info(f"Loading model with trust_remote_code=True")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            trust_remote_code=True
        )
        
        # Move model to device
        logger.info(f"Moving model to {device}")
        model.to(device)
        
        # Test tokenization
        logger.info("Testing tokenization")
        test_input = "Hello, world!"
        tokens = tokenizer(test_input, return_tensors="pt").to(device)
        logger.info(f"Tokenized input shape: {tokens['input_ids'].shape}")
        
        # Test simple generation
        logger.info("Testing generation")
        with torch.no_grad():
            output = model.generate(tokens["input_ids"], max_new_tokens=10)
        
        # Decode output
        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        logger.info(f"Generated text: {decoded}")
        
        logger.info("Approach 4: SUCCESS")
        return True
    except Exception as e:
        logger.error(f"Approach 4 failed: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print_environment_info()
    
    # Test different approaches
    results = []
    results.append(("Approach 1: Standard Loading", test_load_approach1()))
    results.append(("Approach 2: Using device_map='auto'", test_load_approach2()))
    results.append(("Approach 3: Without low_cpu_mem_usage", test_load_approach3()))
    results.append(("Approach 4: With trust_remote_code=True", test_load_approach4()))
    
    # Print summary
    logger.info("\n=== RESULTS SUMMARY ===")
    for name, success in results:
        logger.info(f"{name}: {'SUCCESS' if success else 'FAILED'}")
    
    # Check if any approach succeeded
    if any(success for _, success in results):
        logger.info("\nAt least one approach succeeded. Use the successful approach in tinyllama_service.py")
    else:
        logger.info("\nAll approaches failed. Consider checking for library compatibility issues or GPU memory constraints.")
