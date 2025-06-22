from src.core.base_agent import BaseAgent
import zmq
import json
import os
import threading
import time
import logging
import sys
from typing import List, Dict, Any

# Add the parent directory to sys.path to allow importing from sibling modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from agents.proactive_agent_interface import send_proactive_event
except ImportError:
    def send_proactive_event(event_type, data):
        logging.warning(f"[ContextualMemory] Could not import send_proactive_event, using fallback. Event: {event_type}")

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests
        return None

LOG_PATH = "contextual_memory_agent.log"
MEMORY_STORE_PATH = "contextual_memory_store.json"
USER_PROFILE_PATH = "user_profile.json"
DEFAULT_USER_ID = "default_user"
ZMQ_CONTEXTUAL_MEMORY_PORT = 5596
HEALTH_CHECK_PORT = 5598

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class ContextualMemoryAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="ContextualMemoryAgent")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        
        # Try to bind to the specified port
        try:
            self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
            self.port = zmq_port
            logging.info(f"[ContextualMemory] Successfully bound to port {zmq_port}")
        except zmq.error.ZMQError as e:
            if "Address in use" in str(e):
                logging.warning(f"[ContextualMemory] Port {zmq_port} is in use, trying alternative ports")
                alt_ports = [7596, 7597, 7598, 7599, 7600]
                for alt_port in alt_ports:
                    try:
                        self.socket.bind(f"tcp://127.0.0.1:{alt_port}")
                        self.port = alt_port
                        logging.info(f"[ContextualMemory] Successfully bound to alternative port {alt_port}")
                        break
                    except zmq.error.ZMQError:
                        continue
                else:
                    logging.error("[ContextualMemory] Could not bind to any port. Will keep running but won't process requests.")
                    self.port = None
            else:
                logging.error(f"[ContextualMemory] Error binding to port: {e}")
                self.port = None

        # Initialize health check socket
        self.health_socket = self.context.socket(zmq.REP)
        self.health_socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.health_socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        try:
            self.health_socket.bind(f"tcp://127.0.0.1:{HEALTH_CHECK_PORT}")
            logging.info(f"[ContextualMemory] Health check socket bound to port {HEALTH_CHECK_PORT}")
            self.health_port = HEALTH_CHECK_PORT
        except zmq.error.ZMQError as e:
            logging.error(f"[ContextualMemory] Error binding health check socket: {e}")
            self.health_port = None

        # Initialize memory and user profile
        self.memory = self.load_memory()
        self.user_profile = self.load_user_profile()
        self.lock = threading.Lock()
        self.running = True
        self.save_interval = 60  # seconds

        # Start periodic save thread
        self.save_thread = threading.Thread(target=self.periodic_save, daemon=True)
        self.save_thread.start()

        logging.info("[ContextualMemory] Agent initialized and ready to process requests.")

    def load_memory(self) -> Dict[str, List[Dict[str, Any]]]:
        try:
            if os.path.exists(MEMORY_STORE_PATH):
                with open(MEMORY_STORE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"[ContextualMemory] Error loading memory: {e}")
            return {}

    def save_memory(self):
        with self.lock:
            # Prune memory for each user to keep only the most recent 100 entries
            for user_id in self.memory:
                if isinstance(self.memory[user_id], list) and len(self.memory[user_id]) > 100:
                    self.memory[user_id] = self.memory[user_id][-100:]
            try:
                with open(MEMORY_STORE_PATH, "w", encoding="utf-8") as f:
                    json.dump(self.memory, f, ensure_ascii=False, indent=2)
                logging.info("[ContextualMemory] Memory saved.")
            except Exception as e:
                logging.error(f"[ContextualMemory] Error saving memory: {e}")

    def load_user_profile(self) -> Dict[str, Dict[str, Any]]:
        try:
            if os.path.exists(USER_PROFILE_PATH):
                with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"[ContextualMemory] Error loading user profile: {e}")
            return {}

    def save_user_profile(self):
        try:
            with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.user_profile, f, ensure_ascii=False, indent=2)
            logging.info("[ContextualMemory] User profile saved.")
        except Exception as e:
            logging.error(f"[ContextualMemory] Error saving user profile: {e}")

    def periodic_save(self):
        while self.running:
            time.sleep(self.save_interval)
            self.save_memory()
            self.save_user_profile()

    def broadcast_reminder(self, text, user=None, emotion="neutral"):
        send_proactive_event(event_type="reminder", text=text, user=user, emotion=emotion)

    def handle_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        action = query.get("action")
        user_id = query.get("user_id", DEFAULT_USER_ID)

        if action == "add_context":
            context_entry = query.get("context")
            with self.lock:
                if user_id not in self.memory:
                    self.memory[user_id] = []
                self.memory[user_id].append({
                    "timestamp": time.time(),
                    "context": context_entry
                })
                self.save_memory()
            logging.info(f"[ContextualMemory] Added context for {user_id}: {context_entry}")
            return {"status": "ok"}

        elif action == "get_context":
            with self.lock:
                user_context = self.memory.get(user_id, [])
            return {"status": "ok", "context": user_context}

        elif action == "clear_context":
            with self.lock:
                self.memory[user_id] = []
                self.save_memory()
            logging.info(f"[ContextualMemory] Cleared context for {user_id}")
            return {"status": "ok"}

        elif action == "add_reminder":
            reminder = query.get("reminder")
            if reminder:
                with self.lock:
                    if user_id not in self.user_profile:
                        self.user_profile[user_id] = {"name": "User", "preferences": {}, "taught_commands": {}, "reminders": []}
                    if "reminders" not in self.user_profile[user_id]:
                        self.user_profile[user_id]["reminders"] = []
                    self.user_profile[user_id]["reminders"].append(reminder)
                    self.save_user_profile()
                logging.info(f"[ContextualMemory] Added reminder for {user_id}: {reminder}")
                # Broadcast reminder if it's a proactive type
                if isinstance(reminder, dict) and reminder.get("type") == "reminder":
                    self.broadcast_reminder(
                        text=reminder.get("text", "You have a new reminder."),
                        user=user_id,
                        emotion=reminder.get("emotion", "neutral")
                    )
                return {"status": "ok"}
            return {"status": "error", "reason": "No reminder provided"}

        elif action == "list_reminders":
            reminders = self.user_profile.get(user_id, {}).get("reminders", [])
            return {"status": "ok", "reminders": reminders}

        elif action == "delete_reminder":
            idx = query.get("index")
            with self.lock:
                reminders = self.user_profile.get(user_id, {}).get("reminders", [])
                if idx is not None and 0 <= idx < len(reminders):
                    removed = reminders.pop(idx)
                    self.save_user_profile()
                    logging.info(f"[ContextualMemory] Deleted reminder for {user_id}: {removed}")
                    return {"status": "ok"}
            return {"status": "error", "reason": "Invalid reminder index"}

        elif action == "delete_all_reminders":
            with self.lock:
                if user_id in self.user_profile:
                    self.user_profile[user_id]["reminders"] = []
                    self.save_user_profile()
                    logging.info(f"[ContextualMemory] Cleared all reminders for {user_id}")
                    return {"status": "ok"}
            return {"status": "error", "reason": "User not found"}

        elif action == "get_profile":
            profile = self.user_profile.get(user_id, {"name": "User", "preferences": {}, "taught_commands": {}})
            return {"status": "ok", "profile": profile}

        elif action == "update_profile":
            updates = query.get("updates", {})
            with self.lock:
                if user_id not in self.user_profile:
                    self.user_profile[user_id] = {"name": "User", "preferences": {}, "taught_commands": {}}
                self.user_profile[user_id].update(updates)
                self.save_user_profile()
            return {"status": "ok"}

        elif action == "search_memory":
            keyword = query.get("keyword", "").lower()
            with self.lock:
                user_mem = self.memory.get(user_id, [])
                results = [m for m in user_mem if keyword in json.dumps(m).lower()]
            return {"status": "ok", "results": results}

        else:
            return {"status": "error", "reason": "Unknown action"}

    def handle_health_check(self):
        if self.health_port is None:
            return False
        
        try:
            if self.health_socket.poll(timeout=10) == 0:
                return False
            
            request_str = self.health_socket.recv_string(flags=zmq.NOBLOCK)
            try:
                request = json.loads(request_str)
            except json.JSONDecodeError:
                logging.warning("[ContextualMemory] Invalid JSON in health check request")
                self.health_socket.send_string(json.dumps({"status": "error", "message": "Invalid JSON"}))
                return True
            
            if request.get("request_type") == "health_check":
                logging.debug("[ContextualMemory] Received health check request")
                response = {
                    "status": "success",
                    "agent": "contextual_memory",
                    "timestamp": time.time()
                }
                self.health_socket.send_string(json.dumps(response))
                return True
            else:
                logging.warning(f"[ContextualMemory] Unknown request type: {request.get('request_type')}")
                self.health_socket.send_string(json.dumps({"status": "error", "message": "Unknown request type"}))
                return True
            
        except zmq.Again:
            return False
        except Exception as e:
            logging.error(f"[ContextualMemory] Error handling health check: {str(e)}")
            return False

    def run(self):
        if self.port is None:
            logging.error("[ContextualMemory] Cannot run without a valid port")
            return

        while self.running:
            try:
                # Handle health check requests
                self.handle_health_check()
                
                # Handle main memory requests
                if self.socket.poll(timeout=100) != 0:  # 100ms timeout
                    msg = self.socket.recv_string()
                    query = json.loads(msg)
                    resp = self.handle_query(query)
                    self.socket.send_string(json.dumps(resp))
            except Exception as e:
                logging.error(f"[ContextualMemory] Error in main loop: {e}")
                time.sleep(1)  # Prevent tight loop on error

    def cleanup(self):
        self.running = False
        if self.save_thread.is_alive():
            self.save_thread.join(timeout=5)
        self.socket.close()
        if self.health_port is not None:
            self.health_socket.close()
        self.context.term()

if __name__ == "__main__":
    agent = ContextualMemoryAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logging.info("[ContextualMemory] Shutting down...")
    finally:
        agent.cleanup()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise