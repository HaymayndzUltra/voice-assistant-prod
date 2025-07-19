from main_pc_code.src.core.base_agent import BaseAgent
#!/usr/bin/env python3
"""
Model Manager Agent (MMA) for monitoring and managing pipeline components.
"""
import sys
import os
import json
import logging
import zmq
import time
from pathlib import Path
from datetime import datetime
import threading

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.append(str(project_root))

from main_pc_code.config.system_config import Config
from common.env_helpers import get_env

class ModelManagerAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ModularSystemModelManager")
        self.config = Config()
        self.logger = self._setup_logging()
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        self.health_timeouts = {}
        self.component_status = {}
        
    def _setup_logging(self):
        """Configure logging for the MMA"""
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.DEBUG,  # Changed to DEBUG level
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "model_manager_agent.log"),
                logging.StreamHandler()
            ]
        )
        
        return logging.getLogger("ModelManagerAgent")
    
    def start(self):
        """Start the Model Manager Agent"""
        self.logger.info("Starting Model Manager Agent...")
        
        # Subscribe to health messages on port 5597
        self.subscriber.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5597")
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
        
        self.logger.info("Subscribed to health messages on port 5597")
        
        # Load component configurations
        self._load_component_configs()
        
        # Start monitoring loop
        self._monitor_components()
    
    def _load_component_configs(self):
        """Load component configurations from system_config.py"""
        model_configs = self.config.get("main_pc_settings.model_configs", {})
        
        for component_id, config in model_configs.items():
            if component_id == "wakeword-listener-main-pc":
                self.logger.info(f"[MMA Config DEBUG] Raw config for 'wakeword-listener-main-pc': {config}")
            
            if config.get("enabled", False):
                self.health_timeouts[component_id] = config.get("health_message_timeout_seconds", 15)
                self.component_status[component_id] = {
                    "status": "unknown",
                    "last_seen": None,
                    "expected_response": config.get("expected_health_response_contains", {})
                }
                if component_id == "wakeword-listener-main-pc":
                    self.logger.info(f"[MMA Config DEBUG] Loaded configuration for wakeword-listener-main-pc:")
                    self.logger.info(f"  - Health timeout: {self.health_timeouts[component_id]}s")
                    self.logger.info(f"  - Expected response: {self.component_status[component_id]['expected_response']}")
    
    def _monitor_components(self):
        """Monitor component health messages"""
        while True:
            try:
                # Check for health messages
                if self.subscriber.poll(timeout=1000) == zmq.POLLIN:
                    message = self.subscriber.recv_json()
                    if message.get("component") == "wake_word_pipeline":
                        self.logger.info(f"[MMA Health DEBUG] Received health message from wake word pipeline: {message}")
                    self._process_health_message(message)
                
                # Check for timeouts
                self._check_timeouts()
                
            except KeyboardInterrupt:
                self.logger.info("Received shutdown signal")
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
    
    def _process_health_message(self, message):
        """Process a health message from a component"""
        component = message.get("component")
        if component == "wake_word_pipeline":
            self.logger.info(f"[MMA Health DEBUG] Processing health message from wake word pipeline: {message}")
        
        if component in self.component_status:
            status = self.component_status[component]
            expected = status["expected_response"]
            
            # Check if message contains expected response
            if all(k in message and message[k] == v for k, v in expected.items()):
                status["status"] = "healthy"
                status["last_seen"] = time.time()
                if component == "wake_word_pipeline":
                    self.logger.info(f"[MMA Health DEBUG] Wake word pipeline marked as healthy")
            else:
                status["status"] = "unhealthy"
                if component == "wake_word_pipeline":
                    self.logger.warning(f"[MMA Health DEBUG] Wake word pipeline marked as unhealthy - message does not match expected response")
    
    def _check_timeouts(self):
        """Check for component timeouts"""
        now = time.time()
        for component, status in self.component_status.items():
            if component == "wakeword-listener-main-pc":
                self.logger.debug(f"[MMA Health DEBUG] Checking timeout for wake word pipeline:")
                self.logger.debug(f"  - Current status: {status['status']}")
                self.logger.debug(f"  - Last seen: {status['last_seen']}")
                self.logger.debug(f"  - Timeout: {self.health_timeouts[component]}s")
            
            if status["last_seen"] is not None:
                time_since_last_seen = now - status["last_seen"]
                if time_since_last_seen > self.health_timeouts[component]:
                    status["status"] = "timeout"
                    if component == "wakeword-listener-main-pc":
                        self.logger.warning(f"[MMA Health DEBUG] Wake word pipeline timed out after {time_since_last_seen:.1f}s")

class DynamicSTTModelManager(BaseAgent):
    """
    Manages dynamic/context-aware STT model loading and switching.
    Supports multiple Whisper models and runtime selection based on context.
    """
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ModularSystemModelManager")
        """
        Args:
            available_models (dict): Mapping of model_id to model config (size, language, etc.)
            default_model (str): Default model_id to use if no context match
        """
        self.available_models = available_models  # e.g., {'base': {...}, 'large': {...}, ...}
        self.default_model = default_model
        self.loaded_models = {}  # model_id -> loaded model instance
        self.lock = threading.Lock()
        self.logger = logging.getLogger("DynamicSTTModelManager")

    def get_model(self, language=None, accent=None, context=None):
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

    def _load_model_if_needed(self, model_id):
        if model_id in self.loaded_models:
            self.logger.info(f"STT model '{model_id}' already loaded.")
            return self.loaded_models[model_id]
        try:
            import whisper
    except ImportError as e:
        print(f"Import error: {e}")
            self.logger.info(f"Loading STT model '{model_id}'...")
            model = whisper.load_model(model_id)
            self.loaded_models[model_id] = model
            self.logger.info(f"STT model '{model_id}' loaded successfully.")
            return model
        except Exception as e:
            self.logger.error(f"Failed to load STT model '{model_id}': {e}")
            raise

    def clear_cache(self):
        """Unload all cached models (for test or memory management)."""
        with self.lock:
            self.loaded_models.clear()
            self.logger.info("Cleared all cached STT models.")

if __name__ == "__main__":
    agent = ModelManagerAgent()
    agent.start() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
