from src.core.base_agent import BaseAgent
"""
Learning Manager Agent
Manages and coordinates learning operations across the system
"""

import zmq
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('learning_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('LearningManager')

class LearningManager(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="LearningManager")
        """Initialize the Learning Manager.
        
        Args:
            port: Port for this agent to listen on
            memory_manager_port: Port for the MemoryManager agent
            knowledge_base_port: Port for the KnowledgeBase agent
            coordinator_port: Port for the CoordinatorAgent (for LLM access)
        """
        self.port = port
        self.memory_manager_port = memory_manager_port
        self.knowledge_base_port = knowledge_base_port
        self.coordinator_port = coordinator_port
        
        # Initialize ZMQ context and sockets
        self.context = zmq.Context()
        
        # REP socket for receiving requests
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{port}")
        
        # REQ sockets for connecting to other agents
        self.memory_manager_socket = self.context.socket(zmq.REQ)
        self.memory_manager_socket.connect(f"tcp://{_agent_args.host}:{memory_manager_port}")
        
        self.knowledge_base_socket = self.context.socket(zmq.REQ)
        self.knowledge_base_socket.connect(f"tcp://{_agent_args.host}:{knowledge_base_port}")
        
        self.coordinator_socket = self.context.socket(zmq.REQ)
        self.coordinator_socket.connect(f"tcp://{_agent_args.host}:{coordinator_port}")
        
        # Initialize socket poller for timeouts
        self.poller = zmq.Poller()
        self.poller.register(self.memory_manager_socket, zmq.POLLIN)
        self.poller.register(self.knowledge_base_socket, zmq.POLLIN)
        self.poller.register(self.coordinator_socket, zmq.POLLIN)
        
        # Set timeout for requests (in milliseconds)
        self.request_timeout = 10000  # 10 seconds
        
        # Track agent start time
        self.start_time = time.time()
        
        # Start health check thread
        self.health_check_thread = threading.Thread(target=self._health_check_loop)
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        
        logger.info(f"Learning Manager initialized on port {port}")
        logger.info(f"Connected to MemoryManager on port {memory_manager_port}")
        logger.info(f"Connected to KnowledgeBase on port {knowledge_base_port}")
        logger.info(f"Connected to CoordinatorAgent on port {coordinator_port}")
        
        self.running = True
        self.initialization_status = {
            "is_initialized": False,
            "error": None,
            "progress": 0.0,
            "components": {"core": False}
        }
        self.init_thread = threading.Thread(target=self._perform_initialization, daemon=True)
        self.init_thread.start()
        logger.info("LearningManager basic init complete, async init started")
        
    def _health_check_loop(self):
        """Continuously check the health of the agent and its connections."""
        while True:
            try:
                # Update uptime
                self.uptime = time.time() - self.start_time
                
                # Check connections to other agents
                self.memory_manager_status = self._check_connection(self.memory_manager_socket, "ping")
                self.knowledge_base_status = self._check_connection(self.knowledge_base_socket, "ping")
                self.coordinator_status = self._check_connection(self.coordinator_socket, "ping")
                
                time.sleep(30)  # Check every 30 seconds to reduce overhead
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                
    def _check_connection(self, socket: zmq.Socket, action: str = "ping") -> bool:
        """Check if a connection to another agent is working.
        
        Args:
            socket: ZMQ socket to check
            action: Action to send in the request
            
        Returns:
            True if connection is working, False otherwise
        """
        try:
            # Send ping request
            socket.send_json({
                'action': action
            }, zmq.NOBLOCK)
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(2000))  # 2 second timeout
            if socket in socks and socks[socket] == zmq.POLLIN:
                response = socket.recv_json()
                return response.get('status') == 'success'
            else:
                # Socket timed out
                return False
        except Exception as e:
            logger.error(f"Error checking connection: {e}")
            return False
                
    def get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        return {
            'status': 'success',
            'uptime': time.time() - self.start_time,
            'components': {
                'memory_manager_connection': getattr(self, 'memory_manager_status', False),
                'knowledge_base_connection': getattr(self, 'knowledge_base_status', False),
                'coordinator_connection': getattr(self, 'coordinator_status', False)
            }
        }
        
    def analyze_and_learn(self, conversation: Union[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyze a conversation and extract learnable content.
        
        Args:
            conversation: Either a raw conversation transcript (string) or a structured
                         list of conversation turns with speaker and content.
                         
        Returns:
            Dictionary with status and extracted knowledge
        """
        try:
            # Convert conversation to string if it's a structured format
            if isinstance(conversation, list):
                conversation_text = "\n".join([
                    f"{turn.get('speaker', 'Unknown')}: {turn.get('content', '')}"
                    for turn in conversation
                ])
            else:
                conversation_text = conversation
            
            # Use CoordinatorAgent to analyze the conversation with an LLM
            logger.info("Requesting LLM analysis of conversation")
            
            # Prepare the prompt for extracting learnable content
            system_prompt = """
            You are an AI assistant tasked with extracting knowledge from conversations.
            Your goal is to identify:
            1. Key facts that should be stored in long-term memory
            2. Contextual information that should be kept in short-term memory
            
            For each piece of knowledge, determine:
            - The topic/subject
            - The content (the actual information)
            - Whether it should be stored in long-term or short-term memory
            
            Format your response as a JSON object with the following structure:
            {
                "long_term_knowledge": [
                    {"topic": "topic1", "content": "fact1"},
                    {"topic": "topic2", "content": "fact2"}
                ],
                "short_term_context": [
                    {"source": "user", "content": "contextual information 1"},
                    {"source": "system", "content": "contextual information 2"}
                ]
            }
            """
            
            # Send request to CoordinatorAgent
            self.coordinator_socket.send_json({
                'action': 'request_model_inference',
                'model_name': 'default',
                'prompt': conversation_text,
                'system_prompt': system_prompt,
                'temperature': 0.3,
                'request_id': f"learning_{int(time.time())}"
            })
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(self.request_timeout))
            if self.coordinator_socket in socks and socks[self.coordinator_socket] == zmq.POLLIN:
                response = self.coordinator_socket.recv_json()
                
                if response.get('status') != 'success':
                    logger.error(f"Error from CoordinatorAgent: {response.get('message')}")
                    return {
                        'status': 'error',
                        'message': f"Failed to analyze conversation: {response.get('message')}"
                    }
                
                # Extract the analysis results
                analysis_text = response.get('result', '')
                
                # Parse the JSON response from the LLM
                try:
                    # Find JSON in the response (in case LLM added extra text)
                    import re
                    json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
                    if json_match:
                        analysis_json = json.loads(json_match.group(0))
                    else:
                        analysis_json = json.loads(analysis_text)
                        
                    # Process long-term knowledge
                    long_term_results = []
                    if 'long_term_knowledge' in analysis_json:
                        for item in analysis_json['long_term_knowledge']:
                            # Add to knowledge base
                            result = self._add_to_knowledge_base(item['topic'], item['content'])
                            long_term_results.append(result)
                    
                    # Process short-term context
                    short_term_results = []
                    if 'short_term_context' in analysis_json:
                        for item in analysis_json['short_term_context']:
                            # Add to memory manager
                            result = self._add_to_memory_manager(item)
                            short_term_results.append(result)
                    
                    return {
                        'status': 'success',
                        'message': 'Conversation analyzed and knowledge extracted',
                        'long_term_knowledge': long_term_results,
                        'short_term_context': short_term_results
                    }
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing LLM response as JSON: {e}")
                    logger.error(f"Raw response: {analysis_text}")
                    return {
                        'status': 'error',
                        'message': f"Failed to parse LLM response: {str(e)}"
                    }
            else:
                # Socket timed out
                logger.error("Timeout waiting for response from CoordinatorAgent")
                return {
                    'status': 'error',
                    'message': "Timeout waiting for analysis results"
                }
                
        except Exception as e:
            logger.error(f"Error in analyze_and_learn: {e}")
            return {
                'status': 'error',
                'message': f"Failed to analyze conversation: {str(e)}"
            }
    
    def _add_to_knowledge_base(self, topic: str, content: Any) -> Dict[str, Any]:
        """Add a fact to the knowledge base.
        
        Args:
            topic: Topic of the fact
            content: Content of the fact
            
        Returns:
            Result of the operation
        """
        try:
            # Send request to KnowledgeBase
            self.knowledge_base_socket.send_json({
                'action': 'add_fact',
                'topic': topic,
                'content': content
            })
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(self.request_timeout))
            if self.knowledge_base_socket in socks and socks[self.knowledge_base_socket] == zmq.POLLIN:
                response = self.knowledge_base_socket.recv_json()
                
                # If fact already exists, try to update it
                if response.get('status') == 'error' and 'already exists' in response.get('message', ''):
                    logger.info(f"Fact '{topic}' already exists, updating instead")
                    
                    # Send update request
                    self.knowledge_base_socket.send_json({
                        'action': 'update_fact',
                        'topic': topic,
                        'content': content
                    })
                    
                    # Wait for response with timeout
                    socks = dict(self.poller.poll(self.request_timeout))
                    if self.knowledge_base_socket in socks and socks[self.knowledge_base_socket] == zmq.POLLIN:
                        response = self.knowledge_base_socket.recv_json()
                    else:
                        response = {
                            'status': 'error',
                            'message': 'Timeout waiting for knowledge base update response'
                        }
                
                return {
                    'topic': topic,
                    'result': response
                }
            else:
                # Socket timed out
                logger.error("Timeout waiting for response from KnowledgeBase")
                return {
                    'topic': topic,
                    'result': {
                        'status': 'error',
                        'message': 'Timeout waiting for knowledge base response'
                    }
                }
                
        except Exception as e:
            logger.error(f"Error adding to knowledge base: {e}")
            return {
                'topic': topic,
                'result': {
                    'status': 'error',
                    'message': f"Failed to add to knowledge base: {str(e)}"
                }
            }
    
    def _add_to_memory_manager(self, context_item: Dict[str, Any]) -> Dict[str, Any]:
        """Add a context item to the memory manager.
        
        Args:
            context_item: Context item with source and content
            
        Returns:
            Result of the operation
        """
        try:
            # Send request to MemoryManager
            self.memory_manager_socket.send_json({
                'action': 'add_interaction',
                'interaction': context_item
            })
            
            # Wait for response with timeout
            socks = dict(self.poller.poll(self.request_timeout))
            if self.memory_manager_socket in socks and socks[self.memory_manager_socket] == zmq.POLLIN:
                response = self.memory_manager_socket.recv_json()
                return {
                    'content': context_item.get('content', ''),
                    'result': response
                }
            else:
                # Socket timed out
                logger.error("Timeout waiting for response from MemoryManager")
                return {
                    'content': context_item.get('content', ''),
                    'result': {
                        'status': 'error',
                        'message': 'Timeout waiting for memory manager response'
                    }
                }
                
        except Exception as e:
            logger.error(f"Error adding to memory manager: {e}")
            return {
                'content': context_item.get('content', ''),
                'result': {
                    'status': 'error',
                    'message': f"Failed to add to memory manager: {str(e)}"
                }
            }
        
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Place all blocking init here
            self._init_components()
            self.initialization_status["components"]["core"] = True
            self.initialization_status["progress"] = 1.0
            self.initialization_status["is_initialized"] = True
            logger.info("LearningManager initialization complete")
        except Exception as e:
            self.initialization_status["error"] = str(e)
            self.initialization_status["progress"] = 0.0
            logger.error(f"Initialization error: {e}")

    def run(self):
        logger.info("Starting LearningManager main loop")
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
                        response = self._handle_request(message)
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

    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests."""
        action = request.get('action')
        
        if action == 'ping':
            return {'status': 'success', 'message': 'pong'}
            
        elif action == 'get_health':
            return self.get_health_status()
            
        elif action == 'analyze_and_learn':
            return self.analyze_and_learn(request.get('conversation', ''))
            
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}
            
    def stop(self):
        """Stop the agent and clean up resources."""
        self.socket.close()
        self.memory_manager_socket.close()
        self.knowledge_base_socket.close()
        self.coordinator_socket.close()
        self.context.term()
        logger.info("Learning Manager stopped")

if __name__ == '__main__':
    agent = LearningManager()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
