from src.core.base_agent import BaseAgent
"""
Model Manager / Resource Monitor Agent
- Tracks status and availability of all models
- Reports health to Task Router
- Provides model selection based on availability and task requirements
"""
# MMA_DIAG_VERSION_CHECK: CODE_VERSION_IMPROVED_MMA_001
print("!!! MMA SCRIPT (CODE_VERSION_IMPROVED_MMA_001) IS STARTING EXECUTION !!!")
print("!!! MMA VERSION: IMPROVED_MMA_001 - WITH TYPE HINTS, ERROR HANDLING, AND VERSION TRACKING !!!")

from typing import Dict, List, Optional, Union, Any, Tuple
import zmq
import torch
import json
import time
import logging
import requests
import threading
import sys
import os
import re
from pathlib import Path
import pickle
from datetime import datetime, timedelta
import traceback
import logging.handlers
import socket
import errno
import psutil
import GPUtil

# Add the parent directory to sys.path to import the config module
sys.path.append(str(Path(__file__).parent.parent))

# Import config module
from utils.config_loader import Config
config = Config() # Instantiate the global config object

# Import system_config for per-machine settings
from config import system_config

# Import the GGUF connector
from agents.model_manager_agent_gguf_connector import get_instance as get_gguf_connector

# Import PC2 services config module
from main_pc_code.config.pc2_services_config import load_pc2_services, get_service_connection, list_available_services

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
    """Check if a port is in use
    
    Args:
        port: The port number to check
        
    Returns:
        True if the port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                return True
            raise

def wait_for_port(port: int, timeout: int = 30) -> bool:
    """Wait for a port to become available
    
    Args:
        port: The port number to wait for
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if port became available, False if timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if not is_port_in_use(port):
            return True
        time.sleep(1)
    return False

# --- MMA LOGGING STRATEGY PATCH START ---
from logging.handlers import RotatingFileHandler

# Determine if running in test mode (MMA_CONFIG_PATH set)
test_config_path = os.environ.get("MMA_CONFIG_PATH")
if test_config_path:
    # Dedicated log file for test run
    test_log_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    test_log_filename = f'logs/mma_test_{test_log_timestamp}.log'
    log_file_path = test_log_filename
else:
    # Default log file with rotation
    log_file_path = 'logs/mma_PATCH_VERIFY_TEST.log'

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Remove all existing handlers from root logger
for handler in list(logging.getLogger().handlers):
    logging.getLogger().removeHandler(handler)

# Setup RotatingFileHandler (5MB per file, keep 5 backups)
file_handler = RotatingFileHandler(log_file_path, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Setup StreamHandler for console
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Add handlers to root logger
logging.getLogger().addHandler(file_handler)
logging.getLogger().addHandler(stream_handler)
logging.getLogger().setLevel(logging.DEBUG)

# Create ModelManager logger
logger = logging.getLogger('ModelManager')
logger.setLevel(logging.DEBUG)

logger.critical(f"MMA logging to: {log_file_path} (test mode: {bool(test_config_path)})")
print(f"[MMA STARTUP] Logging to: {log_file_path}")

# === VERSION BANNER ===
logger.critical("--- EXECUTING MAIN MMA (agents/) Version: GGUF_GRANULAR_LOG_V_ULTIMATE ---")

# ZMQ ports
MODEL_MANAGER_PORT = 5570
TASK_ROUTER_PORT = 5571

class ModelManagerAgent(BaseAgent):
    """Model Manager Agent for handling model loading, unloading, and VRAM management."""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ModelManagerAgent")
        """Initialize the Model Manager Agent.
        
        Args:
            test_ports: Optional tuple of (model_port, status_port) for testing
        """
        # === ABSOLUTE FIRST LINES - INITIALIZE DICTIONARY ATTRIBUTES ===
        self.pubsub_health_sockets = {}
        self.pubsub_health_configs = {}
        self.pubsub_health_last_msg = {}
        self.pubsub_health_expected = {}
        self.pubsub_health_timeout = {}
        self.loaded_models = {}
        self.model_last_used = {}
        self.model_memory_usage = {}
        self.loaded_model_instances = {}
        self.model_last_used_timestamp = {}
        self.models = {}
        self.threads = []  # Track all background threads
        self.pc2_services = {}  # Initialize PC2 services dictionary
        # === END OF DICTIONARY ATTRIBUTE INITIALIZATION ===

        # === VRAM ATTRIBUTES: Initialize at the very top ===
        self.vram_budget_percent = 80  # Use 80% of available VRAM
        self.memory_check_interval = 5  # Check every 5 seconds
        self.idle_timeout = 300  # Unload after 5 minutes of inactivity
        self.device = 'cuda' if hasattr(__import__('torch'), 'cuda') and __import__('torch').cuda.is_available() else 'cpu'
        if self.device == 'cuda':
            import torch
            self.total_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)  # MB
            self.vram_budget_mb = self.total_gpu_memory * (self.vram_budget_percent / 100)
        else:
            self.total_gpu_memory = 0
            self.vram_budget_mb = 0
        self.current_vram_used = 0
        self.current_estimated_vram_used = 0
        # === END VRAM ATTRIBUTES ===

        # === LOG VRAM ATTRIBUTES EARLY ===
        print(f"[MMA INIT] VRAM: device={self.device}, total_gpu_memory={self.total_gpu_memory}, vram_budget_mb={self.vram_budget_mb}, vram_budget_percent={self.vram_budget_percent}")
        # === END LOG ===

        # Initialize logging first
        self._init_logging()
        # vram_logger for memory management loop
        import logging
        self.logger = logging.getLogger('ModelManager')  # Ensure logger is initialized
        self.vram_logger = logging.getLogger('vram')

        # Load configuration
        self._load_configuration()
        # Re-apply config VRAM overrides if present
        if hasattr(self, 'config') and 'vram' in self.config:
            vram_config = self.config['vram']
            self.vram_budget_percent = vram_config.get('vram_budget_percentage', self.vram_budget_percent)
            self.vram_budget_mb = vram_config.get('vram_budget_mb', self.vram_budget_mb)
            self.memory_check_interval = vram_config.get('memory_check_interval', self.memory_check_interval)
            self.idle_timeout = vram_config.get('idle_unload_timeout_seconds', self.idle_timeout)
        self.vram_logger.info(f"[MMA INIT] VRAM FINAL: device={self.device}, total_gpu_memory={self.total_gpu_memory}, vram_budget_mb={self.vram_budget_mb}, vram_budget_percent={self.vram_budget_percent}")

        # Initialize ZMQ with test ports if provided, otherwise will use the port from BaseAgent
        test_ports = None  # Ensure we use the port from BaseAgent (from startup_config.yaml)
        self._init_zmq(test_ports)
        self.logger.info(f"[MMA INIT] Model request port: {getattr(self, 'model_port', None)}")
        self.logger.info(f"[MMA INIT] Status PUB port: {getattr(self, 'status_port', None)}")

        # Initialize model registry
        self._init_model_registry()
        # Start background threads
        self.running = True
        self._start_background_threads()
        self.logger.info("Model Manager Agent initialized successfully")
    
    def _init_vram_management(self):
        """Initialize VRAM management settings."""
        # Default VRAM settings
        self.vram_budget_percent = 80  # Use 80% of available VRAM
        self.memory_check_interval = 5  # Check every 5 seconds
        self.idle_timeout = 300  # Unload after 5 minutes of inactivity
        
        # Setup device for GPU acceleration
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.logger.info(f"Model Manager using device: {self.device}")
        
        # Initialize VRAM tracking
        if self.device == 'cuda':
            self.total_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)  # Convert to MB
            self.vram_budget_mb = self.total_gpu_memory * (self.vram_budget_percent / 100)
            self.logger.info(f"Total GPU memory: {self.total_gpu_memory:.2f} MB")
            self.logger.info(f"VRAM budget: {self.vram_budget_mb:.2f} MB")
        else:
            self.total_gpu_memory = 0
            self.vram_budget_mb = 0
        
        # VRAM tracking
        self.current_vram_used = 0
        self.current_estimated_vram_used = 0
        
        # Load VRAM settings from config if available
        if hasattr(self, 'config') and 'vram' in self.config:
            vram_config = self.config['vram']
            self.vram_budget_percent = vram_config.get('vram_budget_percentage', self.vram_budget_percent)
            self.vram_budget_mb = vram_config.get('vram_budget_mb', self.vram_budget_mb)
            self.memory_check_interval = vram_config.get('memory_check_interval', self.memory_check_interval)
            self.idle_timeout = vram_config.get('idle_unload_timeout_seconds', self.idle_timeout)
        
        self.logger.info(f"Initialized VRAM management: budget={self.vram_budget_mb}MB, "
                        f"check_interval={self.memory_check_interval}s, "
                        f"idle_timeout={self.idle_timeout}s")
    
    def _init_zmq(self, test_ports: Optional[Tuple[int, int]] = None):
        """Initialize ZMQ sockets with enhanced error handling."""
        try:
            self.context = zmq.Context()
            
            # Model request socket (REP)
            self.socket = self.context.socket(zmq.REP)
            self.socket.setsockopt(zmq.LINGER, 0)  # Don't wait on close
            self.socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second receive timeout
            self.socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second send timeout
            
            # PRIORITY 1: Use the port from BaseAgent (from startup_config.yaml)
            # This is the definitive source of port configuration
            if hasattr(self, 'port') and self.port:
                self.model_port = self.port
                self.status_port = self.port + 1  # Convention: health check port is main port + 1
                self.logger.info(f"Using port configuration from startup_config.yaml: model_port={self.model_port}, status_port={self.status_port}")
            # PRIORITY 2: Use test ports if provided (for unit tests)
            elif test_ports:
                self.model_port = test_ports[0]
                self.status_port = test_ports[1]
                self.logger.info(f"Using test port configuration: model_port={self.model_port}, status_port={self.status_port}")
            # PRIORITY 3: Use default ports as last resort
            else:
                self.model_port = MODEL_MANAGER_PORT
                self.status_port = MODEL_MANAGER_PORT + 1
                self.logger.info(f"Using default port configuration: model_port={self.model_port}, status_port={self.status_port}")
            
            # Port conflict resolution strategy
            max_retries = 3
            retries = 0
            
            # Try to bind the model port first
            while retries < max_retries:
                if is_port_in_use(self.model_port):
                    self.logger.warning(f"Port {self.model_port} is in use, waiting for it to become available")
                    if wait_for_port(self.model_port, timeout=5):
                        self.logger.info(f"Port {self.model_port} is now available")
                        break
                    else:
                        # If we can't get the exact port, log an error but don't automatically change it
                        # This ensures we respect the startup_config.yaml configuration
                        retries += 1
                        if retries >= max_retries:
                            self.logger.error(f"Could not bind to configured port {self.model_port} after {max_retries} attempts")
                            self.logger.error("This may cause connectivity issues with other agents")
                            # As a last resort, find an available port
                            self.model_port = self._find_available_port()
                            self.logger.warning(f"Using fallback port {self.model_port} instead")
                else:
                    break
            
            # Now handle the status port
            retries = 0
            while retries < max_retries:
                if is_port_in_use(self.status_port):
                    self.logger.warning(f"Port {self.status_port} is in use, waiting for it to become available")
                    if wait_for_port(self.status_port, timeout=5):
                        self.logger.info(f"Port {self.status_port} is now available")
                        break
                    else:
                        retries += 1
                        if retries >= max_retries:
                            self.logger.error(f"Could not bind to status port {self.status_port} after {max_retries} attempts")
                            self.status_port = self._find_available_port()
                            self.logger.warning(f"Using fallback status port {self.status_port} instead")
                else:
                    break
            
            # Bind sockets with retry logic
            bind_success = False
            for attempt in range(3):
                try:
                    self.socket.bind(f"tcp://*:{self.model_port}")
                    bind_success = True
                    self.logger.info(f"Model request REP socket bound to port {self.model_port}")
                    break
                except zmq.error.ZMQError as e:
                    self.logger.error(f"Failed to bind to port {self.model_port} (attempt {attempt+1}/3): {e}")
                    time.sleep(2)
            
            if not bind_success:
                self.logger.critical(f"Could not bind to model port {self.model_port} after multiple attempts")
                raise RuntimeError(f"Failed to bind to model port {self.model_port}")
            
            # Status publisher socket (PUB)
            self.status_socket = self.context.socket(zmq.PUB)
            self.pub_socket = self.status_socket  # Alias for compatibility with existing code
            
            # Bind status socket with retry logic
            bind_success = False
            for attempt in range(3):
                try:
                    self.status_socket.bind(f"tcp://*:{self.status_port}")
                    bind_success = True
                    self.logger.info(f"Status PUB socket bound to port {self.status_port}")
                    break
                except zmq.error.ZMQError as e:
                    self.logger.error(f"Failed to bind to status port {self.status_port} (attempt {attempt+1}/3): {e}")
                    time.sleep(2)
            
            if not bind_success:
                self.logger.critical(f"Could not bind to status port {self.status_port} after multiple attempts")
                # We can continue without the status socket, but log it as a critical issue
            
        except zmq.error.ZMQError as e:
            self.logger.error(f"ZMQ initialization error: {e}")
            self.logger.error(traceback.format_exc())
            raise

    def _find_available_port(self) -> int:
        """Find an available port for ZMQ socket binding."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    def _start_background_threads(self):
        """Start all background threads."""
        # Memory management thread
        self.memory_thread = threading.Thread(target=self._memory_management_loop)
        self.memory_thread.daemon = True
        self.threads.append(self.memory_thread)
        self.memory_thread.start()
        self.logger.info("Memory management thread started")
        
        # Health check thread
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.threads.append(self.health_thread)
        self.health_thread.start()
        self.logger.info("Health check thread started")
        
        # Model request handling thread
        self.request_thread = threading.Thread(target=self._handle_model_requests_loop)
        self.request_thread.daemon = True
        self.threads.append(self.request_thread)
        self.request_thread.start()
        self.logger.info("Model request handling thread started")
    
    def _check_model_health(self, model_id: str) -> bool:
        """Check if a model is healthy.
        
        Args:
            model_id: ID of the model to check
            
        Returns:
            bool: True if model is healthy, False otherwise
        """
        if model_id not in self.loaded_models:
            return False
            
        model = self.loaded_models[model_id]
        try:
            # Check if model is still loaded
            if not hasattr(model, 'is_loaded') or not model.is_loaded():
                return False
                
            # Check if model has crashed
            if hasattr(model, 'has_crashed') and model.has_crashed():
                return False
                
            # Check if model is responsive
            if hasattr(model, 'is_responsive') and not model.is_responsive():
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking model health for {model_id}: {e}")
            return False
    
    def _memory_management_loop(self):
        """Background thread for managing VRAM usage and unloading idle models."""
        self.vram_logger.info("Starting memory management loop")
        import time
        while self.running:
            try:
                # Get current VRAM usage
                current_vram = self._get_current_vram()
                total_vram = self.total_gpu_memory if self.device == 'cuda' else 0
                vram_usage_percent = (current_vram / total_vram) * 100 if total_vram else 0
                self.vram_logger.debug(f"Current VRAM usage: {current_vram:.1f}MB / {total_vram:.1f}MB ({vram_usage_percent:.1f}%)")

                # Check for VRAM pressure (over budget)
                if current_vram > self.vram_budget_mb:
                    self.vram_logger.warning(f"VRAM pressure detected: {current_vram:.1f}MB > {self.vram_budget_mb}MB budget")
                    # Unload models until under budget (FIFO by last used)
                    sorted_models = sorted(self.model_last_used_timestamp.items(), key=lambda x: x[1])
                    for model_id, _ in sorted_models:
                        self.vram_logger.info(f"Unloading model {model_id} due to VRAM pressure")
                        self._unload_model(model_id)
                        current_vram = self._get_current_vram()
                        if current_vram <= self.vram_budget_mb:
                            break

                # Check for idle models
                current_time = time.time()
                for model_id, last_used in list(self.model_last_used_timestamp.items()):
                    idle_time = current_time - last_used
                    if idle_time > self.idle_timeout:
                        self.vram_logger.info(f"Unloading idle model {model_id}: Idle Time: {idle_time:.1f} seconds")
                        self._unload_model(model_id)
                        self.vram_logger.info(f"Updated VRAM usage after idle unload: {self._get_current_vram():.1f}MB")

                time.sleep(self.memory_check_interval)
            except Exception as e:
                self.vram_logger.error(f"Error in memory management loop: {e}")
                import traceback
                self.vram_logger.error(traceback.format_exc())
                time.sleep(1)
    
    def _health_check_loop(self):
        """Enhanced health check loop with service verification."""
        while self.running:
            try:
                # Check local model health
                self.health_check_models(publish_update=True)
                
                # Verify PC2 services
                service_status = self.verify_pc2_services()
                
                # Update service status in model registry
                for service_id, is_healthy in service_status.items():
                    if service_id in self.models:
                        self.models[service_id]['healthy'] = is_healthy
                        
                # Publish health status
                self._publish_status_update()
                
                # Sleep until next check
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                self.logger.error(traceback.format_exc())
                time.sleep(5)  # Sleep before retrying
    
    def cleanup(self):
        """Clean up resources."""
        self.running = False
        
        # Wait for all threads to finish
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        # Close ZMQ sockets
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'pub_socket'):
            self.pub_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        
        # Unload all models
        for model_id in list(self.loaded_models.keys()):
            self._unload_model(model_id)
        
        # Join threads
        for thread in self.threads:
            thread.join(timeout=1)
    
    def run(self):
        """Run the Model Manager Agent."""
        try:
            # Start background threads
            memory_thread = threading.Thread(target=self._memory_management_loop, name="memory_management")
            health_thread = threading.Thread(target=self._health_check_loop, name="health_check")
            request_thread = threading.Thread(target=self._handle_model_requests_loop, name="request_handling")
            
            memory_thread.daemon = True
            health_thread.daemon = True
            request_thread.daemon = True
            
            memory_thread.start()
            health_thread.start()
            request_thread.start()
            
            self.threads.extend([memory_thread, health_thread, request_thread])
            
            # Main thread now just keeps the process alive and handles signals
            self.logger.info("ModelManagerAgent main thread running - press Ctrl+C to exit")
            while self.running:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    self.logger.info("Received keyboard interrupt, shutting down...")
                    self.running = False
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}")
                    self.logger.error(traceback.format_exc())
                    # Don't exit, keep the process running
                    
        except Exception as e:
            self.logger.error(f"Critical error in main thread: {e}")
            self.logger.error(traceback.format_exc())
        finally:
            self.cleanup()

    def _get_current_vram(self) -> float:
        """Get current VRAM usage in MB
        
        Returns:
            Current VRAM usage in MB
        """
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                logger.warning("No GPU found, returning 0 VRAM usage")
                return 0.0
            
            # Get the first GPU's memory usage
            gpu = gpus[0]
            return gpu.memoryUsed
        except Exception as e:
            logger.error(f"Error getting VRAM usage: {e}")
            return 0.0

    def _get_total_vram(self) -> float:
        """Get total available VRAM in MB
        
        Returns:
            Total VRAM in MB
        """
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                logger.warning("No GPU found, returning default VRAM budget")
                return self.vram_budget_mb
            
            # Get the first GPU's total memory
            gpu = gpus[0]
            return gpu.memoryTotal
        except Exception as e:
            logger.error(f"Error getting total VRAM: {e}")
            return self.vram_budget_mb

    def _unload_least_important_model(self):
        """Unload the least important model to free up VRAM"""
        if not self.loaded_models:
            return
        
        # Sort models by priority (lowest number = highest priority)
        sorted_models = sorted(
            self.loaded_models.items(),
            key=lambda x: self.vram_config['priority_levels'].get(x[1].get('priority', 'low'), 3)
        )
        
        # Unload the least important model
        model_id = sorted_models[0][0]
        self._unload_model(model_id)

    def _load_configuration(self) -> None:
        """Load configuration from system config."""
        try:
            # Load machine-specific configuration
            self.config = system_config.get_config_for_machine()
            
            # Extract VRAM management config
            self.vram_management_config = self.config.get("main_mma_vram_config", {}).get("vram_management", {})
            
            # Check for PC2 services flag in configuration
            enable_pc2_services = self.config.get('enable_pc2_services', False)
            self.logger.info(f"PC2 services integration: {'enabled' if enable_pc2_services else 'disabled'}")
            
            # Validate VRAM config
            self._validate_vram_config()
            
            # Apply VRAM settings
            self.vram_budget_percent = self.vram_management_config.get('vram_budget_percentage', 80)
            self.vram_budget_mb = self.vram_management_config.get('vram_budget_mb', 4096)
            self.idle_timeout = self.vram_management_config.get('idle_unload_timeout_seconds', 300)
            self.memory_check_interval = self.vram_management_config.get('memory_check_interval', 5)
            
            self.logger.info("VRAM Management Configuration:")
            self.logger.info(f"  VRAM Budget Percentage: {self.vram_budget_percent}%")
            self.logger.info(f"  VRAM Budget in MB: {self.vram_budget_mb}MB")
            self.logger.info(f"  Idle Timeout: {self.idle_timeout} seconds")
            self.logger.info(f"  Memory Check Interval: {self.memory_check_interval} seconds")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            self.logger.error(traceback.format_exc())
            # Set default values
            self.vram_management_config = DEFAULT_VRAM_CONFIG
            self.vram_budget_percent = 80
            self.vram_budget_mb = 4096
            self.idle_timeout = 300
            self.memory_check_interval = 5

    def _validate_vram_config(self) -> None:
        """Validate VRAM management configuration."""
        required_keys = ['vram_budget_percentage', 'vram_budget_mb', 'idle_unload_timeout_seconds']
        missing_keys = [key for key in required_keys if key not in self.vram_management_config]
        
        if missing_keys:
            self.logger.warning(f"Missing required VRAM config keys: {missing_keys}")
            # Set defaults
            self.vram_management_config.setdefault('vram_budget_percentage', 80)
            self.vram_management_config.setdefault('vram_budget_mb', 4096)
            self.vram_management_config.setdefault('idle_unload_timeout_seconds', 300)
            self.vram_management_config.setdefault('memory_check_interval', 5)
            
        # Validate values
        if not 0 <= self.vram_management_config['vram_budget_percentage'] <= 100:
            self.logger.warning(f"Invalid VRAM budget percentage: {self.vram_management_config['vram_budget_percentage']}. Using default 80%")
            self.vram_management_config['vram_budget_percentage'] = 80
            
        if self.vram_management_config['vram_budget_mb'] < 0:
            self.logger.warning(f"Invalid VRAM budget MB: {self.vram_management_config['vram_budget_mb']}. Using default 4096MB")
            self.vram_management_config['vram_budget_mb'] = 4096
            
        if self.vram_management_config['idle_unload_timeout_seconds'] < 0:
            self.logger.warning(f"Invalid idle timeout: {self.vram_management_config['idle_unload_timeout_seconds']}. Using default 300s")
            self.vram_management_config['idle_unload_timeout_seconds'] = 300

        # Set model priorities if not present
        if 'model_priorities' not in self.vram_management_config:
            self.vram_management_config['model_priorities'] = {
                'high': 1,
                'medium': 2,
                'low': 3
            }
        
        # Set quantization options if not present
        if 'quantization_options_per_model_type' not in self.vram_management_config:
            self.vram_management_config['quantization_options_per_model_type'] = {
                'whisper': 'int8',
                'llm': 'int8',
                'tts': 'float16'
            }
        
        self.logger.info("VRAM configuration validated and defaults applied where needed")

    def _load_cache(self):
        """Load model response cache from disk"""
        cache_file = self.cache_dir / "cache.json"
        logger.debug(f"Attempting to load cache from {cache_file}")
        try:
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} items from cache")
            else:
                logger.info("No cache file found, starting with empty cache")
                self.cache = {}
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.cache = {}

    def _save_cache(self):
        """Save model response cache to disk"""
        try:
            cache_file = self.cache_dir / "cache.json"
            with open(cache_file, 'w') as f:
                json.dump(self.cache, f)
            logger.info(f"Saved {len(self.cache)} items to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def _memory_management_loop(self):
        """Background thread for managing VRAM usage"""
        self.vram_logger.info("Starting memory management loop")
        
        while self.running:
            try:
                current_vram = self._get_current_vram()
                total_vram = self._get_total_vram()
                vram_usage_percent = (current_vram / total_vram) * 100
                
                self.vram_logger.debug(f"Current VRAM usage: {current_vram:.1f}MB / {total_vram:.1f}MB ({vram_usage_percent:.1f}%)")
                
                # Check for VRAM pressure
                if current_vram > self.vram_budget_mb:
                    self.vram_logger.warning(f"VRAM pressure detected: {current_vram:.1f}MB > {self.vram_budget_mb}MB budget")
                    
                    # Get list of loaded models sorted by priority
                    loaded_models = []
                    for model_id, info in self.loaded_models.items():
                        loaded_models.append({
                            'model_id': model_id,
                            'priority': info['priority'],
                            'vram_mb': info['vram_mb'],
                            'last_used': info['last_used_timestamp'],
                            'quantization': info.get('quantization_level', 'none')
                        })
                    
                    # Sort by priority and last used time
                    loaded_models.sort(key=lambda x: (x['priority'], x['last_used']))
                    
                    # Log current state
                    self.vram_logger.info("Current loaded models (sorted by priority):")
                    for model in loaded_models:
                        self.vram_logger.info(
                            f"  - {model['model_id']}: "
                            f"Priority={model['priority']}, "
                            f"VRAM={model['vram_mb']}MB, "
                            f"Last Used={datetime.fromtimestamp(model['last_used']).isoformat()}, "
                            f"Quantization={model['quantization']}"
                        )
                    
                    # Unload lowest priority models until under budget
                    while current_vram > self.vram_budget_mb and loaded_models:
                        model_to_unload = loaded_models.pop(0)
                        model_id = model_to_unload['model_id']
                        
                        self.vram_logger.info(f"Unloading model {model_id} due to VRAM pressure:")
                        self.vram_logger.info(f"  - Priority: {model_to_unload['priority']}")
                        self.vram_logger.info(f"  - VRAM Usage: {model_to_unload['vram_mb']}MB")
                        self.vram_logger.info(f"  - Quantization: {model_to_unload['quantization']}")
                        self.vram_logger.info(f"  - Last Used: {datetime.fromtimestamp(model_to_unload['last_used']).isoformat()}")
                        
                        # Unload the model
                        self._unload_model(model_id)
                        
                        # Update VRAM usage
                        current_vram = self._get_current_vram()
                        self.vram_logger.info(f"Updated VRAM usage after unload: {current_vram:.1f}MB")
                
                # Check for idle models
                current_time = time.time()
                for model_id, info in list(self.loaded_models.items()):
                    idle_time = current_time - info['last_used_timestamp']
                    if idle_time > self.idle_unload_timeout_seconds:
                        self.vram_logger.info(f"Unloading idle model {model_id}:")
                        self.vram_logger.info(f"  - Priority: {info['priority']}")
                        self.vram_logger.info(f"  - VRAM Usage: {info['vram_mb']}MB")
                        self.vram_logger.info(f"  - Quantization: {info.get('quantization_level', 'none')}")
                        self.vram_logger.info(f"  - Idle Time: {idle_time:.1f} seconds")
                        
                        # Unload the model
                        self._unload_model(model_id)
                        
                        # Update VRAM usage
                        current_vram = self._get_current_vram()
                        self.vram_logger.info(f"Updated VRAM usage after idle unload: {current_vram:.1f}MB")
                
                time.sleep(self.memory_check_interval)
            except Exception as e:
                self.vram_logger.error(f"Error in memory management loop: {e}")
                self.vram_logger.error(traceback.format_exc())
                time.sleep(1)

    def _check_idle_models(self) -> None:
        """Check for and unload idle models"""
        current_time = time.time()
        models_to_unload: List[str] = []
        
        for model_id, last_used in self.model_last_used_timestamp.items():
            model_info = self.models.get(model_id)
            if not model_info:
                continue
                
            idle_timeout = model_info.get('idle_timeout_seconds', 300)
            priority = self._get_model_priority(model_id)
            
            if current_time - last_used > idle_timeout:
                logger.info(f"MMA: Idle Timeout - Unloading model '{model_id}' (Priority: {priority}, Idle > {idle_timeout}s).")
                models_to_unload.append(model_id)
                
        for model_id in models_to_unload:
            self._unload_model_by_type(model_id)

    def _get_model_priority(self, model_id: str) -> int:
        """Get the priority of a model
        
        Args:
            model_id: The ID of the model
            
        Returns:
            The model's priority (higher number = higher priority)
        """
        if hasattr(self, 'active_stt_models') and model_id in self.active_stt_models:
            return self.active_stt_models[model_id].get('priority', 
                   self.vram_management_config.get('default_model_priority', 5))
        return self.vram_management_config.get('default_model_priority', 5)

    def _unload_model_by_type(self, model_id: str) -> None:
        """Unload a model based on its serving method
        
        Args:
            model_id: The ID of the model to unload
        """
        model_info = self.models.get(model_id)
        if not model_info:
            logger.warning(f"Attempted to unload unknown model {model_id}")
            return
            
        serving_method = model_info.get('serving_method')
        unload_methods = {
            'gguf_direct': self._unload_gguf_model,
            'ollama': self._unload_ollama_model,
            'custom_api': self._unload_custom_api_model,
            'zmq_service': self._unload_zmq_service_model
        }
        
        unload_method = unload_methods.get(serving_method)
        if unload_method:
            try:
                unload_method(model_id)
            except Exception as e:
                logger.error(f"Error unloading model {model_id} ({serving_method}): {e}")
                logger.error(traceback.format_exc())
        else:
            logger.warning(f"Unknown serving method '{serving_method}' for model {model_id}")

    def _update_vram_usage(self):
        """Update the current_estimated_vram_used attribute with the latest VRAM usage."""
        self.current_estimated_vram_used = self._get_current_vram()

    def _publish_status_update(self):
        """Publish current model status and VRAM usage."""
        try:
            self._update_vram_usage()
            status_message = json.dumps({
                'event': 'model_status_update',
                'models': self.models,
                'loaded_models': list(self.loaded_models.keys()),
                'vram_usage': {
                    'total_budget_mb': self.vram_budget_mb,
                    'used_mb': self.current_estimated_vram_used,
                    'remaining_mb': self.vram_budget_mb - self.current_estimated_vram_used
                },
                'timestamp': time.time()
            })
            
            # Publish status if socket is available
            if hasattr(self, 'pub_socket') and self.pub_socket:
                try:
                    self.pub_socket.send_string(status_message, flags=zmq.NOBLOCK)
                except zmq.error.Again:
                    # Non-blocking send would block, just skip this update
                    self.logger.debug("Status socket would block, skipping this update")
                except Exception as socket_err:
                    self.logger.warning(f"Error sending to status socket: {socket_err}")
            elif hasattr(self, 'status_socket') and self.status_socket:
                try:
                    self.status_socket.send_string(status_message, flags=zmq.NOBLOCK)
                except zmq.error.Again:
                    # Non-blocking send would block, just skip this update
                    self.logger.debug("Status socket would block, skipping this update")
                except Exception as socket_err:
                    self.logger.warning(f"Error sending to status socket: {socket_err}")
            
            status_summary = {model: info.get('status', 'unknown') for model, info in self.models.items()}
            self.logger.info(f"Model status: {status_summary}")
            self.logger.info(f"VRAM usage: {self.current_estimated_vram_used:.2f}MB / {self.vram_budget_mb:.2f}MB")
        except Exception as e:
            self.logger.error(f"Error publishing status update: {e}")
            self.logger.error(traceback.format_exc())

    def _can_accommodate_model(self, model_vram_mb: float) -> bool:
        """Check if a model can fit within the remaining VRAM budget
        
        Args:
            model_vram_mb: The VRAM requirement of the model in MB
            
        Returns:
            True if the model can be accommodated, False otherwise
        """
        if self.device != 'cuda':
            return True  # No VRAM constraints on CPU
            
        remaining_vram = self.vram_budget_mb - self.current_estimated_vram_used
        can_fit = remaining_vram >= model_vram_mb
        
        if not can_fit:
            logger.warning(
                f"Cannot accommodate model requiring {model_vram_mb}MB VRAM. "
                f"Current usage: {self.current_estimated_vram_used}MB, "
                f"Budget: {self.vram_budget_mb}MB, "
                f"Remaining: {remaining_vram}MB"
            )
        
        return can_fit

    def _mark_model_as_loaded(self, model_id: str, model_vram_mb: float) -> None:
        """Mark a model as loaded and update VRAM tracking
        
        Args:
            model_id: The ID of the model
            model_vram_mb: The VRAM usage of the model in MB
        """
        if model_id in self.loaded_model_instances:
            # Already marked as loaded, just update timestamp
            self.model_last_used_timestamp[model_id] = time.time()
            return
            
        self.loaded_model_instances[model_id] = model_vram_mb
        self.current_estimated_vram_used += model_vram_mb
        self.model_last_used_timestamp[model_id] = time.time()
        
        logger.info(
            f"Model {model_id} marked as loaded, using {model_vram_mb}MB VRAM. "
            f"Total VRAM in use: {self.current_estimated_vram_used}MB / {self.vram_budget_mb}MB"
        )

    def _mark_model_as_unloaded(self, model_id: str) -> None:
        """Mark a model as unloaded and update VRAM tracking
        
        Args:
            model_id: The ID of the model to unload
        """
        if model_id not in self.loaded_model_instances:
            logger.warning(f"Attempted to unload model {model_id} that was not marked as loaded")
            return
            
        model_vram_mb = self.loaded_model_instances[model_id]
        self.current_estimated_vram_used -= model_vram_mb
        del self.loaded_model_instances[model_id]
        
        logger.info(
            f"Model {model_id} marked as unloaded, freed {model_vram_mb}MB VRAM. "
            f"Total VRAM in use: {self.current_estimated_vram_used}MB / {self.vram_budget_mb}MB"
        )

    def _load_models_from_config(self):
        """Load model configurations from the central config"""
        try:
            # Determine active PC settings key based on environment variable
            from utils.config_loader import Config
            cfg = Config()
            active_pc_settings_key = cfg.active_pc_settings_key
            logger.info(f"Active PC settings key: {active_pc_settings_key}")
            
            # Get model configurations directly from config object
            model_configs = {}
            try:
                # Try to access model_configs from the active PC settings
                model_configs = config.get(f'{active_pc_settings_key}.model_configs', {})
                logger.info(f"Found model configurations in {active_pc_settings_key}.model_configs")
            except Exception as e:
                logger.warning(f"Could not load model configs from {active_pc_settings_key}: {e}")
                # Fallback to direct model_configs
                model_configs = config.get('model_configs', {})
            
            # Load GGUF models from system_config.py
            gguf_models_count = 0
            if "main_pc_settings" in self.machine_config and "model_configs" in self.machine_config["main_pc_settings"]:
                for model_id, model_cfg in self.machine_config["main_pc_settings"]["model_configs"].items():
                    if model_cfg.get('enabled', True) and model_cfg.get('serving_method') == 'gguf_direct':
                        self.models[model_id] = {
                            'display_name': model_cfg.get('display_name', model_id),
                            'serving_method': 'gguf_direct',
                            'status': 'available_not_loaded',
                            'last_check': 0,
                            'estimated_vram_mb': model_cfg.get('estimated_vram_mb', 0),
                            'context_length': model_cfg.get('context_length', 2048),
                            'idle_timeout_seconds': model_cfg.get('idle_timeout_seconds', self.idle_timeout)
                        }
                        gguf_models_count += 1
            
            logger.info(f"Loaded {gguf_models_count} GGUF model configurations from system_config.py")
            
            # Then try to load additional GGUF models configuration if it exists
            try:
                gguf_models_path = Path("config/gguf_models.json")
                if gguf_models_path.exists():
                    with open(gguf_models_path, 'r') as f:
                        gguf_models = json.load(f)
                    logger.info(f"Loaded {len(gguf_models)} additional GGUF model configurations from {gguf_models_path}")
                    
                    # Add GGUF models to main PC settings if they don't exist
                    if "main_pc_settings" in self.machine_config and "model_configs" in self.machine_config["main_pc_settings"]:
                        for model_id, model_config in gguf_models.items():
                            if model_id not in self.machine_config["main_pc_settings"]["model_configs"]:
                                self.machine_config["main_pc_settings"]["model_configs"][model_id] = model_config
                                logger.info(f"Added GGUF model {model_id} to model configurations")
            except Exception as e:
                logger.warning(f"Error loading GGUF models configuration: {e}")
            
            # Log success
            logger.info("Loaded configurations from system_config.py")
            
            # model_configs already determined earlier via config.get; ensure it's a dict
            if not isinstance(model_configs, dict):
                logger.warning(f"model_configs is not a dict (type={type(model_configs)}). Resetting to empty dict.")
                model_configs = {}
            logger.debug(f"Final model_configs keys: {list(model_configs.keys()) if isinstance(model_configs, dict) else 'N/A'}")
            
            self.models = {} # Clear existing models before loading from new config
            for model_id, model_cfg_item in model_configs.items():
                if not model_cfg_item.get('enabled', True):
                    logger.info(f"Model {model_id} is disabled in config. Skipping.")
                    continue
                
                model_data = {
                    'display_name': model_cfg_item.get('display_name', model_id),
                    'serving_method': model_cfg_item.get('serving_method'),
                    'capabilities': model_cfg_item.get('capabilities', []),
                    'status': 'unknown',  # Initial status
                    'last_check': 0, # Timestamp of the last health check
                    'config': model_cfg_item # Store the full original config for the model
                }
                
                serving_method = model_data['serving_method']
                
                if serving_method == 'zmq_service_remote':
                    model_data['zmq_address'] = model_cfg_item.get('zmq_address')
                    model_data['zmq_actions'] = model_cfg_item.get('zmq_actions', {})
                    model_data['estimated_vram_mb'] = 0  # Not managed by this MMA
                    model_data['idle_timeout_seconds'] = 0 # Not managed by this MMA
                    model_data['context_length'] = model_cfg_item.get('context_length', 2048)
                elif serving_method == 'ollama':
                    model_data['ollama_tag'] = model_cfg_item.get('ollama_tag', model_id)
                    model_data['estimated_vram_mb'] = model_cfg_item.get('estimated_vram_mb', 0)
                    model_data['context_length'] = model_cfg_item.get('context_length', 2048)
                    model_data['idle_timeout_seconds'] = model_cfg_item.get('idle_timeout_seconds', self.idle_timeout)
                elif serving_method == 'custom_api':
                    model_data['api_base_url'] = model_cfg_item.get('api_base_url')
                    model_data['api_model_id'] = model_cfg_item.get('api_model_id', model_id)
                    model_data['estimated_vram_mb'] = model_cfg_item.get('estimated_vram_mb', 0)
                    model_data['context_length'] = model_cfg_item.get('context_length', 2048)
                    model_data['idle_timeout_seconds'] = model_cfg_item.get('idle_timeout_seconds', self.idle_timeout)
                elif serving_method == 'zmq_service': # Local ZMQ service
                    model_data['zmq_address'] = model_cfg_item.get('zmq_address')
                    model_data['zmq_actions'] = model_cfg_item.get('zmq_actions', {})
                    model_data['estimated_vram_mb'] = model_cfg_item.get('estimated_vram_mb', 0)
                    model_data['context_length'] = model_cfg_item.get('context_length', 2048)
                    model_data['idle_timeout_seconds'] = model_cfg_item.get('idle_timeout_seconds', self.idle_timeout)
                elif serving_method == 'gguf_direct':
                    model_data['estimated_vram_mb'] = model_cfg_item.get('estimated_vram_mb', 0)
                    model_data['context_length'] = model_cfg_item.get('context_length', 2048)
                    model_data['idle_timeout_seconds'] = model_cfg_item.get('idle_timeout_seconds', self.idle_timeout)
                elif serving_method == 'zmq_pub_health_local':
                    # PATCH: Recognize zmq_pub_health_local and set up for PUB/SUB health monitoring
                    zmq_addr = model_cfg_item.get('zmq_address')
                    model_data['zmq_address'] = zmq_addr
                    model_data['expected_health_response_contains'] = model_cfg_item.get('expected_health_response_contains', {})
                    model_data['health_message_timeout_seconds'] = model_cfg_item.get('health_message_timeout_seconds', 15)
                    model_data['estimated_vram_mb'] = model_cfg_item.get('estimated_vram_mb', 0)
                    model_data['context_length'] = model_cfg_item.get('context_length', 2048)
                    model_data['idle_timeout_seconds'] = model_cfg_item.get('idle_timeout_seconds', self.idle_timeout)
                    model_data['script_path'] = model_cfg_item.get('script_path')
                    logger.info(f"[MainMMA Config LOAD] Parsed ZMQ_PUBSUB agent '{model_id}': ZMQ Addr='{zmq_addr}', Expected='{model_data['expected_health_response_contains']}', Timeout='{model_data['health_message_timeout_seconds']}'")
                else:
                    # PATCH: Comment out warning for zmq_pub_health_local (handled above)
                    if serving_method != 'zmq_pub_health_local':
                        logger.warning(f"Model {model_id} has unknown or missing serving_method: '{serving_method}'. Storing basic info.");
                    model_data['estimated_vram_mb'] = model_cfg_item.get('estimated_vram_mb', 0)
                    model_data['context_length'] = model_cfg_item.get('context_length', 2048)
                    model_data['idle_timeout_seconds'] = model_cfg_item.get('idle_timeout_seconds', self.idle_timeout)
            
                if not model_data['serving_method']:
                    logger.error(f"Model {model_id} has no serving_method defined in its configuration. Cannot manage this model.")
                    continue
            
                self.models[model_id] = model_data
        
            logger.info(f"Successfully loaded {len(self.models)} model configurations: {list(self.models.keys())}")

            # Perform initial health check for all loaded models
            if hasattr(self, 'health_check_models') and callable(self.health_check_models):
                self.health_check_models(publish_update=True)
            else:
                logger.warning("health_check_models method not found or not callable at the end of _load_models_from_config. Skipping initial health check.")
        except Exception as e:
            logger.error(f"Unhandled error in _load_models_from_config: {e}")
            logger.debug(traceback.format_exc())
            # Fallback to legacy config loading if unexpected error occurs
            self._load_models_from_legacy_config()

        # Load model configs from system_config.py
        model_configs = system_config.get_config_for_machine().get('model_configs', {})
        for model_id, model_cfg_item in model_configs.items():
            if model_cfg_item.get('serving_method') == 'zmq_pub_health_local':
                self.pubsub_health_configs[model_id] = {
                    'zmq_address': model_cfg_item.get('zmq_address'),
                    'expected': model_cfg_item.get('expected_health_response_contains', {}),
                    'timeout': model_cfg_item.get('health_message_timeout_seconds', 15)
                }
                logger.info(f"[MainMMA Config] Identified ZMQ_PUBSUB agent: {model_id} at {model_cfg_item.get('zmq_address')}. Expected: {model_cfg_item.get('expected_health_response_contains')}")

    def _load_models_from_legacy_config(self):
        """Legacy method to load model configurations from old config structure"""
        # Load Ollama models
        ollama_config = config.get('models.ollama', {})
        ollama_url = ollama_config.get('url', 'http://localhost:11434')
        ollama_models = ollama_config.get('models', {})
        
        for model_name, model_config in ollama_models.items():
            if model_config.get('enabled', True):
                self.models[model_name] = {
                    'display_name': model_name,
                    'serving_method': 'ollama',
                    'ollama_tag': model_name,
                    'url': ollama_url,
                    'status': 'unknown',
                    'last_check': 0,
                    'capabilities': model_config.get('capabilities', []),
                    'context_length': model_config.get('context_length', 2048),
                    'estimated_vram_mb': 0,  # Unknown in legacy config
                    'idle_timeout_seconds': self.idle_timeout
                }
        
        # Load Deepseek model if enabled
        deepseek_config = config.get('models.deepseek', {})
        if deepseek_config.get('enabled', False):
            self.models['deepseek'] = {
                'display_name': 'DeepSeek',
                'serving_method': 'custom_api',
                'api_base_url': deepseek_config.get('url', 'http://localhost:8000'),
                'api_model_id': 'deepseek',
                'status': 'unknown',
                'last_check': 0,
                'capabilities': deepseek_config.get('capabilities', []),
                'context_length': deepseek_config.get('context_length', 16000),
                'estimated_vram_mb': 0,  # Unknown in legacy config
                'idle_timeout_seconds': self.idle_timeout
            }
        
        logger.info(f"Loaded {len(self.models)} models from legacy configuration")

    def check_idle_models(self):
        """Check for idle models and unload them if they've been idle too long"""
        logger.info("Memory management idle unloading is now active - checking for idle models")
        
        now = time.time()
        models_to_unload = []
        
        # Find models that have been idle too long
        for model_id in list(self.loaded_model_instances.keys()):
            if model_id not in self.models:
                # Model in loaded_model_instances but not in models config - something's wrong
                logger.warning(f"Model {model_id} is tracked as loaded but not found in models config")
                self._mark_model_as_unloaded(model_id)
                continue
                
            model_info = self.models[model_id]
            idle_timeout = model_info.get('idle_timeout_seconds', self.idle_timeout)
            last_used = self.model_last_used_timestamp.get(model_id, 0)
            
            if now - last_used > idle_timeout:
                models_to_unload.append(model_id)
        
        # Unload idle models
        for model_id in models_to_unload:
            model_info = self.models[model_id]
            serving_method = model_info.get('serving_method', '')
            
            logger.info(f"Unloading idle model {model_id} (idle for {now - self.model_last_used_timestamp.get(model_id, 0):.1f}s)")
            
            if serving_method == 'ollama':
                self._unload_ollama_model(model_id)
            elif serving_method == 'custom_api':
                self._unload_custom_api_model(model_id)
            elif serving_method == 'zmq_service':
                self._unload_zmq_service_model(model_id)
            elif serving_method == 'zmq_service_remote':
                # Do not unload remote services
                continue
            elif serving_method == 'gguf_direct':
                # Unload GGUF model
                self._unload_gguf_model(model_id)
            elif serving_method == 'zmq_pub_health_local':
                # No unload action needed, but recognized
                continue
            else:
                logger.warning(f"Unknown serving method '{serving_method}' for model {model_id}")
                # Mark as unloaded anyway to maintain accurate VRAM tracking
                self._mark_model_as_unloaded(model_id)

    def _unload_ollama_model(self, model_id):
        """Unload an Ollama model by setting minimal keep-alive"""
        try:
            model_info = self.models[model_id]
            ollama_tag = model_info.get('ollama_tag', model_id)
            
            # Send a request with keep_alive=0s to trigger unloading
            url = f"{self.ollama_url}/api/generate"
            payload = {
                "model": ollama_tag,
                "prompt": " ",  # Minimal prompt
                "keep_alive": "0s"  # Request immediate unloading
            }
            
            r = requests.post(url, json=payload, timeout=5)
            
            if r.status_code == 200:
                logger.info(f"Successfully requested unload of Ollama model {model_id}")
                model_info['status'] = 'available_not_loaded'
                self._mark_model_as_unloaded(model_id)
            else:
                logger.warning(f"Failed to unload Ollama model {model_id}: {r.status_code} {r.text}")
        except Exception as e:
            logger.error(f"Error unloading Ollama model {model_id}: {e}")

    def _unload_custom_api_model(self, model_id):
        """Try to unload a custom API model if the API supports it"""
        model_info = self.models[model_id]
        logger.info(f"Custom API model {model_id} idle timeout reached, but cannot programmatically unload")
        logger.info(f"Marking model as unloaded for tracking purposes only")
        model_info['status'] = 'unknown'  # We don't know if it's still loaded on the server
        self._mark_model_as_unloaded(model_id)

    def _unload_zmq_service_model(self, model_id):
        """Unload a ZMQ service model"""
        logger.info(f"--- MMA: _unload_zmq_service_model for {model_id} --- START ---")
        model_info = self.models.get(model_id)
        if not model_info:
            logger.error(f"Model {model_id} not found in config for unloading.")
            self._mark_model_as_unloaded(model_id) # Ensure it's marked unloaded if somehow tracked
            return False

        zmq_address = model_info.get('zmq_address')
        if not zmq_address:
            logger.error(f"ZMQ address not configured for model {model_id}.")
            self._mark_model_as_unloaded(model_id)
            return False

        try:
            # Use a temporary socket for this request to avoid blocking the main REP socket
            # And to handle remote services that might be slow or unresponsive
            temp_context = zmq.Context()
            unload_socket = temp_context.socket(zmq.REQ)
            unload_socket.setsockopt(zmq.LINGER, 0)  # Don't wait for unsent messages on close
            unload_socket.setsockopt(zmq.RCVTIMEO, 5000) # 5 second timeout for receive
            unload_socket.setsockopt(zmq.SNDTIMEO, 5000) # 5 second timeout for send
            unload_socket.connect(zmq_address)

            logger.info(f"Sending unload request to {model_id} at {zmq_address}")
            zmq_actions = model_info.get('zmq_actions', {})
            unload_action = zmq_actions.get('unload', 'request_unload') # Default if not specified
            logger.info(f"Sending '{unload_action}' request to {model_id} at {zmq_address}")
            unload_socket.send_json({"action": unload_action})

            response = unload_socket.recv_json()
            logger.info(f"Received unload response from {model_id}: {response}")

            if response.get('status') == 'success' or response.get('model_status') == 'unloaded':
                model_info['status'] = 'available_not_loaded' # Update status
                self._mark_model_as_unloaded(model_id)
                logger.info(f"Model {model_id} successfully unloaded by service.")
                return True
            else:
                logger.warning(f"Model {model_id} service reported unload failure or unexpected status: {response.get('model_status')}")
                # Even if service fails to unload, mark as unloaded in MMA if we intended to.
                # Or, we could try to re-verify status. For now, assume our intent to unload means it's unusable by us.
                model_info['status'] = 'error' # Or keep previous status if preferred
                self._mark_model_as_unloaded(model_id) # Mark unloaded in MMA to free VRAM tracking
                return False
        except zmq.error.Again as e_again:
            logger.error(f"ZMQ timeout unloading model {model_id} at {zmq_address}: {e_again}")
            model_info['status'] = 'offline' # Service unresponsive
            self._mark_model_as_unloaded(model_id)
            return False
        except Exception as e:
            logger.error(f"Error unloading ZMQ model {model_id} at {zmq_address}: {e}")
            logger.error(traceback.format_exc())
            model_info['status'] = 'error'
            self._mark_model_as_unloaded(model_id)
            return False
        finally:
            if 'unload_socket' in locals():
                unload_socket.close()
            if 'temp_context' in locals():
                temp_context.term()
            logger.info(f"--- MMA: _unload_zmq_service_model for {model_id} --- END ---")

    def _unload_gguf_model(self, model_id):
        """Unload a GGUF model using the GGUF connector."""
        logger.critical(f"--- [MainMMA _unload_gguf_model CRITICAL ENTRY] Called for model_id: {model_id} ---")
        try:
            # Unload the model via GGUF connector
            success = self.gguf_connector.unload_model(model_id)
            if success:
                self._mark_model_as_unloaded(model_id)
                logger.info(f"Successfully unloaded GGUF model {model_id}")
                return True
            else:
                logger.error(f"Failed to unload GGUF model {model_id}")
                return False
        except Exception as e:
            logger.error(f"Error unloading GGUF model {model_id}: {e}")
            return False

    def load_model(self, model_id):
        """Explicitly load a model if supported by its serving method."""
        logger.info(f"--- MMA: load_model request for {model_id} --- START ---")
        if model_id in self.loaded_model_instances:
            logger.info(f"Model {model_id} is already marked as loaded.")
            self.model_last_used_timestamp[model_id] = time.time() # Update LRU
            return True

        model_info = self.models.get(model_id)
        if not model_info:
            logger.error(f"Model {model_id} not found in configuration.")
            return False

        serving_method = model_info.get('serving_method')
        logger.info(f"Serving method for {model_id}: {serving_method}")
        estimated_vram_mb = model_info.get('estimated_vram_mb', 0)

        if serving_method == 'zmq_service':
            zmq_address = model_info.get('zmq_address')
            if not zmq_address:
                logger.error(f"ZMQ address not configured for model {model_id}.")
                model_info['status'] = 'misconfigured'
                return False
        
            logger.info(f"--- MMA: Attempting to load ZMQ service model {model_id} at {zmq_address} ---")

            if not self._can_accommodate_model(estimated_vram_mb):
                logger.info(f"Not enough VRAM for {model_id} ({estimated_vram_mb}MB). Attempting to make room.")
                if not self._make_room_for_model(estimated_vram_mb):
                    logger.error(f"Could not make enough room for {model_id}. Load failed.")
                    return False
                # Re-check after making room
                if not self._can_accommodate_model(estimated_vram_mb):
                    logger.error(f"Still not enough VRAM for {model_id} after attempting to make room. Load failed.")
                    return False
            
            temp_context = None
            load_socket = None
            try:
                temp_context = zmq.Context()
                load_socket = temp_context.socket(zmq.REQ)
                load_socket.setsockopt(zmq.LINGER, 0)
                if model_info.get('zmq_actions', {}).get('load', 'ensure_loaded') == 'ensure_loaded':
                    load_socket.setsockopt(zmq.RCVTIMEO, 15000)  # Set timeout to 15 seconds for ensure_loaded
                else:
                    load_socket.setsockopt(zmq.RCVTIMEO, 120000) # Increased timeout to 120 seconds for TinyLlama loading
                load_socket.setsockopt(zmq.SNDTIMEO, 5000)
                load_socket.connect(zmq_address)

                zmq_actions = model_info.get('zmq_actions', {})
                load_action = zmq_actions.get('load', 'ensure_loaded') # Default if not specified
                logger.info(f"Sending '{load_action}' request to {model_id} at {zmq_address}")
                load_socket.send_json({"action": load_action})
                response = load_socket.recv_json()
                logger.info(f"Received '{load_action}' response from {model_id}: {response}")

                if response.get('status') == 'success':
                    service_model_status = response.get('model_status')
                    if service_model_status == 'loaded':
                        self._mark_model_as_loaded(model_id, estimated_vram_mb)
                        model_info['status'] = 'online'  # Consistent with successful load
                        logger.info(f"Model {model_id} successfully loaded by service and marked in MMA.")
                        return True
                    elif service_model_status == 'loading':
                        self.models[model_id]['status'] = 'loading' # Reflect that the service is loading it
                        logger.info(f"Model {model_id} loading initiated by service. MMA will track via health checks.")
                        return True # Indicate to handle_request that the load command was accepted
                    else:
                        logger.warning(f"Model {model_id} service reported unexpected model_status: '{service_model_status}'. Response: {response}")
                        model_info['status'] = 'error'
                        return False
                else:
                    logger.warning(f"Model {model_id} service reported load failure (status not 'success'). Response: {response}")
                    model_info['status'] = 'error'
                    return False
            except zmq.error.Again as e_again:
                logger.error(f"ZMQ timeout loading model {model_id} at {zmq_address}: {e_again}")
                model_info['status'] = 'offline'
                return False
            except Exception as e:
                logger.error(f"Error loading ZMQ model {model_id} at {zmq_address}: {e}")
                logger.error(traceback.format_exc())
                model_info['status'] = 'error'
                return False
            finally:
                # Clean up ZMQ resources to prevent leaks
                logger.debug(f"Cleaning up ZMQ resources for {model_id} load request")
                if load_socket:
                    try:
                        load_socket.close()
                    except Exception as e:
                        logger.error(f"Error closing ZMQ socket for {model_id}: {e}")
                if temp_context:
                    try:
                        temp_context.term()
                    except Exception as e:
                        logger.error(f"Error terminating ZMQ context for {model_id}: {e}")
                logger.debug(f"ZMQ resources cleanup completed for {model_id} load request")
        elif serving_method == 'ollama':
            # Ollama models are typically loaded on first use by Ollama itself.
            # We can mark it as loaded if its status is already 'online'.
            if model_info.get('status') == 'online':
                self._mark_model_as_loaded(model_id, estimated_vram_mb)
                logger.info(f"Ollama model {model_id} is already online. Marked as loaded in MMA.")
                return True
            else:
                logger.info(f"Ollama model {model_id} cannot be explicitly loaded via MMA 'load_model' command. It loads on demand by Ollama. Current status: {model_info.get('status')}")
                return False # Or True if we consider an attempt to load an 'available' ollama model a success conceptually
        elif serving_method == 'gguf_direct':
            # Try connector first, then direct loading if connector fails
            logger.info(f"Loading GGUF model {model_id} - attempting connector method first")
            
            # First attempt: Use GGUF connector if available
            if self.gguf_available:
                try:
                    logger.info(f"Loading GGUF model {model_id} via connector")
                    response = self.gguf_connector.load_gguf_model(model_id)
                    
                    if response and (response.get('status') == "success" or response.get('status') == "ok"):
                        # Update model status
                        self.models[model_id]['status'] = "online"
                        self.models[model_id]['error'] = None
                        self._mark_model_as_loaded(model_id, estimated_vram_mb)
                        self.model_last_used_timestamp[model_id] = time.time()
                        
                        # Publish model status update
                        self._publish_model_status(model_id, "online")
                        logger.info(f"GGUF model {model_id} successfully loaded via connector")
                        return True
                    else:
                        error_msg = response.get('error', 'Unknown error') if response else 'No response from connector'
                        logger.warning(f"Connector failed to load GGUF model {model_id}: {error_msg}")
                        # Continue to direct loading attempt
                except Exception as e:
                    logger.warning(f"Exception using connector to load GGUF model {model_id}: {e}")
                    # Continue to direct loading attempt
            else:
                logger.warning("GGUF connector not available, attempting direct loading")
            
            # Second attempt: Try direct loading through the GGUF Model Manager
            try:
                from agents.gguf_model_manager import get_instance as get_gguf_manager
                gguf_manager = get_gguf_manager()
                
                logger.info(f"Loading GGUF model {model_id} directly via GGUF Model Manager")
                if gguf_manager.load_model(model_id):
                    # Update model status
                    self.models[model_id]['status'] = "online"
                    self.models[model_id]['error'] = None
                    self._mark_model_as_loaded(model_id, estimated_vram_mb)
                    self.model_last_used_timestamp[model_id] = time.time()
                    
                    # Publish model status update
                    self._publish_model_status(model_id, "online")
                    logger.info(f"GGUF model {model_id} successfully loaded directly")
                    return True
                else:
                    logger.error(f"Failed to load GGUF model {model_id} directly")
                    self.models[model_id]['status'] = "error"
                    self.models[model_id]['error'] = "Failed to load model directly"
                    return False
            except Exception as e:
                logger.error(f"Error during direct GGUF model loading for {model_id}: {e}")
                self.models[model_id]['status'] = "error"
                self.models[model_id]['error'] = str(e)
                return False
        else:
            logger.warning(f"Explicit loading not supported for serving method '{serving_method}' for model {model_id}.")
            return False
        # finally:
        #     logger.info(f"--- MMA: load_model request for {model_id} --- END ---")

    def unload_model(self, model_id):
        """Explicitly unload a model if supported by its serving method."""
        logger.info(f"--- MMA: unload_model request for {model_id} --- START ---")
        if model_id not in self.loaded_model_instances:
            logger.info(f"Model {model_id} is not currently marked as loaded.")
            # Ensure its status reflects it's not loaded if it's in self.models
            condition_is_met = (model_id in self.models and 
                            self.models[model_id].get('status') == 'online')
            if condition_is_met:
                self.models[model_id]['status'] = 'available_not_loaded'
            return True # Considered success as it's already in the desired state

        model_info = self.models.get(model_id)
        if not model_info:
            logger.error(f"Model {model_id} not found in configuration for unload.")
            # If it was in loaded_model_instances but not self.models, clean up
            if model_id in self.loaded_model_instances:
                 self._mark_model_as_unloaded(model_id)
            return False

        serving_method = model_info.get('serving_method')
        unloaded = False
        if serving_method == 'zmq_service':
            unloaded = self._unload_zmq_service_model(model_id)
        elif serving_method == 'ollama':
            unloaded = self._unload_ollama_model(model_id) # This already calls _mark_model_as_unloaded
        elif serving_method == 'gguf_direct':
            unloaded = self._unload_gguf_model(model_id)
        elif serving_method == 'zmq_pub_health_local':
            # No unload action needed, but recognized
            return True  # Return True since no action needed is considered success
        else:
            logger.warning(f"Explicit unloading not supported for serving method '{serving_method}' for model {model_id}.")
            # For unsupported types, if we still want to mark it unloaded in MMA:
            # self._mark_model_as_unloaded(model_id)
            # model_info['status'] = 'available_not_loaded'
            # unloaded = True 
            unloaded = False # Or treat as failure if no action can be taken
        
        logger.info(f"--- MMA: unload_model request for {model_id} --- END. Success: {unloaded} ---")
        return unloaded
    
    def _save_cache(self):
        """Save the model response cache to disk"""
        try:
            if not hasattr(self, 'cache_dir') or not self.cache_dir.exists():
                logger.error("Cache directory does not exist, cannot save cache")
                return False
                
            cache_file = self.cache_dir / "cache.json"
            try:
                with open(cache_file, 'w') as f:
                    json.dump(self.cache, f)
                logger.info(f"Saved {len(self.cache)} items to cache")
                return True
            except Exception as e:
                logger.error(f"Error saving cache: {e}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error in _save_cache: {e}")
            return False
    
    def _clean_cache(self):
        """Remove expired entries from the cache"""
        now = datetime.now()
        expired_keys = []
        
        # Find expired entries
        for key, (timestamp, _) in self.cache.items():
            if now - timestamp > timedelta(seconds=self.cache_ttl):
                expired_keys.append(key)
        
        # Remove expired entries
        for key in expired_keys:
            del self.cache[key]
        
        # If still too many entries, remove oldest ones
        if len(self.cache) > self.max_cache_entries:
            # Sort by timestamp (oldest first)
            sorted_cache = sorted(self.cache.items(), key=lambda x: x[1][0])
            # Keep only the newest max_cache_entries
            to_keep = sorted_cache[-self.max_cache_entries:]
            self.cache = {k: v for k, v in to_keep}
        
        logger.info(f"Cleaned cache: removed {len(expired_keys)} expired entries, {len(self.cache)} remaining")
        return len(expired_keys)
    
    def health_check(self):
        """Check the health/status of all configured models"""
        # Group models by serving method for efficient checking
        ollama_models = {}
        custom_api_models = {}
        zmq_service_models = {}
        zmq_service_remote_models = {}
        gguf_models = {}
        
        # First categorize all models by serving method
        for model_id, model_info in self.models.items():
            serving_method = model_info.get('serving_method')
            if not model_info.get('enabled', True):
                continue
                
            if serving_method == 'ollama':
                ollama_models[model_id] = model_info
            elif serving_method == 'custom_api':
                custom_api_models[model_id] = model_info
            elif serving_method == 'zmq_service':
                zmq_service_models[model_id] = model_info
            elif serving_method == 'zmq_service_remote':
                zmq_service_remote_models[model_id] = model_info
            elif serving_method == 'gguf_direct':
                gguf_models[model_id] = model_info
        
        logger.debug(f"ZMQ remote services to check: {list(zmq_service_remote_models.keys())}")
        
        # Check Ollama models
        if ollama_models:
            self._check_ollama_models(ollama_models)
        
        # Check Custom API models
        for model_id, model_info in custom_api_models.items():
            self._check_custom_api_model(model_id, model_info)
        
        # Check ZMQ Service models
        for model_id, model_info in zmq_service_models.items():
            self._check_zmq_service_model(model_id, model_info)
        
        # Check ZMQ Service Remote models
        for model_id, model_info in zmq_service_remote_models.items():
            self._check_zmq_remote_service_model(model_id, model_info)
        
        # Check GGUF models
        for model_id, model_info in gguf_models.items():
            if hasattr(self, '_check_gguf_model'):
                self._check_gguf_model(model_id, model_info)
            else:
                logger.warning(f"No _check_gguf_model method available to check {model_id}")
        
        # Publish status update
        status_message = json.dumps({
            'event': 'model_status_update',
            'models': self.models,
            'loaded_models': list(self.loaded_model_instances.keys()),
            'vram_usage': {
                'total_budget_mb': self.vram_budget_mb,
                'used_mb': self.current_estimated_vram_used,
                'remaining_mb': self.vram_budget_mb - self.current_estimated_vram_used
            },
            'timestamp': time.time()
        })
        self.pub_socket.send_string(status_message)
        
        # Log status summary
        status_summary = {model: info['status'] for model, info in self.models.items()}
        logger.info(f"Model status: {status_summary}")
        
        # Log detailed PC2 ZMQ service status for validation
        pc2_services = {model_id: info['status'] for model_id, info in self.models.items() 
                       if info.get('serving_method') == 'zmq_service_remote'}
        if pc2_services:
            logger.info(f"PC2 ZMQ Service Status: {pc2_services}")
            logger.debug(f"PC2 ZMQ Service Details: {json.dumps({k: v for k, v in self.models.items() if k in pc2_services}, default=str)}")
        else:
            logger.warning("No PC2 ZMQ services found in model configuration")
            
        logger.info(f"VRAM usage: {self.current_estimated_vram_used}MB / {self.vram_budget_mb}MB")

    def _check_ollama_models(self, ollama_models):
        """Check the status of Ollama models"""
        try:
            # Use the global Ollama URL
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if r.status_code == 200:
                available_models = []
                for model_data in r.json().get('models', []):
                    available_models.append(model_data.get('name', ''))
                
                # Update status for each Ollama model
                for model_id, model_info in ollama_models.items():
                    ollama_tag = model_info.get('ollama_tag', model_id)
                    
                    if ollama_tag in available_models:
                        model_info['status'] = 'online'
                        # If the model just became online, mark it as loaded
                        if model_id not in self.loaded_model_instances:
                            vram_mb = model_info.get('estimated_vram_mb', 0)
                            self._mark_model_as_loaded(model_id, vram_mb)
                    else:
                        # Ollama server is running but the model is not loaded
                        model_info['status'] = 'available_not_loaded'
                        # If the model was previously online, mark it as unloaded
                        if model_id in self.loaded_model_instances:
                            self._mark_model_as_unloaded(model_id)
                    
                    model_info['last_check'] = time.time()
            else:
                # Ollama server error
                for model_id, model_info in ollama_models.items():
                    model_info['status'] = 'server_error'
                    # If the model was previously online, mark it as unloaded
                    if model_id in self.loaded_model_instances:
                        self._mark_model_as_unloaded(model_id)
                    model_info['last_check'] = time.time()
        except Exception as e:
            logger.error(f"Error checking Ollama models: {e}")
            # Mark all models as offline
            for model_id, model_info in ollama_models.items():
                model_info['status'] = 'offline'
                # If the model was previously online, mark it as unloaded
                if model_id in self.loaded_model_instances:
                    self._mark_model_as_unloaded(model_id)
                model_info['last_check'] = time.time()
    
    def _check_zmq_remote_service_model(self, model_id, model_info):
        """Check the health of a remote ZMQ service model (PC2 service)"""
        zmq_address = model_info.get('zmq_address')
        if not zmq_address:
            logger.warning(f"No ZMQ address for remote service model {model_id}")
            model_info['status'] = 'config_error'
            model_info['last_check'] = time.time()
            return
            
        logger.debug(f"Checking PC2 ZMQ remote service: {model_id} at {zmq_address}")
        
        # Get the health check action data
        zmq_actions = model_info.get('zmq_actions', {})
        health_action = zmq_actions.get('health')
        expected_response = model_info.get('expected_health_response_contains', {})
        
        if not health_action:
            logger.warning(f"No health check action defined for {model_id}")
            model_info['status'] = 'health_check_undefined'
            model_info['last_check'] = time.time()
            return
            
        # Create socket for this check
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 1000)  # Close socket even if unsent messages
        socket.setsockopt(zmq.RCVTIMEO, 3000)  # 3 second receive timeout
        socket.setsockopt(zmq.SNDTIMEO, 3000)  # 3 second send timeout
        
        try:
            socket.connect(zmq_address)
            
            # Prepare health check payload based on the type
            if isinstance(health_action, str):
                # Simple string action
                payload = {"action": health_action}
            elif isinstance(health_action, dict):
                # Complex action with parameters
                payload = health_action
            else:
                logger.error(f"Invalid health action format for {model_id}: {health_action}")
                model_info['status'] = 'config_error'
                model_info['last_check'] = time.time()
                socket.close()
                context.term()
                return
                
            # Log the health check attempt
            logger.debug(f"Sending health check to {model_id} at {zmq_address}: {payload}")
            
            # Send health check request
            socket.send_string(json.dumps(payload))
            
            # Get response with timeout
            response_str = socket.recv_string()
            logger.debug(f"Received health response from {model_id}: {response_str}")
            
            try:
                response = json.loads(response_str)
                
                # Check if response matches expected format
                is_valid = True
                for key, expected_value in expected_response.items():
                    if key not in response or response[key] != expected_value:
                        is_valid = False
                        logger.warning(f"Health check for {model_id} failed: expected {key}={expected_value}, got {response.get(key, 'missing')}")
                        break
                        
                if is_valid:
                    model_info['status'] = 'online'
                    # If the model just became online, mark it as loaded
                    if model_id not in self.loaded_model_instances:
                        vram_mb = model_info.get('estimated_vram_mb', 0)
                        self._mark_model_as_loaded(model_id, vram_mb)
                else:
                    model_info['status'] = 'unhealthy'
                    # If the model was previously online, mark it as unloaded
                    if model_id in self.loaded_model_instances:
                        self._mark_model_as_unloaded(model_id)
                        
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response from {model_id}: {response_str}")
                model_info['status'] = 'response_error'
                if model_id in self.loaded_model_instances:
                    self._mark_model_as_unloaded(model_id)
                    
        except zmq.error.Again:
            # Timeout error
            logger.warning(f"Timeout connecting to {model_id} at {zmq_address}")
            model_info['status'] = 'timeout'
            if model_id in self.loaded_model_instances:
                self._mark_model_as_unloaded(model_id)
                
        except Exception as e:
            logger.error(f"Error checking {model_id}: {str(e)}")
            model_info['status'] = 'error'
            if model_id in self.loaded_model_instances:
                self._mark_model_as_unloaded(model_id)
                
        finally:
            socket.close()
            context.term()
            model_info['last_check'] = time.time()

    def _check_custom_api_model(self, model_id, model_info):
        """Check the status of a custom API model"""
        logger.info(f"--- MMA: _check_custom_api_model for {model_id} ---")
        try:
            api_base_url = model_info.get('api_base_url', '')
            if not api_base_url:
                model_info['status'] = 'misconfigured'
                model_info['last_check'] = time.time()
                return
                
            # For custom APIs, just check if the base URL is reachable
            # This could be enhanced to check specific endpoints based on the API
            r = requests.options(api_base_url, timeout=5)
            
            if r.status_code < 500:  # Accept any non-server-error response
                model_info['status'] = 'online'
                vram_mb = model_info.get('estimated_vram_mb', 0)
                self._mark_model_as_loaded(model_id, vram_mb)
            else:
                model_info['status'] = 'error'
                if model_id in self.loaded_model_instances:
                    self._mark_model_as_unloaded(model_id)
        except Exception as e:
            logger.error(f"Error checking custom API model {model_id}: {e}")
            model_info['status'] = 'offline'
            if model_id in self.loaded_model_instances:
                self._mark_model_as_unloaded(model_id)
        
        model_info['last_check'] = time.time()

    def _check_zmq_service_model(self, model_id, model_info):
        """Check the status of a ZMQ service model"""
        logger.info(f"--- MMA: Checking ZMQ service model {model_id} at {model_info.get('zmq_address')} ---")
        
        req_socket = None
        req_context = None
        response_str_for_logging = "N/A"

        try:
            zmq_address = model_info.get('zmq_address', '')
            zmq_actions = model_info.get('zmq_actions', {})
            health_action = zmq_actions.get('health', 'health_check') # Default to 'health_check'
            
            if not zmq_address:
                logger.warning(f"ZMQ service {model_id} is misconfigured: missing zmq_address.")
                model_info['status'] = 'misconfigured'
                return

            req_context = zmq.Context.instance() # Use singleton context instance
            req_socket = req_context.socket(zmq.REQ)
            req_socket.setsockopt(zmq.LINGER, 0)
            req_socket.setsockopt(zmq.RCVTIMEO, 5000) # 5-second receive timeout
            req_socket.setsockopt(zmq.SNDTIMEO, 5000) # 5-second send timeout
            
            logger.info(f"Connecting to ZMQ service {model_id} at {zmq_address} for health check.")
            req_socket.connect(zmq_address)
            
            request_payload = json.dumps({"action": health_action, "model_id": model_id})
            logger.info(f"Sending health check to {model_id}: {request_payload}")
            req_socket.send_string(request_payload)
            
            try:
                response_str_for_logging = req_socket.recv_string()
                logger.info(f"Received health check response from {model_id}: {response_str_for_logging}")
                response_data = json.loads(response_str_for_logging)
                
                # Get service status - accept both 'ok' and 'success'
                service_status = response_data.get('status', '').lower()
                
                # Get model status - check multiple possible fields
                model_actual_status = response_data.get('model_status', '').lower()
                is_loaded = response_data.get('is_loaded', False)
                
                logger.info(f"ZMQ service {model_id} health check: service_status={service_status}, model_status={model_actual_status}, is_loaded={is_loaded}")

                # Validate response against expected_health_response_contains
                expected_response_config = model_info.get('expected_health_response_contains', {})
                is_response_valid_and_healthy = True  # Assume true initially

                if expected_response_config:  # Only check if defined
                    for key, expected_value in expected_response_config.items():
                        actual_value = response_data.get(key)
                        if expected_value == "ANY":  # Handle "ANY" wildcard
                            if actual_value is None:  # Key must exist even for "ANY"
                                is_response_valid_and_healthy = False
                                logger.warning(f"ZMQ service {model_id} health mismatch: Expected key '{key}' to exist (for ANY value), but it's missing.")
                                break
                        elif actual_value != expected_value:
                            is_response_valid_and_healthy = False
                            logger.warning(f"ZMQ service {model_id} health mismatch: Expected '{key}':'{expected_value}', Got:'{actual_value}'")
                            break

                if is_response_valid_and_healthy and service_status in ['ok', 'success', 'healthy']:
                    model_info['status'] = 'online'
                    logger.info(f"ZMQ service {model_id} reported HEALTHY and response VALIDATED.")
                else:
                    model_info['status'] = 'unhealthy'
                    if not is_response_valid_and_healthy:
                        logger.warning(f"ZMQ service {model_id} reported UNHEALTHY due to response mismatch with expected_health_response_contains.")
                    else:  # service_status was not ok/success/healthy
                        logger.warning(f"ZMQ service {model_id} reported UNHEALTHY status: '{service_status}'.")

                # Update model loaded state if available
                if is_loaded is not None:
                    if is_loaded and model_id not in self.loaded_model_instances:
                        self._mark_model_as_loaded(model_id)
                    elif not is_loaded and model_id in self.loaded_model_instances:
                        self._mark_model_as_unloaded(model_id)
                
            except zmq.error.Again:
                logger.error(f"ZMQ socket timeout waiting for health check response from {model_id}")
                model_info['status'] = 'offline'
                if model_id in self.loaded_model_instances:
                    self._mark_model_as_unloaded(model_id)
                    
        except Exception as e:
            logger.error(f"Error checking ZMQ service model {model_id}: {e}")
            model_info['status'] = 'offline'
            if model_id in self.loaded_model_instances:
                self._mark_model_as_unloaded(model_id)
        
        model_info['last_check'] = time.time()

    def _check_zmq_remote_service_model(self, model_id, model_info):
        # TEMPORARY DIAGNOSTIC - _CHECK_ZMQ_REMOTE_SERVICE_MODEL ENTRY
        print("!!! _CHECK_ZMQ_REMOTE_SERVICE_MODEL (PATCHED_ZMQ) ENTERED !!!")
        logger.critical("!!! _CHECK_ZMQ_REMOTE_SERVICE_MODEL (PATCHED_ZMQ) ENTERED !!!")
        """Check the status of a remote ZMQ service model"""
        # Get the action string from the 'health' key in zmq_actions.
        # This 'health_check_action_string' is what the remote service expects as the value for its "action" field.
        health_check_action_string = model_info.get('zmq_actions', {}).get('health') 
        
        if not model_info.get('zmq_address') or not health_check_action_string:
            logger.error(f"Remote ZMQ model {model_id}: Missing 'zmq_address' or 'health' action string not defined in 'zmq_actions'. "
                         f"ZMQ Address: '{model_info.get('zmq_address')}', Configured zmq_actions: {model_info.get('zmq_actions')}")
            if model_info.get('status') != 'error': 
                model_info['status'] = 'error'
            model_info['last_check'] = time.time() 
            return
        
        # Create a new context and socket for each attempt for robustness
        context = zmq.Context() 
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        # TODO: Consider making timeout configurable via system_config.py (already noted in original code)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout for send
        
        current_status = model_info.get('status')
        new_status = current_status 
        response_text_for_logging = "N/A" # Initialize for logging in case recv fails early
        
        try:
            logger.debug(f"Connecting to remote ZMQ service {model_id} at {model_info.get('zmq_address')} for health check (action string from config: '{health_check_action_string}').")
            socket.connect(model_info.get('zmq_address'))

            logger.debug(f"Sending health request to remote {model_id}: {{'action': '{health_check_action_string}'}}")
            socket.send_json({"action": health_check_action_string})

            # RCVTIMEO is set, so recv() will block until timeout or message arrival
            raw_response_bytes = socket.recv() 

            response_text_for_logging = raw_response_bytes.decode('utf-8', errors='replace')
            response = json.loads(response_text_for_logging)
            logger.debug(f"Received health response from remote {model_id}: {response}")
            
            if isinstance(response, dict):
                service_status = response.get('status', '').lower()
                is_alive = response.get('alive', None) # Explicitly check for None vs False

                if service_status in ['loaded', 'online', 'ok', 'success', 'available_not_loaded'] or is_alive is True:
                    new_status = 'online'
                elif service_status in ['offline', 'error', 'failed', 'unloaded', 'not_ready'] or is_alive is False:
                    new_status = 'offline'
                    logger.warning(f"Remote ZMQ service {model_id} reported not ready: {response}")
                else:
                    new_status = 'error' 
                    logger.warning(f"Remote ZMQ service {model_id} returned ambiguous or unexpected health response content: {response}")
            else:
                new_status = 'error' 
                logger.warning(f"Remote ZMQ service {model_id} returned non-JSON or unexpected response format: {response}")
        
        except zmq.error.Again: # Timeout (can be from connect, send, or recv)
            logger.warning(f"Timeout (zmq.error.Again) during ZMQ operation with remote service {model_id} at {model_info.get('zmq_address')}.")
            new_status = 'offline'
        except zmq.error.ZMQError as e:
            logger.error(f"ZMQError (excluding timeout) checking remote ZMQ service {model_id} at {model_info.get('zmq_address')}: {e} (Error Code: {e.errno if hasattr(e, 'errno') else 'N/A'}).")
            if hasattr(e, 'errno') and e.errno == zmq.ENOTSOCK: # zmq.ENOTSOCK is typically the "Socket operation on non-socket"
                 logger.error(f"Caught ENOTSOCK (Socket operation on non-socket) for {model_id}. This strongly indicates a ZMQ context/socket issue.")
            new_status = 'offline'
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError processing response from remote ZMQ service {model_id} at {model_info.get('zmq_address')}: {e}. Raw response: '{response_text_for_logging}'")
            new_status = 'error'
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Generic error checking remote ZMQ service {model_id} at {model_info.get('zmq_address')}: {type(e).__name__} - {e}. Raw response if available: '{response_text_for_logging}'")
            new_status = 'offline' 
        finally:
            socket.close()
            context.term() # Crucially, terminate the local context

        if model_info.get('status') != new_status:
            model_info['status'] = new_status
            logger.info(f"Status for remote model {model_id} updated to '{new_status}' after health check.")
        logger.debug(f"_check_zmq_remote_service_model complete for {model_id}, final status={new_status}")
        
        model_info['last_check'] = time.time() # Ensure last_check is always updated

    def _check_gguf_model(self, model_id, model_info):
        """Check the status of a GGUF model"""
        if not self.gguf_available:
            logger.error(f"GGUF connector not available for checking model {model_id}")
            model_info['status'] = 'error'
            return
        
        logger.info(f"Checking GGUF model {model_id}")
        # Use get_gguf_status method which returns status of all models
        response = self.gguf_connector.get_gguf_status()
        
        if response.get('status') == 'success':
            # The response contains status of all models
            models_status = response.get('models', {})
            
            # Check if this specific model is in the response
            if model_id in models_status:
                model_status = models_status[model_id]
                model_info['status'] = 'online' if model_status.get('loaded', False) else 'available_not_loaded'
                if model_status.get('loaded', False):
                    # If model is loaded, update VRAM tracking
                    vram_mb = model_info.get('estimated_vram_mb', 0)
                    self._mark_model_as_loaded(model_id, vram_mb)
                model_info['last_check'] = time.time()
            else:
                # Model not found in response
                model_info['status'] = 'available_not_loaded'
                model_info['last_check'] = time.time()
        else:
            logger.error(f"Failed to check GGUF model {model_id}: {response.get('error')}")
            model_info['status'] = 'error'
            model_info['last_check'] = time.time()

    def health_check_models(self, publish_update=True):
        """Perform health checks on all configured models."""
        logger.info("--- MMA: health_check_models CALLED ---")
        logger.debug(f"health_check_models: total models to check = {len(self.models)}")
        
        # Track ZMQ health targets for debugging
        zmq_health_targets = [(mid, mcfg.get('zmq_address')) for mid, mcfg in self.models.items() 
                            if mcfg.get('serving_method') == 'zmq_service_remote' and mcfg.get('enabled', True)]
        logger.debug(f"Health check will consider ZMQ addresses: {zmq_health_targets}")
        
        models_to_check = list(self.models.items()) # Create a copy to iterate over
        now = time.time()

        for model_id, model_info in models_to_check:
            serving_method = model_info.get('serving_method')
            logger.info(f"--- MMA: health_check_models: Checking {model_id} using {serving_method} ---")
            
            if serving_method == 'zmq_pub_health_local':
                logger.debug(f"[PUBSUB_HC] Entered PUB/SUB health check for {model_id}")
                sub_sock = self.pubsub_health_sockets.get(model_id)
                
                if not sub_sock:
                    logger.error(f"[PUBSUB_HC] No SUB socket found for {model_id}. Model may not be properly initialized.")
                    model_info['status'] = 'error'
                    model_info['last_check'] = now
                    continue
                
                expected = self.pubsub_health_expected.get(model_id, {})
                timeout = self.pubsub_health_timeout.get(model_id, 15)
                healthy = False
                
                logger.debug(f"[PUBSUB_HC] Checking {model_id} (socket={sub_sock}, expected={expected}, timeout={timeout}s)")
                
                try:
                    # Try to receive any pending messages
                    while True:
                        try:
                            msg = sub_sock.recv_string(flags=zmq.NOBLOCK)
                            logger.debug(f"[PUBSUB_HC] Received health msg from {model_id}: {msg}")
                            
                            try:
                                msg_json = json.loads(msg)
                                match = all(k in msg_json and msg_json[k] == v for k, v in expected.items())
                                logger.debug(f"[PUBSUB_HC] Health msg match result for {model_id}: {match}")
                                
                                if match:
                                    self.pubsub_health_last_msg[model_id] = now
                                    healthy = True
                                    logger.info(f"[PUBSUB_HC] {model_id} marked HEALTHY via PUB msg at {now}")
                            except json.JSONDecodeError as e:
                                logger.warning(f"[PUBSUB_HC] Invalid JSON from {model_id}: {e}")
                                continue
                            
                        except zmq.Again:
                            logger.debug(f"[PUBSUB_HC] No more messages for {model_id} at this poll.")
                            break
                            
                except Exception as e:
                    logger.error(f"[PUBSUB_HC] Error polling SUB socket for {model_id}: {e}")
                    model_info['status'] = 'error'
                    model_info['last_check'] = now
                    continue
                
                # Check if we've received a healthy message within the timeout period
                last_healthy = self.pubsub_health_last_msg.get(model_id, 0)
                time_since_last_healthy = now - last_healthy
                
                logger.debug(f"[PUBSUB_HC] {model_id} last healthy: {last_healthy}, now: {now}, time since: {time_since_last_healthy}s")
                
                if time_since_last_healthy <= timeout:
                    model_info['status'] = 'online'
                    logger.info(f"[PUBSUB_HC] {model_id} is HEALTHY (last healthy msg {time_since_last_healthy:.1f}s ago)")
                else:
                    model_info['status'] = 'timeout_pub'
                    logger.warning(f"[PUBSUB_HC] {model_id} is UNHEALTHY (no healthy msg in {time_since_last_healthy:.1f}s)")
                
                model_info['last_check'] = now
                continue
                
            elif serving_method == 'ollama':
                self._check_ollama_model(model_id, model_info)
            elif serving_method == 'custom_api':
                self._check_custom_api_model(model_id, model_info)
            elif serving_method == 'zmq_service':
                self._check_zmq_service_model(model_id, model_info)
            elif serving_method == 'zmq_service_remote':
                zmq_addr = model_info.get('zmq_address')
                logger.debug(f"Attempting health check for model '{model_id}' at ZMQ address '{zmq_addr}'")
                self._check_zmq_remote_service_model(model_id, model_info)
        
        # Log status summary
        status_summary = {model: info['status'] for model, info in self.models.items()}
        logger.info(f"Model status: {status_summary}")
        logger.info(f"VRAM usage: {self.current_estimated_vram_used}MB / {self.vram_budget_mb}MB")
        logger.debug("--- MMA: health_check_models COMPLETED ---")

    def _check_ollama_model(self, model_id, model_info):
        """Check the status of an Ollama model"""
        logger.info(f"--- MMA: _check_ollama_model for {model_id} --- START ---")
        try:
            ollama_tag = model_info.get('ollama_tag', model_id)
            url = f"{self.ollama_url}/api/tags" # This gets ALL tags
            logger.info(f"--- MMA: _check_ollama_model: Requesting URL: {url} for model {model_id} (tag: {ollama_tag}) ---")
            
            r = requests.get(url, timeout=self.ollama_request_timeout)
            logger.info(f"--- MMA: _check_ollama_model: Response status {r.status_code} from {url} for {model_id} ---")

            if r.status_code == 200:
                logger.info(f"--- MMA: _check_ollama_model: Processing 200 OK response for {model_id} ---")
                response_data = r.json()
                available_models_on_server = [m.get('name') for m in response_data.get('models', [])]
                logger.info(f"--- MMA: _check_ollama_model: Available models on server: {available_models_on_server} ---")
                
                prev_status = model_info.get('status', 'unknown')
                
                if ollama_tag in available_models_on_server:
                    logger.info(f"--- MMA: _check_ollama_model: {model_id} ({ollama_tag}) IS in available models. Setting status to 'online'. Prev status: {prev_status} ---")
                    model_info['status'] = 'online'
                    if prev_status != 'online':
                        vram_mb = model_info.get('estimated_vram_mb', 0)
                        self._mark_model_as_loaded(model_id, vram_mb)
                else:
                    logger.info(f"--- MMA: _check_ollama_model: {model_id} ({ollama_tag}) NOT in available models. Setting status to 'available_not_loaded'. Prev status: {prev_status} ---")
                    model_info['status'] = 'available_not_loaded'
                    if prev_status == 'online' and model_id in self.loaded_model_instances:
                        logger.info(f"--- MMA: _check_ollama_model: Marking {model_id} as unloaded (was online, now not available). ---")
                        self._mark_model_as_unloaded(model_id)
                        logger.info(f"--- MMA: _check_ollama_model: {model_id} marked as unloaded. ---")
                model_info['last_check'] = time.time()
            else:
                logger.info(f"--- MMA: _check_ollama_model: Ollama server returned status {r.status_code} for {model_id} ---")
                model_info['status'] = 'error'
                model_info['last_check'] = time.time()
        except Exception as e:
            logger.error(f"--- MMA: _check_ollama_model: Exception while checking {model_id}: {e}")
            model_info['status'] = 'error'
            model_info['last_check'] = time.time()

    def _check_custom_api_model(self, model_id, model_info):
        """Check the status of a custom API model"""
        logger.info(f"--- MMA: _check_custom_api_model for {model_id} ---")
        try:
            api_base_url = model_info.get('api_base_url', '')
            if not api_base_url:
                model_info['status'] = 'misconfigured'
                model_info['last_check'] = time.time()
                return
                
            # For custom APIs, just check if the base URL is reachable
            # This could be enhanced to check specific endpoints based on the API
            r = requests.options(api_base_url, timeout=5)
            
            if r.status_code < 500:  # Accept any non-server-error response
                model_info['status'] = 'online'
                vram_mb = model_info.get('estimated_vram_mb', 0)
                self._mark_model_as_loaded(model_id, vram_mb)
            else:
                model_info['status'] = 'error'
                if model_id in self.loaded_model_instances:
                    self._mark_model_as_unloaded(model_id)
        except Exception as e:
            logger.error(f"Error checking custom API model {model_id}: {e}")
            model_info['status'] = 'offline'
            if model_id in self.loaded_model_instances:
                self._mark_model_as_unloaded(model_id)
        
        model_info['last_check'] = time.time()

    def select_model(self, task_type, context_size=None):
        """Select the best model for a given task type with VRAM-aware orchestration"""
        # Filter for models that support the requested task type
        capable_models = {}
        for model_id, info in self.models.items():
            if task_type in info.get('capabilities', []):
                capable_models[model_id] = info
        
        if not capable_models:
            logger.warning(f"No models have capability '{task_type}'! Using any available model.")
            capable_models = self.models
        
        # Filter by context size if specified
        if context_size:
            suitable_models = {model_id: info for model_id, info in capable_models.items() 
                             if info.get('context_length', 0) >= context_size}
            
            if suitable_models:
                capable_models = suitable_models
            else:
                logger.warning(f"No models can handle context size {context_size}! Using largest available model.")
                largest_model = max(capable_models.items(), key=lambda x: x[1].get('context_length', 0))[0]
                capable_models = {largest_model: capable_models[largest_model]}
        
        # Prioritize models by status: online > available_not_loaded > others
        online_models = {model_id: info for model_id, info in capable_models.items() 
                        if info.get('status', '') == 'online'}
        
        available_models = {model_id: info for model_id, info in capable_models.items() 
                           if info.get('status', '') == 'available_not_loaded'}
        
        # Select from online models if possible
        if online_models:
            selected_model = self._select_best_from_candidates(online_models)
            logger.info(f"Selected already loaded model '{selected_model}' for task type '{task_type}'")
            # Update last used timestamp
            self.model_last_used_timestamp[selected_model] = time.time()
            return selected_model, self.models[selected_model]
            
        # Try to load a model if none are online
        if available_models:
            selected_model = self._select_best_from_candidates(available_models)
            model_info = self.models[selected_model]
            vram_mb = model_info.get('estimated_vram_mb', 0)
            
            # Check if we can accommodate this model in our VRAM budget
            if self._can_accommodate_model(vram_mb):
                logger.info(f"Selected available model '{selected_model}' for task type '{task_type}', will load on demand")
                # Will be loaded on demand by the requester
                return selected_model, model_info
            else:
                # Try to free up VRAM by unloading least recently used models
                self._make_room_for_model(vram_mb)
                
                # Check again if we can fit the model
                if self._can_accommodate_model(vram_mb):
                    logger.info(f"Made room for model '{selected_model}', will load on demand")
                    return selected_model, model_info
                else:
                    logger.warning(f"Cannot accommodate model '{selected_model}' even after unloading other models")
                    # Fall through to the fallback
        
        # Fallback: use any model that's available, even if offline or errored
        if capable_models:
            selected_model = next(iter(capable_models))
            logger.warning(f"Fallback: selected model '{selected_model}' despite non-ideal status")
            return selected_model, self.models[selected_model]
        
        # Ultimate fallback if no models found
        logger.error(f"No suitable models found for task type '{task_type}'!")
        fallback_model = next(iter(self.models)) if self.models else None
        if fallback_model:
            return fallback_model, self.models[fallback_model]
        else:
            return None, None

    def _select_best_from_candidates(self, candidate_models):
        """Select the best model from a set of candidates based on various criteria"""
        # For now, just pick the model with the lowest estimated VRAM usage
        # This could be enhanced with more sophisticated selection criteria
        if not candidate_models:
            return None
        
        # Sort by VRAM usage (ascending)
        sorted_models = sorted(
            candidate_models.items(),
            key=lambda x: x[1].get('estimated_vram_mb', float('inf'))
        )
        
        return sorted_models[0][0]  # Return the model_id of the first (lowest VRAM) model

    def _make_room_for_model(self, required_vram_mb):
        """Try to free up VRAM by unloading least recently used models"""
        if not self.loaded_model_instances:
            logger.warning("No loaded models to unload for making room")
            return False
        
        # Sort loaded models by last used timestamp (oldest first)
        sorted_models = sorted(
            [(model_id, self.model_last_used_timestamp.get(model_id, 0)) 
             for model_id in self.loaded_model_instances],
            key=lambda x: x[1]
        )
        
        freed_vram = 0
        for model_id, _ in sorted_models:
            model_info = self.models.get(model_id)
            if not model_info:
                # Unknown model in loaded_model_instances - something's wrong
                logger.warning(f"Model {model_id} is tracked as loaded but not found in models config")
                self._mark_model_as_unloaded(model_id)
                continue
                
            serving_method = model_info.get('serving_method', '')
            model_vram = self.loaded_model_instances.get(model_id, 0)
            
            logger.info(f"Unloading model {model_id} to make room, frees {model_vram}MB VRAM")
            
            # Unload the model
            if serving_method == 'ollama':
                self._unload_ollama_model(model_id)
            elif serving_method == 'custom_api':
                self._unload_custom_api_model(model_id)
            elif serving_method == 'zmq_service':
                self._unload_zmq_service_model(model_id)
            elif serving_method == 'zmq_service_remote':
                # Do not unload remote services
                continue
            elif serving_method == 'gguf_direct':
                # Unload GGUF model
                self._unload_gguf_model(model_id)
            elif serving_method == 'zmq_pub_health_local':
                # No unload action needed, but recognized
                continue
            else:
                logger.warning(f"Unknown serving method '{serving_method}' for model {model_id}")
                # Mark as unloaded anyway to maintain accurate VRAM tracking
                self._mark_model_as_unloaded(model_id)

            # Update freed VRAM
            freed_vram += model_vram
            
            # Check if we've freed enough
            if freed_vram >= required_vram_mb:
                logger.info(f"Successfully freed {freed_vram}MB VRAM, which satisfies the requirement of {required_vram_mb}MB")
                return True
        
        logger.warning(f"Could only free {freed_vram}MB VRAM, which is less than the required {required_vram_mb}MB")
        return False
    
    def _process_request(self, request):
        """Process incoming requests and return a response"""
        request_type = request.get('type', '')
        
        if request_type == 'load_model':
            # Request to load a specific model
            model_name = request.get('model_name')
            if not model_name:
                return {
                    "status": "error",
                    "error": "Missing model_name parameter"
                }
                
            # Update last used time - moved to load_model method itself
            # if model_name in self.model_last_used_timestamp:
            #     self.model_last_used_timestamp[model_name] = time.time()
                
            # Check if model is already loaded - handled by load_model method
            # if model_name in self.loaded_model_instances:
            #     return {
            #         "status": "success",
            #         "message": f"Model {model_name} is already loaded",
            #         "model_status": "loaded"
            #     }
                
            # Load the model
            success = self.load_model(model_name) # Calls the new method
            if success:
                return {
                    "status": "success",
                    "message": f"Model {model_name} loaded successfully",
                    "model_status": self.models.get(model_name, {}).get('status', 'loaded') # Get current status
                }
            else:
                return {
                    "status": "error",
                    "error": f"Failed to load model {model_name}",
                    "model_status": self.models.get(model_name, {}).get('status', 'error') # Get current status
                }
                
        elif request_type == 'unload_model':
            # Request to unload a specific model
            model_name = request.get('model_name')
            if not model_name:
                return {
                    "status": "error",
                    "error": "Missing model_name parameter"
                }
                
            # Check if loaded
            if model_name not in self.loaded_model_instances:
                return {
                    "status": "success",
                    "message": f"Model {model_name} is not loaded",
                    "model_status": "unloaded"
                }
                
            # Unload the model
            success = self.unload_model(model_name) # Calls the new method
            if success:
                return {
                    "status": "success",
                    "message": f"Model {model_name} unloaded successfully or was already unloaded",
                    "model_status": self.models.get(model_name, {}).get('status', 'available_not_loaded')
                }
            else:
                return {
                    "status": "error",
                    "error": f"Failed to unload model {model_name}",
                    "model_status": self.models.get(model_name, {}).get('status', 'error')
                }
                
        elif request_type == 'get_model_status':
            # Request to get status of a specific model
            model_name = request.get('model_name')
            if not model_name:
                return {
                    "status": "error",
                    "error": "Missing model_name parameter"
                }
                
            if model_name not in self.models:
                return {
                    "status": "error",
                    "error": f"Unknown model: {model_name}"
                }
            
            model_detail = self.models[model_name]
            is_loaded_instance = model_name in self.loaded_model_instances
            mem_usage = 0
            if is_loaded_instance:
                mem_usage = self.loaded_model_instances.get(model_name, 0)
            elif model_detail.get('status') == 'online': # Not in instances, but config says online (e.g. Ollama)
                mem_usage = model_detail.get('estimated_vram_mb', 0)

            # Return model status
            return {
                "status": "success",
                "model_name": model_name,
                "model_info": model_detail, # Send full model_info
                "is_loaded": is_loaded_instance, # Based on VRAM tracking
                "last_used_timestamp": self.model_last_used_timestamp.get(model_name, 0),
                "current_memory_usage_mb": mem_usage
            }
            
        elif request_type == 'get_all_models':
            # Request to get status of all models
            models_data = {}
            for m_id, m_info in self.models.items():
                is_loaded_instance = m_id in self.loaded_model_instances
                mem_usage = 0
                if is_loaded_instance:
                    mem_usage = self.loaded_model_instances.get(m_id, 0)
                elif m_info.get('status') == 'online':
                     mem_usage = m_info.get('estimated_vram_mb', 0)
                models_data[m_id] = {
                    'info': m_info,
                    'is_loaded': is_loaded_instance,
                    'current_memory_usage_mb': mem_usage,
                    'last_used_timestamp': self.model_last_used_timestamp.get(m_id, 0)
                }
            return {
                "status": "success",
                "models": models_data,
                # "loaded_models_legacy": list(self.loaded_models.keys()), # Deprecate self.loaded_models
                # "memory_usage_legacy": self.model_memory_usage # Deprecate self.model_memory_usage
            }
            
        elif request_type == 'get_memory_status':
            # Request to get memory status
            if self.device == 'cuda':
                # This torch.cuda.memory_allocated() might not reflect externally managed VRAM (like Ollama's)
                # self.current_estimated_vram_used is a better reflection of MMA's view
                # free_memory = torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()
                # free_memory_mb = free_memory / (1024 * 1024)  # Convert to MB
                # used_memory = torch.cuda.memory_allocated() / (1024 * 1024)  # MB
                total_memory_mb = self.total_gpu_memory
                used_memory_mb = self.current_estimated_vram_used
                free_memory_mb = self.vram_budget_mb - used_memory_mb # Free within budget
                actual_free_gpu_mem = (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()) / (1024*1024)
                usage_percent = (used_memory_mb / self.vram_budget_mb) * 100 if self.vram_budget_mb > 0 else 0
                
                return {
                    "status": "success",
                    "device": "cuda",
                    "total_gpu_memory_mb": total_memory_mb,
                    "vram_budget_mb": self.vram_budget_mb,
                    "mma_estimated_used_vram_mb": used_memory_mb,
                    "mma_estimated_free_vram_mb_in_budget": free_memory_mb,
                    "torch_allocated_vram_mb": torch.cuda.memory_allocated() / (1024*1024),
                    "torch_free_total_vram_mb": actual_free_gpu_mem,
                    "usage_percent_of_budget": usage_percent,
                    # "reserved_memory_mb": self.gpu_memory_reserved, # This was never used
                    "loaded_model_instances": self.loaded_model_instances
                }
            else:
                return {
                    "status": "success",
                    "device": "cpu",
                    "message": "Memory tracking not available for CPU"
                }
        
        elif request_type == 'health_check':
            request_id = request.get('request_id', 'N/A')
            logger.info(f"Received health_check request (ID: {request_id}). Performing full health check.")
            
            # Perform the comprehensive health check for all models.
            # This will update self.models with the latest statuses.
            self.health_check_models(publish_update=False) 
            
            response_payload = {
                'status': 'success', # Indicates the health check process was triggered
                'message': 'Full health check performed.',
                'models': self.models, # Return all model statuses
                'loaded_models': list(self.loaded_model_instances.keys()),
                'vram_usage': {
                    'total_budget_mb': self.vram_budget_mb,
                    'used_mb': self.current_estimated_vram_used,
                    'remaining_mb': self.vram_budget_mb - self.current_estimated_vram_used
                },
                'request_id_received': request_id,
                'timestamp': time.time()
            }
            logger.info(f"Responding to health_check request (ID: {request_id}) with full model status.")
            return json.dumps(response_payload)

        elif request_type == 'get_model_status':
            model_id = request.get('model_id') # Corrected from 'model' to 'model_id' for consistency if this is the key used by clients
            if not model_id:
                model_id = request.get('model') # Fallback if 'model' is used by some clients
                
            logger.info(f"Processing 'get_model_status' for model_id='{model_id}' (ID: {request.get('request_id', 'N/A')})")

            if model_id in self.models:
                # Update timestamp if model is being checked
                if model_id in self.loaded_model_instances:
                    self.model_last_used_timestamp[model_id] = time.time()
                        
                return json.dumps({
                    'status': 'success',
                    'model': model_id,
                    'model_info': self.models[model_id],
                    'is_loaded': model_id in self.loaded_model_instances,
                    'last_used': self.model_last_used_timestamp.get(model_id, 0),
                    'vram_usage': self.loaded_model_instances.get(model_id, 0),
                    'request_id': request.get('request_id', 'N/A')
                })
            else:
                logger.warning(f"Model '{model_id}' not found during get_model_status (ID: {request.get('request_id', 'N/A')})")
                return json.dumps({
                    'status': 'error',
                    'message': f"Model '{model_id}' not found",
                    'request_id': request.get('request_id', 'N/A')
                })
            
        elif request_type == 'get_all_models':
            logger.info(f"Processing 'get_all_models' (ID: {request.get('request_id', 'N/A')})")
            return json.dumps({
                'status': 'success',
                'models': self.models,
                'loaded_models': list(self.loaded_model_instances.keys()),
                'vram_usage': {
                    'total_budget_mb': self.vram_budget_mb,
                    'used_mb': self.current_estimated_vram_used,
                    'remaining_mb': self.vram_budget_mb - self.current_estimated_vram_used,
                    'by_model': self.loaded_model_instances
                },
                'request_id': request.get('request_id', 'N/A')
            })
                
        elif request_type == 'load_model':
            logger.info(f"Processing 'load_model' for model_id='{request.get('model_id')}' (ID: {request.get('request_id', 'N/A')})")
            if not request.get('model_id'):
                logger.error(f"Missing model_id parameter for 'load_model' (ID: {request.get('request_id', 'N/A')})")
                return json.dumps({
                    'status': 'error',
                    'message': "Missing model_id parameter",
                    'request_id': request.get('request_id', 'N/A')
                })
                    
            if request.get('model_id') not in self.models:
                logger.warning(f"Unknown model '{request.get('model_id')}' for 'load_model' (ID: {request.get('request_id', 'N/A')})")
                return json.dumps({
                    'status': 'error',
                    'message': f"Unknown model '{request.get('model_id')}'",
                    'request_id': request.get('request_id', 'N/A')
                })
                    
            # Get model info
            model_info = self.models[request.get('model_id')]
            serving_method = model_info.get('serving_method', '')
                
            # Try to load the model if not already loaded
            if request.get('model_id') not in self.loaded_model_instances:
                logger.info(f"Model '{request.get('model_id')}' not loaded yet, attempting to load")
                load_success = self.load_model(request.get('model_id'))
                
                # Re-fetch model info after load attempt
                model_info = self.models[request.get('model_id')]
                
                return json.dumps({
                    'status': 'success' if load_success else 'error',
                    'message': f"Model '{request.get('model_id')}' loading initiated" if load_success else f"Failed to load model '{request.get('model_id')}'",
                    'model_info': model_info,
                    'request_id': request.get('request_id', 'N/A')
                })
                
            # Unload the model
            if serving_method == 'ollama':
                self._unload_ollama_model(request.get('model_id'))
            elif serving_method == 'custom_api':
                self._unload_custom_api_model(request.get('model_id'))
            elif serving_method == 'zmq_service':
                self._unload_zmq_service_model(request.get('model_id'))
            elif serving_method == 'zmq_service_remote':
                # Do not unload remote services
                return json.dumps({
                    'status': 'success',
                    'message': f"Model '{request.get('model_id')}' is a remote service and cannot be unloaded from here",
                    'model_info': model_info,
                    'request_id': request.get('request_id', 'N/A')
                })
            elif serving_method == 'gguf_direct':
                self._unload_gguf_model(request.get('model_id'))
            elif serving_method == 'zmq_pub_health_local':
                # No unload action needed, but recognized
                return True  # Return True since no action needed is considered success
            else:
                # Just mark as unloaded
                self._mark_model_as_unloaded(request.get('model_id'))
                model_info['status'] = 'available_not_loaded'
            
            return json.dumps({
                'status': 'success',
                'message': f"Model '{request.get('model_id')}' unloaded",
                'model_info': model_info,
                'request_id': request.get('request_id', 'N/A')
            })
            
        elif request_type == 'get_cached_response':
            # Check if we have a cached response for this request
            prompt = request.get('prompt')
            model = request.get('model')
            system_prompt = request.get('system_prompt', '')
            
            # Create a cache key from the request parameters
            cache_key = f"{model}:{hash(prompt)}:{hash(system_prompt)}"
            
            if cache_key in self.cache:
                timestamp, response = self.cache[cache_key]
                # Check if cache entry is still valid
                if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                    logger.info(f"Cache hit for model {model}")
                    return json.dumps({
                        'status': 'success',
                        'cached': True,
                        'response': response,
                        'request_id': request.get('request_id', 'N/A')
                    })
            
            # Cache miss
            return json.dumps({
                'status': 'success',
                'cached': False,
                'request_id': request.get('request_id', 'N/A')
            })
        
        elif request_type == 'cache_response':
            # Cache a model response for future use
            prompt = request.get('prompt')
            model = request.get('model')
            system_prompt = request.get('system_prompt', '')
            response = request.get('response')
            
            # Create a cache key from the request parameters
            cache_key = f"{model}:{hash(prompt)}:{hash(system_prompt)}"
            
            # Store in cache with current timestamp
            self.cache[cache_key] = (datetime.now(), response)
            
            # Periodically clean and save cache
            if len(self.cache) % 10 == 0:  # Every 10 entries
                self._clean_cache()
                self._save_cache()
            
            return json.dumps({
                'status': 'success',
                'message': 'Response cached',
                'request_id': request.get('request_id', 'N/A')
            })
        
        else:
            logger.warning(f"Unknown request_type: '{request_type}' (ID: {request.get('request_id', 'N/A')})")
            return json.dumps({
                'status': 'error',
                'message': f"Unknown request type: {request_type}",
                'request_id': request.get('request_id', 'N/A')
            })

    def generate_code_with_cga(self, request_data):
        """
        Send a code generation request to the Code Generator Agent (CGA)
        and return the response.
        
        Args:
            request_data (dict): The request data containing the description and other parameters
            
        Returns:
            dict: The response from the CGA
        """
        logger.info(f"Generating code with CGA for request: {request_data.get('request_id', 'N/A')}")
        
        # Get the description and other parameters
        description = request_data.get('description', '')
        model_id = request_data.get('model_id', 'phi:latest')  # Default model if not specified
        language = request_data.get('language', 'python')  # Default language if not specified
        context = request_data.get('context', '')  # Additional context or files for code generation
        
        # Check if using GGUF model
        model_info = self.models.get(model_id, {})
        serving_method = model_info.get('serving_method', '')
        use_gguf = serving_method == 'gguf_direct'
        
        # Create the CGA request
        cga_request = {
            'request_id': request_data.get('request_id', str(time.time())),
            'timestamp': time.time()
        }
        
        if use_gguf:
            # GGUF model request format
            cga_request['action'] = 'generate_with_gguf'
            cga_request['model_name'] = model_info.get('model_path', model_id)
            cga_request['prompt'] = f"Write {language} code for: {description}\n{context}"
        else:
            # Ollama model request format
            cga_request['action'] = 'generate'
            cga_request['model'] = model_id
            cga_request['prompt'] = f"Write {language} code for: {description}\n{context}"
        
        # Connect to the CGA via ZMQ
        try:
            cga_port = 5604  # Default CGA port
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 120000)  # 120 second timeout for code generation
            socket.connect(f"tcp://localhost:{cga_port}")
            
            # Send the request
            logger.info(f"Sending code generation request to CGA: {json.dumps(cga_request)}")
            socket.send_string(json.dumps(cga_request))
            
            # Wait for response
            logger.info("Waiting for CGA response (may take up to 120 seconds)...")
            response_str = socket.recv_string()
            
            # Parse the response
            try:
                response = json.loads(response_str)
                logger.info(f"Received response from CGA: {response.get('status', 'unknown status')}")
                return response
            except json.JSONDecodeError:
                error_message = f"Invalid JSON response from CGA: {response_str[:100]}..."
                logger.error(error_message)
                return {
                    'status': 'error',
                    'error': error_message,
                    'request_id': request_data.get('request_id', 'N/A')
                }
                
        except zmq.error.Again:
            error_message = "Timeout while waiting for CGA response (120 seconds exceeded)"
            logger.error(error_message)
            return {
                'status': 'error',
                'error': error_message,
                'request_id': request_data.get('request_id', 'N/A')
            }
        except zmq.error.ZMQError as e:
            error_message = f"ZMQ error communicating with CGA: {str(e)}"
            logger.error(error_message)
            return {
                'status': 'error',
                'error': error_message,
                'request_id': request_data.get('request_id', 'N/A')
            }
        except Exception as e:
            error_message = f"Unexpected error in generate_code_with_cga: {str(e)}"
            logger.error(error_message)
            return {
                'status': 'error',
                'error': error_message,
                'request_id': request_data.get('request_id', 'N/A')
            }
        finally:
            # Clean up ZMQ socket
            try:
                socket.close()
                context.term()
            except:
                pass
    
    def handle_request(self, request):
        """Handle incoming requests"""
        try:
            request_data = json.loads(request)
            request_type = request_data.get('request_type')
            
            # Get request_id for logging if available
            request_id = request_data.get('request_id', 'N/A')
            logger.info(f"Received request (ID: {request_id}): type='{request_type}'")

            if request_type == 'health_check':
                logger.info(f"Processing 'health_check' (ID: {request_id}). Sending immediate basic response.")
                # Send a basic, immediate response for testing
                basic_response = {
                    'status': 'success',
                    'message': 'MMA basic health check OK (full health check temporarily bypassed for this test)',
                    'request_id': request_id,
                    'timestamp': time.time()
                }
                return json.dumps(basic_response)
            
            elif request_type == 'select_model':
                task_type = request_data.get('task_type', 'chat')
                context_size = request_data.get('context_size')
                selected_model, model_info = self.select_model(task_type, context_size)
                
                if selected_model:
                    return json.dumps({
                        'status': 'success',
                        'selected_model': selected_model,
                        'model_info': model_info,
                        'vram_usage': {
                            'total_budget_mb': self.vram_budget_mb,
                            'used_mb': self.current_estimated_vram_used,
                            'remaining_mb': self.vram_budget_mb - self.current_estimated_vram_used
                        },
                        'request_id': request_id
                    })
                else:
                    return json.dumps({
                        'status': 'error',
                        'message': f"No suitable model found for task type '{task_type}'",
                        'request_id': request_id
                    })
            
            elif request_type == 'get_model_status':
                model_id = request_data.get('model_id') # Corrected from 'model' to 'model_id' for consistency if this is the key used by clients
                if not model_id:
                    model_id = request_data.get('model') # Fallback if 'model' is used by some clients
                
                logger.info(f"Processing 'get_model_status' for model_id='{model_id}' (ID: {request_id})")

                if model_id in self.models:
                    # Update timestamp if model is being checked
                    if model_id in self.loaded_model_instances:
                        self.model_last_used_timestamp[model_id] = time.time()
                        
                    return json.dumps({
                        'status': 'success',
                        'model': model_id,
                        'model_info': self.models[model_id],
                        'is_loaded': model_id in self.loaded_model_instances,
                        'last_used': self.model_last_used_timestamp.get(model_id, 0),
                        'vram_usage': self.loaded_model_instances.get(model_id, 0),
                        'request_id': request_id
                    })
                else:
                    logger.warning(f"Model '{model_id}' not found during get_model_status (ID: {request_id})")
                    return json.dumps({
                        'status': 'error',
                        'message': f"Model '{model_id}' not found",
                        'request_id': request_id
                    })
            
            elif request_type == 'get_all_models':
                logger.info(f"Processing 'get_all_models' (ID: {request_id})")
                return json.dumps({
                    'status': 'success',
                    'models': self.models,
                    'loaded_models': list(self.loaded_model_instances.keys()),
                    'vram_usage': {
                        'total_budget_mb': self.vram_budget_mb,
                        'used_mb': self.current_estimated_vram_used,
                        'remaining_mb': self.vram_budget_mb - self.current_estimated_vram_used,
                        'by_model': self.loaded_model_instances
                    },
                    'request_id': request_id
                })
                
            elif request_type == 'load_model':
                logger.info(f"Processing 'load_model' for model_id='{request_data.get('model_id')}' (ID: {request_id})")
                if not request_data.get('model_id'):
                    logger.error(f"Missing model_id parameter for 'load_model' (ID: {request_id})")
                    return json.dumps({
                        'status': 'error',
                        'message': "Missing model_id parameter",
                        'request_id': request_id
                    })
                    
                if request_data.get('model_id') not in self.models:
                    logger.warning(f"Unknown model '{request_data.get('model_id')}' for 'load_model' (ID: {request_id})")
                    return json.dumps({
                        'status': 'error',
                        'message': f"Unknown model '{request_data.get('model_id')}'",
                        'request_id': request_id
                    })
                    
                # Get model info
                model_info = self.models[request_data.get('model_id')]
                serving_method = model_info.get('serving_method', '')
                
                # Try to load the model if not already loaded
                if request_data.get('model_id') not in self.loaded_model_instances:
                    logger.info(f"Model '{request_data.get('model_id')}' not loaded yet, attempting to load")
                    load_success = self.load_model(request_data.get('model_id'))
                    
                    # Re-fetch model info after load attempt
                    model_info = self.models[request_data.get('model_id')]
                    
                    return json.dumps({
                        'status': 'success' if load_success else 'error',
                        'message': f"Model '{request_data.get('model_id')}' loading initiated" if load_success else f"Failed to load model '{request_data.get('model_id')}'",
                        'model_info': model_info,
                        'request_id': request_id
                    })
                
                # Unload the model
                if serving_method == 'ollama':
                    self._unload_ollama_model(request_data.get('model_id'))
                elif serving_method == 'custom_api':
                    self._unload_custom_api_model(request_data.get('model_id'))
                elif serving_method == 'zmq_service':
                    self._unload_zmq_service_model(request_data.get('model_id'))
                elif serving_method == 'zmq_service_remote':
                    # Do not unload remote services
                    return json.dumps({
                        'status': 'success',
                        'message': f"Model '{request_data.get('model_id')}' is a remote service and cannot be unloaded from here",
                        'model_info': model_info,
                        'request_id': request_id
                    })
                elif serving_method == 'gguf_direct':
                    self._unload_gguf_model(request_data.get('model_id'))
                elif serving_method == 'zmq_pub_health_local':
                    # No unload action needed, but recognized
                    return True  # Return True since no action needed is considered success
                else:
                    # Just mark as unloaded
                    self._mark_model_as_unloaded(request_data.get('model_id'))
                    model_info['status'] = 'available_not_loaded'
            
                return json.dumps({
                    'status': 'success',
                    'message': f"Model '{request_data.get('model_id')}' unloaded",
                    'model_info': model_info,
                    'request_id': request_id
                })
            
            elif request_type == 'get_cached_response':
                # Check if we have a cached response for this request
                prompt = request_data.get('prompt')
                model = request_data.get('model')
                system_prompt = request_data.get('system_prompt', '')
                
                # Create a cache key from the request parameters
                cache_key = f"{model}:{hash(prompt)}:{hash(system_prompt)}"
                
                if cache_key in self.cache:
                    timestamp, response = self.cache[cache_key]
                    # Check if cache entry is still valid
                    if datetime.now() - timestamp < timedelta(seconds=self.cache_ttl):
                        logger.info(f"Cache hit for model {model}")
                        return json.dumps({
                            'status': 'success',
                            'cached': True,
                            'response': response,
                            'request_id': request_id
                        })
                
                # Cache miss
                return json.dumps({
                    'status': 'success',
                    'cached': False,
                    'request_id': request_id
                })
            
            elif request_type == 'cache_response':
                # Cache a model response for future use
                prompt = request_data.get('prompt')
                model = request_data.get('model')
                system_prompt = request_data.get('system_prompt', '')
                response = request_data.get('response')
                
                # Create a cache key from the request parameters
                cache_key = f"{model}:{hash(prompt)}:{hash(system_prompt)}"
                
                # Store in cache with current timestamp
                self.cache[cache_key] = (datetime.now(), response)
                
                # Periodically clean and save cache
                if len(self.cache) % 10 == 0:  # Every 10 entries
                    self._clean_cache()
                    self._save_cache()
                
                return json.dumps({
                    'status': 'success',
                    'message': 'Response cached',
                    'request_id': request_id
                })
            
            elif request_type == 'unload_model':
                logger.info(f"Processing 'unload_model' for model_id='{request_data.get('model_id')}' (ID: {request_id})")
                if not request_data.get('model_id'):
                    logger.error(f"Missing model_id parameter for 'unload_model' (ID: {request_id})")
                    return json.dumps({
                        'status': 'error',
                        'message': "Missing model_id parameter",
                        'request_id': request_id
                    })
                    
                if request_data.get('model_id') not in self.models:
                    logger.warning(f"Unknown model '{request_data.get('model_id')}' for 'unload_model' (ID: {request_id})")
                    return json.dumps({
                        'status': 'error',
                        'message': f"Unknown model '{request_data.get('model_id')}'",
                        'request_id': request_id
                    })
                
                # Attempt to unload the model
                unload_success = self.unload_model(request_data.get('model_id'))
                
                # Get updated model info
                model_info = self.models[request_data.get('model_id')]
                
                return json.dumps({
                    'status': 'success' if unload_success else 'error',
                    'message': f"Model '{request_data.get('model_id')}' successfully unloaded" if unload_success else f"Failed to unload model '{request_data.get('model_id')}'",
                    'model_info': model_info,
                    'request_id': request_id
                })
            
            # Handle code generation request
            elif request_type == 'generate_code':
                logger.info(f"Processing 'generate_code' request (ID: {request_id})")
                
                # Check required parameters
                if not request_data.get('description'):
                    logger.error(f"Missing 'description' parameter for code generation (ID: {request_id})")
                    return json.dumps({
                        'status': 'error',
                        'message': "Missing 'description' parameter for code generation",
                        'request_id': request_id
                    })
                
                # Generate code with CGA
                result = self.generate_code_with_cga(request_data)
                
                # Return the result (already in dict format)
                return json.dumps(result)
            
            # Handle GGUF connector requests based on 'action' field
            elif 'action' in request_data:
                action = request_data.get('action')
                logger.info(f"Processing GGUF action request: '{action}' (ID: {request_id})")
                
                # Handle get_gguf_status action
                if action == 'get_gguf_status':
                    try:
                        # Use the GGUF connector to get status
                        if hasattr(self, 'gguf_connector') and self.gguf_available:
                            status_response = self.gguf_connector.get_gguf_status()
                            return json.dumps(status_response)
                        else:
                            logger.warning("GGUF connector not available for get_gguf_status request")
                            return json.dumps({
                                'status': 'error',
                                'error': 'GGUF connector not available',
                                'request_id': request_id
                            })
                    except Exception as e:
                        logger.error(f"Error getting GGUF status: {e}")
                        return json.dumps({
                            'status': 'error',
                            'error': f"Failed to get GGUF status: {str(e)}",
                            'request_id': request_id
                        })
                
                # Handle list_gguf_models action
                elif action == 'list_gguf_models':
                    try:
                        # Use the GGUF connector to list models
                        if hasattr(self, 'gguf_connector') and self.gguf_available:
                            models_response = self.gguf_connector.list_gguf_models()
                            return json.dumps(models_response)
                        else:
                            logger.warning("GGUF connector not available for list_gguf_models request")
                            return json.dumps({
                                'status': 'error',
                                'error': 'GGUF connector not available',
                                'request_id': request_id
                            })
                    except Exception as e:
                        logger.error(f"Error listing GGUF models: {e}")
                        return json.dumps({
                            'status': 'error',
                            'error': f"Failed to list GGUF models: {str(e)}",
                            'request_id': request_id
                        })
                
                # Unknown action
                else:
                    logger.warning(f"Unknown GGUF action: '{action}' (ID: {request_id})")
                    return json.dumps({
                        'status': 'error',
                        'error': f"Unknown GGUF action: {action}",
                        'request_id': request_id
                    })
                    
            else:
                logger.warning(f"Unknown request_type: '{request_type}' (ID: {request_id})")
                return json.dumps({
                    'status': 'error',
                    'message': f"Unknown request type: {request_type}",
                    'request_id': request_id
                })

        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError in handle_request: {e}. Request was: {request[:500]}") # Log part of the problematic request
            return json.dumps({'status': 'error', 'message': f'Invalid JSON format: {e}'})
        except Exception as e:
            # Log the full traceback for unexpected errors
            logger.error(f"Unexpected error in handle_request (ID: {request_data.get('request_id', 'N/A') if isinstance(request_data, dict) else 'N/A'}): {e}", exc_info=True)
            return json.dumps({'status': 'error', 'message': f'An unexpected error occurred: {e}'})

    def health_check_loop(self):
        """Background thread for periodic health checks"""
        logger.info("Started health check loop")
        while self.running:
            try:
                self.health_check()
            except Exception as e:
                logger.error(f"Error in health check: {e}")
            
            # Sleep for the health check interval
            for _ in range(self.health_check_interval):
                if not self.running:
                    break
                time.sleep(1)

    def cache_maintenance_loop(self):
        """Background thread for periodic cache maintenance"""
        logger.info("Started cache maintenance loop")
        # Initial delay to avoid immediate cache cleaning
        time.sleep(60)
        
        while self.running:
            try:
                # Clean expired cache entries
                removed = self._clean_cache()
                
                # Save cache to disk if changes were made
                if removed > 0:
                    self._save_cache()
            except Exception as e:
                logger.error(f"Error in cache maintenance: {e}")
            
            # Run cache maintenance every hour
            for _ in range(3600):  # 1 hour
                if not self.running:
                    break
                time.sleep(1)

    def _load_gguf_model(self, model_id):
        """Load a GGUF model using the GGUF connector."""
        logger.critical(f"--- [MainMMA _load_gguf_model CRITICAL ENTRY] Called for model_id: {model_id} ---")
        try:
            # Get model info from config
            model_info = self.models.get(model_id)
            if not model_info:
                logger.error(f"Model {model_id} not found in configuration")
                return False

            # Check if we have enough VRAM
            required_vram = model_info.get('estimated_vram_mb', 0)
            if not self._can_accommodate_model(required_vram):
                logger.error(f"Not enough VRAM to load model {model_id}")
                return False

            # Load the model via GGUF connector
            success = self.gguf_connector.load_model(model_id)
            if success:
                self._mark_model_as_loaded(model_id, required_vram)
                logger.info(f"Successfully loaded GGUF model {model_id}")
                return True
            else:
                logger.error(f"Failed to load GGUF model {model_id}")
                return False
        except Exception as e:
            logger.error(f"Error loading GGUF model {model_id}: {e}")
            return False

    def _unload_gguf_model(self, model_id):
        """Unload a GGUF model using the GGUF connector."""
        logger.critical(f"--- [MainMMA _unload_gguf_model CRITICAL ENTRY] Called for model_id: {model_id} ---")
        try:
            # Unload the model via GGUF connector
            success = self.gguf_connector.unload_model(model_id)
            if success:
                self._mark_model_as_unloaded(model_id)
                logger.info(f"Successfully unloaded GGUF model {model_id}")
                return True
            else:
                logger.error(f"Failed to unload GGUF model {model_id}")
                return False
        except Exception as e:
            logger.error(f"Error unloading GGUF model {model_id}: {e}")
            return False

    def _update_gguf_status(self, model_id):
        """Update the status of a GGUF model."""
        logger.critical(f"--- [MainMMA _update_gguf_status CRITICAL ENTRY] Called for model_id: {model_id} ---")
        try:
            # Get current status from GGUF connector
            status = self.gguf_connector.get_model_status(model_id)
            if status:
                self.models[model_id]['status'] = status
                logger.info(f"Updated status for GGUF model {model_id}: {status}")
                return True
            else:
                logger.error(f"Failed to get status for GGUF model {model_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating status for GGUF model {model_id}: {e}")
            return False

    def _handle_model_requests_loop(self):
        """Enhanced model request handling loop with robust error recovery."""
        self.logger.info("MMA: _handle_model_requests_loop started.")
        self.logger.info("Model request handling thread started")
        self.logger.info("Starting model request handling loop")
        
        socket_reset_count = 0
        max_socket_resets = 5
        reset_cooldown = 0
        
        while self.running:
            try:
                # If we're in cooldown after multiple resets, sleep and continue
                if reset_cooldown > 0:
                    time.sleep(1)
                    reset_cooldown -= 1
                    continue
                
                # Wait for next request from client
                if self.socket.poll(timeout=1000) == 0:
                    continue  # No message available, continue loop
                
                try:
                    request = self.socket.recv_json(flags=zmq.NOBLOCK)
                    self.logger.info(f"MMA: Received ZMQ request: {request}")
                    
                    # Process the request
                    response = self._process_model_request(request)
                    
                    # Send response back to client
                    self.socket.send_json(response)
                    self.logger.debug(f"Sent response: {response}")
                    
                except zmq.error.Again:
                    # This is normal for non-blocking sockets when no message is available
                    # Just continue the loop without error
                    continue
                
            except zmq.error.ZMQError as e:
                self.logger.error(f"ZMQ error in request handling loop: {e}")
                
                # Implement exponential backoff for socket resets
                socket_reset_count += 1
                if socket_reset_count > max_socket_resets:
                    self.logger.warning(f"Too many socket resets ({socket_reset_count}), cooling down for 30 seconds")
                    reset_cooldown = 30
                    socket_reset_count = 0
                    continue
                
                # Reset the socket if there's an error
                try:
                    self.socket.close()
                except:
                    pass
                    
                time.sleep(1)  # Brief pause before recreating socket
                
                try:
                    self.socket = self.context.socket(zmq.REP)
                    self.socket.setsockopt(zmq.LINGER, 0)
                    self.socket.setsockopt(zmq.RCVTIMEO, 5000)
                    self.socket.setsockopt(zmq.SNDTIMEO, 5000)
                    self.socket.bind(f"tcp://*:{self.model_port}")
                    self.logger.info(f"ZMQ socket reset and rebound to port {self.model_port}")
                except Exception as bind_error:
                    self.logger.error(f"Failed to rebind socket: {bind_error}")
                    time.sleep(5)  # Wait longer after a binding failure
                
            except Exception as e:
                self.logger.error(f"Error in request handling loop: {e}")
                self.logger.error(traceback.format_exc())
                # Send error response if possible
                error_response = {
                    "status": "ERROR",
                    "error_message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                try:
                    self.socket.send_json(error_response)
                except:
                    pass  # Ignore errors when sending error response

    def _process_model_request(self, request_data):
        """
        Process a model request from the STT agent.
        
        Args:
            request_data (dict): The request message containing model_id and context
            
        Returns:
            dict: Response message with status and model information
        """
        try:
            model_id = request_data.get("model_id")
            request_id = request_data.get("request_id")
            context = request_data.get("context", {})
            
            self.model_logger.info(f"Processing model request: {model_id} (ID: {request_id})")
            self.model_logger.debug(f"Request context: {context}")
            
            if not model_id:
                self.model_logger.error("No model_id provided in request")
                return {
                    "status": "ERROR_LOADING_MODEL",
                    "request_id": request_id,
                    "error_message": "No model_id provided",
                    "error_code": "MISSING_MODEL_ID",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Get model VRAM estimate
            model_vram_mb = self._get_stt_model_vram_estimate(model_id)
            if not model_vram_mb:
                self.model_logger.error(f"Could not determine VRAM requirements for model {model_id}")
                return {
                    "status": "ERROR_LOADING_MODEL",
                    "request_id": request_id,
                    "model_id": model_id,
                    "error_message": "Could not determine VRAM requirements",
                    "error_code": "UNKNOWN_VRAM",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Get quantization level
            quantization_level = context.get('quantization_level', 
                self.vram_management_config.get('default_quantization_level', 'none'))
            
            self.quant_logger.info(f"Loading model {model_id} with quantization level: {quantization_level}")
            
            # Check if we can accommodate the model
            if not self._can_accommodate_model(model_vram_mb):
                self.vram_logger.warning(f"Insufficient VRAM for model {model_id} ({model_vram_mb}MB required)")
                # Try to make room
                if not self._make_room_for_model(model_vram_mb):
                    self.vram_logger.error(f"Could not make room for model {model_id}")
                    return {
                        "status": "ERROR_LOADING_MODEL",
                        "request_id": request_id,
                        "model_id": model_id,
                        "error_message": "Insufficient VRAM",
                        "error_code": "INSUFFICIENT_VRAM",
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            # Get model path
            model_path = self._get_stt_model_path(model_id)
            if not model_path:
                self.model_logger.error(f"Model {model_id} not found")
                return {
                    "status": "ERROR_LOADING_MODEL",
                    "request_id": request_id,
                    "model_id": model_id,
                    "error_message": "Model not found",
                    "error_code": "MODEL_NOT_FOUND",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Mark model as loaded
            self._mark_model_as_loaded(model_id, model_vram_mb)

            # Store model priority
            model_priority = self.vram_management_config.get("model_priorities", {}).get(
                model_id,
                self.vram_management_config.get("default_model_priority", 5)
            )
            
            self.model_logger.info(f"Model {model_id} assigned priority: {model_priority}")
            
            # Store model info
            self.active_stt_models[model_id] = {
                "vram_mb": model_vram_mb,
                "loaded_at": datetime.utcnow().isoformat(),
                "last_used_timestamp": time.time(),
                "priority": model_priority,
                "quantization_level": quantization_level
            }
            
            self.model_logger.info(f"Successfully loaded model {model_id}")
            return {
                "status": "MODEL_READY",
                "request_id": request_id,
                "model_id": model_id,
                "access_info": {
                    "message": "MMA approved model loading",
                    "model_path_from_config": model_path,
                    "vram_allocated_mb": model_vram_mb,
                    "quantization_level": quantization_level,
                    "priority": model_priority
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.model_logger.error(f"Error processing model request: {e}")
            self.model_logger.error(traceback.format_exc())
            return {
                "status": "ERROR_LOADING_MODEL",
                "request_id": request_id,
                "model_id": model_id,
                "error_message": str(e),
                "error_code": "PROCESSING_ERROR",
                "timestamp": datetime.utcnow().isoformat()
            }

    def _get_stt_model_vram_estimate(self, model_id):
        """
        Get VRAM estimate for an STT model.
        
        Args:
            model_id (str): The model ID to get VRAM estimate for
            
        Returns:
            float: Estimated VRAM usage in MB, or None if unknown
        """
        try:
            # Get model config from system_config
            model_config = self.machine_config.get('whisper_model_config', {}).get('models', {}).get(model_id, {})
            return model_config.get('vram_estimate_mb')
        except Exception as e:
            logger.error(f"Error getting VRAM estimate for model {model_id}: {e}")
            return None

    def _get_stt_model_path(self, model_id):
        """
        Get the path to an STT model.
        
        Args:
            model_id (str): The model ID to get path for
            
        Returns:
            str: Path to the model, or None if not found
        """
        try:
            # Get model config from system_config
            model_config = self.machine_config.get('whisper_model_config', {}).get('models', {}).get(model_id, {})
            return model_config.get('model_path')
        except Exception as e:
            logger.error(f"Error getting path for model {model_id}: {e}")
            return None

    def _unload_idle_models(self):
        current_time = time.time()
        models_to_unload = []
        
        for model_id, last_used in self.model_last_used.items():
            if current_time - last_used > self.idle_unload_timeout_seconds:
                logger.info(f"MMA: Model {model_id} exceeded idle timeout of {self.idle_unload_timeout_seconds} seconds")
                models_to_unload.append(model_id)
        
        for model_id in models_to_unload:
            logger.info(f"MMA: Unloading idle model {model_id}")
            self._unload_model(model_id)
            logger.info(f"MMA: Successfully unloaded idle model {model_id}")

    def _handle_vram_pressure(self):
        current_vram = self._get_current_vram()
        vram_budget = self.vram_budget_mb
        
        logger.info(f"MMA: Checking VRAM pressure - Current: {current_vram}MB, Budget: {vram_budget}MB")
        
        if current_vram > vram_budget:
            logger.warning(f"MMA: VRAM pressure detected! Usage: {current_vram}MB > Budget: {vram_budget}MB")
            
            # Sort models by priority (highest number = lowest priority)
            models_by_priority = sorted(
                self.loaded_models.items(),
                key=lambda x: self.vram_config['priority_levels'].get(x[1].get('priority', 'low'), 3),
                reverse=True
            )
            
            for model_id, _ in models_by_priority:
                logger.info(f"MMA: Attempting to unload model {model_id} due to VRAM pressure")
                self._unload_model(model_id)
                current_vram = self._get_current_vram()
                
                if current_vram <= vram_budget:
                    logger.info(f"MMA: VRAM pressure resolved after unloading {model_id}")
                    break
                else:
                    logger.warning(f"MMA: VRAM still under pressure after unloading {model_id}")

    def _apply_quantization(self, model_id, model_type):
        quantization_type = self.vram_management_config.get('quantization_options_per_model_type', {}).get(
            model_type,
            self.vram_management_config.get('default_quantization', 'float16')
        )
        
        logger.info(f"MMA: Applying quantization for model {model_id}")
        logger.info(f"MMA: Model type: {model_type}, Selected quantization: {quantization_type}")
        
        # ... rest of quantization code ...

    def _init_vram_management(self):
        """Initialize VRAM management settings and tracking."""
        # Default VRAM management settings
        self.vram_budget_percent = 80  # Use 80% of available VRAM
        self.memory_check_interval = 5  # Check every 5 seconds
        self.idle_timeout = 300  # Unload after 5 minutes of inactivity
        
        # VRAM tracking
        self.current_vram_used = 0
        self.loaded_models = {}
        self.model_last_used = {}
        self.model_memory_usage = {}
        
        # Load settings from config if available
        if hasattr(self, 'config') and 'vram_management' in self.config:
            vram_config = self.config['vram_management']
            self.vram_budget_percent = vram_config.get('budget_percent', self.vram_budget_percent)
            self.memory_check_interval = vram_config.get('check_interval', self.memory_check_interval)
            self.idle_timeout = vram_config.get('idle_timeout', self.idle_timeout)
        
        self.vram_logger.info("VRAM management initialized with settings:")
        self.vram_logger.info(f"Budget: {self.vram_budget_percent}%")
        self.vram_logger.info(f"Check interval: {self.memory_check_interval}s")
        self.vram_logger.info(f"Idle timeout: {self.idle_timeout}s")

    def _init_logging(self):
        """Set up logging for the Model Manager Agent."""
        logs_dir = Path('logs')
        logs_dir.mkdir(exist_ok=True)
        log_file = logs_dir / 'model_manager_agent.log'
        log_level = os.environ.get('MMA_LOG_LEVEL', 'DEBUG')
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        # Set up root logger only if it has no handlers
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            logging.basicConfig(
                level=getattr(logging, log_level),
                format=log_format,
                handlers=[
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
        
        # Main logger for this agent
        self.logger = logging.getLogger('ModelManager')
        self.logger.setLevel(getattr(logging, log_level))
        # Sub-loggers for different subsystems
        self.vram_logger = logging.getLogger('vram')
        self.model_logger = logging.getLogger('model')
        self.quant_logger = logging.getLogger('quant')
        self.migrate_logger = logging.getLogger('migrate')
        for l in [self.vram_logger, self.model_logger, self.quant_logger, self.migrate_logger]:
            l.setLevel(getattr(logging, log_level))

    def _init_model_registry(self):
        """Initialize the model registry with PC2 services."""
        try:
            # Check if PC2 services are enabled in the agent's config
            enable_pc2_services = self.config.get('enable_pc2_services', False)
            
            if enable_pc2_services:
                # Load PC2 services using the centralized config module
                self.pc2_services = load_pc2_services()
                
                if self.pc2_services.get('enabled', False):
                    pc2_ip = self.pc2_services.get('ip', '192.168.100.17')
                    self.logger.info(f"PC2 services enabled, connecting to {pc2_ip}")
                    
                    # Get available services
                    available_services = list_available_services()
                    
                    # Register PC2 services in the model registry
                    for service_name, service_config in available_services.items():
                        port = service_config.get('port')
                        priority = service_config.get('priority', 'medium')
                        
                        if port:
                            service_id = f"pc2_{service_name}"
                            connection_str = get_service_connection(service_name)
                            
                            if connection_str:
                                self.models[service_id] = {
                                    'type': 'zmq_service',
                                    'zmq_address': connection_str,
                                    'priority': priority,
                                    'enabled': True,
                                    'estimated_vram_mb': 512  # Default VRAM estimate
                                }
                                self.logger.info(f"Registered PC2 service: {service_id} on {connection_str}")
                    
                    self.logger.info(f"Successfully loaded PC2 services configuration.")
                else:
                    self.logger.warning("PC2 services not enabled in pc2_services.yaml configuration")
            else:
                self.logger.info("PC2 services integration disabled in agent configuration")
                
        except Exception as e:
            self.logger.error(f"Error initializing model registry: {e}")
            self.logger.error(traceback.format_exc())

    def verify_pc2_services(self) -> Dict[str, bool]:
        """Verify health of all PC2 services and attempt recovery if needed."""
        service_status = {}
        
        try:
            # Check if PC2 services are enabled in the agent's config
            enable_pc2_services = self.config.get('enable_pc2_services', False)
            
            if not enable_pc2_services:
                self.logger.debug("PC2 services integration disabled in agent configuration")
                return service_status
                
            # Get PC2 services using the centralized config module
            pc2_config = self.pc2_services
            
            if not pc2_config or not pc2_config.get('enabled', False):
                self.logger.warning("PC2 services not enabled in pc2_services.yaml configuration")
                return service_status
                
            pc2_ip = pc2_config.get('ip', '192.168.100.17')
            
            # Create temporary socket for health checks
            health_socket = self.context.socket(zmq.REQ)
            health_socket.setsockopt(zmq.LINGER, 0)
            health_socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2 second timeout for health checks
            
            # Get available services
            available_services = list_available_services()
            
            for service_name, service_config in available_services.items():
                port = service_config.get('port')
                if not port:
                    continue
                    
                service_id = f"pc2_{service_name}"
                service_status[service_id] = False
                
                # Get connection string from the config module
                connection_str = get_service_connection(service_name)
                if not connection_str:
                    self.logger.warning(f"No connection string available for PC2 service {service_name}")
                    continue
                
                try:
                    # Connect to service
                    health_socket.connect(connection_str)
                    
                    # Send health check request
                    health_socket.send_json({"action": "health_check"})
                    
                    # Wait for response
                    if health_socket.poll(timeout=2000) > 0:
                        response = health_socket.recv_json()
                        if response.get("status") == "ok":
                            service_status[service_id] = True
                            self.logger.info(f"PC2 service {service_id} is healthy")
                        else:
                            self.logger.warning(f"PC2 service {service_id} returned unhealthy status")
                    else:
                        self.logger.warning(f"PC2 service {service_id} did not respond to health check")
                        
                except Exception as e:
                    self.logger.error(f"Error checking health of PC2 service {service_id}: {e}")
                    
                finally:
                    # Disconnect from service
                    try:
                        health_socket.disconnect(connection_str)
                    except:
                        pass
                        
            # Close health check socket
            health_socket.close()
            
            # Log overall status
            healthy_services = sum(1 for status in service_status.values() if status)
            total_services = len(service_status)
            self.logger.info(f"PC2 service health check complete: {healthy_services}/{total_services} services healthy")
            
        except Exception as e:
            self.logger.error(f"Error during PC2 service health verification: {e}")
            self.logger.error(traceback.format_exc())
            
        return service_status

    def _health_check_loop(self):
        """Enhanced health check loop with service verification."""
        while self.running:
            try:
                # Check local model health
                self.health_check_models(publish_update=True)
                
                # Verify PC2 services
                service_status = self.verify_pc2_services()
                
                # Update service status in model registry
                for service_id, is_healthy in service_status.items():
                    if service_id in self.models:
                        self.models[service_id]['healthy'] = is_healthy
                        
                # Publish health status
                self._publish_status_update()
                
                # Sleep until next check
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                self.logger.error(traceback.format_exc())
                time.sleep(5)  # Sleep before retrying

# --- PATCH: Attach standalone functions to ModelManagerAgent class (ensures methods are available before main is executed) ---
# --- END PATCH ---

# Main entry point
if __name__ == "__main__":
    try:
        # Create necessary directories
        Path("logs").mkdir(exist_ok=True)
        Path("cache").mkdir(exist_ok=True)
        
        # Parse command-line arguments
        from utils.config_parser import parse_agent_args
        args = parse_agent_args()
        port = getattr(args, 'port', 5570)
        
        # Initialize and run the agent
        logger.info(f"Starting ModelManagerAgent on port {port}")
        agent = ModelManagerAgent(port=port)
        agent.run()
        
    except KeyboardInterrupt:
        logger.info("ModelManagerAgent interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in ModelManagerAgent: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
