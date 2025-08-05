import zmq
import json
import os
import sys
import time
import threading
import logging
# from datetime import datetime
from typing import List, Dict, Any

# Add the parent directory to sys.path to allow importing from sibling modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))

# Import system config
try:
from pc2_code.config.system_config import config
except ImportError:
    config = {
        'memory.proactive_reminder_broadcast': True  # Default to enabled if config can't be loaded
    }
    logging.warning("[Memory] Could not import system_config, using defaults")

# Import proactive event broadcasting
try:
from pc2_code.agents.proactive_agent_interface import send_proactive_event
except ImportError:
    # Define a fallback function if the import fails
    def send_proactive_event(event_type, text="", user=None, emotion="neutral", **kwargs):
        logging.warning(f"[Memory] Could not import send_proactive_event, using fallback. Event: {event_type}")
        return None

LOG_PATH = str(PathManager.get_logs_dir() / "memory_agent.log")
MEMORY_PATH = "memory_store.json"
USER_PROFILE_PATH = "user_profile.json"
DEFAULT_USER_ID = "default_user"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

ZMQ_MEMORY_AGENT_PORT = 5590
ZMQ_MEMORY_HEALTH_CHECK_PORT = 5598
ZMQ_PROACTIVE_EVENT_PORT = 5595

def send_proactive_event(event_type, text, user=None, emotion="neutral"):
    """Send a proactive event, such as a reminder, to the event bus (e.g., ZeroMQ or fallback)."""
    # This is a stub. In production, this should publish to the event bus.
    logging.info(f"[Memory] Proactive event: type={event_type}, text={text}, user={user}, emotion={emotion}")
    return None

class MemoryAgent:
    def __init__(self, zmq_port=ZMQ_MEMORY_AGENT_PORT, health_check_port=ZMQ_MEMORY_HEALTH_CHECK_PORT, proactive_port=ZMQ_PROACTIVE_EVENT_PORT):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        try:
            self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
            self.port = zmq_port
            logging.info(f"[Memory] Successfully bound to port {zmq_port}")
        except zmq.error.ZMQError as e:
            # If port is in use, try alternative ports
            if "Address in use" in str(e):
                logging.warning(f"[Memory] Port {zmq_port} is in use, trying alternative ports")
                # Try a range of alternative ports
                alt_ports = [7590, 7591, 7592, 7593, 7594]
                for alt_port in alt_ports:
                    try:
                        self.socket.bind(f"tcp://0.0.0.0:{alt_port}")
                        self.port = alt_port
                        logging.info(f"[Memory] Successfully bound to alternative port {alt_port}")
                        break
                    except zmq.error.ZMQError:
                        continue
                else:
                    # If we get here, all ports failed
                    logging.error("[Memory] Could not bind to any port. Will keep running but won't process requests.")
                    self.port = None
            else:
                # Some other ZMQ error
                logging.error(f"[Memory] Error binding to port: {e}")
                self.port = None
        
        # Socket to handle health check requests from dashboard
        self.health_socket = self.context.socket(zmq.REP)
        try:
            # Use the port 5598 as specified in the distributed_config.json
            self.health_socket.bind(f"tcp://0.0.0.0:{health_check_port}")
            logging.info(f"[Memory] Health check socket bound to port {health_check_port}")
            self.health_port = health_check_port
        except zmq.error.ZMQError as e:
            logging.error(f"[Memory] Error binding health check socket to port {health_check_port}: {e}")
            self.health_port = None
            # Don't raise an exception here, just log the error and continue
        
        # Set up proactive event socket if enabled in config
        if config.get('memory.proactive_reminder_broadcast', False):
            try:
                self.proactive_socket = self.context.socket(zmq.PUB)
                self.proactive_socket.bind(f"tcp://0.0.0.0:{proactive_port}")
                logging.info(f"[Memory] Proactive event socket bound to port {proactive_port}")
                self.proactive_port = proactive_port
            except zmq.error.ZMQError as e:
                logging.error(f"[Memory] Error binding proactive event socket to port {proactive_port}: {e}")
                self.proactive_socket = None
                self.proactive_port = None
        else:
            self.proactive_socket = None
            self.proactive_port = None
            logging.info(f"[Memory] Proactive broadcasting is DISABLED")
        
        # Load memory and user profile
        self.memory = self.load_memory()
        self.user_profile = self.load_user_profile()
        self.running = True
        self.save_interval = 60  # seconds
        
        # Start the periodic save thread
        self.save_thread = threading.Thread(
            target=self.periodic_save, daemon=True)
        self.save_thread.start()
        
        logging.info("[Memory] Agent initialized and ready to process requests.")
        # Log a warning if we couldn't bind to any port
        if self.port is None:
            logging.warning("[Memory] Agent is running but won't process requests due to port binding failure.")

    def load_memory(self) -> Dict[str, List[Dict[str, Any]]]:
        try:
            if os.path.exists(MEMORY_PATH):
                with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"[Memory] Error loading memory: {e}")
            return {}

    def save_memory(self):
        # Prune memory for each user to keep only the most recent 100 entries
        for user_id in self.memory:
            if isinstance(self.memory[user_id], list) and len(self.memory[user_id]) > 100:
                self.memory[user_id] = self.memory[user_id][-100:]
        try:
            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
            logging.info("[Memory] Memory saved.")
        except Exception as e:
            logging.error(f"[Memory] Error saving memory: {e}")

    def load_user_profile(self) -> Dict[str, Dict[str, Any]]:
        try:
            if os.path.exists(USER_PROFILE_PATH):
                with open(USER_PROFILE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logging.error(f"[Memory] Error loading user profile: {e}")
            return {}

    def save_user_profile(self):
        try:
            with open(USER_PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.user_profile, f, ensure_ascii=False, indent=2)
            logging.info("[Memory] User profile saved.")
        except Exception as e:
            logging.error(f"[Memory] Error saving user profile: {e}")

    def periodic_save(self):
        while self.running:
            time.sleep(self.save_interval)
            self.save_memory()
            self.save_user_profile()

    def handle_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        action = query.get("action")
        user_id = query.get("user_id", DEFAULT_USER_ID)
        # Reminders are stored as a list in user_profile[user_id]['reminders']
        if action == "delete_all_reminders":
            if user_id in self.user_profile:
                self.user_profile[user_id]["reminders"] = []
                self.save_user_profile()
                logging.info(f"[Memory] Cleared all reminders for {user_id}")
                return {"status": "ok"}
            else:
                return {"status": "error", "reason": "User not found"}
        if action == "add_reminder":
            reminder = query.get("reminder")
            if reminder:
                if user_id not in self.user_profile:
                    self.user_profile[user_id] = {"name": "User", "preferences": {}, "taught_commands": {}, "reminders": []}
                if "reminders" not in self.user_profile[user_id]:
                    self.user_profile[user_id]["reminders"] = []
                self.user_profile[user_id]["reminders"].append(reminder)
                self.save_user_profile()
                logging.info(f"[Memory] Added reminder for {user_id}: {reminder}")
                
                # Proactive broadcast of the reminder if enabled in config
                if config.get('memory.proactive_reminder_broadcast', False) and self.proactive_socket:
                    try:
                        event_data = {
                            "event_type": "reminder",
                            "text": reminder.get('text', ''),
                            "user": user_id,
                            "emotion": reminder.get('emotion', 'neutral'),
                            "timestamp": time.time()
                        }
                        logging.info(f"[Memory] Broadcasting reminder proactively: {reminder['text']}")
                        self.proactive_socket.send_json(event_data)
                        logging.info(f"[Memory] Reminder broadcast complete")
                    except Exception as e:
                        logging.error(f"[Memory] Error broadcasting reminder: {str(e)}")
                
                return {"status": "ok"}
            return {"status": "error", "reason": "No reminder provided"}
        elif action == "list_reminders":
            reminders = self.user_profile.get(user_id, {}).get("reminders", [])
            return {"status": "ok", "reminders": reminders}
        elif action == "delete_reminder":
            idx = query.get("index")
            reminders = self.user_profile.get(user_id, {}).get("reminders", [])
            if idx is not None and 0 <= idx < len(reminders):
                removed = reminders.pop(idx)
                self.save_user_profile()
                logging.info(f"[Memory] Deleted reminder for {user_id}: {removed}")
                return {"status": "ok"}
            return {"status": "error", "reason": "Invalid reminder index"}
        if action == "add_memory":
            entry = query.get("entry")
            if entry:
                if user_id not in self.memory:
                    self.memory[user_id] = []
                self.memory[user_id].append(entry)
                # Keep only the most recent 100 entries for this user
                if len(self.memory[user_id]) > 100:
                    self.memory[user_id] = self.memory[user_id][-100:]
                logging.info(f"[Memory] Added entry for {user_id}: {entry}")
                return {"status": "ok"}
            return {"status": "error", "reason": "No entry provided"}
        elif action == "get_memory":
            limit = query.get("limit", 10)
            context_filter = query.get("context")
            user_mem = self.memory.get(user_id, [])
            if context_filter:
                filtered = [m for m in user_mem if m.get("context") == context_filter]
                return {"status": "ok", "memory": filtered[-limit:]}
            return {"status": "ok", "memory": user_mem[-limit:]}
        elif action == "search_memory":
            keyword = query.get("keyword", "").lower()
            user_mem = self.memory.get(user_id, [])
            results = [m for m in user_mem if keyword in json.dumps(m).lower()]
            return {"status": "ok", "results": results}
        elif action == "get_profile":
            profile = self.user_profile.get(user_id, {"name": "User", "preferences": {}, "taught_commands": {}})
            return {"status": "ok", "profile": profile}
        elif action == "update_profile":
            updates = query.get("updates", {})
            if user_id not in self.user_profile:
                self.user_profile[user_id] = {"name": "User", "preferences": {}, "taught_commands": {}}
            self.user_profile[user_id].update(updates)
            self.save_user_profile()
            return {"status": "ok"}
        else:
            return {"status": "error", "reason": "Unknown action"}

    def handle_health_check(self):
        """Handle health check requests from the dashboard"""
        # Skip if health socket wasn't initialized successfully
        if self.health_port is None:
            return False
        
        try:
            # Check if there's a health check request with a short timeout
            if self.health_socket.poll(timeout=10) == 0:  # 10ms timeout
                return False  # No request
            
            # Receive the request
            request_str = self.health_socket.recv_string(flags=zmq.NOBLOCK)
            try:
                request = json.loads(request_str)
            except json.JSONDecodeError:
                logging.warning("[Memory] Invalid JSON in health check request")
                self.health_socket.send_string(json.dumps({"status": "error", "message": "Invalid JSON"})
                return True
            
            # Check if it's a health check request
            if request.get("request_type") == "health_check":
                logging.debug("[Memory] Received health check request")
                # Send success response
                response = {
                    "status": "success",
                    "agent": "memory",
                    "timestamp": time.time()
                }
                self.health_socket.send_string(json.dumps(response)
                return True
            else:
                # Unknown request type
                logging.warning(f"[Memory] Unknown request type: {request.get('request_type')}")
                self.health_socket.send_string(json.dumps({"status": "error", "message": "Unknown request type"})
                return True
            
        except zmq.Again:
            # No message available
            return False
        except Exception as e:
            logging.error(f"[Memory] Error handling health check: {str(e)}")
            try:
                self.health_socket.send_string(json.dumps({"status": "error", "message": str(e)})
            except Exception:
                pass  # Ignore errors in sending error response
            return True

    def run(self):
        # Check if we successfully bound to a port
        if self.port is None:
            logging.warning("[Memory] Agent cannot process requests due to port binding failure.")
            # Sleep for a while and then return - the outer loop will call run() again
            time.sleep(5.0)
            return
        
        logging.info("[Memory] Agent running on port %s.", self.port)
        
        # Process messages for a limited time before returning
        # This allows the outer loop to check for errors and restart if needed
        start_time = time.time()
        max_processing_time = 5.0  # Process for 5 seconds before returning
        message_count = 0
        
        try:
            # Set socket timeout to prevent blocking forever
            self.socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            
            while self.running and (time.time() - start_time < max_processing_time):
                # Check for health check requests first
                self.handle_health_check()
                
                try:
                    # Try to receive a message with timeout
                    try:
                        msg = self.socket.recv_string()
                        message_count += 1
                    except zmq.error.Again:
                        # No message available, continue loop
                        continue
                        
                    # Process the message
                    try:
                        query = json.loads(msg)
                        response = self.handle_query(query)
                    except json.JSONDecodeError as e:
                        response = {"status": "error", "reason": f"Invalid JSON: {str(e)}"}
                        logging.error(f"[Memory] Invalid JSON received: {e}")
                    except Exception as e:
                        response = {"status": "error", "reason": str(e)}
                        logging.error(f"[Memory] Error handling query: {e}")
                    
                    # Send the response
                    try:
                        self.socket.send_string(json.dumps(response)
                        logging.info(f"[Memory] Processed request: {query.get('action', 'unknown')}")
                    except Exception as e:
                        logging.error(f"[Memory] Error sending response: {e}")
                        
                except KeyboardInterrupt:
                    # Don't exit, just set running to false
                    self.running = False
                    logging.info("[Memory] KeyboardInterrupt received. Will stop after current batch.")
                    break
                except Exception as e:
                    # Log error but continue processing
                    logging.error(f"[Memory] Error in message processing: {e}")
                    import traceback
                    traceback.print_exc()
                    # Small delay to prevent rapid error loops
                    time.sleep(0.5)
            
            # Log processing stats
            if message_count > 0:
                logging.info(f"[Memory] Processed {message_count} messages in this batch")
                
            # Return normally without calling cleanup
            # The outer loop will call run() again
            return
            
        except Exception as e:
            # This should only happen for serious errors
            logging.error(f"[Memory] Critical error in run method: {e}")
            import traceback
            traceback.print_exc()
            # Don't call cleanup here, let the outer loop handle it

    def cleanup(self):
        try:
            self.save_memory()
            self.save_user_profile()
            self.socket.close(0)
            if hasattr(self, 'health_socket'):
                self.health_socket.close(0)
            self.context.term()
            logging.info("[Memory] Agent stopped and cleaned up.")
        except Exception as e:
            logging.error(f"[Memory] Error during cleanup: {e}")


def main():
    """Main function to run the Memory Agent with resilient error handling"""
    # Use a global try-except to catch any errors during startup
    try:
        # Create the agent
        agent = MemoryAgent()
        logging.info("[Memory] Agent created and entering main loop...")
        
        # Enter the main loop - this should never exit
        while True:
            try:
                # Run the agent's main loop
                agent.run()
                # If run() somehow returns (it shouldn't), log and continue
                logging.info("[Memory] Agent.run() returned - restarting main loop")
                time.sleep(1)  # Prevent rapid restart loops
            except KeyboardInterrupt:
                # Handle keyboard interrupt but don't exit
                logging.info("[Memory] Keyboard interrupt received, but continuing operation")
                time.sleep(1)
            except Exception as e:
                # Log any exceptions but don't exit
                logging.error(f"[Memory] Error in main loop: {str(e)}")
                import traceback
                traceback.print_exc()
                time.sleep(5)  # Longer delay on errors
    except Exception as e:
        # Only catch startup exceptions here
        logging.error(f"[Memory] FATAL error in __main__: {e}")
        print(f"[Memory] FATAL error in __main__: {e}")
        import traceback
        traceback.print_exc()
        # Keep the process alive even on startup errors
        while True:
            time.sleep(60)  # Sleep indefinitely

if __name__ == "__main__":
    # Wrap the entire execution in a try-except to catch any possible errors
    try:
        main()
    except Exception as e:
        logging.critical(f"[Memory] Unhandled exception in main thread: {e}")
        print(f"[Memory] CRITICAL: Unhandled exception in main thread: {e}")
        import traceback

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
        traceback.print_exc()
        # Keep the process alive even on critical errors
        while True:
            try:
                time.sleep(60)  # Sleep indefinitely
            except:
                pass  # Ignore any errors in the sleep
