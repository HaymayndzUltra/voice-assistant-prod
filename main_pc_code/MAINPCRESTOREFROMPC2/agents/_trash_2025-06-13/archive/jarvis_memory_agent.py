from main_pc_code.src.core.base_agent import BaseAgent
import zmq
import json
import os
import sys
import traceback

# Add the parent directory to sys.path to allow importing from sibling modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
from main_pc_code.agents.proactive_agent_interface import send_proactive_event
except ImportError:
    # Define a fallback function if the import fails
    def send_proactive_event(event_type, data):
        logging.warning(f"[Jarvis_Memory] Could not import send_proactive_event, using fallback. Event: {event_type}")
        return None

import threading
import time
import logging

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

LOG_PATH = "jarvis_memory_agent.log"
JARVIS_MEMORY_STORE_PATH = "jarvis_memory_store.json"
ZMQ_JARVIS_MEMORY_PORT = 5598

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class JarvisMemoryAgent(BaseAgent):
    def broadcast_reminder(self, text, user=None, emotion="neutral"):
        send_proactive_event(event_type="reminder", text=text, user=user, emotion=emotion)

    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="JarvisMemoryAgent")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        self.memory = self.load_memory()
        self.lock = threading.Lock()
        self.running = True
        logging.info(f"[JarvisMemory] Agent started on port {zmq_port}")

    def load_memory(self):
        if os.path.exists(JARVIS_MEMORY_STORE_PATH):
            with open(JARVIS_MEMORY_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_memory(self):
        with open(JARVIS_MEMORY_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=2)

    def handle_query(self, query):
        action = query.get("action")
        user = query.get("user_id", "default")
        if action == "add_memory":
            memory_entry = query.get("memory")
            with self.lock:
                if user not in self.memory:
                    self.memory[user] = []
                self.memory[user].append({
                    "timestamp": time.time(),
                    "memory": memory_entry
                })
                self.save_memory()
            logging.info(f"[JarvisMemory] Added memory for {user}: {memory_entry}")
            # Proactive broadcast for new memory (if it's a reminder)
            if memory_entry and isinstance(memory_entry, dict) and memory_entry.get("type") == "reminder":
                send_proactive_event(
                    event_type="reminder",
                    text=memory_entry.get("text", "You have a new reminder."),
                    user=user,
                    emotion=memory_entry.get("emotion", "neutral")
                )
            return {"status": "ok"}
        elif action == "get_memories":
            with self.lock:
                user_memories = self.memory.get(user, [])
            return {"status": "ok", "memories": user_memories}
        elif action == "clear_memories":
            with self.lock:
                self.memory[user] = []
                self.save_memory()
            logging.info(f"[JarvisMemory] Cleared memories for {user}")
            return {"status": "ok"}
        else:
            return {"status": "error", "reason": "Unknown action"}

    def run(self):
        while self.running:
            try:
                msg = self.socket.recv_string()
                query = json.loads(msg)
                resp = self.handle_query(query)
                self.socket.send_string(json.dumps(resp))
            except Exception as e:
                logging.error(f"[JarvisMemory] Error: {e}")
                self.socket.send_string(json.dumps({"status": "error", "reason": str(e)}))

if __name__ == "__main__":
    agent = JarvisMemoryAgent()
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise