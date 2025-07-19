import sys
from pathlib import Path
from common.config_manager import get_service_ip, get_service_url, get_redis_url
sys.path.append(str(Path(__file__).parent.parent))
import zmq
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from threading import Thread
from pc2_code.config.system_config import get_service_host, get_service_port

# Add project root to Python path for common_utils import
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    except ImportError as e:
        print(f"Import error: {e}")
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('learning_adjuster.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LearningAdjusterAgent(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self, port: int = None):
         super().__init__(name="LearningAdjusterAgent", port=None)
"""Initialize the LearningAdjusterAgent with ZMQ sockets."""
        self.context = zmq.Context()
        self.name = "LearningAdjusterAgent"
        
        # Get host and port from environment or config
        self.host = get_service_host('learning_adjuster', '0.0.0.0')
        self.port = get_service_port('learning_adjuster', 5643) if port is None else port
        self.health_port = self.port + 1
        
        # Main REP socket for handling requests
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://{self.host}:{self.port}")
            logger.info(f"LearningAdjusterAgent listening on {self.host}:{self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to port {self.port}: {str(e)}")
            raise
        
        # Health check socket
        try:
            if USE_COMMON_UTILS:
                self.health_socket = create_socket(self.context, zmq.REP, server=True)
            else:
                self.health_socket = self.context.socket(zmq.REP)
            self.health_socket.bind(f"tcp://{self.host}:{self.health_port}")
            logger.info(f"Health check socket listening on {self.host}:{self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket to port {self.health_port}: {str(e)}")
            raise
        
        # REQ socket for PerformanceLoggerAgent
        try:
            self.performance_socket = self.context.socket(zmq.REQ)
            performance_host = get_service_host('performance_logger', 'localhost')
            performance_port = get_service_port('performance_logger', 5632)
            self.performance_socket.connect(f"tcp://{performance_host}:{performance_port}")
            logger.info(f"Connected to PerformanceLoggerAgent at {performance_host}:{performance_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to connect to PerformanceLoggerAgent: {str(e)}")
            raise
        
        # REQ socket for AgentTrustScorer
        try:
            self.trust_socket = self.context.socket(zmq.REQ)
            trust_host = get_service_host('agent_trust_scorer', 'localhost')
            trust_port = get_service_port('agent_trust_scorer', 5628)
            self.trust_socket.connect(f"tcp://{trust_host}:{trust_port}")
            logger.info(f"Connected to AgentTrustScorer at {trust_host}:{trust_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to connect to AgentTrustScorer: {str(e)}")
            raise
        
        # REQ socket for LearningAgent
        try:
            self.learning_socket = self.context.socket(zmq.REQ)
            learning_host = get_service_host('learning_agent', 'localhost')
            learning_port = get_service_port('learning_agent', 5633)
            self.learning_socket.connect(f"tcp://{learning_host}:{learning_port}")
            logger.info(f"Connected to LearningAgent at {learning_host}:{learning_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to connect to LearningAgent: {str(e)}")
            raise
        
        # Start threads
        self.running = True
        self.start_time = time.time()
        
        # Start analysis thread
        self.analysis_thread = Thread(target=self._analyze_performance)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        
        # Start health check thread
        self._start_health_check()
        
        logger.info(f"LearningAdjusterAgent initialized on port {port}")
    
    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logger.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logger.info("Health check loop started")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100, zmq.POLLIN):
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._get_health_status()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        uptime = time.time() - self.start_time
        analysis_thread_alive = self.analysis_thread.is_alive() if hasattr(self, 'analysis_thread') else False
        
        return {
            "agent": self.name,
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime,
            "threads": {
                "analysis_thread": analysis_thread_alive,
                "health_thread": True  # This thread is running if we're here
            }
        }
    
    def _get_performance_metrics(self, agent: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance metrics for an agent from the 

# Load configuration at the module level
config = load_config()
from main_pc_code.utils.config_loader import load_config
from main_pc_code.src.core.base_agent import BaseAgentlast N hours."""

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
from common.env_helpers import get_env

        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            self.performance_socket.send_json({
                'action': 'get_agent_metrics',
                'agent': agent,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })
            
            response = self.performance_socket.recv_json()
            
            if response['status'] == 'success':
                return response['metrics']
            else:
                logger.error(f"Failed to get performance metrics: {response.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return []
    
    def _get_resource_usage(self, agent: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get resource usage data for an agent from the last N hours."""
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            self.performance_socket.send_json({
                'action': 'get_agent_resource_usage',
                'agent': agent,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            })
            
            response = self.performance_socket.recv_json()
            
            if response['status'] == 'success':
                return response['usage']
            else:
                logger.error(f"Failed to get resource usage: {response.get('message', 'Unknown error')}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting resource usage: {str(e)}")
            return []
    
    def _get_trust_scores(self, agent: str) -> Dict[str, float]:
        """Get trust scores for an agent."""
        try:
            self.trust_socket.send_json({
                'action': 'get_agent_scores',
                'agent': agent
            })
            
            response = self.trust_socket.recv_json()
            
            if response['status'] == 'success':
                return response['scores']
            else:
                logger.error(f"Failed to get trust scores: {response.get('message', 'Unknown error')}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting trust scores: {str(e)}")
            return {}
    
    def _analyze_agent_performance(self, agent: str) -> Dict[str, Any]:
        """Analyze performance data for an agent and suggest adjustments."""
        metrics = self._get_performance_metrics(agent)
        usage = self._get_resource_usage(agent)
        trust_scores = self._get_trust_scores(agent)
        
        if not metrics and not usage:
            return {
                'status': 'error',
                'message': 'No performance data available'
            }
        
        # Calculate average response time
        avg_response_time = sum(m['duration'] for m in metrics) / len(metrics) if metrics else 0
        
        # Calculate average resource usage
        avg_cpu = sum(u['cpu_percent'] for u in usage) / len(usage) if usage else 0
        avg_memory = sum(u['memory_mb'] for u in usage) / len(usage) if usage else 0
        
        # Get trust scores
        reliability = trust_scores.get('reliability', 0)
        consistency = trust_scores.get('consistency', 0)
        
        # Analyze and suggest adjustments
        suggestions = []
        
        # Response time analysis
        if avg_response_time > 1.0:  # More than 1 second
            suggestions.append({
                'type': 'performance',
                'parameter': 'batch_size',
                'action': 'decrease',
                'reason': f'High response time ({avg_response_time:.2f}s)'
            })
        
        # Resource usage analysis
        if avg_cpu > 80:  # More than 80% CPU
            suggestions.append({
                'type': 'resource',
                'parameter': 'max_workers',
                'action': 'decrease',
                'reason': f'High CPU usage ({avg_cpu:.1f}%)'
            })
        
        if avg_memory > 1000:  # More than 1GB
            suggestions.append({
                'type': 'resource',
                'parameter': 'cache_size',
                'action': 'decrease',
                'reason': f'High memory usage ({avg_memory:.1f}MB)'
            })
        
        # Trust score analysis
        if reliability < 0.7 or consistency < 0.7:
            suggestions.append({
                'type': 'learning',
                'parameter': 'training_frequency',
                'action': 'increase',
                'reason': f'Low trust scores (reliability: {reliability:.2f}, consistency: {consistency:.2f})'
            })
        
        return {
            'status': 'success',
            'analysis': {
                'avg_response_time': avg_response_time,
                'avg_cpu_usage': avg_cpu,
                'avg_memory_usage': avg_memory,
                'reliability_score': reliability,
                'consistency_score': consistency
            },
            'suggestions': suggestions
        }
    
    def _analyze_performance(self):
        """Periodically analyze performance data for all agents."""
        while self.running:
            try:
                # Get list of agents to analyze
                self.learning_socket.send_json({
                    'action': 'get_active_agents'
                })
                
                response = self.learning_socket.recv_json()
                
                if response['status'] == 'success':
                    agents = response['agents']
                    
                    # Analyze each agent
                    for agent in agents:
                        analysis = self._analyze_agent_performance(agent)
                        
                        if analysis['status'] == 'success' and analysis['suggestions']:
                            # Apply suggested adjustments
                            self._apply_adjustments(agent, analysis['suggestions'])
                
                # Wait before next analysis
                time.sleep(3600)  # Analyze every hour
                
            except Exception as e:
                logger.error(f"Error during performance analysis: {str(e)}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def _apply_adjustments(self, agent: str, suggestions: List[Dict[str, Any]]):
        """Apply suggested adjustments to an agent's configuration."""
        try:
            # Group suggestions by type
            performance_adjustments = [s for s in suggestions if s['type'] == 'performance']
            resource_adjustments = [s for s in suggestions if s['type'] == 'resource']
            learning_adjustments = [s for s in suggestions if s['type'] == 'learning']
            
            # Apply performance adjustments
            if performance_adjustments:
                self.learning_socket.send_json({
                    'action': 'update_performance_config',
                    'agent': agent,
                    'adjustments': performance_adjustments
                })
                _ = self.learning_socket.recv_json()
            
            # Apply resource adjustments
            if resource_adjustments:
                self.learning_socket.send_json({
                    'action': 'update_resource_config',
                    'agent': agent,
                    'adjustments': resource_adjustments
                })
                _ = self.learning_socket.recv_json()
            
            # Apply learning adjustments
            if learning_adjustments:
                self.learning_socket.send_json({
                    'action': 'update_learning_config',
                    'agent': agent,
                    'adjustments': learning_adjustments
                })
                _ = self.learning_socket.recv_json()
            
            logger.info(f"Applied {len(suggestions)} adjustments to {agent}")
            
        except Exception as e:
            logger.error(f"Error applying adjustments: {str(e)}")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action', '')
        
        if action == 'health_check' or action == 'ping':
            return self._get_health_status()
        
        if action == 'analyze_agent':
            agent = request.get('agent')
            if not agent:
                return {
                    'status': 'error',
                    'message': 'Missing agent parameter'
                }
            
            return self._analyze_agent_performance(agent)
        
        if action == 'apply_adjustments':
            agent = request.get('agent')
            suggestions = request.get('suggestions', [])
            
            if not agent:
                return {
                    'status': 'error',
                    'message': 'Missing agent parameter'
                }
            
            if not suggestions:
                return {
                    'status': 'error',
                    'message': 'Missing suggestions parameter'
                }
            
            return self._apply_adjustments(agent, suggestions)
        
        return {
            'status': 'error',
            'message': f'Unknown action: {action}'
        }
    
    def run(self):
        """Main run loop."""
        logger.info("LearningAdjusterAgent starting main loop")
        
        try:
            while self.running:
                try:
                    # Use poller to avoid blocking indefinitely
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    # Poll with timeout to allow for clean shutdown
                    if dict(poller.poll(1000)):
                        # Receive and process message
                        message_data = self.socket.recv()
                        
                        try:
                            request = json.loads(message_data)
                            logger.debug(f"Received request: {request}")
                            
                            response = self.handle_request(request)
                            
                            self.socket.send_json(response)
                            logger.debug(f"Sent response: {response}")
                        except json.JSONDecodeError:
                            logger.error(f"Received invalid JSON: {message_data}")
                            self.socket.send_json({
                                'status': 'error',
                                'message': 'Invalid JSON request'
                            })
                        except Exception as e:
                            logger.error(f"Error processing request: {str(e)}")
                            self.socket.send_json({
                                'status': 'error',
                                'message': f'Error processing request: {str(e)}'
                            })
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in main loop: {str(e)}")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop()


    def cleanup(self):

        """Clean up resources before shutdown."""

        logger.info("Cleaning up resources...")

        # Add specific cleanup code here

        super().cleanup()
    
    def stop(self):
        """Stop the agent and clean up resources."""
        logger.info("Stopping LearningAdjusterAgent")
        
        # Set running flag to false to stop all threads
        self.running = False
        
        # Wait for threads to finish
        if hasattr(self, 'analysis_thread') and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=2.0)
            
        if hasattr(self, 'health_thread') and self.health_thread.is_alive():
            self.health_thread.join(timeout=2.0)
        
        # Close sockets
        self.socket.close()
        self.health_socket.close()
        self.performance_socket.close()
        self.trust_socket.close()
        self.learning_socket.close()
        
        # Terminate context
        self.context.term()
        
        logger.info("LearningAdjusterAgent stopped")



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = LearningAdjusterAgent()
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