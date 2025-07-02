from main_pc_code.src.core.base_agent import BaseAgent
import os
import gc
import time
import logging
import threading
import numpy as np
import torch
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass from(BaseAgent) collections import OrderedDict, defaultdict
from concurrent.futures import ThreadPoolExecutor
import psutil
import json
from pathlib import Path


# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

@dataclass class(BaseAgent) ModelConfig:
    name: str
    path: str
    size_mb: float
    precision: str = "float32"
    batch_size: int = 1
    priority: int = 1
    compression_ratio: float = 1.0
    partial_load: bool = False
    partial_layers: List[str] = None

@dataclass class(BaseAgent) VRAMStats:
    total_vram: float
    used_vram: float
    free_vram: float
    fragmentation: float
    timestamp: float

class VRAMManager(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="VramManager copy")
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        
        # Initialize VRAM tracking
        self.total_vram = torch.cuda.get_device_properties(0).total_memory
        self.vram_stats_history: List[VRAMStats] = []
        self.model_pool: OrderedDict[str, torch.nn.Module] = OrderedDict()
        self.model_configs: Dict[str, ModelConfig] = {}
        self.model_usage_stats: Dict[str, Dict] = defaultdict(lambda: {
            "load_count": 0,
            "last_used": 0,
            "total_usage_time": 0,
            "avg_batch_size": 0
        })
        
        # Initialize optimization components
        self.quantization_enabled = self.config.get("enable_quantization", True)
        self.partial_loading_enabled = self.config.get("enable_partial_loading", True)
        self.compression_enabled = self.config.get("enable_compression", True)
        self.cache_clear_interval = self.config.get("cache_clear_interval", 3600)
        self.max_models_in_memory = self.config.get("max_models_in_memory", 3)
        self.vram_threshold = self.config.get("vram_threshold", 0.9)
        
        # Initialize thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.lock = threading.Lock()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitor_vram, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("VRAM Manager initialized with config: %s", self.config)

    def _load_config(self, config_path: str) -> dict:
        """Load VRAM configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_path} not found. Using default settings.")
            return {
                "enable_quantization": True,
                "enable_partial_loading": True,
                "enable_compression": True,
                "cache_clear_interval": 3600,
                "max_models_in_memory": 3,
                "vram_threshold": 0.9,
                "quantization_precision": "int8",
                "compression_method": "pruning",
                "compression_ratio": 0.5
            }

    def _monitor_vram(self):
        """Monitor VRAM usage and trigger optimizations when needed."""
        while True:
            try:
                stats = self._get_vram_stats()
                self.vram_stats_history.append(stats)
                
                # Keep only last hour of stats
                current_time = time.time()
                self.vram_stats_history = [
                    s for s in self.vram_stats_history 
                    if current_time - s.timestamp < 3600
                ]
                
                # Check if VRAM usage is too high
                if stats.used_vram / stats.total_vram > self.vram_threshold:
                    self._optimize_vram_usage()
                
                # Periodic cache clearing
                if len(self.vram_stats_history) > 0:
                    last_clear = self.vram_stats_history[-1].timestamp
                    if current_time - last_clear > self.cache_clear_interval:
                        self._clear_cache()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error in VRAM monitoring: {str(e)}")
                time.sleep(5)

    def _get_vram_stats(self) -> VRAMStats:
        """Get current VRAM statistics."""
        torch.cuda.synchronize()
        allocated = torch.cuda.memory_allocated()
        reserved = torch.cuda.memory_reserved()
        fragmentation = (reserved - allocated) / reserved if reserved > 0 else 0
        
        return VRAMStats(
            total_vram=self.total_vram,
            used_vram=allocated,
            free_vram=self.total_vram - allocated,
            fragmentation=fragmentation,
            timestamp=time.time()
        )

    def _optimize_vram_usage(self):
        """Optimize VRAM usage based on current conditions."""
        with self.lock:
            # Get current VRAM stats
            stats = self._get_vram_stats()
            
            # If fragmentation is high, clear cache
            if stats.fragmentation > 0.3:
                self._clear_cache()
            
            # If too many models in memory, unload least used
            if len(self.model_pool) > self.max_models_in_memory:
                self._unload_least_used_models()
            
            # If VRAM usage is still high, try quantization
            if stats.used_vram / stats.total_vram > self.vram_threshold:
                self._quantize_models()

    def _clear_cache(self):
        """Clear VRAM cache and garbage collect."""
        with self.lock:
            torch.cuda.empty_cache()
            gc.collect()
            self.logger.info("VRAM cache cleared")

    def _unload_least_used_models(self):
        """Unload least frequently used models."""
        with self.lock:
            # Sort models by usage frequency and last used time
            sorted_models = sorted(
                self.model_usage_stats.items(),
                key=lambda x: (x[1]["load_count"], x[1]["last_used"])
            )
            
            # Unload models until we're under the limit
            while len(self.model_pool) > self.max_models_in_memory:
                model_name = sorted_models[0][0]
                self.unload_model(model_name)
                sorted_models.pop(0)

    def _quantize_models(self):
        """Quantize models to reduce VRAM usage."""
        if not self.quantization_enabled:
            return
            
        with self.lock:
            for model_name, model in self.model_pool.items():
                if not hasattr(model, "quantized"):
                    try:
                        # Convert to float16 first
                        model.half()
                        # Then to int8 if needed
                        if self.config.get("quantization_precision") == "int8":
                            model.int8()
                        model.quantized = True
                        self.logger.info(f"Model {model_name} quantized")
                    except Exception as e:
                        self.logger.error(f"Error quantizing model {model_name}: {str(e)}")

    def load_model(self, model_config: ModelConfig) -> torch.nn.Module:
        """Load a model with optimization strategies."""
        with self.lock:
            # Check if model is already loaded
            if model_config.name in self.model_pool:
                self.model_usage_stats[model_config.name]["load_count"] += 1
                self.model_usage_stats[model_config.name]["last_used"] = time.time()
                return self.model_pool[model_config.name]
            
            # Check if we have enough VRAM
            stats = self._get_vram_stats()
            if stats.used_vram + model_config.size_mb * 1024 * 1024 > self.total_vram * self.vram_threshold:
                self._optimize_vram_usage()
            
            try:
                # Load model with appropriate precision
                if model_config.precision == "float16":
                    model = torch.load(model_config.path, map_location="cuda").half()
                elif model_config.precision == "int8":
                    model = torch.load(model_config.path, map_location="cuda").int8()
                else:
                    model = torch.load(model_config.path, map_location="cuda")
                
                # Apply partial loading if enabled
                if self.partial_loading_enabled and model_config.partial_load:
                    self._load_partial_model(model, model_config)
                
                # Store model in pool
                self.model_pool[model_config.name] = model
                self.model_configs[model_config.name] = model_config
                self.model_usage_stats[model_config.name]["load_count"] = 1
                self.model_usage_stats[model_config.name]["last_used"] = time.time()
                
                self.logger.info(f"Model {model_config.name} loaded successfully")
                return model
                
            except Exception as e:
                self.logger.error(f"Error loading model {model_config.name}: {str(e)}")
                raise

    def unload_model(self, model_name: str):
        """Unload a model and free VRAM."""
        with self.lock:
            if model_name in self.model_pool:
                try:
                    # Move model to CPU first
                    self.model_pool[model_name].cpu()
                    # Delete model
                    del self.model_pool[model_name]
                    # Clear cache
                    torch.cuda.empty_cache()
                    self.logger.info(f"Model {model_name} unloaded successfully")
                except Exception as e:
                    self.logger.error(f"Error unloading model {model_name}: {str(e)}")

    def _load_partial_model(self, model: torch.nn.Module, config: ModelConfig):
        """Load only specified layers of a model."""
        if not config.partial_layers:
            return
            
        try:
            # Create a new model with only specified layers
            partial_model = type(model)()
            for layer_name in config.partial_layers:
                if hasattr(model, layer_name):
                    setattr(partial_model, layer_name, getattr(model, layer_name))
            
            # Replace original model with partial model
            self.model_pool[config.name] = partial_model
            self.logger.info(f"Partial model loaded for {config.name}")
            
        except Exception as e:
            self.logger.error(f"Error in partial loading for {config.name}: {str(e)}")

    def compress_model(self, model_name: str, compression_ratio: float = 0.5):
        """Compress model for disk storage."""
        if not self.compression_enabled:
            return
            
        with self.lock:
            if model_name in self.model_pool:
                try:
                    model = self.model_pool[model_name]
                    # Apply pruning
                    if self.config.get("compression_method") == "pruning":
                        self._prune_model(model, compression_ratio)
                    # Save compressed model
                    compressed_path = f"{self.model_configs[model_name].path}.compressed"
                    torch.save(model.state_dict(), compressed_path)
                    self.logger.info(f"Model {model_name} compressed and saved to {compressed_path}")
                except Exception as e:
                    self.logger.error(f"Error compressing model {model_name}: {str(e)}")

    def _prune_model(self, model: torch.nn.Module, ratio: float):
        """Prune model weights to reduce size."""
        for name, module in model.named_modules():
            if isinstance(module, torch.nn.Linear):
                # Calculate threshold for pruning
                threshold = torch.quantile(module.weight.abs(), ratio)
                # Create mask for weights below threshold
                mask = module.weight.abs() > threshold
                # Apply mask
                module.weight.data *= mask

    def predict_vram_usage(self, model_config: ModelConfig) -> float:
        """Predict VRAM usage for a model."""
        # Base size from config
        predicted_size = model_config.size_mb
        
        # Adjust for precision
        if model_config.precision == "float16":
            predicted_size *= 0.5
        elif model_config.precision == "int8":
            predicted_size *= 0.25
            
        # Adjust for compression
        predicted_size *= model_config.compression_ratio
        
        # Add overhead for partial loading
        if model_config.partial_load:
            predicted_size *= 0.7
            
        return predicted_size

    def get_vram_usage_report(self) -> dict:
        """Generate VRAM usage report."""
        stats = self._get_vram_stats()
        return {
            "total_vram_mb": stats.total_vram / (1024 * 1024),
            "used_vram_mb": stats.used_vram / (1024 * 1024),
            "free_vram_mb": stats.free_vram / (1024 * 1024),
            "fragmentation": stats.fragmentation,
            "models_loaded": len(self.model_pool),
            "model_usage": self.model_usage_stats
        }

    def cleanup(self):
        """Cleanup resources."""
        self.executor.shutdown()
        self._clear_cache()
        self.model_pool.clear()
        self.model_configs.clear()
        self.model_usage_stats.clear()
        self.vram_stats_history.clear() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
