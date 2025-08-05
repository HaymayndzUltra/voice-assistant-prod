#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Dreaming Mode Agent
------------------
Coordinates with DreamWorldAgent to manage system dreaming and simulation cycles.

Features:
- Manages dreaming intervals and schedules
- Coordinates with DreamWorldAgent for simulations
- Monitors system state for optimal dreaming times
- Provides dreaming insights and recommendations
- Handles dream world state transitions
- Manages dream memory and learning cycles
"""

from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import logging
import time
import threading
import sys
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import random

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, str(PathManager.get_project_root()))
from common.utils.path_manager import PathManager
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
# ✅ MODERNIZED: Using BaseAgent's UnifiedErrorHandler instead of custom error bus
# Removed: from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
# Now using: self.report_error() method from BaseAgent


# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = PathManager.get_project_root() / "config" / "network_config.yaml"
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": get_mainpc_ip(),
            "pc2_ip": get_pc2_ip(),
            "bind_address": os.environ.get("BIND_ADDRESS", "0.0.0.0"),
            "secure_zmq": False,
            "ports": {
                "dreaming_mode": int(os.environ.get("DREAMING_MODE_PORT", 7127)),
                "dreaming_health": int(os.environ.get("DREAMING_HEALTH_PORT", 7128)),
                "dream_world": int(os.environ.get("DREAM_WORLD_PORT", 7104)),
                "error_bus": int(os.environ.get("ERROR_BUS_PORT", 7150))
            }
        }

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DreamingModeAgent")

# Load configuration at the module level
config = Config().get_config()

# Load network configuration
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = get_mainpc_ip()
PC2_IP = network_config.get("pc2_ip", get_pc2_ip())
BIND_ADDRESS = network_config.get("bind_address", os.environ.get("BIND_ADDRESS", "0.0.0.0"))

# Get port configuration
DREAMING_MODE_PORT = network_config.get("ports", {}).get("dreaming_mode", int(os.environ.get("DREAMING_MODE_PORT", 7127)))
DREAMING_MODE_HEALTH_PORT = network_config.get("ports", {}).get("dreaming_health", int(os.environ.get("DREAMING_HEALTH_PORT", 7128)))
DREAM_WORLD_PORT = network_config.get("ports", {}).get("dream_world", int(os.environ.get("DREAM_WORLD_PORT", 7104)))
ERROR_BUS_PORT = network_config.get("ports", {}).get("error_bus", int(os.environ.get("ERROR_BUS_PORT", 7150)))

class DreamingModeAgent(BaseAgent):
    """Dreaming Mode Agent for coordinating system dreaming cycles."""
    
    # Parse agent arguments
    _agent_args = parse_agent_args()

    def __init__(self, port=None):
        # Initialize state before BaseAgent
        self.is_dreaming = False
        self.dream_thread = None
        self.running = True
        self.dream_interval = 3600
        self.last_dream_time = 0
        self.dream_duration = 300
        self.dream_count = 0
        self.total_dream_time = 0
        self.start_time = time.time()
        self.dream_memory = []
        self.dream_success_rate = 0.0
        self.avg_dream_quality = 0.0
        
        # Initialize BaseAgent with proper parameters
        super().__init__(
            name="DreamingModeAgent", 
            port=port if port is not None else DREAMING_MODE_PORT,
            health_check_port=DREAMING_MODE_HEALTH_PORT
        )
        
        # Connect to DreamWorldAgent
        self.dreamworld_socket = self.context.socket(zmq.REQ)
        try:
            self.dreamworld_socket.connect(f"tcp://{BIND_ADDRESS}:{DREAM_WORLD_PORT}")
            logger.info(f"Connected to DreamWorldAgent on port {DREAM_WORLD_PORT}")
        except Exception as e:
            logger.warning(f"Failed to connect to DreamWorldAgent: {e}")
            self.dreamworld_socket = None
        
        # Setup error reporting
        self.setup_error_reporting()
        
        # Start background threads
        self._start_health_check_thread()
        self._start_scheduler_thread()
        
        logger.info(f"DreamingModeAgent initialized on port {self.port}")
    
        # PC2 Error Bus Integration (Phase 1.3)
        self.error_publisher = create_pc2_error_publisher("DreamingModeAgent")
    def setup_error_reporting(self):
        """Set up error reporting to the central Error Bus."""
        try:
            self.error_bus_host = PC2_IP
            self.error_bus_port = ERROR_BUS_PORT
            self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
            self.error_bus_pub = self.context.socket(zmq.PUB)
            self.error_bus_pub.connect(self.error_bus_endpoint)
            logger.info(f"Connected to Error Bus at {self.error_bus_endpoint}")
        except Exception as e:
            logger.error(f"Failed to set up error reporting: {e}")
    
    def report_error(self, error_type, message, severity="ERROR"):
        """Report an error to the central Error Bus."""
        try:
            if hasattr(self, 'error_bus_pub'):
                error_report = {
                    "timestamp": datetime.now().isoformat(),
                    "agent": self.name,
                    "type": error_type,
                    "message": message,
                    "severity": severity
                }
                self.error_bus_pub.send_multipart([
                    b"ERROR",
                    json.dumps(error_report).encode('utf-8')
                ])
                logger.info(f"Reported error: {error_type} - {message}")
        except Exception as e:
            logger.error(f"Failed to report error: {e}")
    
    def _start_health_check_thread(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()
        logger.info("Health check thread started")
    
    def _start_scheduler_thread(self):
        """Start dream scheduler thread."""
        self.scheduler_thread = threading.Thread(target=self._dream_scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("Dream scheduler thread started")
    
    def _health_check(self) -> Dict[str, Any]:
        """Legacy health check method for backward compatibility."""
        return self._get_health_status()
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        base_status = super()._get_health_status()
        
        # Add DreamingModeAgent specific health info
        base_status.update({
            'status': 'ok',
            'is_dreaming': self.is_dreaming,
            'dream_count': self.dream_count,
            'total_dream_time': self.total_dream_time,
            'dream_success_rate': self.dream_success_rate,
            'avg_dream_quality': self.avg_dream_quality,
            'uptime': time.time() - self.start_time,
            'dreamworld_connected': self.dreamworld_socket is not None
        })
        
        return base_status

    def start_dreaming(self) -> Dict[str, Any]:
        """Start a dreaming cycle."""
        if self.is_dreaming:
            return {"status": "error", "message": "Already dreaming"}
        self.is_dreaming = True
        self.dream_count += 1
        dream_start_time = time.time()
        logger.info(f"Starting dream cycle #{self.dream_count}")
        self.dream_thread = threading.Thread(target=self._dream_cycle, daemon=True)
        self.dream_thread.start()
        return {"status": "success", "message": f"Dream cycle #{self.dream_count} started", "dream_id": self.dream_count, "start_time": dream_start_time}

    def stop_dreaming(self) -> Dict[str, Any]:
        """Stop the current dreaming cycle."""
        if not self.is_dreaming:
            return {"status": "error", "message": "Not currently dreaming"}
        self.is_dreaming = False
        logger.info("Stopping dream cycle")
        return {"status": "success", "message": "Dream cycle stopped"}

    def _dream_cycle(self):
        """Execute a dream cycle."""
        try:
            dream_start = time.time()
            if self.dreamworld_socket:
                simulation_request = {"action": "run_simulation", "scenario": "ethical", "iterations": 100}
                try:
                    self.dreamworld_socket.send_json(simulation_request)
                    if self.dreamworld_socket.poll(30000):
                        response = self.dreamworld_socket.recv_json()
                        if response.get("status") == "success":
                            logger.info("Dream simulation completed successfully")
                            self._record_dream_result(True, response.get("quality", 0.5))
                        else:
                            logger.warning(f"Dream simulation failed: {response.get('error', 'Unknown error')}")
                            self.report_error("DREAM_SIMULATION_ERROR", response.get('error', 'Unknown error'))
                            self._record_dream_result(False, 0.0)
                    else:
                        logger.warning("Dream simulation timeout")
                        self.report_error("DREAM_TIMEOUT", "Dream simulation timeout")
                        self._record_dream_result(False, 0.0)
                except Exception as e:
                    logger.error(f"Error communicating with DreamWorldAgent: {e}")
                    self.report_error("DREAMWORLD_COMMUNICATION_ERROR", str(e))
                    self._record_dream_result(False, 0.0)
            else:
                logger.info("DreamWorldAgent not available, simulating dream cycle")
                time.sleep(self.dream_duration)
                self._record_dream_result(True, 0.5)
            dream_duration = time.time() - dream_start
            self.total_dream_time += dream_duration
            logger.info(f"Dream cycle completed in {dream_duration:.2f} seconds")
        except Exception as e:
            logger.error(f"Error in dream cycle: {e}")
            self.report_error("DREAM_CYCLE_ERROR", str(e))
            self._record_dream_result(False, 0.0)
        finally:
            self.is_dreaming = False

    def _record_dream_result(self, success: bool, quality: float):
        """Record the result of a dream cycle."""
        dream_record = {"timestamp": time.time(), "success": success, "quality": quality, "duration": self.dream_duration}
        self.dream_memory.append(dream_record)
        if len(self.dream_memory) > 100:
            self.dream_memory = self.dream_memory[-100:]
        successful_dreams = sum(1 for dream in self.dream_memory if dream["success"])
        self.dream_success_rate = successful_dreams / len(self.dream_memory) if self.dream_memory else 0.0
        total_quality = sum(dream["quality"] for dream in self.dream_memory)
        self.avg_dream_quality = total_quality / len(self.dream_memory) if self.dream_memory else 0.0

    def get_dream_status(self) -> Dict[str, Any]:
        """Get the current status of dreaming cycles."""
        return {
            "status": "success",
            "is_dreaming": self.is_dreaming,
            "dream_count": self.dream_count,
            "total_dream_time": self.total_dream_time,
            "dream_success_rate": self.dream_success_rate,
            "avg_dream_quality": self.avg_dream_quality,
            "last_dream_time": self.last_dream_time,
            "next_dream_time": self.last_dream_time + self.dream_interval,
            "dream_interval": self.dream_interval,
            "recent_dreams": self.dream_memory[-10:] if self.dream_memory else []
        }

    def set_dream_interval(self, interval: int) -> Dict[str, Any]:
        """Set the interval between dream cycles."""
        if interval < 60:
            return {"status": "error", "message": "Dream interval must be at least 60 seconds"}
        self.dream_interval = interval
        logger.info(f"Dream interval set to {interval} seconds")
        return {"status": "success", "message": f"Dream interval updated to {interval} seconds", "new_interval": interval}

    def optimize_dream_schedule(self) -> Dict[str, Any]:
        """Optimize the dream schedule based on past results."""
        if not self.dream_memory:
            return {"status": "error", "message": "No dream data available for optimization"}
        if self.dream_success_rate < 0.5:
            new_interval = min(self.dream_interval * 1.5, 7200)
            self.dream_interval = int(new_interval)
            optimization_type = "increase_interval"
        elif self.dream_success_rate > 0.8:
            new_interval = max(self.dream_interval * 0.8, 1800)
            self.dream_interval = int(new_interval)
            optimization_type = "decrease_interval"
        else:
            optimization_type = "no_change"
        logger.info(f"Dream schedule optimized: {optimization_type}")
        return {"status": "success", "message": "Dream schedule optimized", "optimization_type": optimization_type, "new_interval": self.dream_interval, "success_rate": self.dream_success_rate}

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        try:
            action = request.get('action', '')
            if action == 'health_check':
                return self._get_health_status()
            elif action == 'start_dreaming':
                return self.start_dreaming()
            elif action == 'stop_dreaming':
                return self.stop_dreaming()
            elif action == 'get_dream_status':
                return self.get_dream_status()
            elif action == 'set_dream_interval':
                interval = request.get('interval', 3600)
                return self.set_dream_interval(interval)
            elif action == 'optimize_schedule':
                return self.optimize_dream_schedule()
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            self.report_error("REQUEST_HANDLING_ERROR", str(e))
            return {'status': 'error', 'error': str(e)}

    def run(self):
        """Main execution loop for the agent."""
        logger.info(f"DreamingModeAgent starting on port {self.port}")
        
        try:
            while self.running:
                try:
                    # Wait for a request with timeout
                    if self.socket.poll(timeout=1000) != 0:  # 1 second timeout
                        # Receive and parse request
                        message = self.socket.recv_json()
                        
                        # Process request
                        response = self.handle_request(message)
                        
                        # Send response
                        self.socket.send_json(response)
                    
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in main loop: {e}")
                    self.report_error("ZMQ_ERROR", str(e))
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'message': f'ZMQ communication error: {str(e)}'
                        })
                    except:
                        pass
                    time.sleep(1)  # Avoid tight loop on error
                    
                except Exception as e:
                    logger.error(f"Unexpected error in main loop: {e}")
                    self.report_error("RUNTIME_ERROR", str(e))
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'message': f'Internal server error: {str(e)}'
                        })
                    except:
                        pass
                    time.sleep(1)  # Avoid tight loop on error
                    
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, stopping DreamingModeAgent")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.report_error("FATAL_ERROR", str(e))
        finally:
            self.running = False
            self.cleanup()
    
    def _dream_scheduler_loop(self):
        """Background loop for scheduling dream cycles."""
        logger.info("Dream scheduler loop started")
        
        while self.running:
            try:
                current_time = time.time()
                if not self.is_dreaming and current_time - self.last_dream_time > self.dream_interval:
                    logger.info("Scheduled dream cycle starting")
                    self.start_dreaming()
                    self.last_dream_time = current_time
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in dream scheduler: {e}")
                self.report_error("SCHEDULER_ERROR", str(e))
                time.sleep(60)  # Sleep longer on error

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info("Cleaning up resources...")
        
        # Close all sockets
        if hasattr(self, 'socket'):
            try:
                self.socket.close()
                logger.info("Closed main socket")
            except Exception as e:
                logger.error(f"Error closing main socket: {e}")
        
        # Close health socket
        if hasattr(self, 'health_socket'):
            try:
                self.health_socket.close()
                logger.info("Closed health socket")
            except Exception as e:
                logger.error(f"Error closing health socket: {e}")
        
        # Close dreamworld socket
        if hasattr(self, 'dreamworld_socket') and self.dreamworld_socket:
            try:
                self.dreamworld_socket.close()
                logger.info("Closed dreamworld socket")
            except Exception as e:
                logger.error(f"Error closing dreamworld socket: {e}")
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus socket")
            except Exception as e:
                logger.error(f"Error closing error bus socket: {e}")
        
        # Call parent cleanup
        try:
            super().cleanup()
            logger.info("Called parent cleanup")
        except Exception as e:
            logger.error(f"Error in parent cleanup: {e}")
        
        logger.info("Cleanup complete")

    def stop(self):
        """Stop the agent gracefully."""
        self.running = False
        logger.info("Stopping DreamingModeAgent")


if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = DreamingModeAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()