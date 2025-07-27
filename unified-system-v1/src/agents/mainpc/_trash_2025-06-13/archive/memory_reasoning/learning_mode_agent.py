from main_pc_code.src.core.base_agent import BaseAgent
import sys
from pathlib import Path
from common.config_manager import get_service_ip, get_service_url, get_redis_url
sys.path.append(str(Path(__file__).parent.parent))
import zmq
import json
import os
from src.agents.mainpc.proactive_agent_interface import send_proactive_event

import threading
import time
import logging
import psutil
from datetime import datetime
from common.env_helpers import get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

LOG_PATH = str(PathManager.get_logs_dir() / "learning_mode_agent.log")
LEARNING_MODE_STORE_PATH = "learning_mode_store.json"
ZMQ_LEARNING_MODE_PORT = 5598  # Changed from 5599 to avoid conflict with health monitoring

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class LearningModeAgent(BaseAgent):
    def broadcast_learning_suggestion(self, text, user=None, emotion="neutral"):
        send_proactive_event(event_type="suggestion", text=text, user=user, emotion=emotion)

    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="LearningModeAgent")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
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
    agent = LearningModeAgent()
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise