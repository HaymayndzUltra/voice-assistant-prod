from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = get_main_pc_code()
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Streaming Language to LLM Connector
Connects the language analyzer to the LLM translation connector.
"""
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import pickle
import json
import time
import logging
import threading
import psutil
from datetime import datetime
from common.env_helpers import get_env
from common.utils.path_env import get_main_pc_code, get_project_root

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LanguageToLLMConnector")

# ZMQ settings
LANGUAGE_PORT = 5577  # Language analyzer output (updated)
LLM_INPUT_PORT = 5580  # LLM translator input

class StreamingLanguageToLLM(BaseAgent):
    """Connects language analyzer to LLM translation connector"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="StreamingLanguageToLlm")
        """Initialize the connector"""
        # Set up ZMQ context
        self.context = None  # Using pool
        
        # Socket to receive from language analyzer
        self.receiver = self.context.socket(zmq.SUB)
        self.receiver.connect(f"tcp://localhost:{LANGUAGE_PORT}")
        self.receiver.setsockopt(zmq.SUBSCRIBE, b"")
        
        # Socket to send to LLM connector
        self.sender = self.context.socket(zmq.PUB)
        self.sender.bind(f"tcp://*:{LLM_INPUT_PORT}")
        
        # Running flag
        self.running = False
        
        logger.info("Language to LLM Connector initialized")
    
    def start(self):
        """Start the connector"""
        self.running = True
        logger.info("Language to LLM Connector started")
        
        while self.running:
            try:
                # Receive message from language analyzer
                msg = self.receiver.recv(flags=zmq.NOBLOCK)
                print(f"[DEBUG] LanguageToLLM received raw msg: {msg}")
                logger.info(f"[DEBUG] LanguageToLLM received raw msg: {msg}")
                data = pickle.loads(msg)
                
                # Check if we have necessary data
                if 'transcription' in data and 'language_type' in data:
                    text = data.get('transcription', '')
                    language_type = data.get('language_type', 'unknown')
                    
                    logger.info(f"Received {language_type} text: {text}")
                    
                    # Forward to LLM connector
                    llm_msg = {
                        'type': 'translation_request',
                        'text': text,
                        'language_type': language_type,
                        'timestamp': time.time()
                    }
                    logger.info(f"DEBUG: Outgoing LLM message: {llm_msg}")
                    self.sender.send(pickle.dumps(llm_msg))
                    logger.info(f"Forwarded to LLM translator")
                    
            except zmq.Again:
                # No message available
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"Error in connector: {e}")
                time.sleep(0.1)
    
    def stop(self):
        """Stop the connector"""
        self.running = False
        
        # Close sockets
        self.receiver.close()
        self.sender.close()
        
        logger.info("Language to LLM Connector stopped")


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
    logger.info("Starting Language to LLM Connector")
    connector = StreamingLanguageToLLM()
    
    try:
        connector.start()
    except KeyboardInterrupt:
        logger.info("Language to LLM Connector stopped by user")
    finally:
        connector.stop()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise