"""
Chitchat Agent
-------------
Handles natural conversational interactions:
- Processes casual conversation requests
- Connects to local or remote LLM for responses
- Maintains conversation context
- Integrates with personality engine
"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.path_env import get_main_pc_code, get_project_root
from common.utils.path_manager import PathManager

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if str(MAIN_PC_CODE_DIR) not in sys.path:
    sys.path.insert(0, str(MAIN_PC_CODE_DIR))

import zmq
import json
import logging
import time
import threading
import uuid
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional

from common.core.base_agent import BaseAgent
from common.config_manager import load_unified_config
from common.env_helpers import get_env
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket

config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chitchat_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ Configuration
ZMQ_CHITCHAT_PORT = 5573  # Port for receiving chitchat requests
ZMQ_HEALTH_PORT = 6582  # Health status
PC2_IP = get_service_ip("pc2")  # PC2 IP address
PC2_LLM_PORT = 5557  # Remote LLM on PC2
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Conversation settings
MAX_HISTORY_LENGTH = 10  # Maximum number of conversation turns to remember
MAX_HISTORY_TOKENS = 2000  # Maximum number of tokens in history

class ChitchatAgent(BaseAgent):
    """Agent for handling natural conversational interactions. Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:')."""
    
    def _get_default_port(self) -> int:
        """Override default port to use the configured port."""
        return 5711  # Using the new port we configured
        
    def __init__(self):
        """Initialize the chitchat agent."""
        # Use config loader for agent args or set defaults
        self.config = load_unified_config(os.path.join(PathManager.get_project_root(), "main_pc_code", "config", "startup_config.yaml")) if callable(load_config) else {}
        super().__init__(
            name=getattr(self.config, 'name', 'ChitchatAgent'),
            port=getattr(self.config, 'port', 5711)
        )
        # Initialize state
        self.start_time = time.time()
        self.running = True
        self.conversation_history = {}  # User ID -> conversation history
        self.health_thread = None
        self.conversations_handled = 0
        self.last_interaction_time = 'N/A'
        # Determine ports
        self.chitchat_port = self.port
        self.health_port = self.port + 1
        # Setup ZMQ sockets
        self._init_sockets()
        logger.info("Chitchat Agent initialized")
    
    

        # Modern error reporting now handled by BaseAgent's UnifiedErrorHandler
    def _init_sockets(self):
        """Set up ZMQ sockets."""
        try:
            # Main REP socket for chitchat requests with fallback if port in use
            self.socket = get_rep_socket(self.endpoint).socket
            self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            rep_port = self.chitchat_port
            while True:
                try:
                    self.socket.bind(f"tcp://*:{rep_port}")
                    if rep_port != self.chitchat_port:
                        logger.warning(f"Chitchat REP port {self.chitchat_port} unavailable, using {rep_port} instead")
                        self.chitchat_port = rep_port
                    break
                except zmq.error.ZMQError as e:
                    if 'Address already in use' in str(e):
                        rep_port += 1  # try next port
                    else:
                        raise
            
            # Health socket with fallback
            self.health_socket = self.context.socket(zmq.PUB)
            health_port = self.health_port
            while True:
                try:
                    self.health_socket.bind(f"tcp://*:{health_port}")
                    if health_port != self.health_port:
                        logger.warning(f"Health port {self.health_port} unavailable, using {health_port} instead")
                        self.health_port = health_port
                    break
                except zmq.error.ZMQError as e:
                    if 'Address already in use' in str(e):
                        health_port += 1
                    else:
                        raise
            
            # PC2 LLM socket
            self.llm_socket = self.context.socket(zmq.REQ)
            self.llm_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
            self.llm_socket.setsockopt(zmq.LINGER, 0)
            self.llm_socket.setsockopt(zmq.RCVTIMEO, 30000)  # 30 second timeout
            self.llm_socket.connect(f"tcp://{PC2_IP}:{PC2_LLM_PORT}")
            
            logger.info(f"ZMQ sockets initialized - Chitchat REP: {self.chitchat_port}, Health: {self.health_port}, LLM: {PC2_IP}:{PC2_LLM_PORT}")
        except Exception as e:
            logger.error(f"Error initializing ZMQ sockets: {str(e)}")
            raise
    
    def _get_conversation_history(self, user_id):
        """Get conversation history for a user."""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        return self.conversation_history[user_id]
    
    def _add_to_history(self, user_id, role, content):
        """Add a message to the conversation history."""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        # Add new message
        self.conversation_history[user_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim history if needed
        if len(self.conversation_history[user_id]) > MAX_HISTORY_LENGTH:
            self.conversation_history[user_id] = self.conversation_history[user_id][-MAX_HISTORY_LENGTH:]
    
    def _format_messages_for_llm(self, history):
        """Format conversation history for LLM."""
        messages = []
        
        # Add system message
        messages.append({
            "role": "system",
            "content": "You are a helpful, friendly, and conversational AI assistant. Respond in a natural, engaging way. Keep responses concise but informative."
        })
        
        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        return messages
    
    def _generate_response_with_local_llm(self, messages):
        """Generate a response using a local LLM."""
        try:
            # TODO: Implement local LLM integration
            # This is a placeholder for future local model integration
            logger.warning("Local LLM not implemented, falling back to remote LLM")
            return self._generate_response_with_remote_llm(messages)
        except Exception as e:
            logger.error(f"Error generating response with local LLM: {str(e)}")
            return "I'm having trouble thinking right now. Can we try again in a moment?"
    
    def _generate_response_with_remote_llm(self, messages):
        """Generate a response using the remote LLM on PC2."""
        try:
            # Create request
            request = {
                "action": "generate_chat_response",
                "messages": messages,
                "model": "gpt-4o",  # Use GPT-4o for best conversational quality
                "temperature": 0.7,
                "max_tokens": 300,
                "request_id": str(uuid.uuid4())
            }
            
            # Send request
            self.llm_socket.send_json(request)
            
            # Get response
            response = self.llm_socket.recv_json()
            
            if response.get("status") == "success":
                return response.get("response", "")
            else:
                logger.error(f"Error from remote LLM: {response.get('message', 'Unknown error')}")
                return "I'm having trouble connecting to my thinking module. Can we try again in a moment?"
        except zmq.error.ZMQError as e:
            logger.error(f"ZMQ error communicating with remote LLM: {str(e)}")
            return "I'm having trouble connecting to my thinking module. Can we try again in a moment?"
        except Exception as e:
            logger.error(f"Error generating response with remote LLM: {str(e)}")
            return "I'm having trouble thinking right now. Can we try again in a moment?"
    
    def process_chitchat(self, text, user_id=None):
        """Process a chitchat request and generate a response."""
        if not user_id:
            user_id = "default"
        
        logger.info(f"Processing chitchat request from user {user_id}: {text[:50]}...")
        
        # Get conversation history
        history = self._get_conversation_history(user_id)
        
        # Add user message to history
        self._add_to_history(user_id, "user", text)
        
        # Format messages for LLM
        messages = self._format_messages_for_llm(history)
        
        # Generate response
        try:
            # Try remote LLM first
            response = self._generate_response_with_remote_llm(messages)
        except Exception as e:
            logger.error(f"Error with remote LLM, falling back to local: {str(e)}")
            # Fallback to local LLM
            response = self._generate_response_with_local_llm(messages)
        
        # Add assistant response to history
        self._add_to_history(user_id, "assistant", response)
        
        # Update metrics
        self.conversations_handled += 1
        self.last_interaction_time = datetime.now().isoformat()
        
        return response
    
    def handle_request(self, request):
        """Handle a request from the coordinator."""
        try:
            action = request.get("action", "") if isinstance(request, dict) else ""
            
            if action == "health_check":
                return {
                    "status": "ok",
                    "message": "ChitchatAgent is healthy",
                    "initialization_status": {"is_initialized": True}
                }
            if action == "chitchat":
                text = request.get("text", "") if isinstance(request, dict) else ""
                user_id = request.get("user_id", "default") if isinstance(request, dict) else "default"
                
                response = self.process_chitchat(text, user_id)
                
                return {
                    "status": "success",
                    "response": response,
                    "request_id": request.get("request_id", "") if isinstance(request, dict) else ""
                }
            elif action == "clear_history":
                user_id = request.get("user_id", "default") if isinstance(request, dict) else "default"
                
                if user_id in self.conversation_history:
                    self.conversation_history[user_id] = []
                
                return {
                    "status": "success",
                    "message": f"Conversation history cleared for user {user_id}",
                    "request_id": request.get("request_id", "") if isinstance(request, dict) else ""
                }
            else:
                return {
                    "status": "error",
                    "message": f"Unknown action: {action}",
                    "request_id": request.get("request_id", "") if isinstance(request, dict) else ""
                }
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {
                "status": "error",
                "message": f"Error: {str(e)}",
                "request_id": request.get("request_id", "") if isinstance(request, dict) and "request_id" in request else ""
            }
    
    def health_broadcast_loop(self):
        """Loop for broadcasting health status."""
        while self.running:
            try:
                # Prepare health status
                status = {
                    "component": "chitchat_agent",
                    "status": "running",
                    "timestamp": datetime.now().isoformat(),
                    "metrics": {
                        "active_users": len(self.conversation_history),
                        "total_conversations": sum(len(history) for history in self.conversation_history.values())
                    }
                }
                
                # Publish health status
                self.health_socket.send_json(status)
                
            except Exception as e:
                logger.error(f"Error broadcasting health status: {str(e)}")
            
            # Sleep for a while
            time.sleep(5)
    
    def run(self):
        """Run the chitchat agent."""
        logger.info("Starting chitchat agent")
        
        # Start health broadcast thread
        self.health_thread = threading.Thread(target=self.health_broadcast_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        
        # Call parent's run method to ensure health check thread works
        super().run()
        
        # Main loop
        while self.running:
            try:
                # Wait for request
                request_json = self.socket.recv_json()
                
                # Process request
                response = self.handle_request(request_json)
                
                # Send response
                self.socket.send_json(response)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                # Try to send error response
                try:
                    self.socket.send_json({
                        "status": "error",
                        "message": f"Server error: {str(e)}",
                        "request_id": request_json.get("request_id", "") if 'request_json' in locals() else ""
                    })
                except:
                    pass
    
    def stop(self):
        """Stop the chitchat agent."""
        logger.info("Stopping chitchat agent")
        self.running = False
        
        # Close sockets
        # TODO-FIXME – removed stray 'self.' (O3 Pro Max fix)
        self.health_socket.close()
        self.llm_socket.close()
        # Wait for threads to finish
        if self.health_thread:
            self.health_thread.join(timeout=1.0)
        
        logger.info("Chitchat agent stopped")

    def _get_health_status(self) -> Dict[str, Any]:
        """Overrides the base method to add agent-specific health metrics."""
        return {
            'status': 'ok',
            'ready': True,
            'initialized': True,
            'service': 'chitchat',
            'components': {
                'llm_connected': hasattr(self, 'llm_socket'),
                'health_broadcast': self.health_thread is not None and self.health_thread.is_alive() if self.health_thread else False
            },
            'chitchat_status': 'active',
            'conversations_handled': self.conversations_handled,
            'last_interaction_time': self.last_interaction_time,
            'active_users': len(self.conversation_history),
            'uptime': time.time() - self.start_time
        }

    def cleanup(self):
        """Gracefully shutdown the agent"""
        logger.info("Cleaning up ChitchatAgent")
        self.running = False
        
        # Close sockets
        if hasattr(self, 'socket'):
                self.socket.close()
        if hasattr(self, 'health_socket'):
            self.health_socket.close()
        if hasattr(self, 'llm_socket'):
            self.llm_socket.close()
        # Wait for threads to finish
        if self.health_thread:
            self.health_thread.join(timeout=1.0)
            
        # Call parent cleanup
        super().cleanup()
        logger.info("ChitchatAgent cleanup complete")

    def _get_translation(self, text, target_lang='en'):
        """Request translation from the new TranslationService via ZMQ."""
        try:
            agent_info = self.discover_agent('TranslationService')
            if not agent_info or not isinstance(agent_info, dict):
                logger.error("Could not discover TranslationService.")
                return None
            # Remove any .get() calls on agent_info; only use direct dict access with fallback/defaults
            port = agent_info['port'] if 'port' in agent_info else 5595
            ip = agent_info['host'] if 'host' in agent_info else 'localhost'
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 5000)
            socket.connect(f"tcp://{ip}:{port}")
            payload = {
                'text': text,
                'target_lang': target_lang
            }
            # Optionally include session_id if available
            if hasattr(self, 'current_session_id'):
                payload['session_id'] = self.current_session_id
            logger.info(f"Requesting translation from TranslationService: {payload}")
            socket.send_json(payload)
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            if poller.poll(5000):
                response = socket.recv_json()
                logger.info(f"Received translation response: {response}")
                if response.get('status') == 'success' and response.get('result'):
                    result = response['result']
                    if isinstance(result, dict) and result.get('translation'):
                        return result['translation']
                    elif isinstance(result, str):
                        return result
                else:
                    logger.error(f"TranslationService error: {response}")
                    return None
            else:
                logger.error("Timeout waiting for TranslationService response.")
                return None
        except Exception as e:
            logger.error(f"Error communicating with TranslationService: {e}")
            return None
        finally:
            if 'socket' in locals() and not socket.closed:
                socket.close()
# Example usage
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = ChitchatAgent()
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