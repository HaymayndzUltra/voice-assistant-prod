"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.path_manager import PathManager

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = PathManager.get_main_pc_code()
if MAIN_PC_CODE_DIR not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE_DIR))

VRAM Optimizer Agent
Handles VRAM monitoring, optimization, and model management
Implements predictive model loading and fine-tuned unloading
"""

import logging
import time
import threading
import zmq
import sys
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Optional, List, Any, Union
import torch
import psutil
import GPUtil
from collections import defaultdict


# Import path manager for containerization-friendly paths
import sys
import os
from pathlib import Path
from common.utils.path_manager import PathManager

sys.path.insert(0, str(PathManager.get_project_root()))
from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from common_utils.error_handling import SafeExecutor

# Parse agent arguments
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VRAMOptimizerAgent")

class VramOptimizerAgent(BaseAgent):
    def __init__(self, port: int = None, name: str = None, **kwargs):
        agent_port = config.get("port", 5000) if port is None else port
        agent_name = config.get("name", 'VRAMOptimizerAgent') if name is None else name
        super().__init__(port=agent_port, name=agent_name)

        # Load configuration from startup_config.yaml
        self._load_configuration()

        # Initialize ZMQ context
        self.context = zmq.Context.instance()

        # Initialize service connections
        self._init_service_connections()

        # Set up VRAM thresholds from config
        self.vram_thresholds = {
            'critical': self.config.get('vram_optimizer.critical_threshold', 0.9),
            'warning': self.config.get('vram_optimizer.warning_threshold', 0.75),
            'safe': self.config.get('vram_optimizer.safe_threshold', 0.5)
        }

        # Model VRAM requirements (will be updated from model manager)
        self.model_vram_requirements = {}

        # Track loaded models
        self.loaded_models = {}
        self.lock = threading.Lock()
        self.running = True
        self.start_time = time.time()

        # Advanced management
        self.memory_pool = {}
        # TODO: Fix incomplete statement


        # Defragmentation threshold configuration
        self.defragmentation_threshold = self.config.get('vram_optimizer.defragmentation_threshold', 0.70)
        self.usage_patterns = defaultdict(list)
        self.prediction_window = self.config.get('vram_optimizer.prediction_window', 3600)
        self.optimization_interval = self.config.get('vram_optimizer.optimization_interval', 300)

        # Idle timeout configuration
        self.idle_timeout = self.config.get('vram_optimizer.idle_timeout', 900)
        self.idle_check_interval = self.config.get('vram_optimizer.idle_check_interval', 60)

        # Predictive loading settings
        self.predictive_loading_enabled = self.config.get('vram_optimizer.predictive_loading_enabled', True)
        self.lookahead_window = self.config.get('vram_optimizer.lookahead_window', 300)

        # VRAM budget per device
        self.mainpc_vram_budget = self.config.get('vram_optimizer.mainpc_vram_budget_mb', 20000)
        self.pc2_vram_budget = self.config.get('vram_optimizer.pc2_vram_budget_mb', 10000)

        # Start monitoring threads
        self.monitor_thread = threading.Thread(target=self._monitor_vram, daemon=True)
        self.optimization_thread = threading.Thread(target=self._optimize_memory, daemon=True)
        self.prediction_thread = threading.Thread(target=self._predict_usage, daemon=True)
        self.idle_monitor_thread = threading.Thread(target=self._monitor_idle_models, daemon=True)

        logger.info("VRAMOptimizerAgent initialized with configuration:")
        logger.info(f"  - VRAM thresholds: {self.vram_thresholds}")
        logger.info(f"  - Idle timeout: {self.idle_timeout}s")
        logger.info(f"  - Predictive loading: {'enabled' if self.predictive_loading_enabled else 'disabled'}")
        logger.info(f"  - VRAM budgets: MainPC={self.mainpc_vram_budget}MB, PC2={self.pc2_vram_budget}MB")

        # Start the threads
        self.monitor_thread.start()
        self.optimization_thread.start()
        self.prediction_thread.start()
        self.idle_monitor_thread.start()

    def _get_health_status(self):
        status = "ok" if self.running else "unhealthy"
        vram_stats = self.get_vram_usage() if hasattr(self, 'get_vram_usage') else {}
        details = {
            "status_message": "Agent is operational." if self.running else "Agent is not running.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0,
            "vram_stats": vram_stats
        }
        return {"status": status, "details": details}
    
    def _load_configuration(self):
        """
        Load configuration from startup_config.yaml
        """
        try:
            # Try to find config file in standard location
            config_path = Path(PathManager.get_project_root()) / "main_pc_code" / "config" / "startup_config.yaml"
            if not config_path.exists():
                # Try relative to parent directory
                config_path = Path(__file__).parent.parent / "config" / "startup_config.yaml"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    full_config = yaml.safe_load(f)
                    # Extract VRAMOptimizerAgent config
                    self.config = full_config.get('VRAMOptimizerAgent', {})
                    logger.info(f"Loaded configuration from {config_path}")
            else:
                logger.warning(f"Configuration file not found at {config_path}, using defaults")
                self.config = {}
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self.config = {}
    
    def _init_service_connections(self):
        """
        Initialize connections to required services using service discovery
        """
        # Import service discovery client
        try:
            from main_pc_code.utils.service_discovery_client import discover_service, get_service_address
            from main_pc_code.src.network.secure_zmq import configure_secure_client, start_auth
            
            # Start the ZMQ authenticator
            start_auth()
            
            # Get SystemDigitalTwin connection
            sdt_info = discover_service("SystemDigitalTwin")
            if sdt_info.get("status") == "SUCCESS":
                sdt_address = f"tcp://{sdt_info['payload']['ip']}:{sdt_info['payload']['port']}"
                logger.info(f"Found SystemDigitalTwin at {sdt_address}")
            else:
                logger.warning("SystemDigitalTwin not found via service discovery, using default")
                sdt_port = config.get("sdt_port", 7000)
                sdt_host = config.get("sdt_host", 'localhost')
                sdt_address = f"tcp://{sdt_host}:{sdt_port}"
            
            # Connect to SystemDigitalTwin
            self.sdt_socket = self.context.socket(zmq.REQ)
            self.sdt_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
            self.sdt_socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5s timeout
            
            # Apply secure ZMQ if enabled
            secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
            if secure_zmq:
                self.sdt_socket = configure_secure_client(self.sdt_socket)
                logger.info("Using secure ZMQ for SystemDigitalTwin connection")
            
            self.sdt_socket.connect(sdt_address)
            logger.info(f"Connected to SystemDigitalTwin at {sdt_address}")
            
            # Get ModelManagerAgent connection
            mma_info = discover_service("ModelManagerAgent")
            if mma_info.get("status") == "SUCCESS":
                mma_address = f"tcp://{mma_info['payload']['ip']}:{mma_info['payload']['port']}"
                logger.info(f"Found ModelManagerAgent at {mma_address}")
            else:
                logger.warning("ModelManagerAgent not found via service discovery, using default")
                mma_port = config.get("mma_port", 5000)
                mma_host = config.get("mma_host", 'localhost')
                mma_address = f"tcp://{mma_host}:{mma_port}"
            
            # Connect to ModelManagerAgent
            self.mma_socket = self.context.socket(zmq.REQ)
            self.mma_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
            self.mma_socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5s timeout
            
            # Apply secure ZMQ if enabled
            if secure_zmq:
                self.mma_socket = configure_secure_client(self.mma_socket)
                logger.info("Using secure ZMQ for ModelManagerAgent connection")
            
            self.mma_socket.connect(mma_address)
            logger.info(f"Connected to ModelManagerAgent at {mma_address}")
            
            # Get RequestCoordinator connection (if available, for predictive loading)
            rc_info = discover_service("RequestCoordinator")
            if rc_info and rc_info.get("status") == "SUCCESS":
                rc_address = f"tcp://{rc_info['payload']['ip']}:{rc_info['payload']['port']}"
                logger.info(f"Found RequestCoordinator at {rc_address}")
                # Connect to RequestCoordinator
                try:
                    self.rc_socket = self.context.socket(zmq.REQ)
                    if secure_zmq:
                        logger.info("Using secure ZMQ for RequestCoordinator connection")
                        configure_secure_client(self.rc_socket)
                    self.rc_socket.connect(rc_address)
                    logger.info(f"Connected to RequestCoordinator at {rc_address}")
                    self.request_coordinator_available = True  # Assuming RC now handles this
                except Exception as e:
                    logger.error(f"Failed to connect to RequestCoordinator: {e}")
                    self.request_coordinator_available = False
            else:
                logger.warning("RequestCoordinator not found via service discovery, predictive loading will be limited")
                self.request_coordinator_available = False
                self.rc_socket = None

            # --- Model Evaluation Framework ---
            mef_info = discover_service("ModelEvaluationFramework")
            if mef_info.get("status") == "SUCCESS":
                mef_address = f"tcp://{mef_info['payload']['ip']}:{mef_info['payload']['port']}"
                logger.info(f"Found ModelEvaluationFramework at {mef_address}")
            else:
                logger.warning("ModelEvaluationFramework not found via service discovery, using default")
                mef_port = config.get("mef_port", 5000)
                mef_host = config.get("mef_host", 'localhost')
                mef_address = f"tcp://{mef_host}:{mef_port}"
            
            # Connect to ModelEvaluationFramework
            self.mef_socket = self.context.socket(zmq.REQ)
            self.mef_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
            self.mef_socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5s timeout
            
            # Apply secure ZMQ if enabled
            if secure_zmq:
                self.mef_socket = configure_secure_client(self.mef_socket)
                logger.info("Using secure ZMQ for ModelEvaluationFramework connection")
            
            self.mef_socket.connect(mef_address)
            logger.info(f"Connected to ModelEvaluationFramework at {mef_address}")
            self.model_evaluation_framework_available = True
            
        except ImportError as e:
            print(f"Import error: {e}")
            logger.error(f"ImportError during service discovery: {e}")
            self._init_fallback_connections()
        except Exception as e:
            logger.error(f"Error initializing service connections: {e}")
            self._init_fallback_connections()
    
    def _init_fallback_connections(self):
        """
        Initialize fallback connections if service discovery fails
        """
        logger.warning("Using fallback connections")
        
        # Get fallback connection details from _agent_args
        sdt_port = config.get("sdt_port", 7000)
        sdt_host = config.get("sdt_host", 'localhost')
        mma_port = config.get("mma_port", 5000)
        mma_host = config.get("mma_host", 'localhost')
        
        # Connect to SystemDigitalTwin
        try:
            self.sdt_socket = self.context.socket(zmq.REQ)
            self.sdt_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
            self.sdt_socket.connect(f"tcp://{sdt_host}:{sdt_port}")
            logger.info(f"Connected to SystemDigitalTwin at tcp://{sdt_host}:{sdt_port} (fallback)")
        except Exception as e:
            logger.error(f"Failed to connect to SystemDigitalTwin: {e}")
            self.sdt_socket = None
        
        # Connect to ModelManagerAgent
        try:
            self.mma_socket = self.context.socket(zmq.REQ)
            self.mma_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5s timeout
            self.mma_socket.connect(f"tcp://{mma_host}:{mma_port}")
            logger.info(f"Connected to ModelManagerAgent at tcp://{mma_host}:{mma_port} (fallback)")
        except Exception as e:
            logger.error(f"Failed to connect to ModelManagerAgent: {e}")
            self.mma_socket = None
        
        # No RequestCoordinator in fallback mode
        self.rc_socket = None
        self.request_coordinator_available = False

        # No ModelEvaluationFramework in fallback mode
        self.mef_socket = None
        self.model_evaluation_framework_available = False
    
    def start_monitoring(self):
        """Start VRAM monitoring thread"""
        self.running = True
        logger.info("VRAM monitoring started")
        
    def stop_monitoring(self):
        """Stop VRAM monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        if self.optimization_thread:
            self.optimization_thread.join()
        if self.prediction_thread:
            self.prediction_thread.join()
        if self.idle_monitor_thread:
            self.idle_monitor_thread.join()
        logger.info("VRAM monitoring stopped")
        
    def get_vram_usage(self) -> Dict[str, float]:
        """Get current VRAM usage statistics"""
        try:
            gpu = GPUtil.getGPUs()[0]  # Get first GPU
            return {
                'total': gpu.memoryTotal / 1024,  # Convert to GB
                'used': gpu.memoryUsed / 1024,
                'free': gpu.memoryFree / 1024,
                'utilization': gpu.load * 100  # GPU utilization percentage
            }
        except Exception as e:
            logger.error(f"Error getting VRAM usage: {e}")
            return {'total': 0, 'used': 0, 'free': 0, 'utilization': 0}
            
    def _consult_digital_twin(self, vram_request_mb: float) -> dict:
        """Consults the SystemDigitalTwin for a predictive recommendation."""
        if not self.sdt_socket:
            logger.warning("Digital Twin socket not available. Proceeding without consultation.")
            return {"recommendation": "proceed"}
        
        try:
            request = {
                "action": "simulate_load",
                "load_type": "vram",
                "value_mb": vram_request_mb
            }
            self.sdt_socket.send_json(request)
            
            poller = zmq.Poller()
            poller.register(self.sdt_socket, zmq.POLLIN)
            if poller.poll(5000): # 5-second timeout
                response = self.sdt_socket.recv_json()
                logger.info(f"Digital Twin recommendation: {response.get('recommendation')}")
                return response
            else:
                logger.error("Timeout waiting for response from SystemDigitalTwinAgent.")
                self.sdt_socket.close()
                self.sdt_socket = self.context.socket(zmq.REQ)
                self.sdt_socket.setsockopt(zmq.RCVTIMEO, 5000)
                self.sdt_socket.setsockopt(zmq.SNDTIMEO, 5000)
                # Try to reconnect to PC2 SystemDigitalTwin
                try:
                    from pathlib import Path
                    from main_pc_code.config.pc2_services_config import get_service_connection
                    
                    # Get connection string for SystemDigitalTwin
                    connection = get_service_connection("SystemDigitalTwin")
                    if connection:
                        # Extract IP and port from connection string
                        # Format: tcp://IP:PORT
                        parts = connection.replace("tcp://", "").split(":")
                        pc2_ip = parts[0]
                        dt_port = int(parts[1])
                    else:
                        # Fallback values
                        pc2_ip = get_pc2_ip()
                        dt_port = 7120
                    self.sdt_socket.connect(f"tcp://{pc2_ip}:{dt_port}")
                    logger.info(f"Reconnected to SystemDigitalTwinAgent on PC2 ({pc2_ip}:{dt_port}).")
                except Exception as e:
                    # Fallback to local connection
                    self.sdt_socket.connect(get_zmq_connection_string(5585, "localhost"))
                    logger.info("Reconnected to local SystemDigitalTwinAgent.")
                return {"recommendation": "proceed"}
        except Exception as e:
            logger.error(f"Error consulting Digital Twin: {e}")
            return {"recommendation": "proceed"}
            
    def can_load_model(self, model_id: str) -> bool:
        """Check if there's enough VRAM to load a model, after consulting the digital twin."""
        required_vram = self.model_vram_requirements.get(model_id, 0)
        
        # --- START OF NEW LOGIC ---
        # For large models (e.g., >2GB), consult the digital twin first as a pre-check
        if required_vram > 2048:
            logger.info(f"Consulting Digital Twin for large model request: {model_id} ({required_vram}MB)")
            dt_response = self._consult_digital_twin(required_vram)
            if dt_response.get("recommendation") != "proceed":
                logger.warning(f"Allocation for {model_id} denied by Digital Twin recommendation.")
                return False
        # --- END OF NEW LOGIC ---
        
        vram_usage = self.get_vram_usage()
        available_vram = vram_usage['free']
        
        return available_vram >= required_vram
        
    def register_model(self, model_id: str, model_instance: any):
        """Register a loaded model"""
        with self.lock:
            self.loaded_models[model_id] = {
                'instance': model_instance,
                'last_used': time.time(),
                'vram_usage': self.model_vram_requirements.get(model_id, 0)
            }
            logger.info(f"Registered model {model_id}")
            
    def unregister_model(self, model_id: str):
        """Unregister a model"""
        with self.lock:
            if model_id in self.loaded_models:
                del self.loaded_models[model_id]
                logger.info(f"Unregistered model {model_id}")
                
    def get_least_used_model(self) -> Optional[str]:
        """Get the least recently used model ID"""
        if not self.loaded_models:
            return None
            
        return min(self.loaded_models.items(), 
                  key=lambda x: x[1]['last_used'])[0]
                  
    def update_model_usage(self, model_id: str):
        """Update last used timestamp for a model"""
        with self.lock:
            if model_id in self.loaded_models:
                self.loaded_models[model_id]['last_used'] = time.time()
                
    def _monitor_vram(self):
        """
        Monitor VRAM usage on both MainPC and PC2 and take action if needed
        """
        while self.running:
            try:
                # Get VRAM usage from SystemDigitalTwin for both machines
                mainpc_vram, pc2_vram = self._get_vram_usage_from_sdt()
                
                # Get loaded models from ModelManagerAgent
                loaded_models = self._get_loaded_models_from_mma()
                
                # Update our local tracking
                with self.lock:
                    self.loaded_models = loaded_models
                    
                    # Check MainPC VRAM usage
                    if mainpc_vram['usage_ratio'] >= self.vram_thresholds['critical']:
                        logger.warning(f"Critical VRAM usage on MainPC: {mainpc_vram['usage_ratio']*100:.1f}%")
                        self._handle_critical_vram("MainPC")
                    elif mainpc_vram['usage_ratio'] >= self.vram_thresholds['warning']:
                        logger.warning(f"High VRAM usage on MainPC: {mainpc_vram['usage_ratio']*100:.1f}%")
                        self._handle_high_vram("MainPC")
                    
                    # Check PC2 VRAM usage (if available)
                    if pc2_vram and pc2_vram['usage_ratio'] >= self.vram_thresholds['critical']:
                        logger.warning(f"Critical VRAM usage on PC2: {pc2_vram['usage_ratio']*100:.1f}%")
                        self._handle_critical_vram("PC2")
                    elif pc2_vram and pc2_vram['usage_ratio'] >= self.vram_thresholds['warning']:
                        logger.warning(f"High VRAM usage on PC2: {pc2_vram['usage_ratio']*100:.1f}%")
                        self._handle_high_vram("PC2")
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in VRAM monitoring: {e}")
                time.sleep(5)
    
    def _get_vram_usage_from_sdt(self):
        """
        Get VRAM usage for both MainPC and PC2 from SystemDigitalTwin
        
        Returns:
            Tuple[Dict, Dict]: (MainPC VRAM info, PC2 VRAM info)
        """
        try:
            # Prepare request for SystemDigitalTwin
            request = {
                "command": "GET_METRICS",
                "payload": {
                    "metrics": ["vram_usage"]
                }
            }
            
            # Send request to SystemDigitalTwin
            self.sdt_socket.send_json(request)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.sdt_socket, zmq.POLLIN)
            if poller.poll(5000):  # 5s timeout
                response = self.sdt_socket.recv_json()
                
                if response.get("status") == "SUCCESS":
                    metrics = response.get("payload", {})
                    
                    # Extract VRAM metrics for MainPC
                    mainpc_vram = {
                        "total_mb": metrics.get("mainpc_vram_total_mb", self.mainpc_vram_budget),
                        "used_mb": metrics.get("mainpc_vram_used_mb", 0),
                        "free_mb": metrics.get("mainpc_vram_free_mb", self.mainpc_vram_budget),
                        "usage_ratio": metrics.get("mainpc_vram_used_mb", 0) / metrics.get("mainpc_vram_total_mb", self.mainpc_vram_budget)
                    }
                    
                    # Extract VRAM metrics for PC2 (if available)
                    if "pc2_vram_total_mb" in metrics:
                        pc2_vram = {
                            "total_mb": metrics.get("pc2_vram_total_mb", self.pc2_vram_budget),
                            "used_mb": metrics.get("pc2_vram_used_mb", 0),
                            "free_mb": metrics.get("pc2_vram_free_mb", self.pc2_vram_budget),
                            "usage_ratio": metrics.get("pc2_vram_used_mb", 0) / metrics.get("pc2_vram_total_mb", self.pc2_vram_budget)
                        }
                    else:
                        pc2_vram = None
                    
                    return mainpc_vram, pc2_vram
                else:
                    # Failed to get metrics
                    logger.warning(f"Failed to get VRAM metrics from SDT: {response.get('message', 'Unknown error')}")
                    # Fallback to local metrics for MainPC
                    local_vram = self._get_local_vram_metrics()
                    return local_vram, None
            else:
                # Timeout waiting for response
                logger.warning("Timeout waiting for response from SystemDigitalTwin")
                # Fallback to local metrics for MainPC
                local_vram = self._get_local_vram_metrics()
                return local_vram, None
        
        except Exception as e:
            logger.error(f"Error getting VRAM usage from SDT: {e}")
            # Fallback to local metrics for MainPC
            local_vram = self._get_local_vram_metrics()
            return local_vram, None
    
    def _get_local_vram_metrics(self):
        """
        Get local VRAM metrics using GPUtil as fallback
        
        Returns:
            Dict: VRAM metrics for local GPU
        """
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Use first GPU
                total_mb = gpu.memoryTotal
                used_mb = gpu.memoryUsed
                free_mb = gpu.memoryFree
                usage_ratio = used_mb / total_mb
                
                return {
                    "total_mb": total_mb,
                    "used_mb": used_mb,
                    "free_mb": free_mb,
                    "usage_ratio": usage_ratio
                }
            else:
                # No GPU found, use defaults
                logger.warning("No GPU found, using default VRAM metrics")
                return {
                    "total_mb": self.mainpc_vram_budget,
                    "used_mb": 0,
                    "free_mb": self.mainpc_vram_budget,
                    "usage_ratio": 0.0
                }
        except Exception as e:
            logger.error(f"Error getting local VRAM metrics: {e}")
            # Return safe defaults
            return {
                "total_mb": self.mainpc_vram_budget,
                "used_mb": 0,
                "free_mb": self.mainpc_vram_budget,
                "usage_ratio": 0.0
            }
    
    def _get_loaded_models_from_mma(self):
        """
        Get currently loaded models and their VRAM usage from ModelManagerAgent
        
        Returns:
            Dict: Loaded models with their info
        """
        try:
            # Prepare request for ModelManagerAgent
            request = {
                "command": "GET_LOADED_MODELS_STATUS"
            }
            
            # Send request to ModelManagerAgent
            self.mma_socket.send_json(request)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.mma_socket, zmq.POLLIN)
            if poller.poll(5000):  # 5s timeout
                response = self.mma_socket.recv_json()
                
                if response.get("status") == "SUCCESS":
                    return response.get("loaded_models", {})
                else:
                    # Failed to get loaded models
                    logger.warning(f"Failed to get loaded models from MMA: {response.get('message', 'Unknown error')}")
                    return {}
            else:
                # Timeout waiting for response
                logger.warning("Timeout waiting for response from ModelManagerAgent")
                return {}
        
        except Exception as e:
            logger.error(f"Error getting loaded models from MMA: {e}")
            return {}
    
    def _handle_critical_vram(self, device: str):
        """
        Handle critical VRAM usage on the specified device
        
        Args:
            device: Device with critical VRAM usage (MainPC/PC2)
        """
        logger.warning(f"Handling critical VRAM usage on {device}")
        
        with self.lock:
            # Get models sorted by VRAM usage (largest first) on this device
            sorted_models = self._get_models_by_vram_usage(device)
            
            # Need to unload at least one model immediately to reduce pressure
            if sorted_models:
                model_to_unload = sorted_models[0]
                success = self._request_model_unload(model_to_unload)
                
                if success:
                    logger.info(f"Unloaded model {model_to_unload} due to critical VRAM usage on {device}")
                else:
                    logger.error(f"Failed to unload model {model_to_unload}")
                    
                    # Try the next model if available
                    if len(sorted_models) > 1:
                        model_to_unload = sorted_models[1]
                        success = self._request_model_unload(model_to_unload)
                        
                        if success:
                            logger.info(f"Unloaded model {model_to_unload} (fallback) due to critical VRAM usage on {device}")
                        else:
                            logger.error(f"Failed to unload fallback model {model_to_unload}")
            else:
                logger.warning(f"No models to unload on {device}")
    
    def _handle_high_vram(self, device: str):
        """
        Handle high VRAM usage on the specified device
        
        Args:
            device: Device with high VRAM usage (MainPC/PC2)
        """
        logger.info(f"Handling high VRAM usage on {device}")
        
        with self.lock:
            # Get idle models on this device
            idle_models = self._get_idle_models(device)
            
            if idle_models:
                # Unload the least recently used idle model
                model_to_unload = idle_models[0]
                success = self._request_model_unload(model_to_unload)
                
                if success:
                    logger.info(f"Unloaded idle model {model_to_unload} due to high VRAM usage on {device}")
                else:
                    logger.error(f"Failed to unload idle model {model_to_unload}")
            else:
                logger.info(f"No idle models to unload on {device}")
    
    def _get_models_by_vram_usage(self, device: str):
        """
        Get models sorted by VRAM usage (largest first) on the specified device
        
        Args:
            device: Device to filter models by (MainPC/PC2)
            
        Returns:
            List[str]: Sorted list of model IDs
        """
        models_on_device = []
        
        for model_id, model_info in self.loaded_models.items():
            if model_info.get("device") == device:
                models_on_device.append((model_id, model_info.get("vram_usage_mb", 0)))
        
        # Sort by VRAM usage (largest first)
        sorted_models = sorted(models_on_device, key=lambda x: x[1], reverse=True)
        
        # Return just the model IDs
        return [model_id for model_id, _ in sorted_models]
    
    def _get_idle_models(self, device: str = None):
        """
        Get models that have been idle longer than the timeout
        
        Args:
            device: Optional device to filter models by (MainPC/PC2)
            
        Returns:
            List[str]: List of idle model IDs sorted by least recently used first
        """
        current_time = time.time()
        idle_models = []
        
        for model_id, model_info in self.loaded_models.items():
            # Skip if device doesn't match (if specified)
            if device and model_info.get("device") != device:
                continue
                
            # Check if model is idle
            last_used = model_info.get("last_used", 0)
            if current_time - last_used > self.idle_timeout:
                idle_models.append((model_id, last_used))
        
        # Sort by last_used (oldest first)
        sorted_idle_models = sorted(idle_models, key=lambda x: x[1])
        
        # Return just the model IDs
        return [model_id for model_id, _ in sorted_idle_models]
    
    def _request_model_unload(self, model_id: str):
        """
        Request ModelManagerAgent to unload a model
        
        Args:
            model_id: ID of the model to unload
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare request for ModelManagerAgent
            request = {
                "command": "UNLOAD_MODEL",
                "model_name": model_id
            }
            
            # Send request to ModelManagerAgent
            self.mma_socket.send_json(request)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.mma_socket, zmq.POLLIN)
            if poller.poll(5000):  # 5s timeout
                response = self.mma_socket.recv_json()
                
                if response.get("status") == "SUCCESS":
                    logger.info(f"Successfully requested unload of model {model_id}")
                    return True
                else:
                    # Failed to unload model
                    logger.warning(f"Failed to unload model {model_id}: {response.get('message', 'Unknown error')}")
                    return False
            else:
                # Timeout waiting for response
                logger.warning(f"Timeout waiting for response to unload model {model_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error requesting model unload for {model_id}: {e}")
            return False
    
    def _predict_usage(self):
        """
        Predict future model usage and preload models based on patterns or TaskRouter queue
        """
        if not self.predictive_loading_enabled:
            return
            
        while self.running:
            try:
                # Fallback mode
                if not self.request_coordinator_available:
                    logger.warning("Predictive loading disabled: RequestCoordinator not available.")
                    time.sleep(60) # Wait a bit before trying again
                    continue

                # --- Predictive Loading Logic ---
                # First approach: Use RequestCoordinator queue (if available)
                if self.predictive_loading_enabled and self.rc_socket:
                    # This logic needs to be adapted based on what RequestCoordinator exposes
                    # For now, we assume it has a 'get_queue_status' action
                    logger.info("Attempting to predict from RequestCoordinator queue...")
                    try:
                        # Prepare request for RequestCoordinator
                        request = {"action": "get_queue_status"}
                        
                        # Send request to RequestCoordinator
                        self.rc_socket.send_json(request)
                        
                        # Wait for response
                        if self.rc_socket.poll(5000): # 5s timeout
                            response = self.rc_socket.recv_json()
                            
                            if response.get("status") == "success":
                                queue_snapshot = response.get("queue", [])
                                # Process snapshot to predict model needs
                                for task in queue_snapshot:
                                    task_type = task.get("task_type")
                                    
                                    # Map task type to model (simplified example)
                                    if task_type == "asr":
                                        model_to_preload = "whisper-large-v3"
                                    elif task_type == "chat":
                                        model_to_preload = "gpt-3.5-turbo"
                                    elif task_type == "image_generation":
                                        model_to_preload = "stable-diffusion-xl"
                                    else:
                                        continue
                                    
                                    # Check if model is already loaded
                                    if model_to_preload not in self.loaded_models:
                                        logger.info(f"Predictive loading: preloading {model_to_preload} for upcoming {task_type} task")
                                        self._request_model_load(model_to_preload)
                                        break  # Only preload one model at a time
                            else:
                                logger.warning(f"Failed to get queue status from RequestCoordinator: {response.get('message', 'Unknown error')}")
                        else:
                            logger.warning("Timeout waiting for response from RequestCoordinator")
                    except Exception as e:
                        logger.error(f"Error predicting from RequestCoordinator: {e}")

                # Second approach: Use historical data (if predictive loading is enabled)
                self._predict_from_usage_patterns()
                
                # Sleep before next prediction
                time.sleep(60)  # Check predictions every minute
                
            except Exception as e:
                logger.error(f"Error in usage prediction: {e}")
                time.sleep(60)
    
    def _predict_from_task_router(self):
        """
        Predict model usage based on TaskRouter's queue
        """
        try:
            # Prepare request for TaskRouter
            request = {
                "command": "GET_QUEUE_STATUS"
            }
            
            # Send request to TaskRouter
            self.tr_socket.send_json(request)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.tr_socket, zmq.POLLIN)
            if poller.poll(5000):  # 5s timeout
                response = self.tr_socket.recv_json()
                
                if response.get("status") == "SUCCESS":
                    queue_status = response.get("queue", {})
                    
                    # Analyze queue for pending tasks
                    pending_tasks = queue_status.get("pending_tasks", [])
                    
                    # Map task types to likely models
                    for task in pending_tasks:
                        task_type = task.get("task_type")
                        
                        # Map task type to model (simplified example)
                        if task_type == "asr":
                            model_to_preload = "whisper-large-v3"
                        elif task_type == "chat":
                            model_to_preload = "gpt-3.5-turbo"
                        elif task_type == "image_generation":
                            model_to_preload = "stable-diffusion-xl"
                        else:
                            continue
                        
                        # Check if model is already loaded
                        if model_to_preload not in self.loaded_models:
                            logger.info(f"Predictive loading: preloading {model_to_preload} for upcoming {task_type} task")
                            self._request_model_load(model_to_preload)
                            break  # Only preload one model at a time
                
                else:
                    # Failed to get queue status
                    logger.warning(f"Failed to get queue status from TaskRouter: {response.get('message', 'Unknown error')}")
            else:
                # Timeout waiting for response
                logger.warning("Timeout waiting for response from TaskRouter")
        
        except Exception as e:
            logger.error(f"Error predicting from TaskRouter: {e}")
    
    def _predict_from_usage_patterns(self):
        """
        Predict model usage based on historical patterns
        """
        try:
            current_time = time.time()
            
            # Analyze usage patterns
            for model_id, timestamps in self.usage_patterns.items():
                # Filter to recent usage
                recent_usage = [t for t in timestamps if current_time - t < self.prediction_window]
                
                if len(recent_usage) > 10:  # Enough data for prediction
                    # Calculate frequency and recency
                    usage_frequency = len(recent_usage) / self.prediction_window
                    last_used = max(recent_usage) if recent_usage else 0
                    time_since_last_use = current_time - last_used
                    
                    # Predict if model will be needed soon
                    if usage_frequency > 0.1 and time_since_last_use > 300 and time_since_last_use < 1800:
                        # High usage frequency, not used in last 5 min but used in last 30 min
                        # This indicates a potential upcoming use
                        
                        # Check if model is already loaded
                        if model_id not in self.loaded_models:
                            logger.info(f"Predictive loading: preloading {model_id} based on usage pattern")
                            self._request_model_load(model_id)
                            break  # Only preload one model at a time
        
        except Exception as e:
            logger.error(f"Error predicting from usage patterns: {e}")
    
    def _request_model_load(self, model_id: str, device: str = "MainPC", quantization: str = "FP16"):
        """
        Request ModelManagerAgent to load a model
        
        Args:
            model_id: ID of the model to load
            device: Target device (MainPC/PC2)
            quantization: Quantization level (FP32/FP16/INT8)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare request for ModelManagerAgent
            request = {
                "command": "LOAD_MODEL",
                "model_name": model_id,
                "device": device,
                "quantization_level": quantization
            }
            
            # Send request to ModelManagerAgent
            self.mma_socket.send_json(request)
            
            # Wait for response with timeout
            poller = zmq.Poller()
            poller.register(self.mma_socket, zmq.POLLIN)
            if poller.poll(5000):  # 5s timeout
                response = self.mma_socket.recv_json()
                
                if response.get("status") == "SUCCESS":
                    logger.info(f"Successfully requested load of model {model_id} on {device} with {quantization} quantization")
                    return True
                else:
                    # Failed to load model
                    logger.warning(f"Failed to load model {model_id}: {response.get('message', 'Unknown error')}")
                    return False
            else:
                # Timeout waiting for response
                logger.warning(f"Timeout waiting for response to load model {model_id}")
                return False
        
        except Exception as e:
            logger.error(f"Error requesting model load for {model_id}: {e}")
            return False

    def get_model_stats(self) -> Dict:
        """Get statistics about loaded models"""
        with self.lock:
            return {
                'total_models': len(self.loaded_models),
                'total_vram_usage': sum(m['vram_usage'] for m in self.loaded_models.values()),
                'models': {k: v['vram_usage'] for k, v in self.loaded_models.items()}
            }

    def _optimize_memory(self):
        """
        Advanced memory optimization loop that implements defragmentation,
        batch size optimization, and other VRAM efficiency improvements
        """
        while self.running:
            try:
                with self.lock:
                    # Check current VRAM usage and fragmentation
                    mainpc_vram, _ = self._get_vram_usage_from_sdt()
                    fragmentation = self._calculate_fragmentation()
                    
                    # Log current status
                    logger.debug(f"Memory optimization check - VRAM usage: {mainpc_vram['usage_ratio']*100:.1f}%, "
                                f"Fragmentation: {fragmentation*100:.1f}%")
                    
                    # Handle high fragmentation
                    if fragmentation > self.defragmentation_threshold:
                        logger.info(f"High memory fragmentation detected: {fragmentation*100:.1f}%")
                        self._defragment_memory()
                    
                    # Apply kernel fusion for active models
                    self._apply_kernel_fusion()
                    
                    # Check batch sizes
                    if mainpc_vram['usage_ratio'] < 0.5:  # Less than 50% VRAM used
                        self._optimize_batch_sizes()
                
                time.sleep(self.optimization_interval)
            except Exception as e:
                logger.error(f"Error in memory optimization: {e}")
                time.sleep(60)  # Longer delay on error
    
    def _defragment_memory(self):
        """Defragment GPU memory"""
        try:
            # Unload all models
            models_to_reload = list(self.loaded_models.keys())
            for model_id in models_to_reload:
                self.unregister_model(model_id)
            
            # Clear CUDA cache
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # Reload models in optimal order
            for model_id in models_to_reload:
                if self.can_load_model(model_id):
                    self._preload_model(model_id)
            
            logger.info("Memory defragmentation completed")
        except Exception as e:
            logger.error(f"Error during memory defragmentation: {e}")

    def _optimize_batch_sizes(self):
        """Optimize batch sizes based on available VRAM"""
        try:
            vram_usage = self.get_vram_usage()
            available_vram = vram_usage['free']
            
            for model_id, model_info in self.loaded_models.items():
                if hasattr(model_info['instance'], 'batch_size'):
                    current_batch = model_info['instance'].batch_size
                    optimal_batch = self._calculate_optimal_batch_size(
                        model_id, available_vram
                    )
                    if optimal_batch != current_batch:
                        model_info['instance'].batch_size = optimal_batch
                        logger.info(f"Optimized batch size for {model_id}: {optimal_batch}")
        except Exception as e:
            logger.error(f"Error optimizing batch sizes: {e}")

    def _apply_kernel_fusion(self):
        """Apply kernel fusion to optimize memory usage"""
        # Implementation depends on specific model architectures
        pass

    def _optimize_memory_mapping(self):
        """Optimize memory mapping for better performance"""
        # Implementation depends on specific hardware
        pass

    def _calculate_fragmentation(self) -> float:
        """
        Calculate GPU memory fragmentation ratio
        
        Returns:
            float: Fragmentation ratio (0.0-1.0)
        """
        try:
            if torch.cuda.is_available():
                # Get memory stats
                allocated = torch.cuda.memory_allocated() / (1024 * 1024)  # MB
                reserved = torch.cuda.memory_reserved() / (1024 * 1024)    # MB
                
                if reserved > 0:
                    # Fragmentation = (reserved - allocated) / reserved
                    return (reserved - allocated) / reserved
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating fragmentation: {e}")
            return 0.0

    def _calculate_optimal_batch_size(self, model_id: str, available_vram: float) -> int:
        """Calculate optimal batch size based on available VRAM"""
        try:
            # This is a simplified calculation
            # In practice, this would depend on model architecture
            base_batch_size = 1
            vram_per_sample = self.model_vram_requirements.get(model_id, 1.0) / base_batch_size
            
            if vram_per_sample > 0:
                # Leave 20% buffer
                optimal_batch = int(available_vram * 0.8 / vram_per_sample)
                return max(1, optimal_batch)  # At least batch size 1
            return 1
        except Exception as e:
            logger.error(f"Error calculating optimal batch size: {e}")
            return 1

    def _preload_model(self, model_id: str):
        """Preload a model based on usage prediction"""
        # This would connect to ModelManagerAgent to request loading
        logger.info(f"Preloading model {model_id} based on usage prediction")
        # Implementation would depend on model loading mechanism

    def get_advanced_stats(self) -> Dict:
        """Get advanced statistics about memory usage"""
        with self.lock:
            return {
                'vram_usage': self.get_vram_usage(),
                'fragmentation': self._calculate_fragmentation(),
                'models': {
                    k: {
                        'vram_usage': v['vram_usage'],
                        'last_used': time.time() - v['last_used'],
                        'idle_status': 'idle' if time.time() - v['last_used'] > self.idle_timeout else 'active'
                    } for k, v in self.loaded_models.items()
                }
            }
    
    def _monitor_idle_models(self):
        """
        Monitor and unload idle models based on timeout
        """
        while self.running:
            try:
                # Get idle models for both devices
                mainpc_idle_models = self._get_idle_models("MainPC")
                pc2_idle_models = self._get_idle_models("PC2")
                
                # Unload idle models on MainPC
                for model_id in mainpc_idle_models:
                    logger.info(f"MainPC model {model_id} has been idle for more than {self.idle_timeout} seconds, unloading")
                    self._request_model_unload(model_id)
                    time.sleep(1)  # Brief pause between unloads to avoid flooding
                
                # Unload idle models on PC2
                for model_id in pc2_idle_models:
                    logger.info(f"PC2 model {model_id} has been idle for more than {self.idle_timeout} seconds, unloading")
                    self._request_model_unload(model_id)
                    time.sleep(1)  # Brief pause between unloads to avoid flooding
                
                time.sleep(self.idle_check_interval)
            except Exception as e:
                logger.error(f"Error in idle model monitoring: {e}")
                time.sleep(60)  # Longer delay on error
    
    def _update_model_vram_requirements(self):
        """
        Update the model VRAM requirements based on actual usage
        """
        try:
            with self.lock:
                for model_id, model_info in self.loaded_models.items():
                    vram_usage = model_info.get("vram_usage_mb", 0)
                    if vram_usage > 0:
                        # Store actual VRAM usage for future reference
                        self.model_vram_requirements[model_id] = vram_usage
                        logger.debug(f"Updated VRAM requirement for {model_id}: {vram_usage}MB")
        except Exception as e:
            logger.error(f"Error updating model VRAM requirements: {e}")
    
    def _track_model_usage(self, model_id):
        """
        Track when a model is used to build usage patterns
        
        Args:
            model_id: ID of the model being used
        """
        try:
            current_time = time.time()
            with self.lock:
                self.usage_patterns[model_id].append(current_time)
                
                # Trim old timestamps
                self.usage_patterns[model_id] = [
                    t for t in self.usage_patterns[model_id]
                    if current_time - t < self.prediction_window
                ]
        except Exception as e:
            logger.error(f"Error tracking model usage: {e}")
    
    def run(self):
        """
        Main run method for the agent
        """
        self.start_time = time.time()
        logger.info("VRAMOptimizerAgent starting...")
        
        # Start monitoring threads
        self.start_monitoring()
        
        # Set up ZMQ socket for incoming requests
        socket = self.context.socket(zmq.REP)
        
        # Apply secure ZMQ if enabled
        secure_zmq = os.environ.get("SECURE_ZMQ", "0") == "1"
        if secure_zmq:
            try:
                from main_pc_code.src.network.secure_zmq import configure_secure_server, start_auth
                start_auth()
                socket = configure_secure_server(socket)
                logger.info("Using secure ZMQ for request handling")
            except Exception as e:
                logger.warning(f"Failed to configure secure ZMQ: {e}")
        
        # Bind to port
        bind_address = f"tcp://*:{self.port}"
        socket.bind(bind_address)
        logger.info(f"VRAMOptimizerAgent listening on {bind_address}")
        
                # Register with SystemDigitalTwin
        try:
            from main_pc_code.utils.service_discovery_client import register_service

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env
            register_service(
                name="VRAMOptimizerAgent",
                location="MainPC",
                port=self.port
            )
            logger.info("Registered with SystemDigitalTwin")
        except Exception as e:
            logger.warning(f"Failed to register with SystemDigitalTwin: {e}")
        
        # Initialize VRAM monitoring immediately
        try:
            mainpc_vram, pc2_vram = self._get_vram_usage_from_sdt()
            logger.info(f"Initial VRAM status - MainPC: {mainpc_vram['usage_ratio']*100:.1f}%, "
                       f"PC2: {pc2_vram['usage_ratio']*100:.1f}% (if available)")
        except Exception as e:
            logger.warning(f"Failed to get initial VRAM status: {e}")
        
        # Main loop - handle incoming requests
        while self.running:
            try:
                # Wait for incoming message
                message = socket.recv_json()
                logger.debug(f"Received message: {message}")
                
                # Process request
                response = self.process_request(message)
                
                # Send response
                socket.send_json(response)
                
            except zmq.ZMQError as e:
                if self.running:  # Only log if we're still supposed to be running
                    logger.error(f"ZMQ error: {e}")
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                
                # Send error response if socket is still connected
                try:
                    socket.send_json({"status": "ERROR", "message": str(e)})
                except:
                    pass
                
                time.sleep(1)
        
        # Clean up
        socket.close()
        logger.info("VRAMOptimizerAgent stopped")
    
    def cleanup(self):
        """
        Clean up resources
        """
        logger.info("Cleaning up VRAMOptimizerAgent resources...")
        self.running = False
        
        # Close ZMQ sockets
        if hasattr(self, 'sdt_socket') and self.sdt_socket:
            self.sdt_socket.close()
        
        if hasattr(self, 'mma_socket') and self.mma_socket:
            self.mma_socket.close()
        
        if hasattr(self, 'rc_socket') and self.rc_socket:
            self.rc_socket.close()
        
        if hasattr(self, 'mef_socket') and self.mef_socket:
            self.mef_socket.close()
        
        # Wait for threads to finish
        if hasattr(self, 'monitor_thread') and self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        if hasattr(self, 'optimization_thread') and self.optimization_thread:
            self.optimization_thread.join(timeout=2)
        
        if hasattr(self, 'prediction_thread') and self.prediction_thread:
            self.prediction_thread.join(timeout=2)
        
        if hasattr(self, 'idle_monitor_thread') and self.idle_monitor_thread:
            self.idle_monitor_thread.join(timeout=2)
        
        logger.info("VRAMOptimizerAgent resources cleaned up")
    
    def stop(self):
        """
        Stop the agent
        """
        self.running = False

    def process_request(self, request):
        """
        Process incoming ZMQ requests
        
        Args:
            request: Request dictionary
            
        Returns:
            Response dictionary
        """
        try:
            command = request.get("command", "")
            
            if command == "TRACK_MODEL_USAGE":
                model_id = request.get("model_id")
                if model_id:
                    self._track_model_usage(model_id)
                    return {"status": "SUCCESS", "message": f"Tracked usage of model {model_id}"}
                else:
                    return {"status": "ERROR", "message": "Missing model_id parameter"}
            
            elif command == "GET_VRAM_STATUS":
                mainpc_vram, pc2_vram = self._get_vram_usage_from_sdt()
                loaded_models = self._get_loaded_models_from_mma()
                
                response = {
                    "status": "SUCCESS",
                    "mainpc_vram": mainpc_vram,
                    "pc2_vram": pc2_vram,
                    "loaded_models": loaded_models,
                    "thresholds": self.vram_thresholds
                }
                
                return response
            
            elif command == "SET_IDLE_TIMEOUT":
                timeout = request.get("timeout_seconds")
                if timeout and isinstance(timeout, int) and timeout > 0:
                    self.idle_timeout = timeout
                    return {"status": "SUCCESS", "message": f"Idle timeout set to {timeout} seconds"}
                else:
                    return {"status": "ERROR", "message": "Invalid timeout parameter"}
            
            elif command == "SET_VRAM_THRESHOLD":
                threshold_type = request.get("threshold_type")
                value = request.get("value")
                
                if threshold_type in self.vram_thresholds and isinstance(value, (int, float)) and 0 < value < 1:
                    self.vram_thresholds[threshold_type] = value
                    return {"status": "SUCCESS", "message": f"VRAM threshold {threshold_type} set to {value}"}
                else:
                    return {"status": "ERROR", "message": "Invalid threshold parameters"}
            
            elif command == "HEALTH_CHECK":
                return self._health_check()
            
            else:
                return {"status": "ERROR", "message": f"Unknown command: {command}"}
        
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {"status": "ERROR", "message": str(e)}
    
    def _health_check(self):
        """
        Perform a health check
        
        Returns:
            dict: Health check result
        """
        # Check if we can communicate with the SystemDigitalTwin
        sdt_reachable = False
        def check_sdt_health():
            request = {"command": "PING"}
            self.sdt_socket.send_json(request)
            
            poller = zmq.Poller()
            poller.register(self.sdt_socket, zmq.POLLIN)
            if poller.poll(5000):  # 5s timeout
                response = self.sdt_socket.recv_json()
                return response.get("status") == "SUCCESS"
            return False
            
        sdt_reachable = SafeExecutor.execute_with_fallback(
            check_sdt_health,
            fallback_value=False,
            context="SDT health check",
            expected_exceptions=(zmq.ZMQError, json.JSONDecodeError, TimeoutError)
        )
        
        # Check if we can communicate with the ModelManagerAgent
        mma_reachable = False
        def check_mma_health():
            request = {"command": "HEALTH_CHECK"}
            self.mma_socket.send_json(request)
            
            poller = zmq.Poller()
            poller.register(self.mma_socket, zmq.POLLIN)
            if poller.poll(5000):  # 5s timeout
                response = self.mma_socket.recv_json()
                return response.get("status") == "SUCCESS"
            return False
            
        mma_reachable = SafeExecutor.execute_with_fallback(
            check_mma_health,
            fallback_value=False,
            context="MMA health check",
            expected_exceptions=(zmq.ZMQError, json.JSONDecodeError, TimeoutError)
        )
        
        # Check if we can communicate with the RequestCoordinator
        rc_reachable = False
        def check_rc_health():
            request = {"action": "ping"}
            self.rc_socket.send_json(request)
            poller = zmq.Poller()
            poller.register(self.rc_socket, zmq.POLLIN)
            if poller.poll(5000):
                response = self.rc_socket.recv_json()
                return response.get("status") == "success"
            return False
            
        rc_reachable = SafeExecutor.execute_with_fallback(
            check_rc_health,
            fallback_value=False,
            context="RC health check",
            expected_exceptions=(zmq.ZMQError, json.JSONDecodeError, TimeoutError)
        )

        # Check if we can communicate with the ModelEvaluationFramework
        mef_reachable = False
        def check_mef_health():
            request = {"command": "HEALTH_CHECK"}
            self.mef_socket.send_json(request)
            poller = zmq.Poller()
            poller.register(self.mef_socket, zmq.POLLIN)
            if poller.poll(5000):
                response = self.mef_socket.recv_json()
                return response.get("status") == "SUCCESS"
            return False
            
        mef_reachable = SafeExecutor.execute_with_fallback(
            check_mef_health,
            fallback_value=False,
            context="MEF health check",
            expected_exceptions=(zmq.ZMQError, json.JSONDecodeError, TimeoutError)
        )
        
        # Build health status
        status = "HEALTHY" if sdt_reachable and mma_reachable and rc_reachable and mef_reachable else "UNHEALTHY"
        
        return {
            "status": "SUCCESS",
            "health_status": {
                "status": status,
                "sdt_reachable": sdt_reachable,
                "mma_reachable": mma_reachable,
                "rc_reachable": rc_reachable,
                "mef_reachable": mef_reachable,
                "uptime_seconds": int(time.time() - self.start_time) if hasattr(self, 'start_time') else 0,
                "connected_services": {
                    "SystemDigitalTwin": sdt_reachable,
                    "ModelManagerAgent": mma_reachable,
                    "RequestCoordinator": rc_reachable,
                    "ModelEvaluationFramework": mef_reachable
                }
            }
        }


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

# Main entry point
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = VRAMOptimizerAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")

# Agent initialization completed
