import sys
import os


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("main_pc_code", "..")))
from common.utils.path_env import get_path, join_path, get_file_path
# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

PROJECT_ROOT = os.path.abspath(join_path("main_pc_code", "..")))
MAIN_PC_CODE = get_main_pc_code()
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if MAIN_PC_CODE not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE)

from common.core.base_agent import BaseAgent
import zmq
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
from main_pc_code.utils.config_loader import load_config
import threading

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(MAIN_PC_CODE, 'logs', 'dynamic_identity.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DynamicIdentityAgent(BaseAgent):
    def __init__(self, port: int = None, name: str = None, **kwargs):
        # Get port and name from _agent_args with fallbacks
        agent_port = config.get("port", 5802) if port is None else port
        agent_name = config.get("name", 'DynamicIdentityAgent') if name is None else name
        # Use strict_port=True to ensure bind failure surfaces instead of silent port change
        agent_port = config.get("port", 5000) if port is None else port
        agent_name = config.get("name", 'DynamicIdentityAgent') if name is None else name
        super().__init__(port=agent_port, name=agent_name)
        
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0
        }
        self.current_persona = 'teacher'
        self.start_time = time.time()
        self.running = True
        
        # Initialize RequestCoordinator connection variables
        self.request_coordinator_connection = None
        self.request_coordinator_connected = False
        # Start a background thread to connect to RequestCoordinator when it becomes available
        threading.Thread(target=self._connect_to_request_coordinator, daemon=True).start()
        
        # Perform remaining initialization asynchronously so that health checks can succeed quickly
        threading.Thread(target=self._perform_initialization, daemon=True).start()
        logger.info("Dynamic Identity Agent initialized (async init started)")
    
    

        self.error_bus_port = 7150

        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)
    def _get_health_status(self):
        # Default health status: Agent is running if its main loop is active.
        # This can be expanded with more specific checks later.
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational.",
            "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else 0
        }
        return {"status": status, "details": details}
    
    def _connect_to_request_coordinator(self):
        """Connect to RequestCoordinator using service discovery when it becomes available."""
        from main_pc_code.utils.service_discovery_client import get_service_address
        
        retry_count = 0
        max_retries = 10
        retry_delay = 5  # seconds
        
        while retry_count < max_retries and self.running:
            try:
                # Try to discover RequestCoordinator service
                request_coordinator_address = get_service_address("RequestCoordinator")
                if request_coordinator_address:
                    logger.info(f"RequestCoordinator discovered at {request_coordinator_address}")
                    # Initialize connection to RequestCoordinator if needed
                    # For now, we just mark it as connected since we don't need direct communication
                    self.request_coordinator_connected = True
                    break
                else:
                    logger.warning("RequestCoordinator not found in service registry, will retry...")
            except Exception as e:
                logger.error(f"Error discovering RequestCoordinator: {e}")
            
            # Wait before retrying
            retry_count += 1
            time.sleep(retry_delay)
        
        if not self.request_coordinator_connected:
            logger.warning("Failed to connect to RequestCoordinator after maximum retries")
    
    def _perform_initialization(self):
        try:
            # Load configuration and personas in background
            config_path = os.path.join(MAIN_PC_CODE, 'config', 'system_config.json')
            try:
                with open(config_path, 'r', encoding='utf-8-sig') as f:
                    config = json.load(f)
            except UnicodeDecodeError:
                with open(config_path, 'r', encoding='utf-16') as f:
                    config = json.load(f)
            agent_config = None
            if 'agents' in config and 'dynamic_identity' in config.get('agents'):
                agent_config = config.get('agents')['dynamic_identity']
            elif 'personality_pipeline' in config and 'dynamic_identity' in config.get('personality_pipeline'):
                agent_config = config.get('personality_pipeline')['dynamic_identity']
            else:
                agent_config = {}
            agent_config.setdefault('port', 5802)
            agent_config.setdefault('emr_port', 5803)
            agent_config.setdefault('empathy_port', 5804)
            agent_config.setdefault('personas_path', os.path.join('data', 'personas.json'))
            self.emr_port = agent_config.get('emr_port')
            self.empathy_port = agent_config.get('empathy_port')
            personas_path = agent_config.get('personas_path')
            with open(personas_path, 'r', encoding='utf-8-sig') as f:
                self.personas = json.load(f)
            # REQ socket for ModelOrchestrator
            self.model_socket = self.context.socket(zmq.REQ)
            self.model_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.model_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            _host = config.get("host", 'localhost')
            self.model_socket.connect(f"tcp://{_host}:{self.emr_port}") # Note: Port might need updating
            # REQ socket for EmpathyAgent
            self.empathy_socket = self.context.socket(zmq.REQ)
            self.empathy_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.empathy_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.empathy_socket.connect(f"tcp://{_host}:{self.empathy_port}")
            self.initialization_status.update({
                "is_initialized": True,
                "progress": 1.0
            })
            # Signal that initialization is complete so health checks succeed
            if hasattr(self, 'is_initialized'):
                self.is_initialized.set()
            logger.info("DynamicIdentityAgent async initialization complete")
        except Exception as e:
            self.initialization_status.update({
                "error": str(e),
                "progress": 0.0
            })
            logger.error(f"Initialization error: {e}")
    
    def _update_model_orchestrator(self, persona: str) -> Dict[str, Any]:
        """Update the ModelOrchestrator with new persona settings."""
        if not self.model_socket:
            return {'status': 'error', 'message': 'ModelOrchestrator not connected'}
            
        try:
            self.model_socket.send_json({
                'action': 'update_system_prompt',
                'prompt': self.personas[persona]['system_prompt']
            })
            
            response = self.model_socket.recv_json()
            if response['status'] != 'success':
                logger.error(f"Error updating model orchestrator: {response['message']}")
            return response
                
        except Exception as e:
            logger.error(f"Error in _update_model_orchestrator: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _update_empathy_agent(self, persona: str) -> Dict[str, Any]:
        """Update the EmpathyAgent with new persona settings."""
        try:
            self.empathy_socket.send_json({
                'action': 'update_emotional_profile',
                'profile': {
                    'persona': persona,
                    'voice_settings': self.personas[persona]['voice_settings']
                }
            })
            
            response = self.empathy_socket.recv_json()
            if response['status'] != 'success':
                logger.error(f"Error updating empathy agent: {response['message']}")
                return response
                
        except Exception as e:
            logger.error(f"Error in _update_empathy_agent: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def switch_persona(self, persona: str) -> Dict[str, Any]:
        """Switch to a different persona."""
        if persona not in self.personas:
            return {
                'status': 'error',
                'message': f'Unknown persona: {persona}'
            }
        
        # Update model orchestrator
        model_response = self._update_model_orchestrator(persona)
        if model_response['status'] != 'success':
            return model_response
        
        # Update empathy agent
        empathy_response = self._update_empathy_agent(persona)
        if empathy_response['status'] != 'success':
            return empathy_response
        
        # Update current persona
        self.current_persona = persona
        
        return {
            'status': 'success',
            'message': f'Switched to {self.personas[persona]["name"]} persona',
            'persona': self.personas[persona]
        }
    
    def get_current_persona(self) -> Dict[str, Any]:
        """Get the current persona settings."""
        return {
            'status': 'success',
            'persona': self.personas[self.current_persona]
        }
    
    def list_personas(self) -> Dict[str, Any]:
        """List all available personas."""
        return {
            'status': 'success',
            'personas': {
                name: data['name']
                for name, data in self.personas.items()
            }
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get('action')
        if action == 'health_check':
            return {'status': 'ok', 'initialization_status': self.initialization_status}
        if action == 'switch_persona':
            persona = request.get('persona')
            return self.switch_persona(persona)
        elif action == 'get_current_persona':
            return self.get_current_persona()
        elif action == 'list_personas':
            return self.list_personas()
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Run the agent's main loop."""
        logger.info("Dynamic Identity Agent started")
        
        while True:
            try:
                # Receive request
                request = self.socket.recv_json()
                
                # Handle request
                response = self.handle_request(request)
                
                # Send response
                self.socket.send_json(response)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                self.socket.send_json({
                    'status': 'error',
                    'message': str(e)
                })
    
    def stop(self):
        """Stop the agent and clean up resources."""
        self.socket.close()
        self.model_socket.close()
        self.empathy_socket.close()
        self.context.term()
        
        logger.info("Dynamic Identity Agent stopped")


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

if __name__ == '__main__':
    # Standardized main execution block
    agent = None
    try:
        # Replace 'ClassName' with the actual agent class from the file.
        agent = DynamicIdentityAgent()
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

if __name__ == "__main__":
    agent = None
    try:
        agent = DynamicIdentityAgent()
        agent.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if agent and hasattr(agent, 'cleanup'):
            agent.cleanup()

    def cleanup(self):
        """Clean up resources before shutdown."""
        logger.info(f"{self.__class__.__name__} cleaning up resources...")
        try:
            # Close ZMQ sockets if they exist
            if hasattr(self, 'socket') and self.socket:
                self.socket.close()
            
            if hasattr(self, 'context') and self.context:
                self.context.term()
                
            # Close any open file handles
            # [Add specific resource cleanup here]
            
            # Call parent class cleanup if it exists
            super().cleanup()
            
            logger.info(f"{self.__class__.__name__} cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
