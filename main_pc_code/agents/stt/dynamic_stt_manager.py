#!/usr/bin/env python3
from common.core.base_agent import BaseAgent
"""
Dynamic STT Model Manager
------------------------
Manages dynamic/context-aware STT model loading and switching.
Supports multiple Whisper models and runtime selection based on context.
"""

import sys
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import time
import torch

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

class DynamicSTTModelManager(BaseAgent):
    """
    Manages dynamic/context-aware STT model loading and switching.
    Supports multiple Whisper models and runtime selection based on context.
    """
    def __init__(self, available_models: Dict = None, default_model: str = 'base', port: int = None, **kwargs):
        super().__init__(port=port, name="DynamicSttManager")
        """
        Args:
            available_models (dict): Mapping of model_id to model config (size, language, etc.)
            default_model (str): Default model_id to use if no context match
        """
        self.available_models = available_models or {'base': {'language': 'en', 'size': 'base'}}
        self.default_model = default_model
        self.loaded_models = {}  # model_id -> loaded model instance
        self.lock = threading.Lock()
        self.logger = logging.getLogger("DynamicSTTModelManager")

    def get_model(self, language: Optional[str] = None, accent: Optional[str] = None, context: Optional[Dict] = None) -> Tuple[Any, str]:
        """
        Select and return the best model for the given context. Loads if not already loaded.
        Args:
            language (str): Language code (e.g., 'en', 'tl')
            accent (str): Accent or region (optional)
            context (dict): Additional context for selection (optional)
        Returns:
            model: Loaded Whisper model instance
            model_id: The model_id used
        """
        with self.lock:
            # Selection logic: prioritize language, then accent, then default
            for model_id, cfg in self.available_models.items():
                if language and cfg.get('language') == language:
                    if not accent or cfg.get('accent') == accent:
                        return self._load_model_if_needed(model_id), model_id
            # Fallback to default
            return self._load_model_if_needed(self.default_model), self.default_model

    def _load_model_if_needed(self, model_id: str) -> Any:
        """Load a model if it's not already loaded"""
        with self.lock:
            if model_id in self.loaded_models:
                self.logger.debug(f"Model '{model_id}' is already loaded.")
                return self.loaded_models[model_id]
            
            try:
                import whisper
                self.logger.info(f"Loading STT model '{model_id}'...")
                start_time = time.time()
                model = whisper.load_model(model_id)
                self.loaded_models[model_id] = model
                end_time = time.time()
                self.logger.info(f"Loaded model '{model_id}' in {end_time - start_time:.2f} seconds.")
                return model
            except ImportError as e:
                self.logger.error(f"Whisper import failed: {e}", exc_info=True)
                raise
            except Exception as e:
                self.logger.error(f"Failed to load STT model '{model_id}': {e}", exc_info=True)
                raise

    def unload_model(self, model_id: str) -> bool:
        """Unloads a specific model from memory."""
        with self.lock:
            if model_id in self.loaded_models:
                self.logger.info(f"Unloading model '{model_id}'...")
                start_time = time.time()
                try:
                    # Remove the model object to allow garbage collection
                    del self.loaded_models[model_id]
                    
                    # If using CUDA, explicitly empty the cache
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        
                    end_time = time.time()
                    self.logger.info(f"Unloaded model '{model_id}' in {end_time - start_time:.2f} seconds.")
                    return True
                except Exception as e:
                    self.logger.error(f"Error unloading model '{model_id}': {e}", exc_info=True)
                    return False
            else:
                self.logger.warning(f"Attempted to unload model '{model_id}', but it was not loaded.")
                return False

    def clear_cache(self) -> None:
        """Unload all cached models (for test or memory management)."""
        with self.lock:
            self.loaded_models.clear()
            self.logger.info("Cleared all cached STT models.")

if __name__ == "__main__":
    # Example usage
    available_models = {
        'base': {'language': 'en', 'size': 'base'},
        'large': {'language': 'en', 'size': 'large'},
        'base-tl': {'language': 'tl', 'size': 'base'}
    }
    
    manager = DynamicSTTModelManager(available_models, default_model='base')
    model, model_id = manager.get_model(language='en')
    print(f"Loaded model: {model_id}")
