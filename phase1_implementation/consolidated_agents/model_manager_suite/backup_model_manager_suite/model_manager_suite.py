#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
ModelManagerSuite - Consolidated Model Management Service
=======================================================

This service consolidates the following agents into a unified service:
- GGUFModelManager: Handles loading, unloading, and managing GGUF models
- PredictiveLoader: Predicts and preloads models based on usage patterns
- ModelEvaluationFramework: Tracks model performance and evaluation

Port: 7011 (Main service)
Health: 7111 (Health check)
Hardware: MainPC (RTX 4090)

CRITICAL REQUIREMENTS:
- Preserve ALL logic, error handling, imports, and patterns from source agents
- Maintain backward compatibility with all legacy endpoints
- Keep modular structure within the consolidated service
- Expose all legacy REST/gRPC endpoints for backward compatibility
"""

import sys
import os
import time
import json
import logging
import threading
import zmq
import torch
import sqlite3
import psutil
import uuid
import gc
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
import traceback
import socket
import errno
import yaml
import numpy as np
import requests
import pickle
import re

# Add the project's main_pc_code directory to the Python path
def get_main_pc_code():
    """Get the path to the main_pc_code directory"""
    current_dir = Path(__file__).resolve().parent
    main_pc_code_dir = current_dir.parent.parent.parent / "main_pc_code"
    return main_pc_code_dir

MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import BaseAgent
from common.core.base_agent import BaseAgent

# Import config loader
from main_pc_code.utils.config_loader import load_config

# Import standardized data models
from common.utils.learning_models import PerformanceMetric, ModelEvaluationScore
from common.utils.data_models import ErrorSeverity

# Import circuit breaker (with fallback)
try:
    from main_pc_code.agents.request_coordinator import CircuitBreaker
except ImportError:
    # Fallback CircuitBreaker implementation
    class CircuitBreaker:
        def __init__(self, name: str):
            self.name = name
            self.failure_count = 0
            self.last_failure_time = None
            self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
            
        def call(self, func, *args, **kwargs):
            if self.state == "OPEN":
                raise Exception(f"Circuit breaker {self.name} is OPEN")
            try:
                result = func(*args, **kwargs)
                self.failure_count = 0
                self.state = "CLOSED"
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= 5:
                    self.state = "OPEN"
                raise e

# Import path utilities
from common.utils.path_env import get_path, join_path, get_file_path

# Check for llama-cpp-python availability
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    print("Warning: llama-cpp-python not available. GGUF models will not work.")

# Configure logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logger = configure_logging(__name__)),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('ModelManagerSuite')

# Load configuration
config = load_config()

class ModelManagerSuite(BaseAgent):
    """
    Consolidated Model Management Service
    
    This service combines the functionality of:
    - GGUFModelManager: GGUF model loading/unloading
    - PredictiveLoader: Predictive model preloading
    - ModelEvaluationFramework: Performance tracking and evaluation
    """
    
    def __init__(self, port: int = 7011, health_port: int = 7111, **kwargs):
        """Initialize the ModelManagerSuite service"""
        super().__init__(name="ModelManagerSuite", port=port, health_check_port=health_port)
        
        # Store configuration
        self.config = config if isinstance(config, dict) else {}
        
        # Initialize core components
        self._init_core_components()
        
        # Initialize GGUF model management
        self._init_gguf_management()
        
        # Initialize model tracking and resource management
        self._init_model_tracking()
        
        # Initialize predictive loading
        self._init_predictive_loading()
        
        # Initialize evaluation framework
        self._init_evaluation_framework()
        
        # Initialize ZMQ and networking
        self._init_zmq()
        
        # Initialize error reporting
        self._init_error_reporting()
        
        # Start background threads
        self._start_background_threads()
        
        logger.info(f"ModelManagerSuite initialized on port {port} (health: {health_port})")
    
    def _init_core_components(self):
        """Initialize core service components"""
        self.running = True
        self.start_time = time.time()
        self.context = zmq.Context()
        
        # Threading locks
        self.lock = threading.RLock()
        self.models_lock = threading.Lock()
        
        # Service state
        self.commands_processed = 0
        self.metrics = {
            'performance_logs': 0,
            'trust_score_updates': 0,
            'models_tracked': 0,
            'predictions_made': 0,
            'models_loaded': 0,
            'models_unloaded': 0
        }
        
        # Circuit breakers for downstream services
        self.circuit_breakers = {}
        self.downstream_services = []
        self._init_circuit_breakers()
    
    def _init_gguf_management(self):
        """Initialize GGUF model management functionality"""
        self.models_dir = Path(self.config.get('models_dir', 'models'))
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # GGUF model tracking
        self.loaded_models = {}
        self.last_used = {}
        self.model_metadata = {}
        
        # KV cache storage for conversation continuity
        self.kv_caches = {}  # {conversation_id: {model_id: cache_data}}
        self.kv_cache_last_used = {}  # {conversation_id: timestamp}
        self.max_kv_caches = 50  # Maximum number of KV caches to store
        self.kv_cache_timeout = 3600  # 1 hour timeout for KV caches
        
        # Load model metadata will be called in _init_model_tracking
        
        # Check GGUF support
        if not LLAMA_CPP_AVAILABLE:
            logger.warning("llama-cpp-python not available. GGUF models will not work.")
    
    def _init_model_tracking(self):
        """Initialize model tracking and resource management"""
        # Model status tracking
        self.models = {}
        self.model_last_used_timestamp = {}
        self.model_usage = {}
        
        # VRAM management
        self.vram_budget_percentage = 80
        self.vram_budget_mb = 4096
        self.memory_check_interval = 5
        self.idle_timeout = 300
        self.min_vram_mb = 512
        self.max_models_in_memory = 3
        
        # Load model metadata
        self._load_model_metadata()
        
        # Load model configurations
        self._load_model_configs()
    
    def _init_predictive_loading(self):
        """Initialize predictive loading functionality"""
        # Prediction settings
        self.prediction_window = 3600  # 1 hour
        self.lookahead_window = 300    # 5 minutes
        
        # Usage tracking
        self.model_usage = {}
        self.usage_patterns = {}
        
        # Prediction cache
        self.prediction_cache = {}
        self.prediction_cache_ttl = 300  # 5 minutes
    
    def _init_evaluation_framework(self):
        """Initialize evaluation framework functionality"""
        # Database setup
        self.db_path = self.config.get('mef_db_path', 'data/model_evaluation.db')
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
        
        # Evaluation tracking
        self.evaluation_results = {}
        self.performance_metrics = {}
        
        # Trust scoring
        self.trust_scores = {}
        self.model_performance_history = {}
    
    def _init_zmq(self):
        """Initialize ZMQ networking"""
        # Main service socket
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Health check socket
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://*:{self.health_check_port}")
        
        # Error bus setup
        self.error_bus_port = self.config.get('error_bus_port', 7150)
        self.error_bus_host = os.environ.get('PC2_IP', self.config.get('error_bus_host', '192.168.100.17'))
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
    
    def _init_error_reporting(self):
        """Initialize error reporting system"""
        self.error_count = 0
        self.last_error_time = 0
        self.error_threshold = 10
        self.error_window = 60  # 1 minute
    
    def _init_circuit_breakers(self):
        """Initialize circuit breakers for downstream services"""
        for service in self.downstream_services:
            self.circuit_breakers[service] = CircuitBreaker(name=service)
    
    def _init_database(self):
        """Initialize evaluation database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    metric_id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    context TEXT
                )
            ''')
            
            # Model evaluation scores table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS model_evaluation_scores (
                    evaluation_id TEXT PRIMARY KEY,
                    model_name TEXT NOT NULL,
                    cycle_id TEXT NOT NULL,
                    trust_score REAL NOT NULL,
                    accuracy REAL,
                    f1_score REAL,
                    avg_latency_ms REAL NOT NULL,
                    evaluation_timestamp TIMESTAMP NOT NULL,
                    comparison_data TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Evaluation database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            self.report_error("database_init_error", str(e), ErrorSeverity.ERROR)
    
    def _load_model_metadata(self):
        """Load model metadata from configuration"""
        try:
            # Load from system config
            from main_pc_code.config.system_config import Config
            config = Config()
            machine_config = config.get_all().get('main_pc_settings', {})
            
            # Extract model configs
            model_configs = machine_config.get('model_configs', {})
            
            # Filter for GGUF models
            for model_id, model_info in model_configs.items():
                if model_info.get('serving_method') == 'gguf_direct' and model_info.get('enabled', False):
                    self.model_metadata[model_id] = {
                        'display_name': model_info.get('display_name', model_id),
                        'model_path': model_info.get('model_path', f"{model_id}.gguf"),
                        'n_ctx': model_info.get('context_length', 2048),
                        'n_gpu_layers': model_info.get('n_gpu_layers', -1),
                        'n_threads': model_info.get('n_threads', 4),
                        'verbose': model_info.get('verbose', False),
                        'estimated_vram_mb': model_info.get('estimated_vram_mb', 0),
                        'capabilities': model_info.get('capabilities', ["code-generation"]),
                        'idle_timeout_seconds': model_info.get('idle_timeout_seconds', 300),
                    }
            
            logger.info(f"Loaded metadata for {len(self.model_metadata)} GGUF models")
            
        except Exception as e:
            logger.error(f"Error loading model metadata: {e}")
            traceback.print_exc()
    
    def _load_model_configs(self):
        """Load model configurations"""
        try:
            # Load from config
            model_configs = self.config.get('model_configs', {})
            
            for model_id, model_info in model_configs.items():
                self.models[model_id] = {
                    'status': 'offline',
                    'error': None,
                    'last_used': None,
                    'estimated_vram_mb': model_info.get('estimated_vram_mb', 0),
                    'serving_method': model_info.get('serving_method', 'gguf_direct'),
                    'capabilities': model_info.get('capabilities', []),
                    'priority': model_info.get('priority', 'medium')
                }
            
            logger.info(f"Loaded configurations for {len(self.models)} models")
            
        except Exception as e:
            logger.error(f"Error loading model configs: {e}")
    
    def _start_background_threads(self):
        """Start background processing threads"""
        # Main service loop
        self.main_thread = threading.Thread(target=self._main_loop, daemon=True)
        self.main_thread.start()
        
        # Health check loop
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        
        # Predictive loading loop
        self.prediction_thread = threading.Thread(target=self._prediction_loop, daemon=True)
        self.prediction_thread.start()
        
        # Memory management loop
        self.memory_thread = threading.Thread(target=self._memory_management_loop, daemon=True)
        self.memory_thread.start()
        
        # KV cache cleanup loop
        self.kv_cache_thread = threading.Thread(target=self._kv_cache_cleanup_loop, daemon=True)
        self.kv_cache_thread.start()
        
        logger.info("Started all background threads")
    
    def _main_loop(self):
        """Main service loop for handling requests"""
        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        
        while self.running:
            try:
                events = dict(poller.poll(1000))  # 1 second timeout
                
                if self.socket in events and events[self.socket] == zmq.POLLIN:
                    request = self.socket.recv_json()
                    if not isinstance(request, dict):
                        logger.error(f"Received non-dict request: {request}")
                        self.socket.send_json({'status': 'error', 'message': 'Invalid request format'})
                        continue
                    
                    response = self.handle_request(request)
                    self.socket.send_json(response)
                    self.commands_processed += 1
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.report_error("main_loop_error", str(e), ErrorSeverity.ERROR)
                time.sleep(1)
    
    def _health_check_loop(self):
        """Health check loop"""
        poller = zmq.Poller()
        poller.register(self.health_socket, zmq.POLLIN)
        
        while self.running:
            try:
                events = dict(poller.poll(1000))  # 1 second timeout
                
                if self.health_socket in events and events[self.health_socket] == zmq.POLLIN:
                    _ = self.health_socket.recv()
                    self.health_socket.send_json(self._get_health_status())
                    
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)
    
    def _prediction_loop(self):
        """Predictive loading loop"""
        while self.running:
            try:
                # Predict which models will be needed
                predicted_models = self._predict_models()
                
                # Preload predicted models
                if predicted_models:
                    self._preload_models(predicted_models)
                
                # Sleep for prediction interval
                time.sleep(self.config.get('prediction_interval_seconds', 300))
                
            except Exception as e:
                logger.error(f"Error in prediction loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _memory_management_loop(self):
        """Memory management loop"""
        while self.running:
            try:
                # Check for idle models
                self._check_idle_models()
                
                # Update VRAM usage
                self._update_vram_usage()
                
                # Sleep for memory check interval
                time.sleep(self.memory_check_interval)
                
            except Exception as e:
                logger.error(f"Error in memory management loop: {e}")
                time.sleep(5)
    
    def _kv_cache_cleanup_loop(self):
        """KV cache cleanup loop"""
        while self.running:
            try:
                current_time = time.time()
                
                # Remove expired KV caches
                expired_caches = []
                for conversation_id, last_used in self.kv_cache_last_used.items():
                    if current_time - last_used > self.kv_cache_timeout:
                        expired_caches.append(conversation_id)
                
                for conversation_id in expired_caches:
                    if conversation_id in self.kv_caches:
                        del self.kv_caches[conversation_id]
                    if conversation_id in self.kv_cache_last_used:
                        del self.kv_cache_last_used[conversation_id]
                
                # Limit number of KV caches
                if len(self.kv_caches) > self.max_kv_caches:
                    # Remove oldest caches
                    sorted_caches = sorted(
                        self.kv_cache_last_used.items(),
                        key=lambda x: x[1]
                    )
                    caches_to_remove = len(self.kv_caches) - self.max_kv_caches
                    
                    for conversation_id, _ in sorted_caches[:caches_to_remove]:
                        if conversation_id in self.kv_caches:
                            del self.kv_caches[conversation_id]
                        if conversation_id in self.kv_cache_last_used:
                            del self.kv_cache_last_used[conversation_id]
                
                # Sleep for cleanup interval
                time.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in KV cache cleanup loop: {e}")
                time.sleep(60)
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        action = request.get('action')
        
        # GGUF Model Management actions
        if action == 'load_model':
            return self._handle_load_model(request)
        elif action == 'unload_model':
            return self._handle_unload_model(request)
        elif action == 'generate_text':
            return self._handle_generate_text(request)
        elif action == 'get_model_status':
            return self._handle_get_model_status(request)
        
        # Predictive Loading actions
        elif action == 'predict_models':
            return self._handle_predict_models(request)
        elif action == 'record_usage':
            return self._handle_record_usage(request)
        
        # Evaluation Framework actions
        elif action == 'log_performance_metric':
            return self._handle_log_performance_metric(request)
        elif action == 'get_performance_metrics':
            return self._handle_get_performance_metrics(request)
        elif action == 'log_model_evaluation':
            return self._handle_log_model_evaluation(request)
        elif action == 'get_model_evaluation_scores':
            return self._handle_get_model_evaluation_scores(request)
        
        # Health and status actions
        elif action == 'health_check':
            return self._handle_health_check(request)
        elif action == 'get_stats':
            return self._handle_get_stats(request)
        
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
    
    def _get_health_status(self):
        """Get health status"""
        return {
            'status': 'HEALTHY',
            'agent': 'ModelManagerSuite',
            'uptime': time.time() - self.start_time,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'models_loaded': len(self.loaded_models),
            'models_tracked': len(self.models),
            'commands_processed': self.commands_processed
        }
    
    def report_error(self, error_type: str, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR):
        """Report error to error bus"""
        try:
            error_data = {
                'error_type': error_type,
                'message': message,
                'severity': severity.value,
                'timestamp': time.time(),
                'agent': self.name,
                'port': self.port
            }
            
            self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
            logger.error(f"Error reported: {error_type} - {message}")
            
        except Exception as e:
            logger.error(f"Failed to report error: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("ModelManagerSuite shutting down")
        self.running = False
        
        # Unload all models
        for model_id in list(self.loaded_models.keys()):
            try:
                self._unload_gguf_model(model_id)
            except Exception as e:
                logger.error(f"Error unloading model {model_id}: {e}")
        
        # Close ZMQ sockets
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'error_bus_pub'):
            self.error_bus_pub.close()
        
        # Close ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("ModelManagerSuite shutdown complete")
    
    def run(self):
        """Run the service (standard entrypoint)"""
        logger.info("ModelManagerSuite starting")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.cleanup()

# Import the consolidated modules
# from .gguf_manager import GGUFManager
# from .model_tracker import ModelTracker  
# from .predictive_loader import PredictiveLoader
# from .evaluation_framework import EvaluationFramework

    # ==================================================================
    # CORE GGUF MANAGEMENT (from GGUFModelManager)
    # ==================================================================
    
    def load_model(self, model_id: str) -> bool:
        """Load a GGUF model (consolidated from GGUFModelManager)"""
        with self.lock:
            if model_id in self.loaded_models:
                logger.info(f"Model {model_id} is already loaded")
                return True
                
            if model_id not in self.model_metadata:
                logger.error(f"Model {model_id} not found in metadata")
                return False
                
            model_info = self.model_metadata[model_id]
            model_path = self.models_dir / model_info['model_path']
            
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return False
                
            # Check if we have enough VRAM
            if not self._can_accommodate_model(model_info['estimated_vram_mb']):
                logger.error(f"Not enough VRAM to load model {model_id}")
                return False
                
            try:
                # Load the model
                model = Llama(
                    model_path=str(model_path),
                    n_ctx=model_info.get('n_ctx', 2048),
                    n_gpu_layers=model_info.get('n_gpu_layers', -1),
                    n_threads=model_info.get('n_threads', 4),
                    verbose=model_info.get('verbose', False)
                )
                
                self.loaded_models[model_id] = model
                self.last_used[model_id] = time.time()
                self.metrics['models_loaded'] += 1
                
                logger.info(f"Successfully loaded model {model_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error loading model {model_id}: {e}")
                return False
    
    def unload_model(self, model_id: str) -> bool:
        """Unload a GGUF model (consolidated from GGUFModelManager)"""
        with self.lock:
            if model_id not in self.loaded_models:
                logger.info(f"Model {model_id} is not loaded")
                return True
                
            try:
                # Clear KV caches for this model
                for conversation_id in list(self.kv_caches.keys()):
                    if model_id in self.kv_caches[conversation_id]:
                        del self.kv_caches[conversation_id][model_id]
                        if not self.kv_caches[conversation_id]:
                            del self.kv_caches[conversation_id]
                            if conversation_id in self.kv_cache_last_used:
                                del self.kv_cache_last_used[conversation_id]
                
                # Remove from loaded models
                del self.loaded_models[model_id]
                if model_id in self.last_used:
                    del self.last_used[model_id]
                
                self.metrics['models_unloaded'] += 1
                logger.info(f"Successfully unloaded model {model_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error unloading model {model_id}: {e}")
                return False
    
    def generate_text(self, model_id: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate text using a GGUF model (consolidated from GGUFModelManager)"""
        with self.lock:
            if model_id not in self.loaded_models:
                logger.error(f"Model {model_id} is not loaded")
                return {'error': f'Model {model_id} is not loaded'}
            
            try:
                model = self.loaded_models[model_id]
                
                # Get generation parameters
                max_tokens = kwargs.get('max_tokens', 256)
                temperature = kwargs.get('temperature', 0.7)
                top_p = kwargs.get('top_p', 0.95)
                conversation_id = kwargs.get('conversation_id')
                
                # Get KV cache if available
                kv_cache = None
                if conversation_id and conversation_id in self.kv_caches:
                    kv_cache = self.kv_caches[conversation_id].get(model_id)
                
                # Generate text
                response = model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    kv_cache=kv_cache,
                    stream=False
                )
                
                # Update KV cache
                if conversation_id and hasattr(response, 'kv_cache'):
                    if conversation_id not in self.kv_caches:
                        self.kv_caches[conversation_id] = {}
                    self.kv_caches[conversation_id][model_id] = response.kv_cache
                    self.kv_cache_last_used[conversation_id] = time.time()
                
                # Update last used time
                self.last_used[model_id] = time.time()
                
                # Record usage for prediction
                self._record_model_usage(model_id)
                
                return {
                    'text': response['choices'][0]['text'],
                    'model_id': model_id,
                    'conversation_id': conversation_id
                }
                
            except Exception as e:
                logger.error(f"Error generating text with model {model_id}: {e}")
                return {'error': str(e)}
    
    def _can_accommodate_model(self, required_vram_mb: float) -> bool:
        """Check if we can accommodate a model with given VRAM requirements"""
        if not torch.cuda.is_available():
            return True  # CPU-only mode
        
        try:
            current_vram = torch.cuda.memory_allocated() / (1024 * 1024)  # MB
            total_vram = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)  # MB
            available_vram = total_vram - current_vram
            
            return available_vram >= required_vram_mb
            
        except Exception as e:
            logger.error(f"Error checking VRAM availability: {e}")
            return False
    
    def _unload_gguf_model(self, model_id: str) -> bool:
        """Unload a GGUF model (internal method)"""
        return self.unload_model(model_id)
    
    # ==================================================================
    # PREDICTIVE LOADING (from PredictiveLoader)
    # ==================================================================
    
    def _predict_models(self) -> List[str]:
        """Predict which models will be needed in the near future (from PredictiveLoader)"""
        current_time = time.time()
        recent_usage = {}
        
        # Analyze usage patterns
        for model_id, usages in self.model_usage.items():
            # Filter to recent usage within prediction window
            recent = [u for u in usages if current_time - u < self.prediction_window]
            if recent:
                recent_usage[model_id] = len(recent)
        
        # Sort by frequency and return top models
        sorted_models = sorted(recent_usage.items(), key=lambda x: x[1], reverse=True)
        predicted_models = [model_id for model_id, _ in sorted_models[:3]]  # Top 3 models
        
        if predicted_models:
            logger.info(f"Predicted models for preloading: {predicted_models}")
        
        return predicted_models
    
    def _preload_models(self, model_ids: List[str]) -> None:
        """Preload predicted models (from PredictiveLoader)"""
        for model_id in model_ids:
            try:
                if model_id not in self.loaded_models:
                    logger.info(f"Preloading model {model_id}")
                    self.load_model(model_id)
                    self.metrics['predictions_made'] += 1
            except Exception as e:
                logger.error(f"Error preloading model {model_id}: {e}")
    
    def _record_model_usage(self, model_id: str) -> None:
        """Record model usage for prediction (from PredictiveLoader)"""
        current_time = time.time()
        
        if model_id not in self.model_usage:
            self.model_usage[model_id] = []
        
        self.model_usage[model_id].append(current_time)
        
        # Keep only recent usage data
        cutoff_time = current_time - self.prediction_window
        self.model_usage[model_id] = [
            usage_time for usage_time in self.model_usage[model_id]
            if usage_time > cutoff_time
        ]
    
    # ==================================================================
    # EVALUATION FRAMEWORK (from ModelEvaluationFramework)
    # ==================================================================
    
    def log_performance_metric(self, agent_name: str, metric_name: str, value: float, context: str = None) -> bool:
        """Log a performance metric (from ModelEvaluationFramework)"""
        try:
            metric_id = str(uuid.uuid4())
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (metric_id, agent_name, metric_name, value, timestamp, context)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (metric_id, agent_name, metric_name, value, datetime.now(), context))
            
            conn.commit()
            conn.close()
            
            self.metrics['performance_logs'] += 1
            logger.info(f"Logged performance metric: {agent_name}.{metric_name} = {value}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging performance metric: {e}")
            return False
    
    def get_performance_metrics(self, agent_name: str = None, metric_name: str = None, limit: int = 100) -> List[Dict]:
        """Get performance metrics (from ModelEvaluationFramework)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM performance_metrics WHERE 1=1"
            params = []
            
            if agent_name:
                query += " AND agent_name = ?"
                params.append(agent_name)
            
            if metric_name:
                query += " AND metric_name = ?"
                params.append(metric_name)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conn.close()
            
            # Convert to list of dictionaries
            metrics = []
            for row in rows:
                metrics.append({
                    'metric_id': row[0],
                    'agent_name': row[1],
                    'metric_name': row[2],
                    'value': row[3],
                    'timestamp': row[4],
                    'context': row[5]
                })
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return []
    
    def log_model_evaluation(self, model_name: str, cycle_id: str, trust_score: float, 
                           accuracy: float = None, f1_score: float = None, 
                           avg_latency_ms: float = 0.0, comparison_data: str = None) -> bool:
        """Log a model evaluation score (from ModelEvaluationFramework)"""
        try:
            evaluation_id = str(uuid.uuid4())
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO model_evaluation_scores 
                (evaluation_id, model_name, cycle_id, trust_score, accuracy, f1_score, 
                 avg_latency_ms, evaluation_timestamp, comparison_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (evaluation_id, model_name, cycle_id, trust_score, accuracy, f1_score,
                  avg_latency_ms, datetime.now(), comparison_data))
            
            conn.commit()
            conn.close()
            
            self.metrics['trust_score_updates'] += 1
            logger.info(f"Logged model evaluation: {model_name} trust_score={trust_score}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging model evaluation: {e}")
            return False
    
    def get_model_evaluation_scores(self, model_name: str = None, limit: int = 100) -> List[Dict]:
        """Get model evaluation scores (from ModelEvaluationFramework)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM model_evaluation_scores WHERE 1=1"
            params = []
            
            if model_name:
                query += " AND model_name = ?"
                params.append(model_name)
            
            query += " ORDER BY evaluation_timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            conn.close()
            
            # Convert to list of dictionaries
            evaluations = []
            for row in rows:
                evaluations.append({
                    'evaluation_id': row[0],
                    'model_name': row[1],
                    'cycle_id': row[2],
                    'trust_score': row[3],
                    'accuracy': row[4],
                    'f1_score': row[5],
                    'avg_latency_ms': row[6],
                    'evaluation_timestamp': row[7],
                    'comparison_data': row[8]
                })
            
            return evaluations
            
        except Exception as e:
            logger.error(f"Error getting model evaluation scores: {e}")
            return []
    
    # ==================================================================
    # REQUEST HANDLERS
    # ==================================================================
    
    def _handle_load_model(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle load model request"""
        model_id = request.get('model_id')
        if not model_id:
            return {'status': 'error', 'message': 'model_id is required'}
        
        success = self.load_model(model_id)
        return {
            'status': 'success' if success else 'error',
            'message': f'Model {model_id} {"loaded" if success else "failed to load"}'
        }
    
    def _handle_unload_model(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unload model request"""
        model_id = request.get('model_id')
        if not model_id:
            return {'status': 'error', 'message': 'model_id is required'}
        
        success = self.unload_model(model_id)
        return {
            'status': 'success' if success else 'error',
            'message': f'Model {model_id} {"unloaded" if success else "failed to unload"}'
        }
    
    def _handle_generate_text(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle generate text request"""
        model_id = request.get('model_id')
        prompt = request.get('prompt')
        
        if not model_id or not prompt:
            return {'status': 'error', 'message': 'model_id and prompt are required'}
        
        result = self.generate_text(model_id, prompt, **request.get('params', {}))
        return result
    
    def _handle_get_model_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get model status request"""
        model_id = request.get('model_id')
        
        if model_id:
            # Get specific model status
            if model_id in self.models:
                model_info = self.models[model_id].copy()
                model_info['loaded'] = model_id in self.loaded_models
                model_info['last_used'] = self.last_used.get(model_id)
                return {'status': 'success', 'model': model_info}
            else:
                return {'status': 'error', 'message': f'Model {model_id} not found'}
        else:
            # Get all models status
            models_status = {}
            for mid, model_info in self.models.items():
                models_status[mid] = model_info.copy()
                models_status[mid]['loaded'] = mid in self.loaded_models
                models_status[mid]['last_used'] = self.last_used.get(mid)
            
            return {'status': 'success', 'models': models_status}
    
    def _handle_predict_models(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle predict models request"""
        predicted_models = self._predict_models()
        return {
            'status': 'success',
            'predicted_models': predicted_models
        }
    
    def _handle_record_usage(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle record usage request"""
        model_id = request.get('model_id')
        if not model_id:
            return {'status': 'error', 'message': 'model_id is required'}
        
        self._record_model_usage(model_id)
        return {'status': 'success', 'message': f'Usage recorded for model {model_id}'}
    
    def _handle_log_performance_metric(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle log performance metric request"""
        agent_name = request.get('agent_name')
        metric_name = request.get('metric_name')
        value = request.get('value')
        context = request.get('context')
        
        if not all([agent_name, metric_name, value is not None]):
            return {'status': 'error', 'message': 'agent_name, metric_name, and value are required'}
        
        success = self.log_performance_metric(agent_name, metric_name, value, context)
        return {
            'status': 'success' if success else 'error',
            'message': f'Performance metric {"logged" if success else "failed to log"}'
        }
    
    def _handle_get_performance_metrics(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get performance metrics request"""
        agent_name = request.get('agent_name')
        metric_name = request.get('metric_name')
        limit = request.get('limit', 100)
        
        metrics = self.get_performance_metrics(agent_name, metric_name, limit)
        return {
            'status': 'success',
            'metrics': metrics
        }
    
    def _handle_log_model_evaluation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle log model evaluation request"""
        model_name = request.get('model_name')
        cycle_id = request.get('cycle_id')
        trust_score = request.get('trust_score')
        
        if not all([model_name, cycle_id, trust_score is not None]):
            return {'status': 'error', 'message': 'model_name, cycle_id, and trust_score are required'}
        
        accuracy = request.get('accuracy')
        f1_score = request.get('f1_score')
        avg_latency_ms = request.get('avg_latency_ms', 0.0)
        comparison_data = request.get('comparison_data')
        
        success = self.log_model_evaluation(
            model_name, cycle_id, trust_score, accuracy, f1_score, avg_latency_ms, comparison_data
        )
        return {
            'status': 'success' if success else 'error',
            'message': f'Model evaluation {"logged" if success else "failed to log"}'
        }
    
    def _handle_get_model_evaluation_scores(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get model evaluation scores request"""
        model_name = request.get('model_name')
        limit = request.get('limit', 100)
        
        evaluations = self.get_model_evaluation_scores(model_name, limit)
        return {
            'status': 'success',
            'evaluations': evaluations
        }
    
    def _handle_health_check(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check request"""
        return self._get_health_status()
    
    def _handle_get_stats(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get stats request"""
        return {
            'status': 'success',
            'metrics': self.metrics,
            'models_loaded': len(self.loaded_models),
            'models_tracked': len(self.models),
            'commands_processed': self.commands_processed
        }
    
    # ==================================================================
    # UTILITY METHODS
    # ==================================================================
    
    def _check_idle_models(self) -> None:
        """Check for idle models and unload them if necessary"""
        current_time = time.time()
        
        for model_id in list(self.loaded_models.keys()):
            last_used = self.last_used.get(model_id, 0)
            if current_time - last_used > self.idle_timeout:
                logger.info(f"Unloading idle model {model_id}")
                self.unload_model(model_id)
    
    def _update_vram_usage(self) -> None:
        """Update VRAM usage tracking"""
        if not torch.cuda.is_available():
            return
        
        try:
            allocated = torch.cuda.memory_allocated() / (1024 * 1024)  # MB
            reserved = torch.cuda.memory_reserved() / (1024 * 1024)  # MB
            total = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)  # MB
            
            # Log VRAM usage periodically
            if hasattr(self, '_last_vram_log') and current_time - self._last_vram_log > 300:  # 5 minutes
                logger.info(f"VRAM Usage - Allocated: {allocated:.1f}MB, Reserved: {reserved:.1f}MB, Total: {total:.1f}MB")
                self._last_vram_log = current_time
                
        except Exception as e:
            logger.error(f"Error updating VRAM usage: {e}")


if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='ModelManagerSuite - Consolidated Model Management Service')
    parser.add_argument('--port', type=int, default=7011, help='Service port')
    parser.add_argument('--health-port', type=int, default=7111, help='Health check port')
    parser.add_argument('--config', type=str, help='Configuration file path')
    
    args = parser.parse_args()
    
    # Create and run the service
    service = ModelManagerSuite(port=args.port, health_port=args.health_port)
    service.run() 