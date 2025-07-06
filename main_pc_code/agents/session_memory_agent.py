"""
Session Memory Agent
------------------
Maintains context memory and session awareness:
- 

# Add the project's main_pc_code directory to the Python path
import sys
import os
from pathlib import Path
MAIN_PC_CODE_DIR = Path(__file__).resolve().parent.parent
if MAIN_PC_CODE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, MAIN_PC_CODE_DIR.as_posix())

Stores conversation history
- Provides context for LLM prompts
- Manages user sessions
- Supports semantic search of past interactions
"""

import zmq
import json
import logging
import time
import threading
import os
import sys
import sqlite3
import uuid
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import numpy as np

from common.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config

# Import the MemoryClient for new orchestrator
try:
    from main_pc_code.src.memory.memory_client import MemoryClient
except Exception as import_error:
    logging.warning(f"[SessionMemoryAgent] Falling back to stub MemoryClient due to import error: {import_error}")
    class MemoryClient:  # type: ignore
        """Lightweight stub when full MemoryClient cannot be imported."""
        def __init__(self):
            self._agent_id = "stub"
            self._session_id = None
        # API mirrors expected methods but only logs actions.
        def set_agent_id(self, agent_id):
            self._agent_id = agent_id
        def set_session_id(self, session_id):
            self._session_id = session_id
        def create_session(self, user_id, session_metadata=None, session_type="conversation"):
            sid = self._session_id or str(uuid.uuid4())
            return {"status": "success", "data": {"session_id": sid}}
        def create_memory(self, memory_type, content, tags=None):
            return {"status": "success"}
        def batch_read(self, memory_type, limit=50, sort_field="created_at", sort_order="desc"):
            return {"status": "success", "data": {"memories": []}}

# Parse command line arguments
config = load_config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('session_memory_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZMQ Configuration
ZMQ_MEMORY_PORT = 5574  # Port for session memory requests
ZMQ_HEALTH_PORT = 6583  # Health status
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

# Memory settings
MAX_CONTEXT_TOKENS = 2000  # Maximum tokens for context
MAX_SESSIONS = 100  # Maximum number of active sessions
SESSION_TIMEOUT = 3600  # Session timeout in seconds (1 hour)
DB_PATH = "data/session_memory.db"  # SQLite database path

class SessionMemoryAgent(BaseAgent):
    """Agent for handling session memory and context management."""
    
    def __init__(self, port: int = 5574, health_port: int = 6583):
        """Initialize the session memory agent."""
        super().__init__(name="SessionMemoryAgent", port=port, health_check_port=health_port)
        self.context = zmq.Context()
        # Service discovery for orchestrator address (replace with actual discovery logic if needed)
        orchestrator_host = "localhost"
        orchestrator_port = 7115
        self.orchestrator_socket = self.context.socket(zmq.REQ)
        self.orchestrator_socket.connect(f"tcp://{orchestrator_host}:{orchestrator_port}")
        self._register_service()

    def _register_service(self):
        # Optionally implement registration logic if needed
        pass

    def _send_to_orchestrator(self, request: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.orchestrator_socket.send_json(request)
            response = self.orchestrator_socket.recv_json()
            if not isinstance(response, dict):
                return {"data": response}
            return response
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        action = request.get("action")
        if action == "create_session":
            return self._create_session(request)
        elif action == "add_interaction":
            return self._add_interaction(request)
        elif action == "get_context":
            return self._get_context(request)
        elif action == "delete_session":
            return self._delete_session(request)
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def _create_session(self, request: Dict[str, Any]) -> Dict[str, Any]:
        user_id = request.get("user_id", "default")
        metadata = request.get("metadata", {})
        payload = {
            "action": "add_memory",
            "payload": {
                "content": f"Session for user {user_id}",
                "memory_type": "session",
                "metadata": metadata,
                "created_at": datetime.now().isoformat()
            }
        }
        return self._send_to_orchestrator(payload)

    def _add_interaction(self, request: Dict[str, Any]) -> Dict[str, Any]:
        session_id = request.get("session_id")
        role = request.get("role")
        content = request.get("content")
        metadata = request.get("metadata", {})
        if not session_id or not role or not content:
            return {"status": "error", "message": "Missing required parameters"}
        payload = {
            "action": "add_memory",
            "payload": {
                "content": content,
                "memory_type": "interaction",
                "metadata": {**metadata, "role": role},
                "parent_id": session_id,
                "created_at": datetime.now().isoformat()
            }
        }
        return self._send_to_orchestrator(payload)

    def _get_context(self, request: Dict[str, Any]) -> Dict[str, Any]:
        session_id = request.get("session_id")
        if not session_id:
            return {"status": "error", "message": "Missing session_id"}
        payload = {
            "action": "get_children",
            "parent_id": session_id
        }
        return self._send_to_orchestrator(payload)

    def _delete_session(self, request: Dict[str, Any]) -> Dict[str, Any]:
        session_id = request.get("session_id")
        if not session_id:
            return {"status": "error", "message": "Missing session_id"}
        payload = {
            "action": "delete_memory",
            "memory_id": session_id
        }
        return self._send_to_orchestrator(payload)

# Example usage
if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = SessionMemoryAgent()
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