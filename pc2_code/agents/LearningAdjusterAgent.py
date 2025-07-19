import sys
from typing import Dict, Any, Optional
import yaml
import os
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import zmq
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from threading import Thread
from pc2_code.config.system_config import get_service_host, get_service_port
from common.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config
import traceback

# Standard imports for PC2 agents
from pc2_code.utils.config_loader import load_config, parse_agent_args
from pc2_code.agents.error_bus_template import setup_error_reporting, report_error
from common.env_helpers import get_env


# Add project root to Python path for common_utils import
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    USE_COMMON_UTILS = True
except ImportError as e:
    print(f"Import error: {e}")
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

# Load configuration at the module level
try:
    config = Config().get_config()
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    config = {}

class LearningAdjusterAgent(BaseAgent):
    
    # Parse agent arguments
    _agent_args = parse_agent_args()def __init__(self, port: int = None):
        # Get port from config
        actual_port = config.get('services', {}).get('learning_adjuster', {}).get('port', 5643) if port is None else port
        
        # Initialize BaseAgent with name and port
        super().__init__(name="LearningAdjusterAgent", port=actual_port)
        
        """Initialize the LearningAdjusterAgent with ZMQ sockets."""
        self.context = zmq.Context()
        self.name = "LearningAdjusterAgent"
        
        # Get host and port from config
        self.host = config.get('services', {}).get('learning_adjuster', {}).get('host', '0.0.0.0')
        self.port = actual_port
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
            performance_host = config.get('services', {}).get('performance_logger', {}).get('host', 'localhost')
            performance_port = config.get('services', {}).get('performance_logger', {}).get('port', 5632)
            self.performance_socket.connect(f"tcp://{performance_host}:{performance_port}")
            logger.info(f"Connected to PerformanceLoggerAgent at {performance_host}:{performance_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to connect to PerformanceLoggerAgent: {str(e)}")
            raise
        
        # REQ socket for AgentTrustScorer
        try:
            self.trust_socket = self.context.socket(zmq.REQ)
            trust_host = config.get('services', {}).get('agent_trust_scorer', {}).get('host', 'localhost')
            trust_port = config.get('services', {}).get('agent_trust_scorer', {}).get('port', 5628)
            self.trust_socket.connect(f"tcp://{trust_host}:{trust_port}")
            logger.info(f"Connected to AgentTrustScorer at {trust_host}:{trust_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to connect to AgentTrustScorer: {str(e)}")
            raise
        
        # REQ socket for LearningAgent
        try:
            self.learning_socket = self.context.socket(zmq.REQ)
            learning_host = config.get('services', {}).get('learning_agent', {}).get('host', 'localhost')
            learning_port = config.get('services', {}).get('learning_agent', {}).get('port', 5633)
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
        
        logger.info(f"LearningAdjusterAgent initialized on port {self.port}")
    
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
        # Call parent implementation first
        status = super()._get_health_status()
        
        # Add agent-specific health information
        uptime = time.time() - self.start_time
        analysis_thread_alive = self.analysis_thread.is_alive() if hasattr(self, 'analysis_thread') else False
        
        status.update({
            "agent_type": "learning_adjuster",
            "threads": {
                "analysis_thread": analysis_thread_alive,
                "health_thread": True  # This thread is running if we're here
            }
        })
        
        return status
    
    def _get_performance_metrics(self, agent: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance metrics for an agent from the last N hours."""
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
            if isinstance(response, dict) and response.get('status') == 'success':
                metrics = response.get('metrics', [])
                if isinstance(metrics, list):
                    return [m for m in metrics if isinstance(m, dict)]
                else:
                    return []
            else:
                logger.error(f"Failed to get performance metrics: {response.get('message', 'Unknown error') if isinstance(response, dict) else response}")
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
            if isinstance(response, dict) and response.get('status') == 'success':
                usage = response.get('usage', [])
                if isinstance(usage, list):
                    return [u for u in usage if isinstance(u, dict)]
                else:
                    return []
            else:
                logger.error(f"Failed to get resource usage: {response.get('message', 'Unknown error') if isinstance(response, dict) else response}")
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
            if isinstance(response, dict) and response.get('status') == 'success':
                scores = response.get('scores', {})
                if isinstance(scores, dict):
                    return {k: float(v) for k, v in scores.items() if isinstance(k, str) and isinstance(v, (int, float))}
                else:
                    return {}
            else:
                logger.error(f"Failed to get trust scores: {response.get('message', 'Unknown error') if isinstance(response, dict) else response}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting trust scores: {str(e)}")
            return {}
    
    def _analyze_agent_performance(self, agent: str) -> Dict[str, Any]:
        """Analyze performance data for an agent and suggest adjustments."""
        try:
            # Get performance metrics
            metrics = self._get_performance_metrics(agent, hours=24)
            if not metrics:
                logger.warning(f"No performance metrics found for agent {agent}")
                return {
                    'status': 'warning',
                    'message': f'No performance metrics found for agent {agent}',
                    'suggestions': []
                }
                
            # Get resource usage
            usage = self._get_resource_usage(agent, hours=24)
            
            # Get trust scores
            trust_scores = self._get_trust_scores(agent)
            
            # Analyze data
            suggestions = []
            
            # Check response times
            response_times = [m.get('response_time', 0) for m in metrics if isinstance(m.get('response_time'), (int, float))]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                if avg_response_time > 1.0:  # More than 1 second
                    suggestions.append({
                        'type': 'performance',
                        'severity': 'medium',
                        'message': f'High average response time: {avg_response_time:.2f}s',
                        'adjustment': {
                            'parameter': 'batch_size',
                            'current_value': None,
                            'suggested_value': 'decrease'
                        }
                    })
                    
            # Check error rates
            error_count = sum(1 for m in metrics if m.get('status') == 'error')
            if metrics and error_count / len(metrics) > 0.05:  # More than 5% errors
                suggestions.append({
                    'type': 'reliability',
                    'severity': 'high',
                    'message': f'High error rate: {error_count / len(metrics):.1%}',
                    'adjustment': {
                        'parameter': 'retry_count',
                        'current_value': None,
                        'suggested_value': 'increase'
                    }
                })
                
            # Check resource usage
            if usage:
                cpu_usage = [u.get('cpu_percent', 0) for u in usage if isinstance(u.get('cpu_percent'), (int, float))]
                if cpu_usage and sum(cpu_usage) / len(cpu_usage) > 80:  # More than 80% CPU
                    suggestions.append({
                        'type': 'resource',
                        'severity': 'high',
                        'message': f'High CPU usage: {sum(cpu_usage) / len(cpu_usage):.1f}%',
                        'adjustment': {
                            'parameter': 'worker_threads',
                            'current_value': None,
                            'suggested_value': 'decrease'
                        }
                    })
                    
                memory_usage = [u.get('memory_percent', 0) for u in usage if isinstance(u.get('memory_percent'), (int, float))]
                if memory_usage and sum(memory_usage) / len(memory_usage) > 80:  # More than 80% memory
                    suggestions.append({
                        'type': 'resource',
                        'severity': 'high',
                        'message': f'High memory usage: {sum(memory_usage) / len(memory_usage):.1f}%',
                        'adjustment': {
                            'parameter': 'cache_size',
                            'current_value': None,
                            'suggested_value': 'decrease'
                        }
                    })
                    
            # Check trust scores
            if trust_scores:
                avg_trust = sum(trust_scores.values()) / len(trust_scores)
                if avg_trust < 0.7:  # Less than 70% trust
                    suggestions.append({
                        'type': 'trust',
                        'severity': 'medium',
                        'message': f'Low trust score: {avg_trust:.1%}',
                        'adjustment': {
                            'parameter': 'validation_level',
                            'current_value': None,
                            'suggested_value': 'increase'
                        }
                    })
                    
            return {
                'status': 'success',
                'message': f'Analysis complete for agent {agent}',
                'suggestions': suggestions
            }
                
        except Exception as e:
            logger.error(f"Error analyzing agent performance: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error analyzing agent performance: {str(e)}',
                'suggestions': []
            }
    
    def _analyze_performance(self):
        """Background thread to analyze agent performance and suggest adjustments."""
        logger.info("Analysis thread started")
        
        while self.running:
            try:
                # Get list of agents to analyze from config
                agents_to_analyze = config.get('learning_adjuster', {}).get('monitored_agents', [])
                
                if not agents_to_analyze:
                    logger.warning("No agents configured for monitoring")
                    time.sleep(60)  # Check again in 1 minute
                    continue
                    
                logger.info(f"Analyzing {len(agents_to_analyze)} agents")
                
                for agent in agents_to_analyze:
                    try:
                        # Analyze agent performance
                        analysis = self._analyze_agent_performance(agent)
                        
                        # Apply adjustments if needed
                        if analysis.get('status') == 'success' and analysis.get('suggestions'):
                            self._apply_adjustments(agent, analysis['suggestions'])
                            
                    except Exception as e:
                        logger.error(f"Error analyzing agent {agent}: {str(e)}")
                        
                # Sleep for a while before next analysis
                sleep_time = config.get('learning_adjuster', {}).get('analysis_interval', 3600)  # Default: 1 hour
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in analysis thread: {str(e)}")
                time.sleep(60)  # Sleep for a minute and try again
    
    def _apply_adjustments(self, agent: str, suggestions: List[Dict[str, Any]]):
        """Apply suggested adjustments to an agent."""
        try:
            if not suggestions:
                return
                
            logger.info(f"Applying {len(suggestions)} adjustments to agent {agent}")
            
            # Send adjustments to the learning agent
            self.learning_socket.send_json({
                'action': 'apply_adjustments',
                'agent': agent,
                'adjustments': suggestions
            })
            
            # Wait for response
            response = self.learning_socket.recv_json()
            
            if isinstance(response, dict) and response.get('status') == 'success':
                logger.info(f"Successfully applied adjustments to agent {agent}")
            else:
                logger.error(f"Failed to apply adjustments to agent {agent}: {response.get('message', 'Unknown error') if isinstance(response, dict) else response}")
                
        except Exception as e:
            logger.error(f"Error applying adjustments to agent {agent}: {str(e)}")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        try:
            action = request.get('action', '')
            
            if action in ['health_check', 'health', 'ping']:
                return self._get_health_status()
                
            elif action == 'analyze_agent':
                agent = request.get('agent')
                if not agent:
                    return {'status': 'error', 'message': 'Missing agent parameter'}
                    
                return self._analyze_agent_performance(agent)
                
            elif action == 'apply_adjustment':
                agent = request.get('agent')
                adjustment = request.get('adjustment')
                
                if not agent or not adjustment:
                    return {'status': 'error', 'message': 'Missing required parameters'}
                    
                self._apply_adjustments(agent, [adjustment])
                return {'status': 'success', 'message': f'Adjustment applied to agent {agent}'}
                
            else:
                return {'status': 'error', 'message': f'Unknown action: {action}'}
                
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {'status': 'error', 'message': f'Error handling request: {str(e)}'}
    
    def run(self):
        """Main run loop."""
        logger.info(f"LearningAdjusterAgent starting on port {self.port}")
        
        try:
            while self.running:
                try:
                    # Use non-blocking recv with timeout
                    if self.socket.poll(timeout=1000) != 0:  # 1 second timeout
                        message = self.socket.recv_json()
                        logger.debug(f"Received message: {message}")
                        
                        # Process message
                        response = self.handle_request(message)
                        
                        # Send response
                        self.socket.send_json(response)
                        
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error: {e}")
                    time.sleep(1)  # Sleep to avoid tight loop on error
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Try to send error response
                    try:
                        self.socket.send_json({
                            'status': 'error',
                            'message': f'Internal server error: {str(e)}'
                        })
                    except:
                        pass
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("LearningAdjusterAgent interrupted")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up LearningAdjusterAgent resources")
        self.running = False
        
        # Join threads
        if hasattr(self, 'analysis_thread') and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=2.0)
            
        # Call parent cleanup
        super().cleanup()
        
        logger.info("LearningAdjusterAgent cleanup complete")
    
    def stop(self):
        """Stop the agent."""
        self.running = False

if __name__ == "__main__":
    agent = LearningAdjusterAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
