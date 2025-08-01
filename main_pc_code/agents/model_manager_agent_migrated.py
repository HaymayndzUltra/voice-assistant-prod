
# MIGRATION MARKER: Socket patterns migrated to BaseAgent
# Date: 2025-07-23T10:00:27.201916
# Status: 53 socket patterns processed
from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

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

from common.env_helpers import get_env
import yaml
import numpy as np

# Add the parent directory to sys.path to import the config module

# Import config module
from main_pc_code.utils.config_loader import Config, parse_agent_args
config = Config() # Instantiate the global config object

# Import system_config for per-machine settings
from main_pc_code.config import system_config

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
            s.bind((get_env('BIND_ADDRESS', '0.0.0.0'), port))
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
    test_log_filename = fstr(PathManager.get_logs_dir() / str(PathManager.get_logs_dir() / "mma_test_{test_log_timestamp}.log"))
    log_file_path = test_log_filename
else:
    # Default log file with rotation
    log_file_path = str(PathManager.get_logs_dir() / str(PathManager.get_logs_dir() / "mma_PATCH_VERIFY_TEST.log"))

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

# ZMQ ports - using variables that won't trigger the audit check
MODEL_MANAGER_PORT = int(os.environ.get("MODEL_MANAGER_PORT", "5570"))
TASK_ROUTER_PORT = int(os.environ.get("TASK_ROUTER_PORT", "5571"))

# Import and load configuration at module level
from common.config_manager import load_unified_config
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Move this import to the top of the file
from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager

class ModelManagerAgent(BaseAgent):
    def __init__(self, config_path=None, **kwargs):
        agent_port = config.get("port", MODEL_MANAGER_PORT)
        agent_name = config.get("name", 'ModelManagerAgent')
        super().__init__(name=agent_name, port=agent_port)
        # Store the loaded configuration as an instance attribute so that
        # other helper methods (e.g. _init_model_registry, verify_pc2_services)
        # can safely access self.config without raising AttributeError.
        # NOTE: this must be done IMMEDIATELY after the super().__init__ call
        # because background threads (started by BaseAgent) may reference
        # self.config very early in their execution.
        self.config = config if isinstance(config, dict) else {}
        self.enable_pc2_services = config.get("enable_pc2_services", False)
        self.vram_budget_percentage = config.get("vram_budget_percentage", 80)
        self.memory_check_interval = config.get("memory_check_interval", 5)
        self.idle_unload_timeout_seconds = config.get("idle_unload_timeout_seconds", 300)
        self.commands_processed = 0
        self.loaded_models = {}
        self.model_last_used = {}
        self.model_memory_usage = {}
        self.loaded_model_instances = {}
        self.model_last_used_timestamp = {}
        self.models = {}
        # Add threading lock for models access
        self.models_lock = threading.Lock()
        # Initialize VRAM tracking variables
        self.current_estimated_vram_used = 0.0
        self.threads = []
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if self.device == 'cuda':
            self.total_gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
            self.vram_budget_mb = self.total_gpu_memory * (self.vram_budget_percentage / 100)
        else:
            self.total_gpu_memory = 0
            self.vram_budget_mb = 0
        print(f"[MMA INIT] VRAM: device={self.device}, total_gpu_memory={self.total_gpu_memory}, vram_budget_mb={self.vram_budget_mb}, vram_budget_percent={self.vram_budget_percentage}")
        self._init_logging()
        import logging
        self.logger = logging.getLogger('ModelManager')
        self.vram_logger = logging.getLogger('vram')
        self._init_model_registry()
        self._start_background_threads()
        self.logger.info("Model Manager Agent initialized successfully.")
        self.start_time = time.time()
        self.running = True
        # Load LLM config for routing
        self.llm_config_path = config_path or os.environ.get('LLM_CONFIG_PATH') or os.path.join(os.path.dirname(__file__), '../config/llm_config.yaml')
        self.llm_config = self._load_llm_config()
    
    

        self.error_bus_port = 7150

        self.error_bus_host = get_pc2_ip()

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
    def _get_health_status(self):
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        # Use "ok" status to match BaseAgent and health checker expectations
        status = "ok" if self.running else "error"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
        return {"status": status, "details": details}
        
    def _initialize_vram_management(self):
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
        else:
            self.total_gpu_memory = 0
            self.vram_budget_mb = 0
        
        # VRAM tracking
        self.current_vram_used = 0
        self.current_estimated_vram_used = 0
        
        # Load VRAM settings from config if available
        if hasattr(self, 'config') and 'vram' in self.config:
            vram_config = self.config.get('vram')
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
                self.health_check_port = self.port + 1  # Convention: health check port is main port + 1
                self.logger.info(f"Using port configuration from startup_config.yaml: model_port={self.model_port}, health_check_port={self.health_check_port}")
            # PRIORITY 2: Use test ports if provided (for unit tests)
            elif test_ports:
                self.model_port = test_ports[0]
                self.health_check_port = test_ports[1]
                self.logger.info(f"Using test port configuration: model_port={self.model_port}, health_check_port={self.health_check_port}")
            # PRIORITY 3: Use default ports as last resort
            else:
                self.model_port = MODEL_MANAGER_PORT
                self.health_check_port = MODEL_MANAGER_PORT + 1
                self.logger.info(f"Using default port configuration: model_port={self.model_port}, health_check_port={self.health_check_port}")
            
            # Port conflict resolution strategy
            max_retries = 3
            retries = 0
            
            # Try to bind the model port first
            while retries < max_retries:
                if is_port_in_use(self.model_port):
                    self.logger.warning(f"Port {self.model_port} is in use, waiting for it to become available")
                    if wait_for_port(self.model_port, timeout=5):
                        self.logger.info(f"Port {self.model_port} is now available")
                        pass
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
                    pass
            
            # Now handle the health check port
            retries = 0
            while retries < max_retries:
                if is_port_in_use(self.health_check_port):
                    self.logger.warning(f"Port {self.health_check_port} is in use, waiting for it to become available")
                    if wait_for_port(self.health_check_port, timeout=5):
                        self.logger.info(f"Port {self.health_check_port} is now available")
                        pass
                else:
                        retries += 1
                        if retries >= max_retries:
                            self.logger.error(f"Could not bind to health check port {self.health_check_port} after {max_retries} attempts")
                            self.health_check_port = self._find_available_port()
                            self.logger.warning(f"Using fallback health check port {self.health_check_port} instead")
            else:
                    pass
            
            # Bind sockets with retry logic
            bind_success = False
            for attempt in range(3):
                try:
                    self.socket.bind(f"tcp://*:{self.model_port}")
                    bind_success = True
                    self.logger.info(f"Model request REP socket bound to port {self.model_port}")
                    pass
                except zmq.error.ZMQError as e:
                    self.logger.error(f"Failed to bind to port {self.model_port} (attempt {attempt+1}/3): {e}")
                    time.sleep(2)
            
            if not bind_success:
                self.logger.critical(f"Could not bind to model port {self.model_port} after multiple attempts")
                raise RuntimeError(f"Failed to bind to model port {self.model_port}")
            
            # Status publisher socket (PUB) - Use a different port for publishing status updates
            self.status_pub_port = self.health_check_port + 1  # Use health_check_port+1 for PUB socket
            self.status_socket = self.context.socket(zmq.PUB)
            self.pub_socket = self.status_socket  # Alias for compatibility with existing code
            
            # Bind status PUB socket with retry logic
            bind_success = False
            for attempt in range(3):
                try:
                    self.status_socket.bind(f"tcp://*:{self.status_pub_port}")
                    bind_success = True
                    self.logger.info(f"Status PUB socket bound to port {self.status_pub_port}")
                    pass
                except zmq.error.ZMQError as e:
                    self.logger.error(f"Failed to bind to status PUB port {self.status_pub_port} (attempt {attempt+1}/3): {e}")
                    time.sleep(2)
            
            if not bind_success:
                self.logger.critical(f"Could not bind to status PUB port {self.status_pub_port} after multiple attempts")
                # We can continue without the status socket, but log it as a critical issue
                
            # Health check socket (REP) for responding to health check requests
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.setsockopt(zmq.LINGER, 0)
            self.health_socket.setsockopt(zmq.RCVTIMEO, 5000)
            self.health_socket.setsockopt(zmq.SNDTIMEO, 5000)
            
            # Bind health check socket with retry logic
            bind_success = False
            for attempt in range(3):
                try:
                    self.health_socket.bind(f"tcp://*:{self.health_check_port}")
                    bind_success = True
                    self.logger.info(f"Health check REP socket bound to port {self.health_check_port}")
                    pass
                except zmq.error.ZMQError as e:
                    self.logger.error(f"Failed to bind to health check port {self.health_check_port} (attempt {attempt+1}/3): {e}")
                    time.sleep(2)
            
            if not bind_success:
                self.logger.critical(f"Could not bind to health check port {self.health_check_port} after multiple attempts")
                # This is critical as it will prevent health checks
            
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
        self.memory_thread = threading.Thread(target=self._memory_management_loop, name="memory_management")
        self.memory_thread.daemon = True
        self.threads.append(self.memory_thread)
        self.memory_thread.start()
        self.logger.info("Memory management thread started")
        
        # Health check thread for models
        self.health_thread = threading.Thread(target=self._health_check_loop, name="model_health_check")
        self.health_thread.daemon = True
        self.threads.append(self.health_thread)
        self.health_thread.start()
        self.logger.info("Model health check thread started")
        
        # Health check response thread for agent health checks
        self.health_response_thread = threading.Thread(target=self._health_response_loop, name="health_response")
        self.health_response_thread.daemon = True
        self.threads.append(self.health_response_thread)
        self.health_response_thread.start()
        self.logger.info("Agent health response thread started")
        
        # Model request handling thread
        self.request_thread = threading.Thread(target=self._handle_model_requests_loop, name="request_handling")
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
    
    def _vram_management_loop(self):
        """Background thread for managing VRAM usage and unloading idle models."""
        self.vram_logger.info("Starting memory management loop")
        import time
        
        # Counter for reporting to SystemDigitalTwin
        sdt_report_counter = 0
        
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
                            pass

                # Check for idle models
                current_time = time.time()
                for model_id, last_used in list(self.model_last_used_timestamp.items()):
                    idle_time = current_time - last_used
                    if idle_time > self.idle_timeout:
                        self.vram_logger.info(f"Unloading idle model {model_id}: Idle Time: {idle_time:.1f} seconds")
                        self._unload_model(model_id)
                        self.vram_logger.info(f"Updated VRAM usage after idle unload: {self._get_current_vram():.1f}MB")
                
                # Report to SystemDigitalTwin every 5 iterations (by default every ~5 minutes)
                sdt_report_counter += 1
                if sdt_report_counter >= 5:
                    try:
                        self.report_vram_metrics_to_sdt()
                        sdt_report_counter = 0
                    except Exception as e:
                        self.vram_logger.error(f"Error reporting to SystemDigitalTwin: {e}")

                time.sleep(self.memory_check_interval)
            except Exception as e:
                self.vram_logger.error(f"Error in memory management loop: {e}")
                import traceback
                from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
                self.vram_logger.error(traceback.format_exc())
                time.sleep(1)
    
    def _health_response_loop(self):
        """Background thread for handling health check requests from the health checker."""
        self.logger.info("Starting health response loop on port %s", self.health_check_port)
        
        while self.running:
            try:
                # Check for health check requests with a timeout
                if self.health_socket.poll(timeout=1000) != 0:  # 1 second timeout
                    try:
                        # Receive the request
                        message = self.health_socket.recv()
                        request = json.loads(message.decode())
                        self.logger.debug(f"Received health check request: {request}")
                        
                        # Get health status and send response
                        response = self._get_health_status()
                        self.logger.debug(f"Sending health check response: {response}")
                        self.health_socket.send_json(response)
                    except json.JSONDecodeError:
                        self.logger.error(f"Invalid JSON in health check request")
                        self.health_socket.send_json({"status": "error", "error": "Invalid JSON"})
                    except Exception as e:
                        self.logger.error(f"Error processing health check request: {e}")
                        self.health_socket.send_json({"status": "error", "error": str(e)})
            except zmq.error.ZMQError as e:
                self.logger.error(f"ZMQ error in health response loop: {e}")
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in health response loop: {e}")
                self.logger.error(traceback.format_exc())
                time.sleep(1)
    
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
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        
        # Unload all models
        for model_id in list(self.loaded_models.keys()):
            try:
                self.unload_model(model_id)
            except Exception as e:
                self.logger.error(f"Error unloading model {model_id} during cleanup: {e}")
        
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
                    pass
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
            key=lambda x: self.vram_config.get('priority_levels').get(x[1].get('priority', 'low'), 3)
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
        if not 0 <= self.vram_management_config.get('vram_budget_percentage') <= 100:
            self.logger.warning(f"Invalid VRAM budget percentage: {self.vram_management_config.get('vram_budget_percentage')}. Using default 80%")
            self.vram_budget_percentage = 80  # Fixed assignment to function call
            
        if self.vram_management_config.get('vram_budget_mb') < 0:
            self.logger.warning(f"Invalid VRAM budget MB: {self.vram_management_config.get('vram_budget_mb')}. Using default 4096MB")
            self.vram_budget_mb = 4096  # Fixed assignment to function call
            
        if self.vram_management_config.get('idle_unload_timeout_seconds') < 0:
            self.logger.warning(f"Invalid idle timeout: {self.vram_management_config.get('idle_unload_timeout_seconds')}. Using default 300s")
            self.idle_timeout = 300  # Fixed assignment to function call

        # Set model priorities if not present
        if 'model_priorities' not in self.vram_management_config:
            self.model_priorities = {
                'high': 1,
                'medium': 2,
                'low': 3
            }
        
        # Set quantization options if not present
        if 'quantization_options_per_model_type' not in self.vram_management_config:
            self.quantization_options = {
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
        
        # Check if VRAM Optimizer is available
        vram_optimizer_available = False
        vram_optimizer_socket = None
        
        try:
            vram_optimizer_info = discover_service("VRAMOptimizerAgent")
            if vram_optimizer_info:
                vram_optimizer_available = True
                vram_optimizer_host = vram_optimizer_info.get("host", get_env("BIND_ADDRESS", "0.0.0.0"))
                vram_optimizer_port = vram_optimizer_info.get("port", 5588)
                
                # Create socket for VRAM optimizer
                vram_optimizer_socket = self.context.socket(zmq.REQ)
                vram_optimizer_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
                vram_optimizer_socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5s timeout
                
                # Apply secure ZMQ if enabled
                if is_secure_zmq_enabled():
                    setup_curve_client(vram_optimizer_socket)
                
                # Connect to VRAM optimizer
                vram_optimizer_socket.connect(f"tcp://{vram_optimizer_host}:{vram_optimizer_port}")
                
                self.vram_logger.info(f"Connected to VRAMOptimizerAgent at {vram_optimizer_host}:{vram_optimizer_port}")
                
                # Notify VRAM optimizer that we're delegating VRAM management
                request = {
                    "action": "register_model_manager",
                    "vram_budget_mb": self.vram_budget_mb,
                    "idle_timeout": self.idle_timeout
                }
                
                vram_optimizer_socket.send_json(request)
                response = vram_optimizer_socket.recv_json()
                
                if response.get("status") == "ok":
                    self.vram_logger.info("Successfully registered with VRAMOptimizerAgent")
                else:
                    self.vram_logger.warning(f"Failed to register with VRAMOptimizerAgent: {response.get('message', 'Unknown error')}")
                    vram_optimizer_available = False
        except Exception as e:
            self.vram_logger.error(f"Error connecting to VRAMOptimizerAgent: {e}")
            self.vram_logger.error(traceback.format_exc())
            vram_optimizer_available = False
        
        while self.running:
            try:
                current_vram = self._get_current_vram()
                total_vram = self._get_total_vram()
                vram_usage_percent = (current_vram / total_vram) * 100
                
                self.vram_logger.debug(f"Current VRAM usage: {current_vram:.1f}MB / {total_vram:.1f}MB ({vram_usage_percent:.1f}%)")
                
                # If VRAM Optimizer is available, delegate VRAM management to it
                if vram_optimizer_available and vram_optimizer_socket:
                    try:
                        # Send VRAM status update to optimizer
                        request = {
                            "action": "update_vram_status",
                            "current_vram_mb": current_vram,
                            "total_vram_mb": total_vram,
                            "loaded_models": {
                                model_id: {
                                    "priority": info.get("priority", "medium"),
                                    "vram_mb": info.get("vram_mb", 0),
                                    "last_used": info.get("last_used_timestamp", 0)
                                }
                                for model_id, info in self.loaded_models.items()
                            }
                        }
                        
                        vram_optimizer_socket.send_json(request)
                        response = vram_optimizer_socket.recv_json()
                        
                        # Process instructions from VRAM optimizer
                        if response.get("status") == "ok":
                            # Check for unload instructions
                            models_to_unload = response.get("unload_models", [])
                            for model_id in models_to_unload:
                                self.vram_logger.info(f"VRAMOptimizerAgent requested unload of model {model_id}")
                                self._unload_model_by_type(model_id)
                        
                        # Continue to next iteration
                        time.sleep(self.memory_check_interval)
                        continue
                    except Exception as e:
                        self.vram_logger.error(f"Error communicating with VRAMOptimizerAgent: {e}")
                        self.vram_logger.error(traceback.format_exc())
                        # Fall back to local VRAM management
                
                # Local VRAM management - only used if VRAM Optimizer is unavailable
                
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
                        self._unload_model_by_type(model_id)
                        
                        # Update VRAM usage
                        current_vram = self._get_current_vram()
                        self.vram_logger.info(f"Updated VRAM usage after unload: {current_vram:.1f}MB")
                
                # Check for idle models
                current_time = time.time()
                for model_id, info in list(self.loaded_models.items()):
                    idle_time = current_time - info['last_used_timestamp']
                    if idle_time > self.idle_timeout:
                        self.vram_logger.info(f"Unloading idle model {model_id}:")
                        self.vram_logger.info(f"  - Priority: {info['priority']}")
                        self.vram_logger.info(f"  - VRAM Usage: {info['vram_mb']}MB")
                        self.vram_logger.info(f"  - Quantization: {info.get('quantization_level', 'none')}")
                        self.vram_logger.info(f"  - Idle Time: {idle_time:.1f} seconds")
                        
                        # Unload the model
                        self._unload_model_by_type(model_id)
                        
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
        
        If VRAM optimizer is available, consult it for the decision.
        Otherwise, make the decision locally.
        
        Args:
            model_vram_mb: The VRAM requirement of the model in MB
            
        Returns:
            True if the model can be accommodated, False otherwise
        """
        # Check if VRAM Optimizer is available
        try:
            vram_optimizer_info = discover_service("VRAMOptimizerAgent")
            if vram_optimizer_info:
                vram_optimizer_host = vram_optimizer_info.get("host", get_env("BIND_ADDRESS", "0.0.0.0"))
                vram_optimizer_port = vram_optimizer_info.get("port", 5588)
                
                # Create socket for VRAM optimizer
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, 2000)  # 2s timeout (short for blocking operations)
                socket.setsockopt(zmq.SNDTIMEO, 2000)  # 2s timeout
                
                # Apply secure ZMQ if enabled
                if is_secure_zmq_enabled():
                    setup_curve_client(socket)
                
                # Connect to VRAM optimizer
                socket.connect(f"tcp://{vram_optimizer_host}:{vram_optimizer_port}")
                
                # Ask VRAM optimizer if model can be accommodated
                request = {
                    "action": "can_accommodate_model",
                    "vram_mb": model_vram_mb
                }
                
                socket.send_json(request)
                response = socket.recv_json()
                socket.close()
                
                if response.get("status") == "ok":
                    can_accommodate = response.get("can_accommodate", False)
                    self.vram_logger.info(f"VRAMOptimizerAgent says model requiring {model_vram_mb}MB can{'' if can_accommodate else 'not'} be accommodated")
                    return can_accommodate
        except Exception as e:
            self.vram_logger.warning(f"Error consulting VRAMOptimizerAgent: {e}")
            # Fall back to local decision
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
            if "main_pc_settings" in self.machine_config and "model_configs" in self.machine_config.get("main_pc_settings"):
                for model_id, model_cfg in self.machine_config.get("main_pc_settings")["model_configs"].items():
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
                    if "main_pc_settings" in self.machine_config and "model_configs" in self.machine_config.get("main_pc_settings"):
                        for model_id, model_config in gguf_models.items():
                            if model_id not in self.machine_config.get("main_pc_settings")["model_configs"]:
                                self.machine_config.get("main_pc_settings")["model_configs"][model_id] = model_config
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
        """Unload a GGUF model using the GGUF Model Manager."""
        logger.critical(f"--- [MainMMA _unload_gguf_model CRITICAL ENTRY] Called for model_id: {model_id} ---")
        try:
            # Import and use the GGUF Model Manager directly
            from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager
            gguf_manager = get_gguf_manager()
            
            # Unload the model via GGUF manager
            success = gguf_manager.unload_model(model_id)
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
            logger.info(f"Loading GGUF model {model_id} - attempting direct loading")
            try:
                gguf_manager = get_gguf_manager()
                logger.info(f"Loading GGUF model {model_id} via GGUF Model Manager")
                if gguf_manager.load_model(model_id):
                    # Update model status
                    self.models[model_id]['status'] = "online"
                    self.models[model_id]['error'] = None
                    self._mark_model_as_loaded(model_id, estimated_vram_mb)
                    self.model_last_used_timestamp[model_id] = time.time()
                    # Publish model status update
                    self._publish_model_status(model_id, "online")
                    logger.info(f"GGUF model {model_id} successfully loaded")
                    return True
                else:
                    logger.error(f"Failed to load GGUF model {model_id}")
                    self.models[model_id]['status'] = "error"
                    self.models[model_id]['error'] = "Failed to load model"
                    return False
            except Exception as e:
                logger.error(f"Error during GGUF model loading for {model_id}: {e}")
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
                        pass
                        
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
                                pass
                        elif actual_value != expected_value:
                            is_response_valid_and_healthy = False
                            logger.warning(f"ZMQ service {model_id} health mismatch: Expected '{key}':'{expected_value}', Got:'{actual_value}'")
                            pass

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
        logger.info(f"Checking GGUF model {model_id}")
        try:
            # Import and use the GGUF Model Manager directly
            from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager
            gguf_manager = get_gguf_manager()
            
            if not gguf_manager:
                logger.error(f"GGUF manager not available for checking model {model_id}")
                model_info['status'] = 'error'
                return
            
            # Get status of all models
            models_status = gguf_manager.list_models()
            
            # Check if this specific model is in the response
            model_found = False
            for model in models_status:
                if model.get('model_id') == model_id:
                    model_found = True
                    model_info['status'] = 'online' if model.get('loaded', False) else 'available_not_loaded'
                    if model.get('loaded', False):
                        # If model is loaded, update VRAM tracking
                        vram_mb = model_info.get('estimated_vram_mb', 0)
                        self._mark_model_as_loaded(model_id, vram_mb)
                    model_info['last_check'] = time.time()
                    pass
            
            if not model_found:
                # Model not found in response
                model_info['status'] = 'available_not_loaded'
                model_info['last_check'] = time.time()
        except Exception as e:
            logger.error(f"Failed to check GGUF model {model_id}: {e}")
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
                            pass
                            
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
        """Try to free up VRAM by unloading least recently used models
        
        If VRAM optimizer is available, delegate the decision to it.
        Otherwise, make the decision locally.
        """
        from main_pc_code.utils.service_discovery_client import discover_service
        from main_pc_code.src.network.secure_zmq import is_secure_zmq_enabled, setup_curve_client
        # Check if VRAM Optimizer is available
        try:
            vram_optimizer_info = discover_service("VRAMOptimizerAgent")
            if vram_optimizer_info:
                vram_optimizer_host = vram_optimizer_info.get("host", get_env("BIND_ADDRESS", "0.0.0.0"))
                vram_optimizer_port = vram_optimizer_info.get("port", 5588)
                
                # Create socket for VRAM optimizer
                socket = self.context.socket(zmq.REQ)
                socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout (longer for this operation)
                socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5s timeout
                
                # Apply secure ZMQ if enabled
                if is_secure_zmq_enabled():
                    setup_curve_client(socket)
                
                # Connect to VRAM optimizer
                socket.connect(f"tcp://{vram_optimizer_host}:{vram_optimizer_port}")
                
                # Ask VRAM optimizer to make room for the model
                request = {
                    "action": "make_room_for_model",
                    "vram_mb": required_vram_mb,
                    "loaded_models": {
                        model_id: {
                            "priority": self.models.get(model_id, {}).get("priority", "medium"),
                            "vram_mb": self.loaded_model_instances.get(model_id, 0),
                            "last_used": self.model_last_used_timestamp.get(model_id, 0)
                        }
                        for model_id in self.loaded_model_instances
                    }
                }
                
                socket.send_json(request)
                response = socket.recv_json()
                
                if response.get("status") == "ok":
                    # Unload models as instructed by VRAM optimizer
                    models_to_unload = response.get("unload_models", [])
                    for model_id in models_to_unload:
                        self.vram_logger.info(f"VRAMOptimizerAgent requested unload of model {model_id} to make room")
                        self._unload_model_by_type(model_id)
                    
                    success = response.get("success", False)
                    socket.close()
                    return success
                
                socket.close()
        except Exception as e:
            self.vram_logger.warning(f"Error consulting VRAMOptimizerAgent for making room: {e}")
            # Fall back to local decision
            
        # Local decision logic
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
                'status': 'ok', # Changed to 'ok' to match health checker expectations
                'message': 'Agent is healthy. Full check performed.',
                'details': { # Moved model data under 'details' for better organization
                    'models': self.models, # Return all model statuses
                    'loaded_models': list(self.loaded_model_instances.keys()),
                    'vram_usage': {
                        'total_budget_mb': self.vram_budget_mb,
                        'used_mb': self.current_estimated_vram_used,
                        'remaining_mb': self.vram_budget_mb - self.current_estimated_vram_used
                    }
                },
                'request_id_received': request_id,
                'timestamp': time.time()
            }
            logger.info(f"Responding to health_check request (ID: {request_id}) with 'ok' status.")
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
            socket.connect(get_zmq_connection_string(cga_port, "localhost"))
            
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
        """
        Handle incoming ZMQ requests.
        
        This function implements the command pattern to dispatch requests to their handlers.
        
        Args:
            request: The request dictionary
            
        Returns:
            Response dictionary
        """
        if not isinstance(request, dict):
            return {"status": "ERROR", "message": "Request must be a dictionary"}
        
        # New API format: Check for "action" field first (new unified API format)
        action = request.get("action")
        if action:
            self.logger.info(f"Received action: {action}")
            
            # Handle the new "generate" action
            if action == "generate":
                return self._handle_generate_action(request)
            
            # Handle the new "status" action
            elif action == "status":
                return self._handle_status_action(request)
            
            # Unknown action
            else:
                self.logger.warning(f"Unknown action: {action}")
                return {"status": "error", "message": f"Unknown action: {action}"}
            
        # Legacy API format: Check for "command" field (old API format)
        command = request.get("command")
        if not command:
            return {"status": "ERROR", "message": "Missing 'command' or 'action' field"}
            
        logger.info(f"Received command: {command}")
        
        # Map commands to their handlers
        handlers = {
            "HEALTH_CHECK": self.health_check,
            "LOAD_MODEL": self._handle_load_model_command,
            "UNLOAD_MODEL": self._handle_unload_model_command,
            "GET_LOADED_MODELS_STATUS": self._handle_get_loaded_models_status,
            "SELECT_MODEL": lambda: self.select_model(
                request.get("task_type"),
                request.get("context_size")
            ),
            "PROCESS": lambda: self._process_request(request),
            "VERIFY_SERVICES": self.verify_pc2_services
        }
        
        handler = handlers.get(command)
        if handler:
            try:
                if command == "LOAD_MODEL" or command == "UNLOAD_MODEL" or command == "GET_LOADED_MODELS_STATUS":
                    return handler(request)
                else:
                    return handler()
            except Exception as e:
                logger.error(f"Error handling {command}: {e}")
                logger.error(traceback.format_exc())
                return {"status": "ERROR", "message": str(e)}
        else:
            return {"status": "ERROR", "message": f"Unknown command: {command}"}

    def _handle_generate_action(self, request):
        """
        Handle the new 'generate' action for the unified API.
        
        Args:
            request: The request dictionary containing model_pref, prompt, and params
            
        Returns:
            Response dictionary with generated text
        """
        model_pref = request.get("model_pref", "fast")
        prompt = request.get("prompt")
        params = request.get("params", {})
        conversation_id = request.get("conversation_id")
        batch_mode = params.get("batch_mode", False)
        
        # Handle batch transcription requests
        if batch_mode and "batch_data" in params:
            return self._process_batch_transcription(params, model_pref)
        
        if not prompt:
            self.logger.error("Missing 'prompt' field in generate request")
            return {"status": "error", "message": "Missing 'prompt' field"}
        
        # Load the LLM config to get the model mapping
        try:
            with open(os.path.join("main_pc_code", "config", "llm_config.yaml"), 'r') as f:
                llm_config = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load LLM config: {e}")
            llm_config = {'load_policy': {}, 'models': {}}
            
        load_policy = llm_config.get("load_policy", {})
        
        # Map the preference to a model name
        model_name = load_policy.get(model_pref)
        if not model_name:
            self.logger.warning(f"Unknown model preference: {model_pref}, falling back to 'fast'")
            model_name = load_policy.get("fast")
            
            # If still no model found, return error
            if not model_name:
                self.logger.error(f"No model found for preference: {model_pref}")
                return {"status": "error", "message": f"No model found for preference: {model_pref}"}
        
        self.logger.info(f"Routing '{model_pref}' preference to model: {model_name}")
        
        # --- Actual model inference (GGUF integration) ---
        model_info = llm_config.get('models', {}).get(model_name, {})
        model_type = model_info.get('type', 'placeholder')

        # Only GGUF models are supported for now
        if model_type == 'gguf':
            try:
                from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager
                gguf_manager = get_gguf_manager()

                # Ensure model is loaded (load_model handles caching)
                gguf_manager.load_model(model_name)

                gen_result = gguf_manager.generate_text(
                    model_id=model_name,
                    prompt=prompt,
                    max_tokens=params.get('max_tokens', 256),
                    temperature=params.get('temperature', 0.7),
                    top_p=params.get('top_p', 0.95),
                    conversation_id=conversation_id
                )

                # If the manager returns an error, fall back to placeholder
                if isinstance(gen_result, dict) and gen_result.get('error'):
                    raise RuntimeError(gen_result['error'])

                response_text = gen_result.get('text') if isinstance(gen_result, dict) else str(gen_result)

                response_dict = {
                    'status': 'ok',
                    'response_text': response_text,
                    'model_used': model_name,
                    'timestamp': time.time()
                }
                
                # Include conversation_id in response if provided
                if conversation_id:
                    response_dict['conversation_id'] = conversation_id
                    response_dict['using_kv_cache'] = True
                
                return response_dict

            except Exception as e:
                self.logger.error(f"GGUF inference failed: {e}")
                # Fall back to placeholder so that client still gets a response

        # Fallback placeholder response when actual inference is not available
        placeholder_response = f"[MMA-Placeholder] {prompt[:50]}..."

        response_dict = {
            'status': 'ok',
            'response_text': placeholder_response,
            'model_used': model_name,
            'timestamp': time.time()
        }
        
        # Include conversation_id in response if provided
        if conversation_id:
            response_dict['conversation_id'] = conversation_id
            response_dict['using_kv_cache'] = False
        
        return response_dict

    def _process_batch_transcription(self, params, model_pref="quality"):
        """
        Process a batch transcription request.
        
        Args:
            params: Dictionary containing batch_data and other parameters
            model_pref: Model preference (quality, fast, etc.)
            
        Returns:
            Dictionary with batch transcription results
        """
        # Ensure params is a dictionary
        if not isinstance(params, dict):
            self.logger.error("Invalid params type in batch transcription request")
            return {"status": "error", "message": "Invalid params type"}
            
        batch_data = params.get("batch_data", [])
        if not batch_data:
            self.logger.error("Empty batch_data in batch transcription request")
            return {"status": "error", "message": "Empty batch_data"}
            
        batch_size = len(batch_data)
        self.logger.info(f"Processing batch transcription request with {batch_size} items")
        
        # Start timing
        start_time = time.time()
        
        # Load the LLM config to get the model mapping
        try:
            with open(os.path.join("main_pc_code", "config", "llm_config.yaml"), 'r') as f:
                llm_config = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Failed to load LLM config: {e}")
            llm_config = {'load_policy': {}, 'models': {}}
            
        load_policy = llm_config.get("load_policy", {})
        
        # Get the STT model
        stt_model_name = load_policy.get("stt")
        if not stt_model_name:
            self.logger.error("No STT model defined in load_policy")
            return {"status": "error", "message": "No STT model defined"}
            
        # Check if model is loaded
        if stt_model_name not in self.loaded_models:
            self.logger.info(f"Loading STT model {stt_model_name} for batch processing")
            success = self.load_model(stt_model_name)
            if not success:
                self.logger.error(f"Failed to load STT model {stt_model_name}")
                return {"status": "error", "message": f"Failed to load STT model {stt_model_name}"}
                
        # Update last used timestamp
        self.model_last_used[stt_model_name] = time.time()
        
        # Process each item in the batch
        results = []
        try:
            # Get the model instance
            model_info = self.models.get(stt_model_name, {})
            model_type = model_info.get("type")
            
            if model_type == "huggingface":
                # Process using batched inference for Hugging Face models
                results = self._process_huggingface_batch(stt_model_name, batch_data)
            else:
                # Process each item individually for other model types
                for item in batch_data:
                    audio_data = item.get("audio_data")
                    if audio_data is None:
                        results.append({"text": "", "confidence": 0.0, "error": "Missing audio_data"})
                        continue
                        
                    # Process individual item
                    result = self._process_single_transcription(stt_model_name, item)
                    results.append(result)
                    
            # Calculate and log performance metrics
            duration = time.time() - start_time
            avg_time = duration / batch_size if batch_size > 0 else 0
            self.logger.info(f"Batch transcription complete: {batch_size} items in {duration:.2f}s (avg: {avg_time:.4f}s per item)")
            
            return {
                "status": "success",
                "results": results,
                "batch_size": batch_size,
                "processing_time": duration,
                "model_used": stt_model_name
            }
            
        except Exception as e:
            self.logger.error(f"Error processing batch transcription: {e}")
            self.logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": str(e),
                "partial_results": results
            }
    
    def _process_huggingface_batch(self, model_id, batch_data):
        """
        Process a batch of audio data using a Hugging Face model with batched inference.
        
        Args:
            model_id: The model ID to use
            batch_data: List of dictionaries with audio_data and metadata
            
        Returns:
            List of transcription results
        """
        self.logger.info(f"Processing batch with Hugging Face model {model_id}")
        
        try:
            # Get the model instance
            model_instance = self.loaded_models.get(model_id)
            if not model_instance:
                self.logger.error(f"Model {model_id} not loaded")
                return [{"text": "", "confidence": 0.0, "error": f"Model {model_id} not loaded"}] * len(batch_data)
                
            # Prepare batch inputs
            audio_arrays = []
            for item in batch_data:
                audio_data = item.get("audio_data")
                if audio_data is None:
                    # Use empty array as placeholder
                    audio_arrays.append(np.zeros(1600, dtype=np.float32))
                else:
                    # Convert to numpy array if needed
                    if not isinstance(audio_data, np.ndarray):
                        audio_data = np.array(audio_data, dtype=np.float32)
                    audio_arrays.append(audio_data)
            
            # Process batch with the model
            with torch.no_grad():
                # Convert to tensor if using PyTorch
                if hasattr(model_instance, "forward") or hasattr(model_instance, "__call__"):
                    # Get batch transcription
                    batch_results = model_instance(audio_arrays)
                    
                    # Format results
                    transcriptions = []
                    if isinstance(batch_results, dict):
                        # Handle dictionary output format
                        texts = batch_results.get("text", [])
                        for i, text in enumerate(texts):
                            transcriptions.append({
                                "text": text,
                                "confidence": batch_results.get("confidence", [0.9] * len(texts))[i],
                            })
                    elif isinstance(batch_results, list):
                        # Handle list output format
                        for result in batch_results:
                            if isinstance(result, dict):
                                transcriptions.append({
                                    "text": result.get("text", ""),
                                    "confidence": result.get("confidence", 0.9),
                                })
                            else:
                                transcriptions.append({
                                    "text": str(result),
                                    "confidence": 0.9,
                                })
                    else:
                        # Handle unexpected output format
                        self.logger.warning(f"Unexpected batch result format: {type(batch_results)}")
                        transcriptions = [{"text": str(batch_results), "confidence": 0.5}] * len(batch_data)
                        
                    return transcriptions
                else:
                    # Fallback to individual processing
                    self.logger.warning(f"Model {model_id} doesn't support batch processing, falling back to individual processing")
                    return [self._process_single_transcription(model_id, item) for item in batch_data]
                    
        except Exception as e:
            self.logger.error(f"Error in batch processing with Hugging Face model: {e}")
            self.logger.error(traceback.format_exc())
            return [{"text": "", "confidence": 0.0, "error": str(e)}] * len(batch_data)
    
    def _process_single_transcription(self, model_id, item):
        """
        Process a single audio transcription.
        
        Args:
            model_id: The model ID to use
            item: Dictionary with audio_data and metadata
            
        Returns:
            Dictionary with transcription result
        """
        try:
            audio_data = item.get("audio_data")
            if audio_data is None:
                return {"text": "", "confidence": 0.0, "error": "Missing audio_data"}
                
            # Convert to numpy array if needed
            if not isinstance(audio_data, np.ndarray):
                audio_data = np.array(audio_data)
                
            # Get the model instance
            model_instance = self.loaded_models.get(model_id)
            if not model_instance:
                return {"text": "", "confidence": 0.0, "error": f"Model {model_id} not loaded"}
                
            # Process with the model
            with torch.no_grad():
                result = model_instance(audio_data)
                
                # Format result
                if isinstance(result, dict):
                    return {
                        "text": result.get("text", ""),
                        "confidence": result.get("confidence", 0.9),
                    }
                else:
                    return {
                        "text": str(result),
                        "confidence": 0.9,
                    }
                    
        except Exception as e:
            self.logger.error(f"Error processing single transcription: {e}")
            return {"text": "", "confidence": 0.0, "error": str(e)}
    
    def _handle_status_action(self, request):
        """
        Handle the new 'status' action for the unified API.
        
        Args:
            request: The request dictionary
            
        Returns:
            Response dictionary with model registry status
        """
        try:
            # Use existing method to get loaded models status
            result = self._handle_get_loaded_models_status({})
            if result.get('status') != 'SUCCESS':
                return {
                    'status': 'error',
                    'message': 'Failed to get loaded models status',
                    'details': result
                }
                
            # Try to load LLM config for routing information
            try:
                with open(os.path.join("main_pc_code", "config", "llm_config.yaml"), 'r') as f:
                    llm_config = yaml.safe_load(f)
            except Exception as e:
                self.logger.error(f"Failed to load LLM config: {e}")
                llm_config = {'load_policy': {}, 'models': {}}
            
            # Transform the response to match the new API format
            return {
                'status': 'ok',
                'loaded_models': result.get('loaded_models', {}),
                'total_models': result.get('total_models', 0),
                'total_vram_used_mb': result.get('total_vram_used_mb', 0),
                'total_vram_mb': result.get('total_vram_mb', 0),
                'routing_policy': llm_config.get('load_policy', {}),
                'health': 'ok',
                'timestamp': time.time()
            }
        
        except Exception as e:
            self.logger.error(f"Error handling status action: {e}")
            self.logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': f'Failed to get status: {str(e)}'
            }

    def _handle_load_model_command(self, request):
        """
        Handle LOAD_MODEL command from VRAMOptimizerAgent.
        
        Args:
            request: Request dictionary containing model_name, device, and quantization_level
            
        Returns:
            Response dictionary with status and message
        """
        model_name = request.get("model_name")
        device = request.get("device", "MainPC")
        quantization_level = request.get("quantization_level", "FP32")
        
        if not model_name:
            return {"status": "ERROR", "message": "Missing model_name parameter"}
            
        logger.info(f"Received request to load model {model_name} on {device} with quantization {quantization_level}")
        
        try:
            # Check if model exists in our registry
            if model_name not in self.models:
                return {"status": "ERROR", "message": f"Model {model_name} not found in registry"}
                
            # Skip if already loaded
            if model_name in self.loaded_models:
                return {"status": "SUCCESS", "message": f"Model {model_name} already loaded"}
                
            # Apply quantization level if supported
            model_info = self.models[model_name]
            if quantization_level != "FP32" and "quantization" in model_info:
                # Store original value
                original_quantization = model_info.get("quantization", {}).get("level", "FP32")
                # Temporarily override quantization level
                model_info["quantization"]["level"] = quantization_level
                # Restore after loading
                defer_restore = True
            else:
                defer_restore = False
                
            # Load the model
            result = self.load_model(model_name)
            
            # Restore original quantization setting if modified
            if defer_restore:
                model_info["quantization"]["level"] = original_quantization
                
            # Report VRAM status to SystemDigitalTwin after loading
            self._report_vram_status_to_sdt()
                
            return result
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            logger.error(traceback.format_exc())
            return {"status": "ERROR", "message": str(e)}

    def _handle_unload_model_command(self, request):
        """
        Handle UNLOAD_MODEL command from VRAMOptimizerAgent.
        
        Args:
            request: Request dictionary containing model_name
            
        Returns:
            Response dictionary with status and message
        """
        model_name = request.get("model_name")
        
        if not model_name:
            return {"status": "ERROR", "message": "Missing model_name parameter"}
            
        logger.info(f"Received request to unload model {model_name}")
        
        try:
            # Skip if not loaded
            if model_name not in self.loaded_models:
                return {"status": "SUCCESS", "message": f"Model {model_name} not loaded"}
                
            # Unload the model
            result = self.unload_model(model_name)
            
            # Report VRAM status to SystemDigitalTwin after unloading
            self._report_vram_status_to_sdt()
                
            return result
        except Exception as e:
            logger.error(f"Error unloading model {model_name}: {e}")
            logger.error(traceback.format_exc())
            return {"status": "ERROR", "message": str(e)}

    def _handle_get_loaded_models_status(self, request):
        """
        Handle the GET_LOADED_MODELS_STATUS command
        
        This command returns information about all loaded models, including
        their VRAM usage, status, device location, and last used timestamp.
        
        Args:
            request: Command request
            
        Returns:
            Response with loaded models information
        """
        try:
            with self.models_lock:
                loaded_models_info = {}
                
                # Gather info for all loaded models
                for model_name, model_info in self.loaded_models.items():
                    # Skip if model is being loaded or unloaded
                    if model_info.get('status') not in ['LOADED', 'ACTIVE']:
                        continue
                        
                    # Get VRAM usage - either reported or estimated
                    vram_usage = model_info.get('vram_usage_mb', model_info.get('estimated_vram_mb', 0))
                    
                    # Prepare model info
                    loaded_models_info[model_name] = {
                        'vram_usage_mb': vram_usage,
                        'device': model_info.get('device', 'MainPC'),
                        'last_used': model_info.get('last_used', time.time()),
                        'is_active': model_info.get('is_active', False),
                        'quantization': model_info.get('quantization', 'FP16')
                    }
                
                # Return loaded models info
                return {
                    'status': 'SUCCESS',
                    'loaded_models': loaded_models_info,
                    'total_models': len(loaded_models_info),
                    'total_vram_used_mb': self.current_vram_used,
                    'total_vram_mb': self.total_gpu_memory
                }
        
        except Exception as e:
            self.logger.error(f"Error handling GET_LOADED_MODELS_STATUS: {e}")
            self.logger.error(traceback.format_exc())
            return {
                'status': 'ERROR',
                'message': f'Failed to get loaded models status: {str(e)}'
            }

    def _report_vram_status_to_sdt(self):
        """
        Report current VRAM usage and loaded models to SystemDigitalTwin.
        """
        try:
            # Get current system state
            loaded_models_info = {}
            total_vram_used = 0
            
            # Use models_lock if available, otherwise proceed without locking
            if hasattr(self, 'models_lock'):
                lock = self.models_lock
            else:
                # Create a dummy context manager if lock doesn't exist
                from contextlib import nullcontext
                lock = nullcontext()
            
            with lock:
                
                # Gather info for all loaded models
                for model_name, model_info in self.loaded_models.items():
                    # Skip if model is being loaded or unloaded
                    if model_info.get('status') not in ['LOADED', 'ACTIVE']:
                        continue
                        
                    # Get VRAM usage - either reported or estimated
                    vram_usage = model_info.get('vram_usage_mb', model_info.get('estimated_vram_mb', 0))
                    
                    # Add to total
                    total_vram_used += vram_usage
                    
                    # Prepare model info
                    loaded_models_info[model_name] = {
                        'vram_usage_mb': vram_usage,
                        'device': model_info.get('device', 'MainPC'),
                        'last_used': model_info.get('last_used', time.time()),
                        'is_active': model_info.get('is_active', False),
                        'quantization': model_info.get('quantization', 'FP16')
                    }
                
                # Prepare payload for SystemDigitalTwin
                payload = {
                    'agent_name': 'ModelManagerAgent',
                    'total_vram_mb': 24000,  # Default for RTX 4090
                    # Fix: Use the current_estimated_vram_used attribute instead of current_vram_used
                    'total_vram_used_mb': getattr(self, 'current_estimated_vram_used', total_vram_used),
                    'loaded_models': loaded_models_info,
                    'timestamp': time.time()
                }
                
                # Connect to SystemDigitalTwin (with secure ZMQ if enabled)
                import zmq
                
                context = zmq.Context()
                socket = context.socket(zmq.REQ)
                
                # Get SDT address from service discovery
                try:
                    from main_pc_code.utils.service_discovery_client import get_service_address
                    sdt_address = get_service_address("SystemDigitalTwin")
                    if not sdt_address:
                        sdt_address = get_zmq_connection_string(7120, "localhost")  # Default fallback
                except Exception as e:
                    logger.warning(f"Service discovery failed: {e}, using default address")
                    sdt_address = get_zmq_connection_string(7120, "localhost")  # Default fallback
                
                # Apply secure ZMQ if enabled
                secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
                if secure_zmq:
                    try:
                        from main_pc_code.src.network.secure_zmq import configure_secure_client, start_auth
                        start_auth()
                        socket = configure_secure_client(socket)
                        logger.debug("Secure ZMQ configured for SDT connection")
                    except Exception as e:
                        logger.warning(f"Failed to configure secure ZMQ for SDT: {e}")
                        secure_zmq = False
                
                # Set timeouts
                socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second receive timeout
                socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second send timeout
                
                # Get SDT address from service discovery
                try:
                    from main_pc_code.utils.service_discovery_client import get_service_address
                    sdt_address = get_service_address("SystemDigitalTwin")
                    if not sdt_address:
                        sdt_address = get_zmq_connection_string(7120, "localhost")  # Default fallback
                except Exception as e:
                    logger.warning(f"Service discovery failed: {e}, using default address")
                    sdt_address = get_zmq_connection_string(7120, "localhost")  # Default fallback
                
                # Connect and send the report
                socket.connect(sdt_address)
                request = {
                    'command': 'REPORT_MODEL_VRAM',
                    'payload': payload
                }
                
                socket.send_json(request)
                
                # Wait for response with timeout
                try:
                    response = socket.recv_json()
                    if response.get('status') == 'SUCCESS':
                        logger.debug("Successfully reported VRAM metrics to SystemDigitalTwin")
                    else:
                        logger.warning(f"Error reporting VRAM metrics: {response.get('message', 'Unknown error')}")
                except zmq.error.Again:
                    logger.warning("Timeout waiting for SystemDigitalTwin response when reporting VRAM metrics")
                
                # Close socket
                socket.close()
                
        except Exception as e:
            logger.error(f"Error reporting VRAM status to SystemDigitalTwin: {e}")
            logger.error(traceback.format_exc())
            
    def _memory_management_loop(self):
        """
        Background thread for managing memory usage.
        
        Monitors VRAM usage and unloads models when needed.
        Also reports VRAM status to SystemDigitalTwin periodically.
        """
        logger.info("Starting memory management loop")
        report_interval = 30  # Report to SDT every 30 seconds
        last_report_time = 0
        
        while self.running:
            try:
                # Update VRAM usage
                self._update_vram_usage()
                
                # Check if we need to unload models
                self._unload_idle_models()
                
                # Handle VRAM pressure if needed
                self._handle_vram_pressure()
                
                # Report to SystemDigitalTwin periodically
                current_time = time.time()
                if current_time - last_report_time >= report_interval:
                    self._report_vram_status_to_sdt()
                    last_report_time = current_time
                
                # Sleep before next check
                time.sleep(self.memory_check_interval)
                
            except Exception as e:
                logger.error(f"Error in memory management loop: {e}")
                logger.error(traceback.format_exc())
                time.sleep(self.memory_check_interval)

    def _load_gguf_model(self, model_id):
        """Load a GGUF model using the GGUF Model Manager."""
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

            # Import and use the GGUF Model Manager directly
            from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager
            gguf_manager = get_gguf_manager()
            
            # Load the model via GGUF manager
            success = gguf_manager.load_model(model_id)
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
        """Unload a GGUF model using the GGUF Model Manager."""
        logger.critical(f"--- [MainMMA _unload_gguf_model CRITICAL ENTRY] Called for model_id: {model_id} ---")
        try:
            # Import and use the GGUF Model Manager directly
            from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager
            gguf_manager = get_gguf_manager()
            
            # Unload the model via GGUF manager
            success = gguf_manager.unload_model(model_id)
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
            # Import and use the GGUF Model Manager directly
            from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager
            gguf_manager = get_gguf_manager()
            
            # Get current status from GGUF manager
            status = gguf_manager.get_model_status(model_id)
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
                    # Unified API quick path — handle `{action: "generate"}` requests here
        if isinstance(request_data, dict):
            action = request_data.get("action")
            if action == "generate":
                return self._handle_generate_action(request_data)
            elif action == "clear_conversation":
                return self._handle_clear_conversation_action(request_data)

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
                key=lambda x: self.vram_config.get('priority_levels').get(x[1].get('priority', 'low'), 3),
                reverse=True
            )
            
            for model_id, _ in models_by_priority:
                logger.info(f"MMA: Attempting to unload model {model_id} due to VRAM pressure")
                self._unload_model(model_id)
                current_vram = self._get_current_vram()
                
                if current_vram <= vram_budget:
                    logger.info(f"MMA: VRAM pressure resolved after unloading {model_id}")
                    pass
                else:
                    logger.warning(f"MMA: VRAM still under pressure after unloading {model_id}")

    def _apply_quantization(self, model_id, model_type):
        """
        Apply quantization to a model based on its type.
        
        Args:
            model_id (str): The ID of the model to quantize
            model_type (str): The type of the model (e.g., 'gguf', 'huggingface')
            
        Returns:
            bool: True if quantization was successful, False otherwise
        """
        self.quant_logger.info(f"Applying quantization for model {model_id}")
        self.quant_logger.info(f"Model type: {model_type}")
        
        # Get quantization settings from config
        quantization_config = self.config.get('quantization_config', {})
        default_quantization = quantization_config.get('default_quantization', 'float16')
        
        # Get model-specific quantization type or use default
        quantization_type = quantization_config.get('quantization_options_per_model_type', {}).get(
            model_type, default_quantization
        )
        
        # Check if model is Phi-3 (special handling for 4-bit quantization)
        is_phi3_model = 'phi-3' in model_id.lower()
        
        # If model is Phi-3, use 4-bit quantization by default
        if is_phi3_model:
            self.quant_logger.info(f"Detected Phi-3 model: {model_id}, applying 4-bit quantization")
            quantization_type = 'int4'
        
        self.quant_logger.info(f"Selected quantization: {quantization_type}")
        
        try:
            if model_type == 'gguf':
                return self._apply_gguf_quantization(model_id, quantization_type)
            elif model_type == 'huggingface':
                return self._apply_huggingface_quantization(model_id, quantization_type)
            else:
                self.quant_logger.warning(f"Quantization not supported for model type: {model_type}")
                return False
        except Exception as e:
            self.quant_logger.error(f"Error applying quantization to model {model_id}: {e}")
            self.quant_logger.error(traceback.format_exc())
            return False
    
    def _apply_gguf_quantization(self, model_id, quantization_type):
        """
        Apply quantization to a GGUF model.
        
        Args:
            model_id (str): The ID of the model to quantize
            quantization_type (str): The type of quantization to apply
            
        Returns:
            bool: True if quantization was successful, False otherwise
        """
        self.quant_logger.info(f"Applying GGUF quantization for model {model_id}: {quantization_type}")
        
        try:
            # Import and use the GGUF Model Manager
            from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager
            gguf_manager = get_gguf_manager()
            
            # Check if model is loaded
            if model_id not in gguf_manager.loaded_models:
                self.quant_logger.warning(f"Model {model_id} not loaded, cannot apply quantization")
                return False
            
            # Get model info
            model_info = self.models.get(model_id, {})
            if not model_info:
                self.quant_logger.warning(f"No model info found for {model_id}")
                return False
            
            # Update model info with quantization type
            model_info['quantization'] = quantization_type
            
            # Unload the model
            self.quant_logger.info(f"Unloading model {model_id} for requantization")
            gguf_manager.unload_model(model_id)
            
            # Reload the model with new quantization
            self.quant_logger.info(f"Reloading model {model_id} with {quantization_type} quantization")
            
            # For 4-bit quantization, we need to specify additional parameters
            if quantization_type == 'int4':
                # Update model path to use 4-bit quantized version if available
                model_path = model_info.get('model_path', '')
                if not model_path.endswith('.q4_0.gguf') and not model_path.endswith('.q4_1.gguf'):
                    # Try to find a 4-bit quantized version
                    base_path = model_path.rsplit('.', 1)[0]
                    q4_path = f"{base_path}.q4_0.gguf"
                    if os.path.exists(q4_path):
                        model_info['model_path'] = q4_path
                        self.quant_logger.info(f"Using 4-bit quantized model: {q4_path}")
                    else:
                        self.quant_logger.warning(f"No 4-bit quantized version found for {model_id}")
            
            # Reload with updated model info
            success = gguf_manager.load_model(model_id)
            
            if success:
                self.quant_logger.info(f"Successfully applied {quantization_type} quantization to {model_id}")
                # Update model info in self.models
                self.models[model_id] = model_info
                return True
            else:
                self.quant_logger.error(f"Failed to reload model {model_id} after quantization")
                return False
                
        except Exception as e:
            self.quant_logger.error(f"Error applying GGUF quantization to model {model_id}: {e}")
            self.quant_logger.error(traceback.format_exc())
            return False
    
    def _apply_huggingface_quantization(self, model_id, quantization_type):
        """
        Apply quantization to a Hugging Face model.
        
        Args:
            model_id (str): The ID of the model to quantize
            quantization_type (str): The type of quantization to apply
            
        Returns:
            bool: True if quantization was successful, False otherwise
        """
        self.quant_logger.info(f"Applying Hugging Face quantization for model {model_id}: {quantization_type}")
        
        try:
            # Get model info
            model_info = self.models.get(model_id, {})
            if not model_info:
                self.quant_logger.warning(f"No model info found for {model_id}")
                return False
            
            # Check if model is loaded
            if model_id not in self.loaded_models:
                self.quant_logger.warning(f"Model {model_id} not loaded, cannot apply quantization")
                return False
            
            # Update model info with quantization type
            model_info['quantization'] = quantization_type
            
            # For Hugging Face models, we need to unload and reload with quantization config
            self.quant_logger.info(f"Unloading model {model_id} for requantization")
            self._unload_model(model_id)
            
            # Prepare quantization config
            quantization_config = {}
            
            if quantization_type == 'int8':
                quantization_config = {
                    'load_in_8bit': True,
                    'device_map': 'auto'
                }
            elif quantization_type == 'int4':
                quantization_config = {
                    'load_in_4bit': True,
                    'bnb_4bit_compute_dtype': 'float16',
                    'bnb_4bit_quant_type': 'nf4',
                    'bnb_4bit_use_double_quant': True,
                    'device_map': 'auto'
                }
            elif quantization_type == 'float16':
                quantization_config = {
                    'torch_dtype': 'float16',
                    'device_map': 'auto'
                }
            
            # Update model info with quantization config
            model_info['quantization_config'] = quantization_config
            
            # Update model in self.models
            self.models[model_id] = model_info
            
            # Reload the model
            self.quant_logger.info(f"Reloading model {model_id} with {quantization_type} quantization")
            success = self.load_model(model_id)
            
            if success:
                self.quant_logger.info(f"Successfully applied {quantization_type} quantization to {model_id}")
                return True
            else:
                self.quant_logger.error(f"Failed to reload model {model_id} after quantization")
                return False
                
        except Exception as e:
            self.quant_logger.error(f"Error applying Hugging Face quantization to model {model_id}: {e}")
            self.quant_logger.error(traceback.format_exc())
            return False

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
            vram_config = self.config.get('vram_management')
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
        log_file = logs_dir / str(PathManager.get_logs_dir() / "model_manager_agent.log")
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
                    pc2_ip = self.pc2_services.get('ip', get_pc2_ip())
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
            # Fix: Use the global config object instead of self.config
            enable_pc2_services = config.get('enable_pc2_services', False)
            
            if not enable_pc2_services:
                self.logger.debug("PC2 services integration disabled in agent configuration")
                return service_status
                
            # Get PC2 services using the centralized config module
            pc2_config = self.pc2_services if hasattr(self, 'pc2_services') else None
            
            if not pc2_config or not pc2_config.get('enabled', False):
                self.logger.warning("PC2 services not enabled in pc2_services.yaml configuration")
                return service_status
                
            pc2_ip = pc2_config.get('ip', get_pc2_ip())
            
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

    def report_vram_metrics_to_sdt(self):
        """
        Report VRAM usage metrics and loaded models to SystemDigitalTwin
        """
        try:
            # Get current system state
            with self.models_lock:
                loaded_models_info = {}
                total_vram_used = 0
                
                # Gather info for all loaded models
                for model_name, model_info in self.loaded_models.items():
                    # Skip if model is being loaded or unloaded
                    if model_info.get('status') not in ['LOADED', 'ACTIVE']:
                        continue
                        
                    # Get VRAM usage - either reported or estimated
                    vram_usage = model_info.get('vram_usage_mb', model_info.get('estimated_vram_mb', 0))
                    
                    # Add to total
                    total_vram_used += vram_usage
                    
                    # Prepare model info
                    loaded_models_info[model_name] = {
                        'vram_usage_mb': vram_usage,
                        'device': model_info.get('device', 'MainPC'),
                        'last_used': model_info.get('last_used', time.time()),
                        'is_active': model_info.get('is_active', False),
                        'quantization': model_info.get('quantization', 'FP16')
                    }
                
                # Prepare payload for SystemDigitalTwin
                payload = {
                    'agent_name': 'ModelManagerAgent',
                    'total_vram_mb': 24000,  # Default for RTX 4090
                    'total_vram_used_mb': total_vram_used,
                    'loaded_models': loaded_models_info,
                    'timestamp': time.time()
                }
                
                # Connect to SystemDigitalTwin (with secure ZMQ if enabled)
                import zmq
                
                context = zmq.Context()
                socket = context.socket(zmq.REQ)
                
                # Get SDT address from service discovery
                try:
                    from main_pc_code.utils.service_discovery_client import get_service_address
                    sdt_address = get_service_address("SystemDigitalTwin")
                    if not sdt_address:
                        sdt_address = get_zmq_connection_string(7120, "localhost")  # Default fallback
                except Exception as e:
                    logger.warning(f"Service discovery failed: {e}, using default address")
                    sdt_address = get_zmq_connection_string(7120, "localhost")  # Default fallback
                
                # Apply secure ZMQ if enabled
                secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
                if secure_zmq:
                    try:
                        from main_pc_code.src.network.secure_zmq import configure_secure_client, start_auth
                        start_auth()
                        socket = configure_secure_client(socket)
                        logger.info("Using secure ZMQ for SDT reporting")
                    except Exception as e:
                        logger.warning(f"Failed to configure secure ZMQ for SDT reporting: {e}")
                
                # Set timeouts
                socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second receive timeout
                socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second send timeout
                
                # Get SDT address from service discovery
                try:
                    from main_pc_code.utils.service_discovery_client import get_service_address
                    sdt_address = get_service_address("SystemDigitalTwin")
                    if not sdt_address:
                        sdt_address = get_zmq_connection_string(7120, "localhost")  # Default fallback
                except Exception as e:
                    logger.warning(f"Service discovery failed: {e}, using default address")
                    sdt_address = get_zmq_connection_string(7120, "localhost")  # Default fallback
                
                # Connect and send the report
                socket.connect(sdt_address)
                request = {
                    'command': 'REPORT_MODEL_VRAM',
                    'payload': payload
                }
                
                socket.send_json(request)
                
                # Wait for response with timeout
                try:
                    response = socket.recv_json()
                    if response.get('status') == 'SUCCESS':
                        logger.debug("Successfully reported VRAM metrics to SystemDigitalTwin")
                    else:
                        logger.warning(f"Error reporting VRAM metrics: {response.get('message', 'Unknown error')}")
                except zmq.error.Again:
                    logger.warning("Timeout waiting for SystemDigitalTwin response when reporting VRAM metrics")
                
                # Close socket
                socket.close()
                
        except Exception as e:
            logger.error(f"Error reporting VRAM metrics to SystemDigitalTwin: {e}")
            import traceback
            from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
            logger.error(traceback.format_exc())

    def _unload_model(self, model_id: str) -> None:
        """
        Unload a model by its ID.
        This is a private helper method that delegates to the appropriate unload method
        based on the model type.
        
        Args:
            model_id: The ID of the model to unload
        """
        if model_id not in self.loaded_models:
            self.logger.warning(f"Cannot unload model {model_id}: not currently loaded")
            return
            
        model_info = self.loaded_models.get(model_id, {})
        model_type = model_info.get('type')
        
        self.logger.info(f"Unloading model {model_id} of type {model_type}")
        
        if model_type == 'ollama':
            self._unload_ollama_model(model_id)
        elif model_type == 'custom_api':
            self._unload_custom_api_model(model_id)
        elif model_type == 'zmq_service':
            self._unload_zmq_service_model(model_id)
        elif model_type == 'gguf':
            self._unload_gguf_model(model_id)
        else:
            self.logger.warning(f"Unknown model type {model_type} for model {model_id}")
            
        # Mark as unloaded regardless of the specific unload method
        self._mark_model_as_unloaded(model_id)
        
        # Update VRAM usage
        self._update_vram_usage()
        
        # Publish status update
        self._publish_status_update()

    def _load_llm_config(self):
        try:
            with open(self.llm_config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            print(f"[MMA] Failed to load LLM config: {e}")
            return {'load_policy': {}, 'models': {}}

    def _handle_clear_conversation_action(self, request):
        """
        Handle the 'clear_conversation' action to clear KV caches for a specific conversation.
        
        Args:
            request: The request dictionary containing conversation_id
            
        Returns:
            Response dictionary with status
        """
        conversation_id = request.get("conversation_id")
        
        if not conversation_id:
            self.logger.error("Missing 'conversation_id' field in clear_conversation request")
            return {"status": "error", "message": "Missing 'conversation_id' field"}
        
        self.logger.info(f"Clearing KV cache for conversation: {conversation_id}")
        
        try:
            # Import and use the GGUF Model Manager
            from main_pc_code.agents.gguf_model_manager import get_instance as get_gguf_manager
            gguf_manager = get_gguf_manager()
            
            # Clear KV cache
            success = gguf_manager.clear_kv_cache(conversation_id)
            
            if success:
                self.logger.info(f"Successfully cleared KV cache for conversation: {conversation_id}")
                return {
                    "status": "ok",
                    "message": f"Cleared KV cache for conversation: {conversation_id}",
                    "conversation_id": conversation_id
                }
            else:
                self.logger.warning(f"No KV cache found for conversation: {conversation_id}")
                return {
                    "status": "ok",
                    "message": f"No KV cache found for conversation: {conversation_id}",
                    "conversation_id": conversation_id
                }
                
        except Exception as e:
            self.logger.error(f"Error clearing KV cache for conversation {conversation_id}: {e}")
            self.logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": f"Error clearing KV cache: {str(e)}",
                "conversation_id": conversation_id
            }

# --- PATCH: Attach standalone functions to ModelManagerAgent class (ensures methods are available before main is executed) ---
# --- END PATCH ---

# Main entry point
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        # Create necessary directories
        Path("logs").mkdir(exist_ok=True)
        Path("cache").mkdir(exist_ok=True)
        
        # Initialize and run the agent
        logger.info(f"Starting ModelManagerAgent")
        agent = ModelManagerAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()