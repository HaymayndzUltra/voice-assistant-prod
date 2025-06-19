"""
Quick diagnostic script for TinyLlama model loading issues
"""
import sys
import torch
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("QuickTinyLlamaDebug")

# Print system info
logger.info(f"Python version: {sys.version}")
logger.info(f"PyTorch version: {torch.__version__}")
logger.info(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    logger.info(f"CUDA version: {torch.version.cuda}")
    logger.info(f"GPU: {torch.cuda.get_device_name(0)}")

try:
    import transformers
    logger.info(f"Transformers version: {transformers.__version__}")
    
    # Try to load just the tokenizer (quick operation)
    logger.info("Testing tokenizer loading...")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
    logger.info("✅ Tokenizer loaded successfully")
    
    # Check if we have the model cached locally
    import os
    import huggingface_hub
    
    cache_dir = transformers.utils.hub.get_transformers_cache()
    logger.info(f"Transformers cache directory: {cache_dir}")
    
    # Check specific error cause
    logger.info("Testing minimal model loading with device_map='auto'...")
    
    # Import with configurations that might avoid the meta tensor error
    from transformers import AutoConfig, AutoModelForCausalLM
    
    # First try with device_map="auto" which often works around meta tensor issues
    try:
        model = AutoModelForCausalLM.from_pretrained(
            "TinyLlama/TinyLlama-1.1B-Chat-v1.0", 
            device_map="auto",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        logger.info("✅ Model loaded successfully with device_map='auto'")
        # Try a very simple forward pass
        input_ids = torch.tensor([[1, 2, 3, 4, 5]]).to(model.device)
        with torch.no_grad():
            output = model(input_ids)
        logger.info("✅ Model forward pass successful")
    except Exception as e:
        logger.error(f"❌ Error loading with device_map='auto': {e}")
        
        # Try without using accelerate/device_map
        logger.info("Testing minimal model loading without device_map...")
        try:
            model = AutoModelForCausalLM.from_pretrained(
                "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            logger.info("✅ Model loaded successfully without device_map")
        except Exception as e:
            logger.error(f"❌ Error loading without device_map: {e}")
    
except ImportError as e:
    logger.error(f"❌ Error importing required libraries: {e}")
except Exception as e:
    logger.error(f"❌ Unexpected error: {e}")

logger.info("Diagnostic complete!")
