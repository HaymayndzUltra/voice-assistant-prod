from src.core.base_agent import BaseAgent
import zmq
import json
import subprocess
import threading
import logging
import time
# from web_automation import GLOBAL_TASK_MEMORY  # Unified adaptive memory and emotion/skill tracking (commented out for PC1)

# Logging setup
LOG_PATH = "executor_agent.log"
# Centralized logging: Forward logs to orchestrator
import zmq
from utils.config_parser import parse_agent_args
_agent_args = parse_agent_args()
ZMQ_LOG_PORT = 5600  # Central log collector port
log_context = zmq.Context()
log_socket = log_context.socket(zmq.PUB)
log_socket.connect(f"tcp://127.0.0.1:{ZMQ_LOG_PORT}")

def send_log(level, msg):
    log_msg = json.dumps({"agent": "executor", "level": level, "message": msg, "timestamp": time.time()})
    try:
        log_socket.send_string(log_msg)
    except Exception as e:
        # Fallback to local logging if ZMQ fails
        logging.error(f"[Executor] Failed to send log to orchestrator: {e}")
        logging.log(getattr(logging, level.upper(), logging.INFO), msg)

# Command mapping: spoken command -> system action
COMMAND_MAP = {
    "open notepad": lambda: subprocess.Popen(["notepad.exe"]),
    "open calculator": lambda: subprocess.Popen(["calc.exe"]),
    "shutdown": lambda: subprocess.Popen(["shutdown", "/s", "/t", "0"]),
    "lock computer": lambda: subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"]),
    "open edge": lambda: subprocess.Popen(["cmd", "/c", "start msedge"]),
    "open explorer": lambda: subprocess.Popen(["explorer.exe"]),
    "take screenshot": lambda: subprocess.Popen(["snippingtool.exe"]),
    "mute audio": lambda: subprocess.Popen(["nircmd.exe", "mutesysvolume", "1"]),
    "unmute audio": lambda: subprocess.Popen(["nircmd.exe", "mutesysvolume", "0"]),
    # Add more mappings here
}

# Sensitive commands that require special permission
SENSITIVE_COMMANDS = {"shutdown", "lock computer"}

# Example user permissions (should be loaded from a profile/memory agent in production)
USER_PERMISSIONS = {
    "admin": {"all"},
    "default": {"open notepad", "open calculator", "open edge", "open explorer", "take screenshot", "mute audio", "unmute audio"},
    # Add more users/permissions as needed
}


class ExecutorAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="Executor")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        # Feedback PUB socket
        self.feedback_socket = self.context.socket(zmq.PUB)
        self.feedback_socket.bind(f"tcp://127.0.0.1:{zmq_feedback_port}")
        logging.info(
            f"[Executor] Listening for commands on port {zmq_port}...")
        self.running = True
        self.last_command = None
        self.command_history = []
        self.health_status = "OK"
        self.last_health_check = time.time()
        self.hot_reload_thread = threading.Thread(
            target=self.hot_reload_watcher, daemon=True)
        self.hot_reload_thread.start()

    def authenticate_user(self, user):
        """
        Prompt for user password and check against stored credentials in user_profile.json.
        Returns True if authenticated, False otherwise.
        """
        import os
        USER_PROFILE_PATH = "user_profile.json"
        try:
            if not os.path.exists(USER_PROFILE_PATH):
                logging.warning("[Executor] user_profile.json not found for authentication.")
                return False
            with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
                profile = json.load(f)
            # Support both old and new user profile formats
            if isinstance(profile, dict) and "users" in profile:
                users = profile["users"]
            else:
                users = profile
            if user not in users or "password" not in users[user]:
                logging.warning(f"[Executor] No password set for user '{user}'.")
                return False
            password_actual = users[user]["password"]
            password_input = input(f"Enter password for user '{user}': ")
            if password_input == password_actual:
                logging.info(f"[Executor] Authentication success for user '{user}'.")
                return True
            else:
                logging.warning(f"[Executor] Authentication failed for user '{user}'.")
                return False
        except Exception as e:
            logging.error(f"[Executor] Error during authentication: {e}")
            return False

    def execute_command(self, command, user="default"):
        # Permission check
        allowed = False
        if user in USER_PERMISSIONS:
            allowed_cmds = USER_PERMISSIONS[user]
            if "all" in allowed_cmds or command in allowed_cmds:
                allowed = True
        if command in SENSITIVE_COMMANDS:
            if not allowed:
                logging.warning(f"[Executor] User '{user}' not permitted to execute sensitive command: {command}")
                status = "permission_denied"
                self.command_history.append({"command": command, "user": user, "status": status, "timestamp": time.time()})
                self.send_feedback(command, user, status)
                log_usage_analytics(user, command, status)
                return
            # --- User authentication for sensitive commands ---
            if not self.authenticate_user(user):
                logging.warning(f"[Executor] Authentication failed for user '{user}' on sensitive command: {command}")
                status = "auth_failed"
                self.command_history.append({"command": command, "user": user, "status": status, "timestamp": time.time()})
                self.send_feedback(command, user, status)
                log_usage_analytics(user, command, status)
                return
        if command in COMMAND_MAP:
            try:
                logging.info(f"[Executor] Executing: {command} for user {user}")
                COMMAND_MAP[command]()
                status = "success"
                self.command_history.append(
                    {"command": command, "user": user, "status": status, "timestamp": time.time()})
                self.send_feedback(command, user, status)
                log_usage_analytics(user, command, status)
            except Exception as e:
                logging.error(f"[Executor] Error executing '{command}': {e}")
                status = f"error: {e}"
                self.command_history.append(
                    {"command": command, "user": user, "status": status, "timestamp": time.time()})
                self.send_feedback(command, user, status)
                log_usage_analytics(user, command, status)
        else:
            logging.warning(f"[Executor] Unknown command: {command}")
            status = "unknown_command"
            self.command_history.append(
                {"command": command, "user": user, "status": status, "timestamp": time.time()})
            self.send_feedback(command, user, status)
            log_usage_analytics(user, command, status)

    def send_feedback(self, command, user, status):
        msg = json.dumps({
            "command": command,
            "user": user,
            "status": status,
            "timestamp": time.time()
        })
        self.feedback_socket.send_string(msg)

    def start(self):
        logging.info("[Executor] Agent started. Press Ctrl+C to stop.")
        while self.running:
            try:
                msg = self.socket.recv_string()
                data = json.loads(msg)
                command = data.get("command", "").strip().lower()
                user = data.get("user", "default")
                logging.info(f"[Executor] Received command: {command} from user: {user}")
                self.last_command = command
                self.execute_command(command, user)
            except Exception as e:
                logging.error(f"[Executor] Error: {e}")
        logging.info("[Executor] Agent stopped.")

    def stop(self):
        self.running = False
        self.socket.close()
        self.context.term()
        logging.info("[Executor] Stopped.")

    def hot_reload_watcher(self):
        # Placeholder for future hot reload of command map
        last_cmd_map = COMMAND_MAP.copy()
        while self.running:
            time.sleep(5)
            try:
                if COMMAND_MAP != last_cmd_map:
                    logging.info("[Executor] Command map hot reloaded.")
                    last_cmd_map = COMMAND_MAP.copy()
            except Exception as e:
                logging.error(f"[Executor] Hot reload watcher error: {e}")

    def health_check(self):
        now = time.time()
        if now - self.last_health_check > 60:
            self.last_health_check = now
            return {"status": self.health_status, "uptime": now}
        return {"status": self.health_status}


if __name__ == "__main__":
    agent = ExecutorAgent()
    try:
        agent.start()
    except KeyboardInterrupt:
        logging.info("[Executor] KeyboardInterrupt received. Stopping...")
        agent.stop()
    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise
