"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
Client library for interacting with the ModelManagerAgent.
This provides a simplified interface for generating text, transcribing audio, etc.
"""

import zmq
import time
import logging
import os
import uuid
from typing import Dict, Any, List, Optional

from common.utils.network_util import retry_with_backoff
from main_pc_code.utils.service_discovery_client import get_service_address
from main_pc_code.utils.network_utils import get_zmq_connection_string

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

# Default configuration (legacy)
DEFAULT_MMA_PORT = 5555
DEFAULT_TIMEOUT_MS = 30000  # 30 seconds

# ModelOpsCoordinator defaults
DEFAULT_MOC_ZMQ_PORT = int(os.environ.get("MOC_ZMQ_PORT", 7211))
DEFAULT_MOC_HOST = os.environ.get("MOC_HOST", "localhost")

def request_inference(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a generic inference request to ModelOpsCoordinator (preferred),
    falling back to legacy ModelManagerAgent if needed.
    """
    # Try ModelOpsCoordinator via service discovery first
    moc_addr = get_service_address("ModelOpsCoordinator")
    if not moc_addr:
        moc_addr = get_zmq_connection_string(DEFAULT_MOC_ZMQ_PORT, DEFAULT_MOC_HOST)
    try:
        return _send_request(request, moc_addr)
    except Exception as e:
        logger.warning(f"MOC request failed ({e}); attempting legacy MMA")
        legacy_addr = f"tcp://localhost:{int(os.environ.get('MODEL_MANAGER_PORT', DEFAULT_MMA_PORT))}"
        return _send_request(request, legacy_addr)


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
    Generate text via ModelOpsCoordinator.
    """
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
    if conversation_id:
        request["conversation_id"] = conversation_id
    if batch_mode and batch_data:
        request["params"]["batch_mode"] = True
        request["params"]["batch_data"] = batch_data
    return request_inference(request)


def clear_conversation(conversation_id: str) -> Dict[str, Any]:
    request = {"action": "clear_conversation", "conversation_id": conversation_id}
    return request_inference(request)


def get_status() -> Dict[str, Any]:
    request = {"action": "status"}
    return request_inference(request)

# Apply retry decorator with reasonable defaults
@retry_with_backoff(max_retries=3, base_delay=0.5, jitter=0.4, exceptions=(zmq.error.Again, zmq.ZMQError, TimeoutError))
def _send_request(request: Dict[str, Any], address: str) -> Dict[str, Any]:
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    try:
        socket.connect(address)
        socket.setsockopt(zmq.RCVTIMEO, DEFAULT_TIMEOUT_MS)
        if "request_id" not in request:
            request["request_id"] = str(uuid.uuid4())
        if "timestamp" not in request:
            request["timestamp"] = time.time()
        socket.send_json(request)
        response = socket.recv_json()
        if not isinstance(response, dict):
            response = {"status": "error", "message": "Invalid response format", "raw_response": str(response)}
        return response
    except zmq.error.Again:
        logger.error(f"Timeout waiting for response at {address}")
        return {"status": "error", "message": f"Timeout waiting for response at {address}", "request_id": request.get("request_id", "unknown")}
    except Exception as e:
        logger.error(f"Error communicating with inference backend at {address}: {e}")
        raise
    finally:
        socket.close()
        context.term() 