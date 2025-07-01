from src.core.base_agent import BaseAgent
import zmq
import json
import logging
import threading
import time
import os
from datetime import datetime
from collections import deque
from utils.config_loader import parse_agent_args
import psutil
from datetime import datetime

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
_agent_args = parse_agent_args()

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
    def __init__(self):
        self.port = _agent_args.get('port')
        super().__init__(_agent_args)
        self.context = zmq.Context()
        
        # Subscribe to UMRA output
        self.umra_socket = self.context.socket(zmq.SUB)
        self.umra_socket.connect(f"tcp://localhost:{_agent_args.umra_port}")
        self.umra_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Subscribe to Coordinator output
        self.coordinator_socket = self.context.socket(zmq.SUB)
        self.coordinator_socket.connect(f"tcp://localhost:{_agent_args.coordinator_port}")
        self.coordinator_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Connect to SelfTrainingOrchestrator
        self.orchestrator_socket = self.context.socket(zmq.REQ)
        self.orchestrator_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.orchestrator_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.orchestrator_socket.connect(f"tcp://localhost:{_agent_args.orchestrator_port}")
        
        self.running = True
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
            
            response = self.orchestrator_socket.recv_json()
            if response['status'] == 'started':
                logger.info(f"Triggered fine-tuning job {response['job_id']}")
            else:
                logger.error(f"Failed to trigger fine-tuning: {response.get('error')}")
                
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
        """Monitor Coordinator output for valuable interactions"""
        while self.running:
            try:
                message = self.coordinator_socket.recv_json()
                if message.get('type') == 'interaction':
                    self.interaction_buffer.append(message)
            except Exception as e:
                logger.error(f"Error monitoring Coordinator: {str(e)}")
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
        """Overrides the base method to add agent-specific health metrics."""
        base_status = super()._get_health_status()
        specific_metrics = {
            "status_detail": "active",
            "processed_items": getattr(self, 'processed_items', 0),
            "monitored_events": getattr(self, 'monitored_events', 0)
        }
        base_status.update(specific_metrics)
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

if __name__ == "__main__":
    monitor = ActiveLearningMonitor()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        monitor.shutdown() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise