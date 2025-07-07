"""
LearningOpportunityDetector Agent

This agent monitors user-agent interactions and performance metrics to detect
valuable learning opportunities. It combines the monitoring capabilities of
ActiveLearningMonitor with the performance analysis logic from TutorAgent.
"""

import os
import json
import time
import logging
import threading
import zmq
from datetime import datetime
from collections import deque
from typing import Dict, List, Any, Optional
import numpy as np
import psutil

# Import BaseAgent
from common.core.base_agent import BaseAgent

# Import standardized data models
from common.utils.learning_models import LearningOpportunity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('learning_opportunity_detector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LearningOpportunityDetector")

class LearningOpportunityDetector(BaseAgent):
    """
    LearningOpportunityDetector: Monitors interactions and performance metrics to identify
    valuable learning opportunities for model improvement.
    """
    def __init__(self):
        self.name = "LearningOpportunityDetector"
        self.port = 5710  # Choose an available port
        self.start_time = time.time()
        self.running = True
        self.processed_items = 0
        self.detected_opportunities = 0
        
        # Initialize BaseAgent
        super().__init__()
        
        # Buffer for recent interactions
        self.interaction_buffer = deque(maxlen=1000)  # Store last 1000 interactions
        
        # Buffer for detected opportunities
        self.opportunity_buffer = deque(maxlen=100)  # Store last 100 opportunities
        
        # Buffer for performance metrics
        self.performance_buffer = deque(maxlen=500)  # Store last 500 performance metrics
        
        # Initialize error bus
        self.error_bus_port = 7150
        self.error_bus_host = os.environ.get('PC2_IP', '192.168.100.17')
        
        # Start monitoring threads
        self.umra_thread = None
        self.coordinator_thread = None
        self.analysis_thread = None
        
        logger.info(f"{self.name} initialized")
    
    def _setup_sockets(self):
        """Set up ZMQ sockets for communication"""
        self.context = zmq.Context()
        
        # Main REP socket for receiving requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.port}")
        
        # Subscribe to UMRA output
        self.umra_socket = self.context.socket(zmq.SUB)
        self.umra_socket.connect(f"tcp://localhost:5701")  # UMRA port
        self.umra_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Subscribe to RequestCoordinator output
        self.coordinator_socket = self.context.socket(zmq.SUB)
        self.coordinator_socket.connect(f"tcp://localhost:5702")  # RequestCoordinator port
        self.coordinator_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        
        # Error bus connection
        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
        self.error_bus_pub = self.context.socket(zmq.PUB)
        self.error_bus_pub.connect(self.error_bus_endpoint)
        
        logger.info("ZMQ sockets initialized")
    
    def _register_with_digital_twin(self):
        """Register with SystemDigitalTwin"""
        try:
            # Create a socket to connect to SystemDigitalTwin
            digital_twin_socket = self.context.socket(zmq.REQ)
            digital_twin_socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 seconds timeout
            digital_twin_socket.connect("tcp://localhost:5555")  # SystemDigitalTwin port
            
            # Prepare registration message
            registration_msg = {
                "action": "register",
                "agent_id": self.name,
                "agent_type": "learning",
                "host": "localhost",
                "port": self.port,
                "capabilities": ["learning_opportunity_detection", "performance_analysis"],
                "dependencies": ["UMRA", "RequestCoordinator"]
            }
            
            # Send registration message
            digital_twin_socket.send_json(registration_msg)
            response = digital_twin_socket.recv_json()
            
            if response.get("status") == "success":
                logger.info(f"Successfully registered with SystemDigitalTwin: {response}")
            else:
                logger.error(f"Failed to register with SystemDigitalTwin: {response}")
                
        except Exception as e:
            logger.error(f"Error registering with SystemDigitalTwin: {str(e)}")
        finally:
            if 'digital_twin_socket' in locals():
                digital_twin_socket.close()
    
    def run(self):
        """Main agent loop"""
        try:
            # Setup ZMQ sockets
            self._setup_sockets()
            
            # Register with SystemDigitalTwin
            self._register_with_digital_twin()
            
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
            
            logger.info(f"{self.name} started and running")
            
            # Main loop - handle requests
            while self.running:
                try:
                    # Use poll to avoid blocking indefinitely
                    poller = zmq.Poller()
                    poller.register(self.socket, zmq.POLLIN)
                    
                    socks = dict(poller.poll(1000))  # 1 second timeout
                    
                    if self.socket in socks and socks[self.socket] == zmq.POLLIN:
                        message = self.socket.recv_json()
                        response = self._handle_request(message)
                        self.socket.send_json(response)
                        self.processed_items += 1
                        
                except zmq.ZMQError as e:
                    if e.errno == zmq.EAGAIN:
                        continue
                    else:
                        logger.error(f"ZMQ error in main loop: {str(e)}")
                        self.report_error("zmq_error", str(e))
                except Exception as e:
                    logger.error(f"Error in main loop: {str(e)}")
                    self.report_error("main_loop_error", str(e))
                    
                time.sleep(0.01)  # Small sleep to prevent CPU overuse
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down")
        except Exception as e:
            logger.error(f"Unexpected error in run method: {str(e)}")
            self.report_error("fatal_error", str(e))
        finally:
            self.cleanup()
    
    def _handle_request(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests"""
        action = message.get("action", "")
        
        if action == "health_check":
            return self._get_health_status()
        elif action == "get_opportunities":
            return self._handle_get_opportunities(message)
        elif action == "submit_performance_metric":
            return self._handle_submit_performance(message)
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
    
    def _handle_get_opportunities(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle request to get detected learning opportunities"""
        limit = message.get("limit", 10)
        
        opportunities = list(self.opportunity_buffer)[-limit:]
        
        return {
            "status": "success",
            "opportunities": opportunities,
            "total_available": len(self.opportunity_buffer)
        }
    
    def _handle_submit_performance(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle submission of performance metrics"""
        performance_data = message.get("performance_data")
        
        if not performance_data:
            return {
                "status": "error",
                "message": "Missing performance_data"
            }
        
        # Add to performance buffer
        self.performance_buffer.append(performance_data)
        
        # Analyze for learning opportunities
        opportunity = self._detect_performance_opportunity(performance_data)
        
        if opportunity:
            return {
                "status": "success",
                "message": "Performance metric submitted and opportunity detected",
                "opportunity": opportunity.dict()
            }
        else:
            return {
                "status": "success",
                "message": "Performance metric submitted successfully"
            }
    
    def _monitor_umra(self):
        """Monitor UMRA output for valuable interactions"""
        while self.running:
            try:
                message = self.umra_socket.recv_json(flags=zmq.NOBLOCK)
                if message.get('type') == 'interaction':
                    self.interaction_buffer.append(message)
            except zmq.ZMQError:
                # No message available
                pass
            except Exception as e:
                logger.error(f"Error monitoring UMRA: {str(e)}")
                self.report_error("umra_monitor_error", str(e))
            
            time.sleep(0.1)  # Small sleep to prevent CPU overuse
    
    def _monitor_coordinator(self):
        """Monitor RequestCoordinator output for valuable interactions"""
        while self.running:
            try:
                message = self.coordinator_socket.recv_json(flags=zmq.NOBLOCK)
                if message.get('type') == 'interaction':
                    self.interaction_buffer.append(message)
            except zmq.ZMQError:
                # No message available
                pass
            except Exception as e:
                logger.error(f"Error monitoring RequestCoordinator: {str(e)}")
                self.report_error("coordinator_monitor_error", str(e))
            
            time.sleep(0.1)  # Small sleep to prevent CPU overuse
    
    def _analyze_interactions(self):
        """Analyze buffered interactions for training value"""
        while self.running:
            try:
                if self.interaction_buffer:
                    interaction = self.interaction_buffer.popleft()
                    if self._is_high_value_interaction(interaction):
                        opportunity = self._create_opportunity_from_interaction(interaction)
                        if opportunity:
                            self.opportunity_buffer.append(opportunity.dict())
                            self.detected_opportunities += 1
                            logger.info(f"Detected learning opportunity: {opportunity.opportunity_type} with priority {opportunity.priority_score}")
            except Exception as e:
                logger.error(f"Error analyzing interactions: {str(e)}")
                self.report_error("analysis_error", str(e))
            
            time.sleep(0.05)  # Small sleep to prevent CPU overuse
    
    def _is_high_value_interaction(self, interaction: Dict[str, Any]) -> bool:
        """Determine if an interaction is valuable for training (from ActiveLearningMonitor)"""
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
    
    def _create_opportunity_from_interaction(self, interaction: Dict[str, Any]) -> Optional[LearningOpportunity]:
        """Create a standardized LearningOpportunity from an interaction"""
        try:
            # Determine opportunity type
            opportunity_type = "user_correction"
            if any(keyword in interaction.get('user_input', '').lower() 
                   for keyword in ['yes,', 'correct', 'right', 'exactly', 'perfect']):
                opportunity_type = "positive_feedback"
            
            # Score the opportunity
            priority_score = self._score_opportunity(interaction, "interaction")
            
            # Create the standardized LearningOpportunity
            opportunity = LearningOpportunity(
                source_agent=interaction.get('agent', 'unknown'),
                interaction_data=interaction,
                opportunity_type=opportunity_type,
                priority_score=priority_score
            )
            
            return opportunity
        except Exception as e:
            logger.error(f"Error creating opportunity: {str(e)}")
            self.report_error("opportunity_creation_error", str(e))
            return None
    
    def _detect_performance_opportunity(self, performance_data: Dict[str, Any]) -> Optional[LearningOpportunity]:
        """Detect learning opportunity from performance metrics (from TutorAgent)"""
        try:
            # Check if this performance data indicates a learning need
            if not self._is_high_value_performance(performance_data):
                return None
            
            # Score the opportunity
            priority_score = self._score_opportunity(performance_data, "performance")
            
            # Create the standardized LearningOpportunity
            opportunity = LearningOpportunity(
                source_agent=performance_data.get('agent_name', 'unknown'),
                interaction_data=performance_data,
                opportunity_type="performance_degradation",
                priority_score=priority_score
            )
            
            return opportunity
        except Exception as e:
            logger.error(f"Error detecting performance opportunity: {str(e)}")
            self.report_error("performance_detection_error", str(e))
            return None
    
    def _is_high_value_performance(self, performance_data: Dict[str, Any]) -> bool:
        """Determine if performance data indicates a learning need (from TutorAgent)"""
        # Check for accuracy below threshold
        if 'accuracy' in performance_data and performance_data['accuracy'] < 0.7:
            return True
        
        # Check for significant latency increase
        if 'latency_ms' in performance_data and performance_data['latency_ms'] > 500:
            return True
        
        # Check for high error rate
        if 'error_rate' in performance_data and performance_data['error_rate'] > 0.3:
            return True
        
        # Check for specific error patterns
        if 'errors' in performance_data and len(performance_data['errors']) > 0:
            # Look for recurring error patterns
            return True
        
        return False
    
    def _score_opportunity(self, interaction_data: Dict[str, Any], detection_method: str) -> float:
        """Score a learning opportunity based on its characteristics"""
        base_score = 0.5  # Default medium priority
        
        if detection_method == "interaction":
            # Scoring logic for interaction-based opportunities
            
            # Higher priority for explicit corrections
            if 'user_input' in interaction_data:
                user_input = interaction_data['user_input'].lower()
                if any(keyword in user_input for keyword in ['wrong', 'incorrect', 'that\'s not']):
                    base_score += 0.2
                
                # Higher priority for detailed corrections
                if len(user_input.split()) > 10:
                    base_score += 0.1
                
                # Higher priority for emotional responses
                if any(keyword in user_input for keyword in ['frustrated', 'annoyed', 'disappointed']):
                    base_score += 0.15
            
        elif detection_method == "performance":
            # Scoring logic for performance-based opportunities
            
            # Higher priority for severe accuracy drops
            if 'accuracy' in interaction_data:
                accuracy = interaction_data['accuracy']
                if accuracy < 0.5:
                    base_score += 0.3
                elif accuracy < 0.7:
                    base_score += 0.2
            
            # Higher priority for critical errors
            if 'error_severity' in interaction_data and interaction_data['error_severity'] == 'critical':
                base_score += 0.25
                
            # Higher priority for user-facing errors
            if 'user_visible' in interaction_data and interaction_data['user_visible']:
                base_score += 0.15
        
        # Ensure score is between 0.0 and 1.0
        return min(max(base_score, 0.0), 1.0)
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent"""
        status = {
            "status": "healthy",
            "agent_name": self.name,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "processed_items": self.processed_items,
            "detected_opportunities": self.detected_opportunities,
            "buffers": {
                "interaction_buffer": len(self.interaction_buffer),
                "opportunity_buffer": len(self.opportunity_buffer),
                "performance_buffer": len(self.performance_buffer)
            },
            "system_metrics": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent
            }
        }
        return status
    
    def report_error(self, error_type: str, message: str, severity: str = "ERROR", context: Optional[Dict[str, Any]] = None):
        """Report error to the Error Bus"""
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
            logger.error(f"Failed to publish error to Error Bus: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        logger.info(f"Cleaning up {self.name} resources")
        
        self.running = False
        
        # Wait for threads to finish
        if self.umra_thread and self.umra_thread.is_alive():
            self.umra_thread.join(timeout=2.0)
        
        if self.coordinator_thread and self.coordinator_thread.is_alive():
            self.coordinator_thread.join(timeout=2.0)
        
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=2.0)
        
        # Close sockets
        if hasattr(self, 'socket') and self.socket:
            self.socket.close()
        
        if hasattr(self, 'umra_socket') and self.umra_socket:
            self.umra_socket.close()
        
        if hasattr(self, 'coordinator_socket') and self.coordinator_socket:
            self.coordinator_socket.close()
        
        if hasattr(self, 'error_bus_pub') and self.error_bus_pub:
            self.error_bus_pub.close()
        
        # Terminate ZMQ context
        if hasattr(self, 'context') and self.context:
            self.context.term()
        
        logger.info(f"{self.name} cleanup complete")


if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = LearningOpportunityDetector()
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