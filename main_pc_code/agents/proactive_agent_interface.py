from main_pc_code.src.core.base_agent import BaseAgent
# Proactive Agent Interface: For unified reminder/suggestion broadcasting
# Other agents (Jarvis Memory, Digital Twin, Learning Mode) can use this to send proactive events
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import os

from main_pc_code.utils.network import get_host

def send_proactive_event(event_type, text, user=None, emotion="neutral", extra=None):
    context = None  # Using pool
    socket = get_pub_socket(endpoint).socket
    # Determine host/port from environment or config
    host = get_host("PROACTIVE_HOST", "zmq.proactive_host")
    port = int(os.getenv("PROACTIVE_PORT", 5558))
    socket.connect(f"tcp://{host}:{port}")
    msg = {
        "type": event_type,  # 'reminder', 'suggestion', 'context', etc.
        "text": text,
        "user": user,
        "emotion": emotion,
        "proactive": True
    }
    if extra:
        msg.update(extra)
    socket.send_string(json.dumps(msg))
    print(f"[ProactiveAgentInterface] Sent event: {msg}")
if __name__ == "__main__":
    # Example usage: send a suggestion
    send_proactive_event("suggestion", "Time to take a break!", user="DemoUser", emotion="encouraging")

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
