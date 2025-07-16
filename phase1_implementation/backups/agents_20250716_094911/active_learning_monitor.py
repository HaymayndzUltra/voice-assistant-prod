from common.core.base_agent import BaseAgent
import zmq
import json
import logging
import threading
import time
import os
from datetime import datetime
from collections import deque
from main_pc_code.utils.config_loader import load_config
import psutil
from typing import Any, Dict, cast
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('active_learning_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ActiveLearningMonitor(BaseAgent):
    """
    ActiveLearningMonitor: Monitors active learning processes. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    """
    def __init__(self):
        self.port = config.get("port", 5700)
        self.start_time = time.time()
        self.name = "ActiveLearningMonitor"
        self.running = True
        self.processed_items = 0
        self.monitored_events = 0
        # Initialize BaseAgent with explicit port and name to ensure deterministic binding
        super().__init__(port=self.port, name=self.name)
        # Use the context created by BaseAgent; no need to reinitialize
        
        # Subscribe to UMRA output
        self.umra_socket = self.context.socket(zmq.SUB)
        self.umra_socket.connect(get_zmq_connection_string(5701))
        self.umra_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Subscribe to RequestCoordinator output
        self.coordinator_socket = self.context.socket(zmq.SUB)
        self.coordinator_socket.connect(get_zmq_connection_string(5702))
        self.coordinator_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Connect to SelfTrainingOrchestrator
        self.orchestrator_socket = self.context.socket(zmq.REQ)
        self.orchestrator_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.orchestrator_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.orchestrator_socket.connect(get_zmq_connection_string(5703))
        
        self.training_data = []
        self.interaction_buffer = deque(maxlen=1000)  # Store last 1000 interactions
        
        # Create data directory
        self.data_dir = "training_data"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Start monitoring threads
        self.umra_thread = threading.Thread(target=self._monitor_umra)
        self.coordinator_thread = threading.Thread(target=self._monitor_coordinator)
        self.analysis_thread = threading.Thread(target=self._analyze_interactions)
        
        self.umra_thread.daemon = True
        self.coordinator_thread.daemon = True
        self.analysis_thread.daemon = True
        
        self.umra_thread.start()
        self.coordinator_thread.start()
        self.analysis_thread.start()
        
        logger.info("ActiveLearningMonitor initialized")
        
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
    
    def _is_high_value_interaction(self, interaction):
        """Determine if an interaction is valuable for training"""
        # Check for explicit corrections
        if any(keyword in interaction.get('user_input', '').lower() 
               for keyword in ['no,', 'incorrect', 'wrong', 'that\'s not', 'actually']):
            return True
        
        # Check for implicit corrections (user restating the question)
        if interaction.get('user_input') and interaction.get('assistant_response'):
            if len(interaction['user_input'].split()) > 5:  # Substantial input
                if any(word in interaction['user_input'].lower() 
                       for word in ['but', 'however', 'although', 'though']):
                    return True
        
        # Check for positive reinforcement
        if any(keyword in interaction.get('user_input', '').lower() 
               for keyword in ['yes,', 'correct', 'right', 'exactly', 'perfect']):
            return True
        
        return False
    
    def _save_training_data(self, interaction):
        """Save valuable interaction to training dataset"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.data_dir, f"training_data_{timestamp}.json")
        
        try:
            with open(filename, 'w') as f:
                json.dump(interaction, f, indent=2)
            
            self.training_data.append({
                'filename': filename,
                'timestamp': timestamp,
                'interaction': interaction
            })
            
            logger.info(f"Saved valuable interaction to {filename}")
            
            # Notify orchestrator
            self.orchestrator_socket.send_json({
                'action': 'trigger_finetune',
                'data_source': filename,
                'model_to_tune': 'current_model',  # This should be configurable
                'parameters': {
                    'epochs': 1,
                    'batch_size': 4
                }
            })
            
            response_any = self.orchestrator_socket.recv_json()
            if isinstance(response_any, dict):
                response: Dict[str, Any] = cast(Dict[str, Any], response_any)
                if response.get('status') == 'started':
                    logger.info(f"Triggered fine-tuning job {response.get('job_id')}")
                else:
                    logger.error(f"Failed to trigger fine-tuning: {response.get('error')}")
            else:
                logger.error(f"Failed to trigger fine-tuning: invalid response type ({type(response_any).__name__})")
                
        except Exception as e:
            logger.error(f"Error saving training data: {str(e)}")
    
    def _monitor_umra(self):
        """Monitor UMRA output for valuable interactions"""
        while self.running:
            try:
                message = self.umra_socket.recv_json()
                if message.get('type') == 'interaction':
                    self.interaction_buffer.append(message)
            except Exception as e:
                logger.error(f"Error monitoring UMRA: {str(e)}")
                time.sleep(1)
    
    def _monitor_coordinator(self):
        """Monitor RequestCoordinator output for valuable interactions"""
        while self.running:
            try:
                message = self.coordinator_socket.recv_json()
                if message.get('type') == 'interaction':
                    self.interaction_buffer.append(message)
            except Exception as e:
                logger.error(f"Error monitoring RequestCoordinator: {str(e)}")
                time.sleep(1)
    
    def _analyze_interactions(self):
        """Analyze buffered interactions for training value"""
        while self.running:
            try:
                if self.interaction_buffer:
                    interaction = self.interaction_buffer.popleft()
                    if self._is_high_value_interaction(interaction):
                        self._save_training_data(interaction)
            except Exception as e:
                logger.error(f"Error analyzing interactions: {str(e)}")
            time.sleep(0.1)  # Prevent CPU overuse
    
    def get_training_data_stats(self):
        """Get statistics about collected training data"""
        return {
            'total_interactions': len(self.training_data),
            'latest_interaction': self.training_data[-1] if self.training_data else None,
            'buffer_size': len(self.interaction_buffer)
        }
    
    def shutdown(self):
        """Gracefully shutdown the monitor"""
        self.running = False
        self.umra_socket.close()
        self.coordinator_socket.close()
        self.orchestrator_socket.close()
        self.context.term()
        logger.info("ActiveLearningMonitor shutdown complete")

    def _get_health_status(self):
        """Overrides the base method to add agent-specific health metrics with ZMQ readiness check."""
        base_status = super()._get_health_status()

        zmq_ready = hasattr(self, 'orchestrator_socket') and self.orchestrator_socket is not None
        specific_metrics = {
            "status_detail": "active" if getattr(self, 'running', True) else "inactive",
            "processed_items": getattr(self, 'processed_items', 0),
            "monitored_events": getattr(self, 'monitored_events', 0),
            "zmq_ready": zmq_ready
        }
        overall_status = "ok" if zmq_ready else "degraded"
        base_status.update({
            "status": overall_status,
            "agent_specific_metrics": specific_metrics
        })
        return base_status

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

    def report_error(self, error_type, message, severity="ERROR", context=None):
        error_data = {
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "context": context or {}
        }
        try:
            msg = json.dumps(error_data).encode('utf-8')
            self.error_bus_pub.send_multipart([b"ERROR:", msg])
        except Exception as e:
            print(f"Failed to publish error to Error Bus: {e}")

if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ActiveLearningMonitor()
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
