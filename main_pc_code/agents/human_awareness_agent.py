"""
Human Awareness Agent implementation
Monitors and analyzes human presence and behavior
"""
from common.utils.path_manager import PathManager

# Removed sys.path.insert - rely on PYTHONPATH=/app in Docker environment

import time
import logging
from common.utils.log_setup import configure_logging
import threading
import json
import os
from typing import Dict, Any
from datetime import datetime
import sys


# Import path manager for containerization-friendly paths
import sys
import os
import os
import sys
from common.utils.path_manager import PathManager

# Removed sys.path.insert - rely on PYTHONPATH=/app in Docker environment

from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
import psutil

logger = logging.getLogger(__name__)

# Load configuration at module level
config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

class HumanAwarenessAgent(BaseAgent):
    def __init__(self, port=None):
        # Get port from config with fallback
        agent_port = config.get("port", 5642) if port is None else port
        agent_name = config.get("name", "HumanAwarenessAgent")
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        self.running = True
        # Add async init status
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0,
            "components": {"core": False}
        }
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        logger.info("HumanAwarenessAgent basic init complete, async init started")
        
        # Initialize state tracking
        self.presence_detected = False
        self.last_presence_time = None
        self.presence_duration = 0
        self.emotion_state = None
        self.attention_level = 0
        
        # Load configuration
        self.agent_config = self._load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))
        
        # Record start time for uptime calculation
        self.start_time = time.time()
        
        # Modern error reporting using BaseAgent.report_error()
        self.context = None  # Using pool
        
    def _load_config(self) -> Dict:
        """Load agent configuration."""
        try:
            config_path = os.path.join('config', 'system_config.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('agents', {}).get('human_awareness', {})
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
        
    def _perform_initialization(self):
        try:
            self._init_components()
            self.initialization_status["components"]["core"] = True
            self.initialization_status["progress"] = 1.0
            self.initialization_status["is_initialized"] = True
            logger.info("HumanAwarenessAgent initialization complete")
        except Exception as e:
            self.initialization_status["error"] = str(e)
            self.initialization_status["progress"] = 0.0
            logger.error(f"Initialization error: {e}")
            
    def _init_components(self):
        """Initialize agent components."""
        # TODO: Initialize actual components based on config
        
    def _get_health_status(self) -> Dict[str, Any]:
        """Get detailed health status."""
        base_status = super()._get_health_status()
        
        # Add agent-specific metrics
        base_status.update({
            "presence_detected": self.presence_detected,
            "last_presence_time": self.last_presence_time.isoformat() if self.last_presence_time else None,
            "presence_duration": self.presence_duration,
            "emotion_state": self.emotion_state,
            "attention_level": self.attention_level
        })
        
        return base_status
        
    def handle_request(self, request: Dict) -> Dict:
        """Handle incoming requests."""
        action = request.get("action")
        
        if action == "get_presence":
            return {
                "status": "ok",
                "presence_detected": self.presence_detected,
                "last_presence_time": self.last_presence_time.isoformat() if self.last_presence_time else None,
                "presence_duration": self.presence_duration
            }
            
        elif action == "get_emotion":
            return {
                "status": "ok",
                "emotion_state": self.emotion_state,
                "attention_level": self.attention_level
            }
            
        return super().handle_request(request)
        
    def run(self):
        logger.info("Starting HumanAwarenessAgent main loop")
        while self.running:
            try:
                if hasattr(self, 'socket'):
                    if self.socket.poll(timeout=100):
                        message = self.socket.recv_json()
                        if message.get("action") == "health_check":
                            self.socket.send_json({
                                "status": "ok" if self.initialization_status["is_initialized"] else "initializing",
                                "initialization_status": self.initialization_status
                            })
                            continue
                        if not self.initialization_status["is_initialized"]:
                            self.socket.send_json({
                                "status": "error",
                                "error": "Agent is still initializing",
                                "initialization_status": self.initialization_status
                            })
                            continue
                        response = self.handle_request(message)
                        self.socket.send_json(response)
                    else:
                        time.sleep(0.05)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                try:
                    if hasattr(self, 'socket'):
                        self.socket.send_json({'status': 'error','message': str(e)})
                except Exception as zmq_err:
                    logger.error(f"ZMQ error while sending error response: {zmq_err}")
                    time.sleep(1)
                
    def _update_presence(self):
        """Update human presence detection."""
        # TODO: Implement actual presence detection logic
        
    def _update_emotion(self):
        """Update emotion and attention analysis."""
        # TODO: Implement actual emotion analysis logic

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

    def cleanup(self):
        """Clean up resources when the agent is stopping."""
        logger.info("Cleaning up resources...")
        
        # Set running flag to False to stop threads
        self.running = False
        
        try:
            # Join init thread if it exists and is alive
            if hasattr(self, 'init_thread') and self.init_thread and self.init_thread.is_alive():
                try:
                    self.init_thread.join(timeout=2.0)
                    logger.info("Initialization thread joined")
                except Exception as e:
                    logger.error(f"Error joining initialization thread: {e}")
            
            # Close all ZMQ sockets
            for socket_name in ['socket', 'error_bus_pub']:
                if hasattr(self, socket_name) and getattr(self, socket_name):
                    try:
                        getattr(self, socket_name).close()
                        logger.info(f"{socket_name} closed")
                    except Exception as e:
                        logger.error(f"Error closing {socket_name}: {e}")
            
            # Terminate ZMQ context
            if hasattr(self, 'context') and self.context:
                try:
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
                    logger.info("ZMQ context terminated")
                except Exception as e:
                    logger.error(f"Error terminating ZMQ context: {e}")
            
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        # Call parent cleanup method
        super().cleanup()

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = HumanAwarenessAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup() 