#!/usr/bin/env python3
"""
PC2 Model Loader Script

This script downloads and sets up all necessary models for PC2 containerization.
"""

import os
import sys
import argparse
import logging
from pathlib import Path


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root()
from common.utils.path_manager import PathManager
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ModelLoader")

def setup_environment():
    """Set up the environment variables and directories"""
    # Create model directories
    os.makedirs(PathManager.join_path("models", "translation"), exist_ok=True)
    os.makedirs(PathManager.join_path("models", "llm"), exist_ok=True)
    os.makedirs(PathManager.join_path("models", "cache"), exist_ok=True)
    
    # Set environment variables
    os.environ["TRANSFORMERS_CACHE"] = str(Path(PathManager.join_path("models", "cache").absolute()
    os.environ["HF_HOME"] = str(Path(PathManager.join_path("models", "cache").absolute()
    
    logger.info("Environment and directories set up")

def download_translation_models():
    """Download NLLB translation models"""
    logger.info("Starting download of translation models")
    
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        
        # Download NLLB distilled 600M model
        logger.info("Downloading NLLB-200-distilled-600M model")
        model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-600M")
        tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
        
        # Save model to local directory
        model_path = Path(PathManager.join_path("models", "translation/nllb-200-distilled-600M")
        model.save_pretrained(model_path)
        tokenizer.save_pretrained(model_path)
        
        logger.info(f"NLLB-200-distilled-600M saved to {model_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading translation models: {e}")
        return False

def download_tinyllama():
    """Download TinyLlama model"""
    logger.info("Starting download of TinyLlama-1.1B-Chat")
    
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        # Download TinyLlama model
        logger.info("Downloading TinyLlama-1.1B-Chat model")
        model = AutoModelForCausalLM.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        tokenizer = AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0")
        
        # Save model to local directory
        model_path = Path(PathManager.join_path("models", "llm/tinyllama-1.1b-chat")
        model.save_pretrained(model_path)
        tokenizer.save_pretrained(model_path)
        
        logger.info(f"TinyLlama-1.1B-Chat saved to {model_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading TinyLlama model: {e}")
        return False

def download_mistral():
    """Download Mistral-7B-Instruct model"""
    logger.info("Starting download of Mistral-7B-Instruct")
    
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        # Download Mistral model
        logger.info("Downloading Mistral-7B-Instruct model")
        model = AutoModelForCausalLM.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")
        tokenizer = AutoTokenizer.from_pretrained("mistralai/Mistral-7B-Instruct-v0.2")
        
        # Save model to local directory
        model_path = Path(PathManager.join_path("models", "llm/mistral-7b-instruct")
        model.save_pretrained(model_path)
        tokenizer.save_pretrained(model_path)
        
        logger.info(f"Mistral-7B-Instruct saved to {model_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading Mistral model: {e}")
        return False

def download_bergamot():
    """Download Bergamot translation model (optional)"""
    logger.info("Starting download of Bergamot model")
    
    try:
        # This is a placeholder - actual Bergamot download would require
        # installing and configuring the bergamot-translator package
        # For now, we'll just create a placeholder directory
        model_path = Path(PathManager.join_path("models", "translation/bergamot")
        model_path.mkdir(exist_ok=True)
        
        logger.info(f"Bergamot download would be done to {model_path}")
        logger.info("Note: Bergamot setup requires custom installation steps")
        return True
    except Exception as e:
        logger.error(f"Error setting up Bergamot model: {e}")
        return False

def setup_model_config():
    """Set up model configuration file"""
    logger.info("Setting up model configuration")
    
    try:
        config_path = Path(get_file_path("pc2_config", "model_config.yaml")
        config_dir = config_path.parent
        config_dir.mkdir(exist_ok=True)
        
        config_content = """# PC2 Model Configuration
models:
  translation:
    nllb_600m:
      path: models/translation/nllb-200-distilled-600M
      vram_mb: 2000
      priority: high
      preload: true
      quantized: false
      language_pairs: 
        - source: "en"
          target: "tl"
        - source: "tl"
          target: "en"
        # Add more language pairs as needed
    
  llm:
    mistral:
      path: models/llm/mistral-7b-instruct
      vram_mb: 8000
      priority: medium
      preload: false
      quantized: true
      quantization_bits: 4
      
    tinyllama:
      path: models/llm/tinyllama-1.1b-chat
      vram_mb: 1500
      priority: low
      preload: true
      quantized: false
      
global:
  vram_limit_mb: 10000  # 10GB VRAM limit for RTX 3060 (12GB)
  model_timeout_sec: 300  # 5 minutes of inactivity before unloading
  emergency_vram_threshold: 0.05  # 5% of total VRAM
"""
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Model configuration written to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error setting up model configuration: {e}")
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="PC2 Model Loader Script")
    parser.add_argument("--all", action="store_true", help="Download all models")
    parser.add_argument("--translation", action="store_true", help="Download translation models")
    parser.add_argument("--tinyllama", action="store_true", help="Download TinyLlama model")
    parser.add_argument("--mistral", action="store_true", help="Download Mistral model")
    parser.add_argument("--bergamot", action="store_true", help="Set up Bergamot model")
    parser.add_argument("--config", action="store_true", help="Set up model configuration")
    args = parser.parse_args()
    
    # If no specific models are specified, download all
    if not any([args.translation, args.tinyllama, args.mistral, args.bergamot, args.config]):
        args.all = True
    
    # Set up environment
    setup_environment()
    
    # Download models based on command line arguments
    results = {}
    
    if args.all or args.translation:
        results["translation"] = download_translation_models()
    
    if args.all or args.tinyllama:
        results["tinyllama"] = download_tinyllama()
    
    if args.all or args.mistral:
        results["mistral"] = download_mistral()
    
    if args.all or args.bergamot:
        results["bergamot"] = download_bergamot()
    
    if args.all or args.config:
        results["config"] = setup_model_config()
    
    # Print summary
    logger.info("=== Download Summary ===")
    for model, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"{model}: {status}")

if __name__ == "__main__":
    main() 