from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List
import os
import uuid
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_breeder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentBreeder(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Agentbreeder")
        """Initialize the AgentBreeder with ZMQ sockets."""
        self.port = port
        self.context = zmq.Context()
        
        # Main REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{port}")
        logger.info(f"AgentBreeder initialized and bound to port {port}")
        
        # Socket for AutoGen Framework
        self.autogen_socket = self.context.socket(zmq.REQ)
        self.autogen_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.autogen_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.autogen_socket.connect("tcp://localhost:5650")  # AutoGen Framework
        logger.info(f"Connected to AutoGen Framework on port 5650")
        
        # Socket for CoordinatorAgent (for LLM access)
        self.coordinator_socket = self.context.socket(zmq.REQ)
        self.coordinator_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.coordinator_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.coordinator_socket.connect("tcp://localhost:5590")  # CoordinatorAgent
        logger.info(f"Connected to CoordinatorAgent on port 5590")
        
        # Poller for non-blocking socket operations
        self.poller = zmq.Poller()
        self.poller.register(self.coordinator_socket, zmq.POLLIN)
        self.poller.register(self.autogen_socket, zmq.POLLIN)
        
        # Track breeding requests
        self.breeding_requests = {}
        
        # Track uptime
        self.start_time = time.time()
        
        # Agent template for future implementation
        self.agent_template = '''import zmq
import json
import logging
from typing import Dict, Any

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('{agent_name}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class {agent_class}:
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Agentbreeder")
        """Initialize the {agent_class} with ZMQ sockets."""
        self.port = port
        self.context = zmq.Context()
        
        # Main REP socket for handling requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://*:{port}")
        
        # Connect to AutoGen Framework
        self.autogen_socket = self.context.socket(zmq.REQ)
        self.autogen_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.autogen_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.autogen_socket.connect("tcp://localhost:5650")  # AutoGen Framework
        
        # Register with AutoGen Framework
        self.register_with_autogen()
        
        logger.info(f"{agent_class} initialized on port {port}")
    
    def register_with_autogen(self):
        """Register this agent with the AutoGen Framework."""
        try:
            self.autogen_socket.send_json({
                "action": "register",
                "agent_id": "{agent_id}",
                "capabilities": {capabilities}
            })
            response = self.autogen_socket.recv_json()
            if response.get("status") == "success":
                logger.info(f"Successfully registered with AutoGen Framework")
            else:
                logger.error(f"Failed to register with AutoGen Framework: {response.get('message')}")
        except Exception as e:
            logger.error(f"Error registering with AutoGen Framework: {str(e)}")
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == '{action}':
            return self.{action}(request)
        elif action == 'ping':
            return {'status': 'success', 'message': 'pong'}
        elif action == 'get_health':
            return self.get_health()
        else:
            return {{
                'status': 'error',
                'message': f'Unknown action: {{action}}'
            }}
    
    def {action}(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """{action_description}"""
        try:
            {action_implementation}
            
            return {{
                'status': 'success',
                'message': '{success_message}',
                'result': result
            }}
            
        except Exception as e:
            logger.error(f"Error in {action}: {{str(e)}}")
            return {{
                'status': 'error',
                'message': str(e)
            }}
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status of the agent."""
        return {{
            'status': 'success',
            'uptime': time.time() - self.start_time,
            'agent_id': "{agent_id}",
            'capabilities': {capabilities}
        }}
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("{agent_class} started")
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.debug(f"Received request: {{message}}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.debug(f"Sent response: {{response}}")
                
            except Exception as e:
                logger.error(f"Error processing request: {{str(e)}}")
                self.socket.send_json({{
                    'status': 'error',
                    'message': str(e)
                }})
    
    def stop(self):
        """Stop the agent and clean up resources."""
        # Unregister from AutoGen Framework
        try:
            self.autogen_socket.send_json({
                "action": "unregister",
                "agent_id": "{agent_id}"
            })
            self.autogen_socket.recv_json()  # Wait for response
        except:
            pass
            
        self.socket.close()
        self.autogen_socket.close()
        self.context.term()

if __name__ == '__main__':
    agent = {agent_class}()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
'''
    
    def breed_agent(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent breeding request (placeholder implementation).
        
        Args:
            request: Dictionary containing breeding parameters
            
        Returns:
            Response dictionary with status and message
        """
        try:
            # Extract request parameters
            task_description = request.get('task_description', '')
            capabilities = request.get('capabilities', [])
            agent_name = request.get('agent_name', f"SpecialistAgent_{uuid.uuid4().hex[:6]}")
            priority = request.get('priority', 'normal')
            
            # Generate a unique request ID
            request_id = f"breed_{uuid.uuid4().hex[:8]}"
            
            # Store request details
            self.breeding_requests[request_id] = {
                'status': 'scheduled',
                'task_description': task_description,
                'capabilities': capabilities,
                'agent_name': agent_name,
                'priority': priority,
                'timestamp': datetime.now().isoformat(),
                'completion_estimate': '24h'  # Placeholder estimate
            }
            
            # Log the request
            logger.info(f"Received breeding request {request_id} for task: {task_description}")
            logger.info(f"Requested capabilities: {capabilities}")
            
            # In a real implementation, this would trigger the agent creation process
            # For now, just return a placeholder response
            
            return {
                'status': 'success',
                'message': f"Agent breeding for task '{task_description}' is scheduled. A specialist will be available in the future.",
                'request_id': request_id,
                'estimated_completion': '24h'
            }
            
        except Exception as e:
            logger.error(f"Error in breed_agent: {str(e)}")
            traceback.print_exc()
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_breeding_status(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get status of a breeding request.
        
        Args:
            request: Dictionary containing request_id
            
        Returns:
            Response dictionary with breeding status
        """
        try:
            request_id = request.get('request_id')
            
            if not request_id:
                return {
                    'status': 'error',
                    'message': 'Missing request_id parameter'
                }
            
            if request_id in self.breeding_requests:
                return {
                    'status': 'success',
                    'breeding_status': self.breeding_requests[request_id]
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Breeding request {request_id} not found'
                }
                
        except Exception as e:
            logger.error(f"Error in get_breeding_status: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_all_breeding_requests(self) -> Dict[str, Any]:
        """Get all breeding requests.
        
        Returns:
            Response dictionary with all breeding requests
        """
        try:
            return {
                'status': 'success',
                'breeding_requests': self.breeding_requests
            }
                
        except Exception as e:
            logger.error(f"Error in get_all_breeding_requests: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def register_with_autogen(self) -> Dict[str, Any]:
        """Register this agent with the AutoGen Framework.
        
        Returns:
            Response dictionary with registration status
        """
        try:
            # Send registration request
            self.autogen_socket.send_json({
                "action": "register",
                "agent_id": "AgentBreeder",
                "capabilities": ["agent_breeding", "agent_generation"]
            })
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(5000))  # 5 second timeout
            if self.autogen_socket in socks and socks[self.autogen_socket] == zmq.POLLIN:
                response = self.autogen_socket.recv_json()
                
                if response.get('status') == 'success':
                    logger.info("Successfully registered with AutoGen Framework")
                    return {
                        'status': 'success',
                        'message': 'Successfully registered with AutoGen Framework'
                    }
                else:
                    logger.error(f"Failed to register with AutoGen Framework: {response.get('message')}")
                    return {
                        'status': 'error',
                        'message': f"Failed to register with AutoGen Framework: {response.get('message')}"
                    }
            else:
                logger.error("Timeout waiting for registration response")
                return {
                    'status': 'error',
                    'message': 'Timeout waiting for registration response'
                }
                
        except Exception as e:
            logger.error(f"Error registering with AutoGen Framework: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the agent.
        
        Returns:
            Response dictionary with health status
        """
        return {
            'status': 'success',
            'uptime': time.time() - self.start_time,
            'breeding_requests': len(self.breeding_requests),
            'agent_id': 'AgentBreeder',
            'capabilities': ['agent_breeding', 'agent_generation']
        }
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests.
        
        Args:
            request: Request dictionary
            
        Returns:
            Response dictionary
        """
        action = request.get('action')
        
        if action == 'ping':
            return {'status': 'success', 'message': 'pong'}
            
        elif action == 'get_health':
            return self.get_health_status()
            
        elif action == 'breed_agent':
            return self.breed_agent(request)
            
        elif action == 'get_breeding_status':
            return self.get_breeding_status(request)
            
        elif action == 'get_all_breeding_requests':
            return self.get_all_breeding_requests()
            
        elif action == 'register_with_autogen':
            return self.register_with_autogen()
            
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    
    def run(self):
        """Main loop for handling requests."""
        logger.info("AgentBreeder started")
        
        # Register with AutoGen Framework on startup
        self.register_with_autogen()
        
        while True:
            try:
                # Wait for next request
                message = self.socket.recv_json()
                logger.info(f"Received request: {message}")
                
                # Process request
                response = self.handle_request(message)
                
                # Send response
                self.socket.send_json(response)
                logger.info(f"Sent response: {response}")
                
            except Exception as e:
                logger.error(f"Error processing request: {str(e)}")
                traceback.print_exc()
                try:
                    self.socket.send_json({
                        'status': 'error',
                        'message': str(e)
                    })
                except zmq.error.ZMQError as zmq_err:
                    logger.error(f"ZMQ error sending response: {zmq_err}")
    
    def stop(self):
        """Stop the agent and clean up resources."""
        # Unregister from AutoGen Framework
        try:
            self.autogen_socket.send_json({
                "action": "unregister",
                "agent_id": "AgentBreeder"
            })
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(5000))  # 5 second timeout
            if self.autogen_socket in socks and socks[self.autogen_socket] == zmq.POLLIN:
                self.autogen_socket.recv_json()
        except:
            pass
            
        self.socket.close()
        self.autogen_socket.close()
        self.coordinator_socket.close()
        self.context.term()
        logger.info("AgentBreeder stopped")

if __name__ == '__main__':
    agent = AgentBreeder()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop() 
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise