"""
Client library for interacting with the ModelManagerAgent.
This provides a simplified interface for generating text, transcribing audio, etc.
"""

import zmq
import time
import json
import logging
import os
import uuid
from typing import Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_MMA_PORT = 5555
DEFAULT_TIMEOUT_MS = 30000  # 30 seconds

def generate(prompt: str, 
             model_pref: str = "fast", 
             max_tokens: int = 256,
             temperature: float = 0.7,
             top_p: float = 0.95,
             conversation_id: Optional[str] = None,
             batch_mode: bool = False,
             batch_data: Optional[List[Dict[str, Any]]] = None,
             **kwargs) -> Dict[str, Any]:
    """
    Generate text using the ModelManagerAgent.
    
    Args:
        prompt: The prompt to generate from
        model_pref: Model preference ("fast", "quality", "balanced", etc.)
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature (higher = more random)
        top_p: Nucleus sampling parameter
        conversation_id: Optional conversation ID for KV-cache reuse
        batch_mode: Whether to use batch processing mode
        batch_data: List of data items for batch processing
        **kwargs: Additional parameters to pass to the model
        
    Returns:
        Dictionary with generated text and metadata
    """
    # Prepare the request
    request = {
        "action": "generate",
        "model_pref": model_pref,
        "prompt": prompt,
        "params": {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            **kwargs
        }
    }
    
    # Add conversation_id if provided
    if conversation_id:
        request["conversation_id"] = conversation_id
    
    # Add batch processing parameters if enabled
    if batch_mode and batch_data:
        request["params"]["batch_mode"] = True
        request["params"]["batch_data"] = batch_data
    
    # Send the request to the ModelManagerAgent
    response = _send_request(request)
    
    return response

def clear_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Clear the KV cache for a specific conversation.
    
    Args:
        conversation_id: The conversation ID to clear
        
    Returns:
        Dictionary with status information
    """
    request = {
        "action": "clear_conversation",
        "conversation_id": conversation_id
    }
    
    response = _send_request(request)
    return response

def get_status() -> Dict[str, Any]:
    """
    Get the status of the ModelManagerAgent.
    
    Returns:
        Dictionary with status information
    """
    request = {
        "action": "status"
    }
    
    response = _send_request(request)
    return response

def _send_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a request to the ModelManagerAgent and get the response.
    
    Args:
        request: The request dictionary
        
    Returns:
        The response dictionary
    """
    # Get MMA port from environment or use default
    mma_port = int(os.environ.get("MMA_PORT", DEFAULT_MMA_PORT))
    
    # Create ZMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    
    try:
        # Connect to the ModelManagerAgent
        socket.connect(f"tcp://localhost:{mma_port}")
        
        # Set timeout
        socket.setsockopt(zmq.RCVTIMEO, DEFAULT_TIMEOUT_MS)
        
        # Add request ID if not present
        if "request_id" not in request:
            request["request_id"] = str(uuid.uuid4())
            
        # Add timestamp if not present
        if "timestamp" not in request:
            request["timestamp"] = time.time()
        
        # Send the request
        socket.send_json(request)
        
        # Wait for the response
        response = socket.recv_json()
        
        # Ensure response is a dictionary
        if not isinstance(response, dict):
            response = {"status": "error", "message": "Invalid response format", "raw_response": str(response)}
        
        return response
    
    except zmq.error.Again:
        logger.error(f"Timeout waiting for response from ModelManagerAgent (port {mma_port})")
        return {
            "status": "error",
            "message": "Timeout waiting for response from ModelManagerAgent",
            "request_id": request.get("request_id", "unknown")
        }
    
    except Exception as e:
        logger.error(f"Error communicating with ModelManagerAgent: {e}")
        return {
            "status": "error",
            "message": f"Error communicating with ModelManagerAgent: {str(e)}",
            "request_id": request.get("request_id", "unknown")
        }
    
    finally:
        # Clean up
        socket.close()
        context.term() 