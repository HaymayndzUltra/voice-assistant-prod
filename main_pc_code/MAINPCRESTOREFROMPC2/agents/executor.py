import os, sys
# Ensure project root (main_pc_code) is in sys.path so that local packages can be imported reliably
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from main_pc_code.agents.base_agent import BaseAgent
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

# ---------------------------------------------------------------------------
# Helper: Usage analytics logger (ensures NameError does not occur at runtime)
# ---------------------------------------------------------------------------

def log_usage_analytics(user: str, command: str, status: str):
    """Basic stub for usage analytics so that ExecutorAgent does not crash.

    In a production setup this would push structured events to a monitoring
    service.  For now we forward the information over the same PUB socket used
    for normal logs so that the orchestrator can collect them.
    """
    try:
        analytics_msg = json.dumps({
            "agent": "executor",
            "event": "usage",
            "user": user,
            "command": command,
            "status": status,
            "timestamp": time.time(),
        })
        log_socket.send_string(analytics_msg)
    except Exception as _e:
        # Fall back to local logging if PUB socket unavailable
        logging.debug(f"[Executor] Failed to send usage analytics: {_e}")

import zmq
from main_pc_code.utils.config_parser import parse_agent_args
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
        # Default ports if none provided
        if port is None:
            port = 5606  # Base REP port to receive privileged commands (if any)
        self.port = port

        # Initialize BaseAgent (this allocates main REP and a health port, which may shift if ports are occupied)
        super().__init__(port=self.port, name="Executor")

        # Determine ports for command SUB and feedback PUB that do not clash with the chosen health port
        sub_port_start = self.health_port + 1
        pub_port_start = sub_port_start + 1

        # Create additional sockets using existing context (do NOT overwrite BaseAgent sockets)
        max_attempts = 10
        self.command_socket = self.context.socket(zmq.SUB)
        bound = False
        for i in range(max_attempts):
            candidate_sub_port = sub_port_start + i
            try:
                self.command_socket.bind(f"tcp://127.0.0.1:{candidate_sub_port}")
                sub_port_start = candidate_sub_port
                bound = True
                break
            except zmq.error.ZMQError:
                logging.warning(f"[Executor] SUB port {candidate_sub_port} in use, trying next...")
                continue
        if not bound:
            raise RuntimeError("[Executor] Unable to bind SUB socket after multiple attempts")
        self.command_socket.setsockopt_string(zmq.SUBSCRIBE, "")

        # Bind PUB socket for feedback; retry on conflict
        self.feedback_socket = self.context.socket(zmq.PUB)
        pub_bound = False
        for i in range(max_attempts):
            candidate_pub_port = pub_port_start + i
            try:
                self.feedback_socket.bind(f"tcp://127.0.0.1:{candidate_pub_port}")
                pub_port_start = candidate_pub_port
                pub_bound = True
                break
            except zmq.error.ZMQError:
                logging.warning(f"[Executor] PUB port {candidate_pub_port} in use, trying next...")
                continue
        if not pub_bound:
            raise RuntimeError("[Executor] Unable to bind PUB socket after multiple attempts")

        logging.info(
            f"[Executor] main REP {self.port}, health REP {self.health_port}, SUB {sub_port_start}, PUB {pub_port_start}.")
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
                msg = self.command_socket.recv_string()
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
        self.command_socket.close()
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
            logging.error(f"Initialization error: {e}")
            raise
