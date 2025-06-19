import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import zmq
import json
import os
from agents.proactive_agent_interface import send_proactive_event

import threading
import time
import logging

LOG_PATH = "learning_mode_agent.log"
LEARNING_MODE_STORE_PATH = "learning_mode_store.json"
ZMQ_LEARNING_MODE_PORT = 5599

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class LearningModeAgent:
    def broadcast_learning_suggestion(self, text, user=None, emotion="neutral"):
        send_proactive_event(event_type="suggestion", text=text, user=user, emotion=emotion)

    def __init__(self, zmq_port=ZMQ_LEARNING_MODE_PORT):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
        self.learning_data = self.load_learning_data()
        self.lock = threading.Lock()
        self.running = True
        logging.info(f"[LearningMode] Agent started on port {zmq_port}")

    def load_learning_data(self):
        if os.path.exists(LEARNING_MODE_STORE_PATH):
            with open(LEARNING_MODE_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_learning_data(self):
        with open(LEARNING_MODE_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.learning_data, f, ensure_ascii=False, indent=2)

    def handle_query(self, query):
        action = query.get("action")
        user = query.get("user_id", "default")
        if action == "start_learning":
            topic = query.get("topic")
            with self.lock:
                if user not in self.learning_data:
                    self.learning_data[user] = []
                self.learning_data[user].append({
                    "timestamp": time.time(),
                    "topic": topic,
                    "status": "started"
                })
                self.save_learning_data()
            logging.info(f"[LearningMode] Started learning for {user}: {topic}")
            return {"status": "ok"}
        elif action == "get_learning_sessions":
            with self.lock:
                sessions = self.learning_data.get(user, [])
            return {"status": "ok", "sessions": sessions}
        elif action == "clear_learning_sessions":
            with self.lock:
                self.learning_data[user] = []
                self.save_learning_data()
            logging.info(f"[LearningMode] Cleared learning sessions for {user}")
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
                logging.error(f"[LearningMode] Error: {e}")
                self.socket.send_string(json.dumps({"status": "error", "reason": str(e)}))

if __name__ == "__main__":
    agent = LearningModeAgent()
    agent.run()
