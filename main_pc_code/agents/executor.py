import os, sys
from common.config_manager import get_service_ip, get_service_url, get_redis_url
# Ensure project root (main_pc_code) is in sys.path so that local packages can be imported reliably
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_CURRENT_DIR, '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from common.core.base_agent import BaseAgent
from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
import json
import subprocess
import threading
import logging
import time
# from web_automation import GLOBAL_TASK_MEMORY  # Unified adaptive memory and emotion/skill tracking (commented out for PC1)
from main_pc_code.utils.config_loader import load_config
from main_pc_code.utils.env_loader import get_env
from datetime import datetime

# Load configuration at module level
config = load_config()

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

from common.pools.zmq_pool import get_req_socket, get_rep_socket, get_pub_socket, get_sub_socket
from common.env_helpers import get_env
ZMQ_LOG_PORT = 5600  # Central log collector port
log_context = None  # Using pool
log_socket = log_context.socket(zmq.PUB)
log_collector_host = os.environ.get('LOG_COLLECTOR_HOST', 'localhost')
log_socket.connect(f"tcp://{log_collector_host}:{ZMQ_LOG_PORT}")

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
    """
    ExecutorAgent:  Now reports errors via the central, event-driven Error Bus (ZMQ PUB/SUB, topic 'ERROR:').
    
    Containerization Note: Interactive password prompts are not supported. Passwords must be provided as part of the command request payload (JSON field 'password').
    """
    def __init__(self, port=None):
        # Get configuration values with fallbacks
        agent_port = int(config.get("port", 5709)) if port is None else port
        agent_name = config.get("name", "ExecutorAgent")
        bind_address = config.get("bind_address", get_env('BIND_ADDRESS', '<BIND_ADDR>'))
        zmq_timeout = int(config.get("zmq_request_timeout", 5000))
        
        # Call BaseAgent's __init__ with proper parameters
        super().__init__(name=agent_name, port=agent_port)
        
        # Store important attributes
        self.bind_address = bind_address
        self.zmq_timeout = zmq_timeout
        self.start_time = time.time()
        
        # Initialize agent state
        self.running = True
        self.last_command = None
        self.command_history = []
        self.health_status = "OK"
        self.last_health_check = time.time()
        
        # Initialize ZMQ sockets - adding a socket for receiving commands
        self.context = None  # Using pool
        self.command_socket = self.context.socket(zmq.REP)
        bind_address = f"tcp://{self.bind_address}:{self.port}"
        self.command_socket.bind(bind_address)
        logging.info(f"[Executor] Command socket bound to {bind_address}")
        
        # Initialize feedback socket for sending execution results
        self.feedback_socket = self.context.socket(zmq.PUB)
        feedback_port = int(config.get("executor_feedback_port", 5710))
        feedback_address = f"tcp://{self.bind_address}:{feedback_port}"
        self.feedback_socket.bind(feedback_address)
        logging.info(f"[Executor] Feedback socket bound to {feedback_address}")
        
        # Start hot reload watcher thread
        self.hot_reload_thread = threading.Thread(
            target=self.hot_reload_watcher, daemon=True)
        self.hot_reload_thread.start()

    

        self.error_bus_port = 7150

        self.error_bus_host = get_service_ip("pc2")

        self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"

        self.error_bus_pub = self.context.socket(zmq.PUB)

        self.error_bus_pub.connect(self.error_bus_endpoint)

    def authenticate_user(self, user, password=None):
        """
        Authenticate user by checking provided password against stored credentials in user_profile.json.
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
            if password is None:
                logging.warning(f"[Executor] No password provided for user '{user}'.")
                return False
            if password == password_actual:
                logging.info(f"[Executor] Authentication success for user '{user}'.")
                return True
            else:
                logging.warning(f"[Executor] Authentication failed for user '{user}'.")
                return False
        except Exception as e:
            logging.error(f"[Executor] Error during authentication: {e}")
            return False

    def execute_command(self, command, user="default", password=None):
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
            if not self.authenticate_user(user, password):
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

    def run(self):
        logging.info("[Executor] Agent started. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                try:
                    # Set a timeout to avoid blocking indefinitely
                    poller = zmq.Poller()
                    poller.register(self.command_socket, zmq.POLLIN)
                    
                    if poller.poll(1000):  # 1 second timeout
                        msg = self.command_socket.recv_string()
                        data = json.loads(msg)
                        command = data.get("command", "").strip().lower()
                        user = data.get("user", "default")
                        password = data.get("password", None)
                        logging.info(f"[Executor] Received command: {command} from user: {user}")
                        self.last_command = command
                        
                        # Execute the command
                        self.execute_command(command, user, password)
                        
                        # Send acknowledgement to the client
                        self.command_socket.send_string(json.dumps({"status": "processed"}))
                    
                except zmq.ZMQError as e:
                    logging.error(f"[Executor] ZMQ error: {e}")
                except json.JSONDecodeError as e:
                    logging.error(f"[Executor] Invalid JSON: {e}")
                except Exception as e:
                    logging.error(f"[Executor] Error: {e}")
                
                time.sleep(0.01)  # Small sleep to reduce CPU usage
        except KeyboardInterrupt:
            logging.info("[Executor] Keyboard interrupt received")
        except Exception as e:
            logging.error(f"[Executor] Unexpected error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        
        # Close ZMQ sockets
        try:
            if hasattr(self, 'command_socket'):
                self.command_
            if hasattr(self, 'feedback_socket'):
                self.feedback_
            if hasattr(self, 'context'):
                self.
        except Exception as e:
            logging.error(f"[Executor] Error during cleanup: {e}")
        
        # Call BaseAgent's cleanup
        super().cleanup()
        
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
        """Perform a health check and return status."""
        try:
            now = time.time()
            uptime = now - self.start_time
            
            # Check if we're due for a detailed health check
            if now - self.last_health_check > 60:
                self.last_health_check = now
                
                # Perform more detailed checks here if needed
                # For example, check if command history has recent entries
                
                # Check system resources
                cpu_percent = 0
                memory_percent = 0
                try:
                    import psutil
                    cpu_percent = psutil.cpu_percent()
                    memory_percent = psutil.virtual_memory().percent
                except ImportError as e:
                    print(f"Import error: {e}")
                    logging.warning("[Executor] psutil not available for system metrics")
                
                return {
                    "status": self.health_status,
                    "agent_name": self.name,
                    "uptime": uptime,
                    "last_command": self.last_command,
                    "command_count": len(self.command_history),
                    "system_metrics": {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory_percent
                    }
                }
            
            # For frequent checks, return minimal info
            return {
                "status": self.health_status,
                "uptime": uptime
            }
        except Exception as e:
            logging.error(f"[Executor] Health check error: {e}")
            return {"status": "ERROR", "error": str(e)}

    def _get_health_status(self):
        """Default health status implementation required by BaseAgent."""
        status = "HEALTHY" if self.running else "UNHEALTHY"
        details = {
            "status_message": "Agent is operational" if self.running else "Agent is not running",
            "uptime_seconds": time.time() - self.start_time,
            "last_command": self.last_command,
            "command_history_size": len(self.command_history)
        }
        return {"status": status, "details": details}

# -------------------- Agent Entrypoint --------------------
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Standardized main execution block
    agent = None
    try:
        logging.info("Starting ExecutorAgent...")
        agent = ExecutorAgent()
        agent.run()
    except KeyboardInterrupt:
        logging.info(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        logging.error(f"An unexpected error occurred in {agent.name if agent else 'ExecutorAgent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            logging.info(f"Cleaning up {agent.name}...")
            agent.cleanup()