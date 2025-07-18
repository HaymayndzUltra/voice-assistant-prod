#!/usr/bin/env python3
"""
ModelManagerSuite - Consolidated Model Management Service
=======================================================

This service consolidates the following agents into a unified service:
- GGUFModelManager: Handles loading, unloading, and managing GGUF models
- ModelManagerAgent: Tracks status and availability of all models
- PredictiveLoader: Predicts and preloads models based on usage patterns
- ModelEvaluationFramework: Tracks model performance and evaluation

Port: 7011 (Main service)
Health: 7112 (Health check)
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
    main_pc_code_dir = current_dir.parent
    return main_pc_code_dir

def join_path(*args):
    return os.path.join(*args)

sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
from common.core.base_agent import BaseAgent
from common.utils.data_models import ErrorSeverity
from common.utils.learning_models import PerformanceMetric, ModelEvaluationScore

# Import config modules
from main_pc_code.utils.config_loader import load_config, Config, parse_agent_args
from main_pc_code.config import system_config
from main_pc_code.config.pc2_services_config import load_pc2_services, get_service_connection, list_available_services

# Try to import Llama from llama_cpp
try:
    from llama_cpp import Llama  # type: ignore
    LLAMA_CPP_AVAILABLE = True
except ImportError as e:
    LLAMA_CPP_AVAILABLE = False
    print(f"WARNING: llama-cpp-python not available. GGUF models will not work. Error: {e}")

# Configure logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'model_manager_suite.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ModelManagerSuite")

# Load configuration
config = load_config()

# Default VRAM management settings
DEFAULT_VRAM_CONFIG = {
    'vram_budget_percentage': 80,  # Use up to 80% of available VRAM
    'vram_budget_mb': 4096,        # Default to 4GB VRAM budget
    'idle_unload_timeout_seconds': 300,  # Unload models after 5 minutes of inactivity
    'memory_check_interval': 5,    # Check memory every 5 seconds
    'min_vram_mb': 512,           # Minimum VRAM to keep free
    'max_models_in_memory': 3,     # Maximum number of models to keep loaded
    'priority_levels': {
        'high': 1,
        'medium': 2,
        'low': 3
    }
}

def is_port_in_use(port: int) -> bool:
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                return True
            raise

def wait_for_port(port: int, timeout: int = 30) -> bool:
    """Wait for a port to become available"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            return True
        time.sleep(1)
    return False

