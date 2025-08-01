import zmq
import json
import logging
import threading
import time
import sys
import os
from datetime import datetime
from common.config_manager import get_service_ip, get_service_url, get_redis_url


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("pc2_code", ".."))))
from common.utils.path_manager import PathManager
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
from common.env_helpers import get_env


# Load configuration at the module level
config = load_config()(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PathManager.join_path("logs", str(PathManager.get_logs_dir() / "experience_tracker.log"))),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ExperienceTrackerAgent(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self, port=7112, health_port=7113, episodic_agent_port=7106):
         super().__init__(name="ExperienceTrackerAgent", port=7112)
self.port = port
        self.health_port = health_port
        self.episodic_agent_port = episodic_agent_port
        self.context = zmq.Context()
        self.initialized = False
        self.initialization_error = None
        self._setup_sockets()
        self._start_health_check()
        self._init_thread = threading.Thread(target=self._initialize_background, daemon=True)
        self._init_thread.start()
        logger.info(f"ExperienceTrackerAgent starting on port {port} (health: {health_port})")

    def _setup_sockets(self):
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://*:{self.port}")
            logger.info(f"ExperienceTrackerAgent main socket bound to port {self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind main socket to port {self.port}: {str(e)}")
            raise
        try:
            self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://*:{self.health_port}")
            logger.info(f"Health check endpoint on port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check to port {self.health_port}: {str(e)}")
            raise
        # Socket to communicate with EpisodicMemoryAgent
        self.episodic_socket = self.context.socket(zmq.REQ)
        self.episodic_socket.connect(f"tcp://localhost:{self.episodic_agent_port}")

    def _start_health_check(self):
        def health_check_loop():
            while True:
                try:
                    request = self.health_socket.recv_json()
                    if request.get('action') == 'health_check':
                        response = {
                            'status': 'ok' if self.initialized else 'initializing',
                            'service': 'ExperienceTracker',
                            'initialization_status': 'complete' if self.initialized else 'in_progress',
                            'port': self.port,
                            'health_port': self.health_port,
                            'timestamp': datetime.now().isoformat()
                        }
                        if self.initialization_error:
                            response['initialization_error'] = str(self.initialization_error)
                    else:
                        response = {
                            'status': 'unknown_action',
                            'message': f"Unknown action: {request.get('action', 'none')}"
                        }
                    self.health_socket.send_json(response)
                except Exception as e:
                    logger.error(f"Health check error: {str(e)}")
                    time.sleep(1)
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()

    def _initialize_background(self):
        try:
            # Simulate any heavy initialization if needed
            time.sleep(1)
            self.initialized = True
            logger.info("ExperienceTrackerAgent initialization completed")
        except Exception as e:
            self.initialization_error = str(e)
            logger.error(f"ExperienceTrackerAgent initialization failed: {str(e)}")

    def handle_request(self, request: dict) -> dict:
        action = request.get('action')
        if action == 'track_experience':
            # Forward to EpisodicMemoryAgent
            self.episodic_socket.send_json({
                'action': 'store_memory',
                'content': request.get('content'),
                'memory_type': 'experience',
                'importance_score': request.get('importance_score', 0.5),
                'metadata': request.get('metadata'),
                'expires_at': request.get('expires_at')
            })
            response = self.episodic_socket.recv_json()
            return response
        elif action == 'get_experiences':
            self.episodic_socket.send_json({
                'action': 'retrieve_memory',
                'memory_type': 'experience',
                'limit': request.get('limit', 10)
            })
            response = self.episodic_socket.recv_json()
            return response
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def run(self):
        logger.info("Starting ExperienceTrackerAgent main loop")
        while True:
            try:
                if self.socket.poll(1000) > 0:
                    request = self.socket.recv_json()
                    response = self.handle_request(request)
                    self.socket.send_json(response)
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(1)


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to ExperienceTrackerAgent

        base_status.update({

            'service': 'ExperienceTrackerAgent',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status


    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()

    def shutdown(self):
        self.socket.close()
        self.health_socket.close()
        self.episodic_socket.close()
        self.context.term()
        logger.info("ExperienceTrackerAgent shutdown complete")



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ExperienceTrackerAgent()
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