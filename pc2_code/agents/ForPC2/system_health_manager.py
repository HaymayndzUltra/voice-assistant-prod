#!/usr/bin/env python3
"""
System Health Manager

This agent monitors the health of all system components and services,
with a special focus on the memory system components.
"""

import os
import sys
import time
import json
import logging
import threading
import zmq
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add the project's pc2_code directory to the Python path
PC2_CODE_DIR = Path(__file__).resolve().parent.parent.parent
if PC2_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, PC2_CODE_DIR.as_posix())

# Add the project's root directory to the Python path
ROOT_DIR = PC2_CODE_DIR.parent
if ROOT_DIR.as_posix() not in sys.path:
    sys.path.insert(0, ROOT_DIR.as_posix())

from common.core.base_agent import BaseAgent

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/system_health_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SystemHealthManager")

class SystemHealthManager(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()"""
    System Health Manager
    
    Monitors the health of all system components and services,
    with a special focus on the memory system components.
    """
    
    def __init__(self, port: int = 7121, health_check_port: int = 8121, **kwargs):
        super().__init__(name="SystemHealthManager", port=port, health_check_port=health_check_port, **kwargs)
        
        # Configuration
        self.memory_orchestrator_host = os.environ.get("PC2_IP", "localhost")
        self.memory_orchestrator_port = 7140
        self.memory_orchestrator_endpoint = f"tcp://{self.memory_orchestrator_host}:{self.memory_orchestrator_port}"
        
        self.memory_scheduler_host = os.environ.get("PC2_IP", "localhost")
        self.memory_scheduler_port = 7142
        self.memory_scheduler_endpoint = f"tcp://{self.memory_scheduler_host}:{self.memory_scheduler_port}"
        
        # Error bus configuration
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        
        # ZMQ setup
        self.orchestrator_socket = None
        self.scheduler_socket = None
        self.error_bus_pub = None
        self._setup_zmq()
        
        # Health check configuration
        self.health_check_interval = 60  # seconds
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._run_health_checks, daemon=True)
        self.health_check_thread.start()
        
        logger.info(f"{self.name} initialized successfully")
    
    def _setup_zmq(self):
        """Set up ZMQ connections"""
        try:
            # Connection to MemoryOrchestratorService
            self.orchestrator_socket = self.context.socket(zmq.REQ)
            self.orchestrator_socket.connect(self.memory_orchestrator_endpoint)
            self.orchestrator_socket.setsockopt(zmq.LINGER, 0)
            self.orchestrator_socket.setsockopt(zmq.RCVTIMEO, 5000)
            self.orchestrator_socket.setsockopt(zmq.SNDTIMEO, 5000)
            logger.info(f"Connected to MemoryOrchestratorService at {self.memory_orchestrator_endpoint}")
            
            # Connection to MemoryScheduler
            self.scheduler_socket = self.context.socket(zmq.REQ)
            self.scheduler_socket.connect(self.memory_scheduler_endpoint)
            self.scheduler_socket.setsockopt(zmq.LINGER, 0)
            self.scheduler_socket.setsockopt(zmq.RCVTIMEO, 5000)
            self.scheduler_socket.setsockopt(zmq.SNDTIMEO, 5000)
            logger.info(f"Connected to MemoryScheduler at {self.memory_scheduler_endpoint}")
            
            # Connection to Error Bus
            self.error_bus_pub = self.context.socket(zmq.PUB)
            self.error_bus_pub.connect(self.error_bus_endpoint)
            logger.info(f"Connected to error bus at {self.error_bus_endpoint}")
        except Exception as e:
            logger.error(f"Error setting up ZMQ connections: {e}")
            self._report_error("zmq_setup_error", str(e))
    
    def _run_health_checks(self):
        """Run periodic health checks on all monitored services"""
        logger.info("Health check thread started")
        while self.running:
            try:
                self._check_memory_orchestrator_health()
                self._check_memory_scheduler_health()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health check thread: {e}")
                self._report_error("health_check_error", str(e))
    
    def _check_memory_orchestrator_health(self):
        """Check the health of the MemoryOrchestratorService"""
        try:
            if self.orchestrator_socket is None:
                logger.error("Orchestrator socket is not initialized")
                return
                
            request = {
                "action": "health_check",
                "data": {}
            }
            self.orchestrator_socket.send_json(request)
            response = self.orchestrator_socket.recv_json()
            
            # Check if response is a dictionary before using .get()
            if isinstance(response, dict):
                if response.get("status") == "success":
                    logger.debug("MemoryOrchestratorService is healthy")
                else:
                    logger.warning(f"MemoryOrchestratorService health check failed: {response.get('message', 'Unknown error')}")
                    self._report_error("memory_orchestrator_health_check_failed", str(response.get('message', 'Unknown error')))
            else:
                logger.error(f"Invalid response format from MemoryOrchestratorService: {response}")
                self._report_error("memory_orchestrator_invalid_response", f"Invalid response format: {str(response)}")
        except zmq.error.Again:
            logger.error("Request to MemoryOrchestratorService timed out")
            self._report_error("memory_orchestrator_timeout", "Health check request timed out")
        except Exception as e:
            logger.error(f"Error checking MemoryOrchestratorService health: {e}")
            self._report_error("memory_orchestrator_health_check_error", str(e))
    
    def _check_memory_scheduler_health(self):
        """Check the health of the MemoryScheduler"""
        try:
            if self.scheduler_socket is None:
                logger.error("Scheduler socket is not initialized")
                return
                
            request = {
                "action": "health_check",
                "data": {}
            }
            self.scheduler_socket.send_json(request)
            response = self.scheduler_socket.recv_json()
            
            # Check if response is a dictionary before using .get()
            if isinstance(response, dict):
                if response.get("status") == "success":
                    logger.debug("MemoryScheduler is healthy")
                else:
                    logger.warning(f"MemoryScheduler health check failed: {response.get('message', 'Unknown error')}")
                    self._report_error("memory_scheduler_health_check_failed", str(response.get('message', 'Unknown error')))
            else:
                logger.error(f"Invalid response format from MemoryScheduler: {response}")
                self._report_error("memory_scheduler_invalid_response", f"Invalid response format: {str(response)}")
        except zmq.error.Again:
            logger.error("Request to MemoryScheduler timed out")
            self._report_error("memory_scheduler_timeout", "Health check request timed out")
        except Exception as e:
            logger.error(f"Error checking MemoryScheduler health: {e}")
            self._report_error("memory_scheduler_health_check_error", str(e))
            
    def _report_error(self, error_type: str, error_message: str):
        """Report errors to the central error bus"""
        try:
            if self.error_bus_pub:
                error_data = {
                    "timestamp": time.time(),
                    "agent": self.name,
                    "error_type": error_type,
                    "message": error_message,
                    "severity": "ERROR"
                }
                self.error_bus_pub.send_string(f"ERROR:{json.dumps(error_data)}")
        except Exception as e:
            logger.error(f"Failed to report error to error bus: {e}")
            
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests"""
        if not isinstance(request, dict):
            return {"status": "error", "message": "Invalid request format"}
            
        action = request.get("action")
        data = request.get("data", {})
        
        if action == "health_check":
            return self.handle_health_check(data)
        elif action == "get_system_status":
            return self.get_system_status(data)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}
    
    def handle_health_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check requests"""
        return {
            "status": "success",
            "agent": self.name,
            "uptime": time.time() - self.start_time
        }
    
    def get_system_status(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get the status of all monitored system components"""
        # This would be expanded in a real implementation to check all system components
        return {
            "status": "success",
            "memory_system": {
                "orchestrator": self._get_orchestrator_status(),
                "scheduler": self._get_scheduler_status()
            }
        }
    
    def _get_orchestrator_status(self) -> Dict[str, Any]:
        """Get the status of the MemoryOrchestratorService"""
        try:
            if self.orchestrator_socket is None:
                return {"status": "error", "message": "Orchestrator socket is not initialized"}
                
            request = {
                "action": "get_memory_system_status",
                "data": {}
            }
            self.orchestrator_socket.send_json(request)
            response = self.orchestrator_socket.recv_json()
            
            # Ensure we return a dictionary
            if isinstance(response, dict):
                return response
            else:
                return {"status": "error", "message": f"Invalid response format: {str(response)}"}
        except Exception as e:
            logger.error(f"Error getting orchestrator status: {e}")
            return {"status": "error", "message": str(e)}
    
    def _get_scheduler_status(self) -> Dict[str, Any]:
        """Get the status of the MemoryScheduler"""
        try:
            if self.scheduler_socket is None:
                return {"status": "error", "message": "Scheduler socket is not initialized"}
                
            request = {
                "action": "health_check",
                "data": {}
            }
            self.scheduler_socket.send_json(request)
            response = self.scheduler_socket.recv_json()
            
            # Ensure we return a dictionary
            if isinstance(response, dict):
                return response
            else:
                return {"status": "error", "message": f"Invalid response format: {str(response)}"}
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {"status": "error", "message": str(e)}
    
    def cleanup(self):
        """Clean up resources before shutdown"""
        logger.info("Cleaning up resources")
        if self.orchestrator_socket:
            self.orchestrator_socket.close()
        if self.scheduler_socket:
            self.scheduler_socket.close()
        if self.error_bus_pub:
            self.error_bus_pub.close()
        super().cleanup()


    def _get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent.
        
        Returns:
            Dict[str, Any]: Health status information
        """
        return {
            "status": "ok",
            "uptime": time.time() - self.start_time,
            "name": self.name,
            "version": getattr(self, "version", "1.0.0"),
            "port": self.port,
            "health_port": getattr(self, "health_port", None),
            "error_reporting": bool(getattr(self, "error_bus", None))
        }
if __name__ == "__main__":
    try:
        health_manager = SystemHealthManager()
        health_manager.run()
    except KeyboardInterrupt:
        logger.info("SystemHealthManager shutting down")
    except Exception as e:
        logger.critical(f"SystemHealthManager failed to start: {e}", exc_info=True)
    finally:
        if 'health_manager' in locals() and hasattr(health_manager, 'cleanup'):
            health_manager.cleanup() 