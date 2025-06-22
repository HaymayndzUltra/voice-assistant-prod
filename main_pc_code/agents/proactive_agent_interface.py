from src.core.base_agent import BaseAgent
# Proactive Agent Interface: For unified reminder/suggestion broadcasting
# Other agents (Jarvis Memory, Digital Twin, Learning Mode) can use this to send proactive events
import zmq
import json

def send_proactive_event(event_type, text, user=None, emotion="neutral", extra=None):
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect("tcp://127.0.0.1:5558")  # Proactive agent PUB port
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
    socket.close()
    context.term()

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
