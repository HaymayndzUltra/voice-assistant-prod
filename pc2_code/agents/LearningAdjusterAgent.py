import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import zmq
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from threading import Thread
from config.system_config import get_service_host, get_service_port

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

class LearningAdjusterAgent:
    def __init__(self, port: int = None):
        """Initialize the LearningAdjusterAgent with ZMQ sockets."""
        self.context = zmq.Context()
        
        # Get host and port from environment or config
        self.host = get_service_host('learning_adjuster', '0.0.0.0')
        self.port = get_service_port('learning_adjuster', 5643) if port is None else port
        
        # Main REP socket for handling requests
        try:
            self.socket = self.context.socket(zmq.REP)
            self.socket.bind(f"tcp://{self.host}:{self.port}")
            logger.info(f"LearningAdjusterAgent listening on {self.host}:{self.port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind to port {self.port}: {str(e)}")
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
        
        # Start analysis thread
        self.running = True
        self.analysis_thread = Thread(target=self._analyze_performance)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        
        logger.info(f"LearningAdjusterAgent initialized on port {port}")
    
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
        action = request.get('action')
        
        if action == 'analyze_agent':
            agent = request['agent']
            
            analysis = self._analyze_agent_performance(agent)
            
            return {
                'status': 'success',
                'analysis': analysis
            }
            
        elif action == 'get_suggestions':
            agent = request['agent']
            
            analysis = self._analyze_agent_performance(agent)
            
            if analysis['status'] == 'success':
                return {
                    'status': 'success',
                    'suggestions': analysis['suggestions']
                }
            else:
                return analysis
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("LearningAdjusterAgent started")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {message}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.debug(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                self.socket.send_json({
                    'status': 'error',
                    'message': str(e)
                })
    
    def stop(self):
        """Stop the agent and clean up resources."""
        self.running = False
        self.analysis_thread.join()
        
        self.socket.close()
        self.performance_socket.close()
        self.trust_socket.close()
        self.learning_socket.close()
        self.context.term()

if __name__ == '__main__':
    agent = LearningAdjusterAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop() 