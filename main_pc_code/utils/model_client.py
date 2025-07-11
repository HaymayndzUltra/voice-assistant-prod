import zmq
import os
import logging
import json
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# Use environment variables for flexibility in Docker
MMA_HOST = os.environ.get('MODEL_MANAGER_HOST', 'localhost')
MMA_PORT = os.environ.get('MODEL_MANAGER_PORT', '5588') # Default to test port, should be updated by env
MMA_ADDRESS = f"tcp://{MMA_HOST}:{MMA_PORT}"

# Network settings
# Allow override of timeout via env variable, default to 15000ms (15s)
REQUEST_TIMEOUT = int(os.environ.get("MODEL_CLIENT_TIMEOUT_MS", "15000"))  # in milliseconds
REQUEST_RETRIES = 3

# --- ZMQ Context Management ---
# Use a single, thread-safe context for the entire application
_context = zmq.Context.instance()


def _create_request_socket():
    """Creates and configures a ZMQ REQ socket."""
    socket = _context.socket(zmq.REQ)
    socket.connect(MMA_ADDRESS)
    
    # Set linger to 0 to prevent hanging on close
    socket.setsockopt(zmq.LINGER, 0)
    
    # Log connection for debugging
    logger.debug(f"Creating socket connected to {MMA_ADDRESS}")
    
    return socket


def generate(prompt: str, quality: str = "fast", **kwargs) -> dict:
    """
    Sends a generation request to the ModelManagerAgent and handles retries.

    Args:
        prompt (str): The text prompt to send to the LLM.
        quality (str): The desired model quality ('fast', 'quality', 'fallback').
        **kwargs: Additional parameters to pass to the model (e.g., temperature).

    Returns:
        dict: The JSON response from the server, or an error dictionary.
    """
    socket = _create_request_socket()
    
    request = {
        "action": "generate",
        "model_pref": quality,
        "prompt": prompt,
        "params": kwargs
    }

    retries_left = REQUEST_RETRIES
    while retries_left > 0:
        try:
            logger.debug(f"Sending request to {MMA_ADDRESS}: {json.dumps(request)}")
            socket.send_json(request)

            # Use a poller for robust timeout handling
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            
            if poller.poll(REQUEST_TIMEOUT):
                response = socket.recv_json()
                logger.debug(f"Received response: {json.dumps(response)}")
                socket.close()
                return response
            else:
                logger.warning(f"Timeout waiting for response from {MMA_ADDRESS}. Retrying...")
                retries_left -= 1
                # Recreate socket on timeout for a clean state
                socket.close()
                socket = _create_request_socket()
                # Add a small delay before retrying
                time.sleep(0.5)

        except zmq.ZMQError as e:
            logger.error(f"ZMQ Error during request: {e}")
            retries_left -= 1
            time.sleep(0.5) # Wait a bit before retrying on error
            # Recreate socket on error
            socket.close()
            socket = _create_request_socket()
    
    # If all retries fail
    socket.close()
    logger.error(f"Failed to get response from ModelManagerAgent after {REQUEST_RETRIES} retries.")
    return {
        "status": "error",
        "message": "Failed to communicate with ModelManagerAgent."
    }


def get_status() -> dict:
    """
    Pulls the status from the ModelManagerAgent.
    Uses a shorter timeout as status checks should be fast.
    """
    socket = _create_request_socket()
    request = {"action": "status"}
    
    try:
        logger.debug(f"Sending status request to {MMA_ADDRESS}")
        socket.send_json(request)
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)
        
        if poller.poll(1000): # 1-second timeout for status
            response = socket.recv_json()
            logger.debug(f"Received status response: {json.dumps(response)}")
            socket.close()
            return response
        else:
            logger.warning(f"Timeout getting status from {MMA_ADDRESS}")
            socket.close()
            return {"status": "error", "message": "Timeout getting status."}
    except zmq.ZMQError as e:
        logger.error(f"ZMQ Error during status request: {e}")
        socket.close()
        return {"status": "error", "message": f"ZMQ Error: {e}"} 