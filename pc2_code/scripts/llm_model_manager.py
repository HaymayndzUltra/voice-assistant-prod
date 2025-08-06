#!/usr/bin/env python3
"""
LLM Model Manager for PC2

This script handles downloading, optimizing, and managing LLM models 
for the PC2 containerization system. It ensures efficient memory usage
and optimizes models for deployment.

Usage:
    python llm_model_manager.py --download [model_name]
    python llm_model_manager.py --optimize [model_name]
    python llm_model_manager.py --list
    python llm_model_manager.py --prune [model_name]
    python llm_model_manager.py --quantize [model_name]
"""

import os
import sys
import json
import shutil
import argparse
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

import torch
from common.utils.log_setup import configure_logging
try:
    from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM
    from transformers import BitsAndBytesConfig
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import ctranslate2

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
    CTRANSLATE_AVAILABLE = True
except ImportError:
    CTRANSLATE_AVAILABLE = False

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger("llm_model_manager")

# Default paths
BASE_DIR = Path(os.environ.get("MODEL_DIR", "/app/models")
CONFIG_FILE = BASE_DIR / "model_config.json"
CACHE_DIR = Path(str(PathManager.get_temp_dir() / "model_cache")

# Model definitions
DEFAULT_MODELS = {
    "nllb-200-distilled-600M": {
        "hf_name": "facebook/nllb-200-distilled-600M",
        "type": "translation",
        "optimization": "ctranslate2",
        "quantization": "int8"
    },
    "whisper-small": {
        "hf_name": "openai/whisper-small",
        "type": "speech",
        "optimization": "faster-whisper",
        "quantization": "int8"
    },
    "mpt-7b-instruct": {
        "hf_name": "mosaicml/mpt-7b-instruct",
        "type": "llm",
        "optimization": "bitsandbytes",
        "quantization": "4bit"
    }
}


def check_disk_space(path: Path, required_gb: float = 10.0) -> bool:
    """Check if enough disk space is available."""
    try:
        stats = shutil.disk_usage(path)
        available_gb = stats.free / (1024 * 1024 * 1024)
        logger.info(f"Available disk space: {available_gb:.2f} GB")
        if available_gb < required_gb:
            logger.error(f"Not enough disk space. Required: {required_gb} GB, Available: {available_gb:.2f} GB")
            return False
        return True
    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return False


def load_config() -> Dict:
    """Load model configuration from JSON file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    # Create default config if not exists
    config = {"models": DEFAULT_MODELS, "downloaded": {}}
    save_config(config)
    return config


def save_config(config: Dict) -> None:
    """Save model configuration to JSON file."""
    try:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {e}")


def download_model(model_name: str, force: bool = False) -> bool:
    """Download model from HuggingFace."""
    if not TRANSFORMERS_AVAILABLE:
        logger.error("Transformers library not available. Please install it first.")
        return False
    
    config = load_config()
    
    if model_name not in config["models"]:
        logger.error(f"Model {model_name} not found in config")
        return False
    
    model_config = config["models"][model_name]
    hf_name = model_config["hf_name"]
    model_type = model_config["type"]
    
    # Create model directory
    model_dir = BASE_DIR / model_type / model_name
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if model already downloaded
    if not force and model_name in config.get("downloaded", {}):
        logger.info(f"Model {model_name} already downloaded")
        return True
    
    # Check disk space (approximate size needed)
    required_gb = 15.0  # Default requirement
    if "llm" in model_type:
        required_gb = 30.0  # LLMs are larger
    
    if not check_disk_space(BASE_DIR, required_gb):
        return False
    
    try:
        logger.info(f"Downloading {model_name} from {hf_name}")
        
        # Download tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            hf_name, 
            cache_dir=str(CACHE_DIR),
            local_files_only=False
        )
        tokenizer.save_pretrained(str(model_dir)
        
        # Download model with appropriate config
        if model_type == "llm":
            # For LLMs, use quantization to save memory
            quantization = model_config.get("quantization", "4bit")
            if quantization == "4bit":
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_use_double_quant=True
                )
                model = AutoModelForCausalLM.from_pretrained(
                    hf_name,
                    cache_dir=str(CACHE_DIR),
                    quantization_config=bnb_config,
                    device_map="auto",
                    local_files_only=False,
                    torch_dtype=torch.float16
                )
            else:
                model = AutoModelForCausalLM.from_pretrained(
                    hf_name,
                    cache_dir=str(CACHE_DIR),
                    device_map="auto",
                    local_files_only=False
                )
        else:
            # For smaller models, download normally
            model = AutoModel.from_pretrained(
                hf_name,
                cache_dir=str(CACHE_DIR),
                local_files_only=False
            )
        
        model.save_pretrained(str(model_dir)
        
        # Update config
        config["downloaded"][model_name] = {
            "path": str(model_dir),
            "optimized": False
        }
        save_config(config)
        
        logger.info(f"Model {model_name} downloaded successfully to {model_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading model {model_name}: {e}")
        return False


def optimize_model(model_name: str) -> bool:
    """Optimize model for inference."""
    config = load_config()
    
    if model_name not in config["models"]:
        logger.error(f"Model {model_name} not found in config")
        return False
    
    if model_name not in config.get("downloaded", {}):
        logger.error(f"Model {model_name} not downloaded yet")
        return False
    
    model_config = config["models"][model_name]
    model_type = model_config["type"]
    optimization = model_config.get("optimization", "none")
    model_dir = Path(config["downloaded"][model_name]["path"])
    
    logger.info(f"Optimizing {model_name} using {optimization}")
    
    try:
        # Apply optimization based on type
        if optimization == "ctranslate2" and CTRANSLATE_AVAILABLE:
            # Optimize translation model with CTranslate2
            output_dir = model_dir / "ctranslate2"
            quantization = model_config.get("quantization", "int8")
            
            logger.info(f"Converting {model_name} to CTranslate2 format with {quantization} quantization")
            ctranslate2.converters.convert_from_pretrained(
                model_id=model_dir,
                output_dir=output_dir,
                quantization=quantization,
                force=True
            )
            
            # Update config
            config["downloaded"][model_name]["optimized"] = True
            config["downloaded"][model_name]["optimization_type"] = "ctranslate2"
            config["downloaded"][model_name]["optimized_path"] = str(output_dir)
            save_config(config)
            
            logger.info(f"Model {model_name} optimized successfully")
            return True
            
        elif optimization == "bitsandbytes" and TRANSFORMERS_AVAILABLE:
            # Already handled during download for LLMs
            config["downloaded"][model_name]["optimized"] = True
            config["downloaded"][model_name]["optimization_type"] = "bitsandbytes"
            save_config(config)
            
            logger.info(f"Model {model_name} optimized successfully with BitsAndBytes")
            return True
            
        else:
            logger.warning(f"Optimization {optimization} not supported or libraries not available")
            return False
            
    except Exception as e:
        logger.error(f"Error optimizing model {model_name}: {e}")
        return False


def list_models() -> None:
    """List all models and their status."""
    config = load_config()
    
    print("\n=== Available Models ===")
    print(f"{'Model Name':<30} {'Type':<15} {'Downloaded':<12} {'Optimized':<12}")
    print("-" * 70)
    
    for model_name, model_config in config["models"].items():
        downloaded = model_name in config.get("downloaded", {})
        optimized = downloaded and config["downloaded"][model_name].get("optimized", False)
        model_type = model_config["type"]
        
        print(f"{model_name:<30} {model_type:<15} {'✓' if downloaded else '✗':<12} {'✓' if optimized else '✗':<12}")


def prune_model(model_name: str) -> bool:
    """Prune unnecessary files from model to save space."""
    config = load_config()
    
    if model_name not in config.get("downloaded", {}):
        logger.error(f"Model {model_name} not downloaded")
        return False
    
    model_dir = Path(config["downloaded"][model_name]["path"])
    
    try:
        # Files to prune (common large files not needed for inference)
        prune_patterns = [
            "*.pt",  # PyTorch temporary files
            "*.bin.index.*",  # Index files not needed after load
            "optimizer.pt",  # Optimizer states not needed for inference
            "training_args.bin",  # Training arguments not needed for inference
        ]
        
        pruned_files = 0
        saved_bytes = 0
        
        for pattern in prune_patterns:
            for file_path in model_dir.glob(f"**/{pattern}"):
                if file_path.is_file():
                    size = file_path.stat().st_size
                    file_path.unlink()
                    pruned_files += 1
                    saved_bytes += size
        
        logger.info(f"Pruned {pruned_files} files, saved {saved_bytes / (1024 * 1024):.2f} MB")
        
        # Update config
        config["downloaded"][model_name]["pruned"] = True
        save_config(config)
        
        return True
    
    except Exception as e:
        logger.error(f"Error pruning model {model_name}: {e}")
        return False


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(description="LLM Model Manager for PC2")
    
    # Command-line arguments
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--download", metavar="MODEL", help="Download a model")
    command_group.add_argument("--optimize", metavar="MODEL", help="Optimize a downloaded model")
    command_group.add_argument("--list", action="store_true", help="List all available models")
    command_group.add_argument("--prune", metavar="MODEL", help="Prune unnecessary files from model")
    command_group.add_argument("--quantize", metavar="MODEL", help="Quantize model to reduce size")
    
    # Optional arguments
    parser.add_argument("--force", action="store_true", help="Force download even if model exists")
    
    args = parser.parse_args()
    
    # Create cache directory
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Execute command
    if args.download:
        success = download_model(args.download, args.force)
        if success and load_config()["models"][args.download].get("optimization", "none") != "none":
            optimize_model(args.download)
        if success:
            prune_model(args.download)
        return 0 if success else 1
    
    elif args.optimize:
        success = optimize_model(args.optimize)
        return 0 if success else 1
    
    elif args.list:
        list_models()
        return 0
    
    elif args.prune:
        success = prune_model(args.prune)
        return 0 if success else 1
    
    elif args.quantize:
        # Quantization is currently handled in optimize_model
        logger.info("Quantization is handled during optimization")
        success = optimize_model(args.quantize)
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main() 