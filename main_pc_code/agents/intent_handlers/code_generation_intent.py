from common.core.base_agent import BaseAgent
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Code Generation Intent Handler
-----------------------------
Handles code generation intent detection and processing
Connects to Model Manager Agent to request code generation
"""
import os
import zmq
import json
import time
import uuid
import logging
import pickle
from typing import Dict, Any, Optional


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(PathManager.join_path("main_pc_code", "..")))
from common.utils.path_manager import PathManager
from common.env_helpers import get_env
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PathManager.join_path("logs", "code_generation_intent.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CodeGenerationIntent")

class CodeGenerationIntentHandler(BaseAgent):
    """Handler for code generation intents"""
    
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="CodeGenerationIntent")
        """Initialize the code generation intent handler
        
        Args:
            mma_port: Port of the Model Manager Agent
        """
        self.mma_port = mma_port
        self.context = zmq.Context()
        self.socket = None
        self.connected = False
        self.request_timeout = 30000  # 30 seconds timeout for requests
        
        # Try to connect to the MMA
        self._connect()
    
    def _connect(self) -> bool:
        """Connect to the Model Manager Agent
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        if self.connected and self.socket is not None:
            return True
            
        try:
            # Create socket if it doesn't exist
            if self.socket is None:
                self.socket = self.context.socket(zmq.REQ)
                self.socket.setsockopt(zmq.LINGER, 0)
                self.socket.setsockopt(zmq.RCVTIMEO, self.request_timeout)
                self.socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second send timeout
            
            # Connect to the MMA
            self.socket.connect(f"tcp://localhost:{self.mma_port}")
            
            # Test connection with ping
            self.socket.send_string(json.dumps({"action": "ping"}))
            response_str = self.socket.recv_string()
            response = json.loads(response_str)
            
            if response.get("status") in ["ok", "success"]:
                logger.info(f"Connected to Model Manager Agent on port {self.mma_port}")
                self.connected = True
                return True
            else:
                logger.error(f"Failed to connect to Model Manager Agent: {response}")
                self.connected = False
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to Model Manager Agent: {e}")
            self.connected = False
            
            # Cleanup socket on error
            if self.socket is not None:
                self.socket.close()
                self.socket = None
                
            return False
    
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               
    
    def detect_code_generation_intent(self, text: str) -> Dict[str, Any]:
        """Detect if the text contains a code generation intent
        
        Args:
            text: The text to check for code generation intent
            
        Returns:
            Dict with intent detection result and extracted parameters
        """
        # Code generation trigger phrases and patterns
        code_triggers = [
            "write code", "generate code", "create program", "make a script",
            "code for", "program that", "function to", "can you code", 
            "develop a", "implement", "build me", "code that", "script for",
            "write a function", "create a class", "code snippet", "script that"
        ]
        
        # Filipino code triggers
        filipino_code_triggers = [
            "gumawa ng code", "mag-code", "gumawa ng program",
            "code para sa", "program na", "function para sa"
        ]
        
        # Check if any trigger phrase is present
        has_trigger = False
        for trigger in code_triggers + filipino_code_triggers:
            if trigger.lower() in text.lower():
                has_trigger = True
                break
                
        if not has_trigger:
            return {"is_code_intent": False}
            
        # Basic language detection
        languages = ["python", "javascript", "java", "c++", "c#", "html", "css", "php"]
        detected_language = None
        
        for language in languages:
            if language.lower() in text.lower():
                detected_language = language
                break
                
        # Extract the actual code request by removing the trigger phrases
        code_prompt = text
        for trigger in code_triggers + filipino_code_triggers:
            if trigger.lower() in code_prompt.lower():
                # Keep the text after the trigger phrase as the code prompt
                trigger_index = code_prompt.lower().find(trigger.lower())
                if trigger_index >= 0:
                    code_prompt = code_prompt[trigger_index + len(trigger):].strip()
                    
        # If language is in the prompt, remove it from the prompt
        if detected_language and detected_language.lower() in code_prompt.lower():
            code_prompt = code_prompt.lower().replace(detected_language.lower(), "").strip()
            
        return {
            "is_code_intent": True,
            "language": detected_language,
            "code_prompt": code_prompt or text,  # Fallback to original text if extraction fails
            "confidence": 0.8  # Add confidence score
        }
    
    def handle_code_intent(self, text: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Handle a possible code generation intent
        
        Args:
            text: The text to process for code generation intent
            request_id: Optional request ID for tracking
            
        Returns:
            Dict with processing result
        """
        # Detect if this is a code generation intent
        intent_result = self.detect_code_generation_intent(text)
        
        if not intent_result.get("is_code_intent", False):
            return {"status": "not_code_intent", "request_id": request_id}
            
        # We have a code generation intent, handle it
        language = intent_result.get("language")
        code_prompt = intent_result.get("code_prompt", text)
        
        # Generate code
        generation_result = self.generate_code(
            prompt=code_prompt,
            language=language,
            request_id=request_id
        )
        
        # Add intent detection info to the result
        generation_result.update({
            "detected_language": language,
            "code_prompt": code_prompt,
            "original_text": text
        })
        
        return generation_result
    
    def close(self):
        """Close the connection to the Model Manager Agent"""
        if self.socket is not None:
            self.socket.close()
            self.socket = None
        self.connected = False

# Singleton instance
_instance = None

def get_instance(mma_port: int = 5556) -> CodeGenerationIntentHandler:
    """Get the singleton instance of the code generation intent handler
    
    Args:
        mma_port: Port of the Model Manager Agent
        
    Returns:
        The code generation intent handler instance
    """
    global _instance
    if _instance is None:
        _instance = CodeGenerationIntentHandler(mma_port)
    return _instance

# Test code
if __name__ == "__main__":
    handler = get_instance()
    
    # Test intent detection
    test_phrases = [
        "Write code for a Fibonacci sequence",
        "Can you generate a Python function to sort a list?",
        "Create a program that calculates prime numbers",
        "What's the weather today?",
        "Gumawa ng code para sa pag-compute ng average",
        "Mag-code ng Python function para sa translation"
    ]
    
    print("Testing code generation intent detection:")
    for phrase in test_phrases:
        result = handler.detect_code_generation_intent(phrase)
        print(f"- '{phrase}': {result}")
        
    # Test code generation
    print("\nTesting code generation:")
    try:
        result = handler.handle_code_intent("Write a Python function to calculate factorial")
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            print("Generated code:")
            print(result.get('code', ''))
    except Exception as e:
        print(f"Error testing code generation: {e}")
        
    # Close connection
    handler.close()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