class ModelManagerSuite(BaseAgent):
    """
    Consolidated Model Management Service
    
    This service combines the functionality of:
    - GGUFModelManager: GGUF model loading/unloading
    - ModelManagerAgent: Model status tracking and resource management
    - PredictiveLoader: Predictive model preloading
    - ModelEvaluationFramework: Performance tracking and evaluation
    """
    
    def __init__(self, port: int = 7011, health_port: int = 7112, **kwargs):
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
        # VRAM management
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if self.device == 'cuda':
            self.total_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
            self.vram_budget_percentage = self.config.get('vram_budget_percentage', 80)
            self.vram_budget_mb = self.total_gpu_memory * (self.vram_budget_percentage / 100)
        else:
            self.total_gpu_memory = 0
            self.vram_budget_mb = 0
        
        # Model tracking
        self.loaded_model_instances = {}
        self.model_last_used = {}
        self.model_memory_usage = {}
        self.model_last_used_timestamp = {}
        self.models = {}
        self.current_estimated_vram_used = 0.0
        
        # Memory management settings
        self.memory_check_interval = self.config.get('memory_check_interval', 5)
        self.idle_unload_timeout_seconds = self.config.get('idle_unload_timeout_seconds', 300)
        
        logger.info(f"Model tracking initialized - VRAM: device={self.device}, total={self.total_gpu_memory:.0f}MB, budget={self.vram_budget_mb:.0f}MB")
    
    def _init_predictive_loading(self):
        """Initialize predictive loading functionality"""
        self.model_usage = {}
        self.prediction_window = 3600  # 1 hour
        self.lookahead_window = 300    # 5 minutes
        
        # Prediction tracking
        self.prediction_history = []
        self.last_prediction_time = time.time()
    
    def _init_evaluation_framework(self):
        """Initialize model evaluation framework"""
        self.db_path = self.config.get('mef_db_path', join_path("data", "model_evaluation.db"))
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_database()
        
        # Evaluation metrics
        self.evaluation_scores = {}
        self.performance_history = {}
    
    def _init_zmq(self):
        """Initialize ZMQ sockets and networking"""
        # Main service socket
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Health check socket
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.bind(f"tcp://*:{self.health_check_port}")
        
        # Request coordinator connection
        self.request_coordinator_port = self.config.get('request_coordinator_port', 8571)
        self.request_coordinator_socket = self.context.socket(zmq.REQ)
        self.request_coordinator_socket.connect(f"tcp://localhost:{self.request_coordinator_port}")
        
        logger.info(f"ZMQ initialized - Main: {self.port}, Health: {self.health_check_port}")
    
    def _init_error_reporting(self):
        """Initialize error reporting system"""
        self.error_bus_port = self.config.get('error_bus_port', 7150)
        self.error_bus_host = os.environ.get('PC2_IP', self.config.get('error_bus_host', '192.168.100.17'))
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
    
    def _init_circuit_breakers(self):
        """Initialize circuit breakers for downstream services"""
        try:
            from main_pc_code.agents.request_coordinator import CircuitBreaker
            for service in self.downstream_services:
                self.circuit_breakers[service] = CircuitBreaker(name=service)
        except ImportError:
            logger.warning("CircuitBreaker not available, skipping circuit breaker initialization")
    
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
    

    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main request handler - consolidated from all 4 source agents
        Routes requests to appropriate functionality based on action
        """
        try:
            action = request.get('action')
            if not action:
                return {'status': 'error', 'message': 'Missing action field'}
            
            # ==================================================================
            # GGUF MANAGEMENT ACTIONS (from GGUFModelManager)
            # ==================================================================
            if action == 'load_model':
                model_id = request.get('model_id')
                if not model_id:
                    return {'status': 'error', 'message': 'model_id required'}
                success = self.load_model(model_id)
                return {'status': 'success' if success else 'error', 'loaded': success}
            
            elif action == 'unload_model':
                model_id = request.get('model_id')
                if not model_id:
                    return {'status': 'error', 'message': 'model_id required'}
                success = self.unload_model(model_id)
                return {'status': 'success' if success else 'error', 'unloaded': success}
            
            elif action == 'generate_text':
                model_id = request.get('model_id')
                prompt = request.get('prompt')
                if not model_id or not prompt:
                    return {'status': 'error', 'message': 'model_id and prompt required'}
                
                result = self.generate_text(
                    model_id=model_id,
                    prompt=prompt,
                    system_prompt=request.get('system_prompt'),
                    max_tokens=request.get('max_tokens', 1024),
                    temperature=request.get('temperature', 0.7),
                    top_p=request.get('top_p', 0.95),
                    stop=request.get('stop'),
                    conversation_id=request.get('conversation_id')
                )
                return result
            
            elif action == 'list_models':
                return {'status': 'success', 'models': self.list_models()}
            
            # ==================================================================
            # MODEL MANAGEMENT ACTIONS (from ModelManagerAgent)
            # ==================================================================
            elif action == 'health_check':
                return self.health_check()
            
            elif action == 'select_model':
                task_type = request.get('task_type')
                context_size = request.get('context_size')
                if not task_type:
                    return {'status': 'error', 'message': 'task_type required'}
                
                selected_model = self.select_model(task_type, context_size)
                if selected_model:
                    return {'status': 'success', 'selected_model': selected_model}
                else:
                    return {'status': 'error', 'message': 'No suitable model found'}
            
            elif action == 'get_loaded_models_status':
                loaded_models = {}
                with self.lock:
                    for model_id in self.loaded_models:
                        loaded_models[model_id] = {
                            'status': 'online',
                            'last_used': self.last_used.get(model_id),
                            'vram_usage': self.model_memory_usage.get(model_id, 0)
                        }
                return {'status': 'success', 'loaded_models': loaded_models}
            
            # ==================================================================
            # PREDICTIVE LOADING ACTIONS (from PredictiveLoader)
            # ==================================================================
            elif action == 'predict_models':
                predicted_models = self._predict_models()
                return {'status': 'success', 'predicted_models': predicted_models}
            
            elif action == 'record_usage':
                model_id = request.get('model_id')
                if not model_id:
                    return {'status': 'error', 'message': 'model_id required'}
                self._record_model_usage(model_id)
                return {'status': 'success', 'message': 'Usage recorded'}
            
            elif action == 'preload_models':
                model_ids = request.get('model_ids', [])
                self._preload_models(model_ids)
                return {'status': 'success', 'message': f'Preloaded {len(model_ids)} models'}
            
            # ==================================================================
            # EVALUATION FRAMEWORK ACTIONS (from ModelEvaluationFramework)
            # ==================================================================
            elif action == 'log_performance_metric':
                agent_name = request.get('agent_name')
                metric_name = request.get('metric_name')
                value = request.get('value')
                metadata = request.get('metadata')
                
                if not agent_name or not metric_name or value is None:
                    return {'status': 'error', 'message': 'agent_name, metric_name, and value required'}
                
                try:
                    return self.log_performance_metric(str(agent_name), str(metric_name), float(value), metadata)
                except (ValueError, TypeError) as e:
                    return {'status': 'error', 'message': f'Invalid value types: {e}'}
            
            elif action == 'log_model_evaluation':
                model_name = request.get('model_name')
                cycle_id = request.get('cycle_id')
                trust_score = request.get('trust_score')
                
                if not model_name or not cycle_id or trust_score is None:
                    return {'status': 'error', 'message': 'model_name, cycle_id, and trust_score required'}
                
                try:
                    return self.log_model_evaluation(
                        model_name=str(model_name),
                        cycle_id=str(cycle_id),
                        trust_score=float(trust_score),
                        accuracy=float(request.get('accuracy', 0)) if request.get('accuracy') is not None else None,
                        f1_score=float(request.get('f1_score', 0)) if request.get('f1_score') is not None else None,
                        avg_latency_ms=float(request.get('avg_latency_ms', 0.0)),
                        comparison_data=request.get('comparison_data')
                    )
                except (ValueError, TypeError) as e:
                    return {'status': 'error', 'message': f'Invalid value types: {e}'}
            
            elif action == 'get_performance_metrics':
                agent_name = request.get('agent_name')
                start_time = request.get('start_time')
                end_time = request.get('end_time')
                
                try:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    query = "SELECT * FROM performance_metrics WHERE 1=1"
                    params = []
                    
                    if agent_name:
                        query += " AND agent_name = ?"
                        params.append(agent_name)
                    
                    if start_time:
                        query += " AND timestamp >= ?"
                        params.append(start_time)
                    
                    if end_time:
                        query += " AND timestamp <= ?"
                        params.append(end_time)
                    
                    query += " ORDER BY timestamp DESC LIMIT 100"
                    
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    conn.close()
                    
                    metrics = []
                    for row in results:
                        metrics.append({
                            'metric_id': row[0],
                            'agent_name': row[1],
                            'metric_name': row[2],
                            'value': row[3],
                            'timestamp': row[4],
                            'context': json.loads(row[5]) if row[5] else None
                        })
                    
                    return {'status': 'success', 'metrics': metrics}
                    
                except Exception as e:
                    logger.error(f"Error getting performance metrics: {e}")
                    return {'status': 'error', 'message': str(e)}
            
            elif action == 'get_stats':
                return {'status': 'success', 'metrics': self.metrics}
            
            # ==================================================================
            # LEGACY COMPATIBILITY ACTIONS
            # ==================================================================
            elif action == 'generate':  # Legacy from ModelManagerAgent
                model_pref = request.get('model_pref', 'fast')
                prompt = request.get('prompt')
                if not prompt:
                    return {'status': 'error', 'message': 'prompt required'}
                
                # Simple model selection based on preference
                if model_pref == 'fast':
                    task_type = 'code-generation'
                elif model_pref == 'smart':
                    task_type = 'reasoning'
                else:
                    task_type = 'code-generation'
                
                model_id = self.select_model(task_type)
                if not model_id:
                    return {'status': 'error', 'message': 'No suitable model available'}
                
                return self.generate_text(
                    model_id=model_id,
                    prompt=prompt,
                    max_tokens=request.get('params', {}).get('max_tokens', 256),
                    temperature=request.get('params', {}).get('temperature', 0.7),
                    conversation_id=request.get('conversation_id')
                )
            
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
            
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.report_error("handle_request_error", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def _start_background_threads(self):
        """Start all background threads"""
        threads = [
            threading.Thread(target=self._main_loop, daemon=True),
            threading.Thread(target=self._health_check_loop, daemon=True),
            threading.Thread(target=self._vram_management_loop, daemon=True),
            threading.Thread(target=self._prediction_loop, daemon=True),
            threading.Thread(target=self._kv_cache_cleanup_loop, daemon=True),
        ]
        
        for thread in threads:
            thread.start()
        
        self._background_threads = threads
        logger.info(f"Started {len(threads)} background threads")
    
    def _main_loop(self):
        """Main service loop"""
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
                events = dict(poller.poll(1000))
                if self.health_socket in events and events[self.health_socket] == zmq.POLLIN:
                    message = self.health_socket.recv_json()
                    self.health_socket.send_json(self._get_health_status())
            except Exception as e:
                logger.error(f"Health check error: {e}")
                time.sleep(1)
    
    def _vram_management_loop(self):
        """VRAM management loop"""
        while self.running:
            try:
                self._check_idle_models()
                self._update_vram_usage()
                time.sleep(self.memory_check_interval)
            except Exception as e:
                logger.error(f"VRAM management error: {e}")
                time.sleep(5)
    
    def _prediction_loop(self):
        """Predictive loading loop"""
        while self.running:
            try:
                predicted_models = self._predict_models()
                if predicted_models:
                    self._preload_models(predicted_models)
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Prediction error: {e}")
                time.sleep(60)
    
    def _kv_cache_cleanup_loop(self):
        """KV cache cleanup loop"""
        while self.running:
            try:
                self._manage_kv_cache_size()
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"KV cache cleanup error: {e}")
                time.sleep(300)
    
    def _get_health_status(self):
        """Get health status for the service"""
        return {
            'status': 'ok',
            'agent': 'ModelManagerSuite',
            'uptime': time.time() - self.start_time,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
            'commands_processed': self.commands_processed,
            'loaded_models': len(self.loaded_models),
            'vram_used_mb': self.current_estimated_vram_used,
            'vram_budget_mb': self.vram_budget_mb,
            'device': self.device,
            'metrics': self.metrics
        }
    
    def report_error(self, error_type: str, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR):
        """Report error to the error bus"""
        try:
            error_message = {
                'topic': 'ERROR',
                'error_type': error_type,
                'message': message,
                'severity': severity.value,
                'timestamp': time.time(),
                'agent': 'ModelManagerSuite'
            }
            self.error_bus_pub.send_json(error_message)
        except Exception as e:
            logger.error(f"Failed to report error: {e}")
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        
        # Unload all models
        with self.lock:
            for model_id in list(self.loaded_models.keys()):
                self.unload_model(model_id)
        
        # Close ZMQ sockets
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'request_coordinator_socket'):
            self.request_coordinator_socket.close()
        if hasattr(self, 'error_bus_pub'):
            self.error_bus_pub.close()
        
        # Close ZMQ context
        if hasattr(self, 'context'):
            self.context.term()
        
        logger.info("ModelManagerSuite cleanup completed")
    
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
                self.last_used[model_id] = time.time()
                return True
                
            if model_id not in self.model_metadata:
                logger.error(f"Model {model_id} not found in metadata")
                return False
                
            model_info = self.model_metadata[model_id]
            models_dir = Path(self.config.get('models_dir', 'models'))
            model_path = models_dir / model_info['model_path']
            
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return False
                
            # Check VRAM availability
            required_vram = model_info.get('estimated_vram_mb', 0)
            if not self._can_accommodate_model(required_vram):
                logger.error(f"Not enough VRAM to load model {model_id}")
                return False
                
            try:
                if LLAMA_CPP_AVAILABLE:
                    # Load using llama-cpp-python
                    model = Llama(
                        model_path=str(model_path),
                        n_ctx=model_info.get('n_ctx', 2048),
                        n_gpu_layers=model_info.get('n_gpu_layers', -1),
                        n_threads=model_info.get('n_threads', 4),
                        verbose=model_info.get('verbose', False)
                    )
                    
                    self.loaded_models[model_id] = model
                    self.last_used[model_id] = time.time()
                    self.current_estimated_vram_used += required_vram
                    self.model_memory_usage[model_id] = required_vram
                    
                    # Update model status
                    if model_id in self.models:
                        self.models[model_id]['status'] = 'online'
                        
                    logger.info(f"Successfully loaded GGUF model {model_id}")
                    return True
                else:
                    logger.error("llama-cpp-python not available")
                    return False
                    
            except Exception as e:
                logger.error(f"Error loading model {model_id}: {e}")
                self.report_error("model_load_error", str(e))
                return False
    
    def unload_model(self, model_id: str) -> bool:
        """Unload a GGUF model (consolidated from GGUFModelManager)"""
        with self.lock:
            if model_id not in self.loaded_models:
                logger.warning(f"Model {model_id} is not loaded")
                return True
                
            try:
                # Remove from loaded models
                del self.loaded_models[model_id]
                
                # Update VRAM tracking
                vram_used = self.model_memory_usage.get(model_id, 0)
                self.current_estimated_vram_used -= vram_used
                self.model_memory_usage.pop(model_id, None)
                self.last_used.pop(model_id, None)
                
                # Update model status
                if model_id in self.models:
                    self.models[model_id]['status'] = 'available_not_loaded'
                
                # Force garbage collection
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                logger.info(f"Successfully unloaded model {model_id}")
                return True
                
            except Exception as e:
                logger.error(f"Error unloading model {model_id}: {e}")
                self.report_error("model_unload_error", str(e))
                return False
    
    def generate_text(self, model_id: str, prompt: str, system_prompt: Optional[str] = None,
                     max_tokens: int = 1024, temperature: float = 0.7,
                     top_p: float = 0.95, stop: Optional[List[str]] = None,
                     conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate text using a GGUF model (consolidated from GGUFModelManager)"""
        if not LLAMA_CPP_AVAILABLE:
            return {"error": "llama-cpp-python not available"}
            
        if model_id not in self.loaded_models:
            logger.warning(f"Model {model_id} not loaded, attempting to load")
            if not self.load_model(model_id):
                return {"error": f"Failed to load model {model_id}"}
        
        # Update last used timestamp
        self.last_used[model_id] = time.time()
        
        try:
            model = self.loaded_models[model_id]
            
            # Build the full prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
            
            # Generate text
            response = model(
                full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop or []
            )
            
            generated_text = response['choices'][0]['text']
            
            # Record usage for prediction
            self._record_model_usage(model_id)
            
            return {
                "status": "success",
                "text": generated_text,
                "model_id": model_id,
                "tokens_generated": len(generated_text.split()),
                "conversation_id": conversation_id
            }
            
        except Exception as e:
            logger.error(f"Error generating text with model {model_id}: {e}")
            self.report_error("text_generation_error", str(e))
            return {"error": str(e)}
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all available models with their status (consolidated from GGUFModelManager)"""
        models = []
        
        with self.lock:
            for model_id, metadata in self.model_metadata.items():
                model_info = metadata.copy()
                model_info['model_id'] = model_id
                model_info['loaded'] = model_id in self.loaded_models
                model_info['status'] = self.models.get(model_id, {}).get('status', 'unknown')
                
                if model_id in self.last_used:
                    model_info['last_used'] = self.last_used[model_id]
                    model_info['idle_time'] = time.time() - self.last_used[model_id]
                
                models.append(model_info)
        
        return models
    
    # ==================================================================
    # MODEL TRACKING & HEALTH (from ModelManagerAgent)
    # ==================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health/status of all configured models (from ModelManagerAgent)"""
        try:
            results = {}
            total_models = len(self.models)
            online_models = 0
            
            for model_id, model_info in self.models.items():
                status = self._check_individual_model_health(model_id, model_info)
                results[model_id] = status
                if status.get('status') == 'online':
                    online_models += 1
            
            overall_status = "healthy" if online_models > 0 else "degraded"
            
            return {
                "status": overall_status,
                "total_models": total_models,
                "online_models": online_models,
                "loaded_models": len(self.loaded_models),
                "vram_used_mb": self.current_estimated_vram_used,
                "vram_budget_mb": self.vram_budget_mb,
                "model_details": results,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return {"status": "error", "message": str(e)}
    
    def select_model(self, task_type: str, context_size: Optional[int] = None) -> Optional[str]:
        """Select the best model for a given task type (from ModelManagerAgent)"""
        # Filter for models that support the requested task type
        capable_models = {}
        for model_id, info in self.models.items():
            if task_type in info.get('capabilities', []):
                capable_models[model_id] = info
        
        if not capable_models:
            logger.warning(f"No models have capability '{task_type}'!")
            return None
        
        # Filter by context size if specified
        if context_size:
            suitable_models = {
                model_id: info for model_id, info in capable_models.items() 
                if info.get('context_length', 0) >= context_size
            }
            
            if suitable_models:
                capable_models = suitable_models
            else:
                logger.warning(f"No models can handle context size {context_size}!")
        
        # Prioritize loaded models, then by status
        online_models = {
            model_id: info for model_id, info in capable_models.items() 
            if info.get('status', '') == 'online'
        }
        
        if online_models:
            # Return the first online model (could add more sophisticated selection logic)
            return list(online_models.keys())[0]
        
        # If no online models, return any available model
        available_models = {
            model_id: info for model_id, info in capable_models.items() 
            if info.get('status', '') == 'available_not_loaded'
        }
        
        if available_models:
            return list(available_models.keys())[0]
        
        return None
    
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
        
        # Keep only recent usage (within prediction window)
        cutoff_time = current_time - self.prediction_window
        self.model_usage[model_id] = [
            usage_time for usage_time in self.model_usage[model_id] 
            if usage_time > cutoff_time
        ]
    
    # ==================================================================
    # EVALUATION FRAMEWORK (from ModelEvaluationFramework)
    # ==================================================================
    
    def log_performance_metric(self, agent_name: str, metric_name: str, 
                             value: float, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """Log a performance metric (from ModelEvaluationFramework)"""
        try:
            metric_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO performance_metrics 
                (metric_id, agent_name, metric_name, value, timestamp, context)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                metric_id,
                agent_name,
                metric_name,
                value,
                timestamp.isoformat(),
                json.dumps(metadata) if metadata else None
            ))
            conn.commit()
            conn.close()
            
            self.metrics['performance_logs'] += 1
            logger.info(f"Logged performance metric: {agent_name}.{metric_name} = {value}")
            
            return {'status': 'success', 'metric_id': metric_id}
            
        except Exception as e:
            logger.error(f"Error logging performance metric: {e}")
            self.report_error("log_performance_metric_error", str(e))
            return {'status': 'error', 'message': str(e)}
    
    def log_model_evaluation(self, model_name: str, cycle_id: str, trust_score: float,
                           accuracy: Optional[float] = None, f1_score: Optional[float] = None,
                           avg_latency_ms: float = 0.0, comparison_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Log model evaluation scores (from ModelEvaluationFramework)"""
        try:
            evaluation_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO model_evaluation_scores 
                (evaluation_id, model_name, cycle_id, trust_score, accuracy, f1_score, 
                 avg_latency_ms, evaluation_timestamp, comparison_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                evaluation_id,
                model_name,
                cycle_id,
                trust_score,
                accuracy,
                f1_score,
                avg_latency_ms,
                timestamp.isoformat(),
                json.dumps(comparison_data) if comparison_data else None
            ))
            conn.commit()
            conn.close()
            
            self.metrics['trust_score_updates'] += 1
            logger.info(f"Logged model evaluation: {model_name} (trust: {trust_score})")
            
            return {'status': 'success', 'evaluation_id': evaluation_id}
            
        except Exception as e:
            logger.error(f"Error logging model evaluation: {e}")
            self.report_error("log_model_evaluation_error", str(e))
            return {'status': 'error', 'message': str(e)}
    
    # ==================================================================
    # HELPER METHODS
    # ==================================================================
    
    def _can_accommodate_model(self, required_vram_mb: float) -> bool:
        """Check if we can accommodate a model with given VRAM requirements"""
        available_vram = self.vram_budget_mb - self.current_estimated_vram_used
        return available_vram >= required_vram_mb
    
    def _check_individual_model_health(self, model_id: str, model_info: Dict) -> Dict[str, Any]:
        """Check health of an individual model"""
        try:
            if model_id in self.loaded_models:
                return {"status": "online", "message": "Model is loaded and ready"}
            elif model_info.get('status') == 'available_not_loaded':
                return {"status": "available", "message": "Model is available but not loaded"}
            else:
                return {"status": "error", "message": "Model status unknown"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _load_model_metadata(self):
        """Load model metadata from configuration"""
        try:
            from main_pc_code.config.system_config import Config
            system_config = Config()
            machine_config = system_config.get_all().get('main_pc_settings', {})
            
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
                    
                    # Initialize in models registry
                    self.models[model_id] = {
                        'display_name': model_info.get('display_name', model_id),
                        'serving_method': 'gguf_direct',
                        'status': 'available_not_loaded',
                        'estimated_vram_mb': model_info.get('estimated_vram_mb', 0),
                        'context_length': model_info.get('context_length', 2048),
                        'capabilities': model_info.get('capabilities', ["code-generation"]),
                        'idle_timeout_seconds': model_info.get('idle_timeout_seconds', 300)
                    }
                    
            logger.info(f"Loaded metadata for {len(self.model_metadata)} GGUF models")
            
        except Exception as e:
            logger.error(f"Error loading model metadata: {e}")
            self.report_error("metadata_load_error", str(e))
    
    def _check_idle_models(self):
        """Check for idle models and unload them if necessary"""
        current_time = time.time()
        models_to_unload = []
        
        with self.lock:
            for model_id in list(self.loaded_models.keys()):
                last_used_time = self.last_used.get(model_id, current_time)
                idle_time = current_time - last_used_time
                
                model_timeout = self.models.get(model_id, {}).get('idle_timeout_seconds', self.idle_unload_timeout_seconds)
                
                if idle_time > model_timeout:
                    models_to_unload.append(model_id)
        
        for model_id in models_to_unload:
            logger.info(f"Unloading idle model {model_id}")
            self.unload_model(model_id)
    
    def _update_vram_usage(self):
        """Update VRAM usage tracking"""
        if torch.cuda.is_available():
            try:
                current_usage = torch.cuda.memory_allocated() / (1024 * 1024)  # Convert to MB
                logger.debug(f"Current GPU memory usage: {current_usage:.2f}MB")
            except Exception as e:
                logger.debug(f"Could not get GPU memory usage: {e}")
    
    def _manage_kv_cache_size(self):
        """Manage KV cache size and cleanup old entries"""
        current_time = time.time()
        
        # Remove expired caches
        expired_conversations = []
        for conversation_id, last_used_time in self.kv_cache_last_used.items():
            if current_time - last_used_time > self.kv_cache_timeout:
                expired_conversations.append(conversation_id)
        
        for conversation_id in expired_conversations:
            self.kv_caches.pop(conversation_id, None)
            self.kv_cache_last_used.pop(conversation_id, None)
        
        # Limit total cache size
        if len(self.kv_caches) > self.max_kv_caches:
            # Remove oldest caches
            sorted_conversations = sorted(
                self.kv_cache_last_used.items(), 
                key=lambda x: x[1]
            )
            
            conversations_to_remove = sorted_conversations[:-self.max_kv_caches]
            for conversation_id, _ in conversations_to_remove:
                self.kv_caches.pop(conversation_id, None)
                self.kv_cache_last_used.pop(conversation_id, None)

if __name__ == "__main__":
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="ModelManagerSuite - Consolidated Model Management Service")
    parser.add_argument("--port", type=int, default=7011, help="Main service port")
    parser.add_argument("--health-port", type=int, default=7112, help="Health check port")
    parser.add_argument("--config", type=str, help="Configuration file path")
    
    args = parser.parse_args()
    
    # Create and run the service
    service = ModelManagerSuite(port=args.port, health_port=args.health_port)
    service.run()