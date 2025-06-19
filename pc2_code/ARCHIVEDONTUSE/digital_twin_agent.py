import zmq
import json
import os
import threading
import time
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
LOG_PATH = Path(os.path.dirname(__file__)).parent / "logs" / "digital_twin_agent.log"
LOG_PATH.parent.mkdir(exist_ok=True)
TWIN_STORE_PATH = Path(os.path.dirname(__file__)).parent / "data" / "digital_twin_store.json"
TWIN_STORE_PATH.parent.mkdir(exist_ok=True)
ZMQ_DIGITAL_TWIN_PORT = 5597  # Changed from 5596 to avoid conflict with contextual memory agent
MODEL_MANAGER_HOST = "192.168.1.27"  # Main PC's IP address
MODEL_MANAGER_PORT = 5556  # Main PC's MMA port

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DigitalTwinAgent")

class DigitalTwinAgent:
    def __init__(self, zmq_port=ZMQ_DIGITAL_TWIN_PORT):
        """Initialize the Digital Twin Agent"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        # Try to bind to the specified port
        try:
            self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
            self.port = zmq_port
            logger.info(f"Successfully bound to port {zmq_port}")
        except zmq.error.ZMQError as e:
            # If port is in use, try alternative ports
            if "Address in use" in str(e):
                logger.warning(f"Port {zmq_port} is in use, trying alternative ports")
                # Try a range of alternative ports
                alt_ports = [7597, 7598, 7599, 7600, 7601]
                for alt_port in alt_ports:
                    try:
                        self.socket.bind(f"tcp://0.0.0.0:{alt_port}")
                        self.port = alt_port
                        logger.info(f"Successfully bound to alternative port {alt_port}")
                        break
                    except zmq.error.ZMQError:
                        continue
                else:
                    # If we get here, all ports failed
                    logger.error("Could not bind to any port. Will keep running but won't process requests.")
                    self.port = None
            else:
                # Some other ZMQ error
                logger.error(f"Error binding to port: {e}")
                self.port = None
        
        self.twins = self.load_twins()
        self.lock = threading.Lock()
        self.running = True
        
        # Agent state
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = None
        self.health_check_count = 0
        self.update_count = 0
        self.get_count = 0
        self.delete_count = 0
        self.successful_updates = 0
        self.failed_updates = 0
        
        logger.info(f"[DigitalTwin] Agent started on port {self.port}")
        logger.info(f"[DigitalTwin] Twin store path: {TWIN_STORE_PATH}")

    def load_twins(self):
        """Load digital twins from the store file"""
        try:
            if TWIN_STORE_PATH.exists():
                with open(TWIN_STORE_PATH, "r", encoding="utf-8") as f:
                    twins = json.load(f)
                logger.info(f"Loaded {len(twins)} digital twins from store")
                return twins
            logger.info("No existing twin store found, starting with empty store")
            return {}
        except Exception as e:
            logger.error(f"Error loading twin store: {e}")
        return {}

    def save_twins(self):
        """Save digital twins to the store file"""
        try:
            with open(TWIN_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.twins, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved {len(self.twins)} digital twins to store")
            return True
        except Exception as e:
            logger.error(f"Error saving twin store: {e}")
            return False

    def get_status(self):
        """Get the current status of the Digital Twin Agent"""
        with self.lock:
            uptime = time.time() - self.start_time
            return {
                "status": "ok",
                "service": "digital_twin_agent",
                "timestamp": time.time(),
                "uptime_seconds": uptime,
                "request_count": self.request_count,
                "error_count": self.error_count,
                "last_request_time": self.last_request_time,
                "health_check_count": self.health_check_count,
                "update_count": self.update_count,
                "get_count": self.get_count,
                "delete_count": self.delete_count,
                "successful_updates": self.successful_updates,
                "failed_updates": self.failed_updates,
                "total_twins": len(self.twins),
                "bind_address": f"tcp://0.0.0.0:{self.port}" if self.port else None
            }

    def handle_query(self, query):
        """Handle incoming queries"""
        try:
            action = query.get("action")
            user = query.get("user_id", "default")
            
            # Update request tracking
            with self.lock:
                self.request_count += 1
                self.last_request_time = time.time()
            
            if action == "health_check":
                self.health_check_count += 1
                return self.get_status()
            elif action == "update_twin":
                self.update_count += 1
                twin_data = query.get("twin_data")
                if not twin_data:
                    self.failed_updates += 1
                    return {"status": "error", "reason": "No twin data provided"}
                
                with self.lock:
                    self.twins[user] = twin_data
                    if self.save_twins():
                        self.successful_updates += 1
                        logger.info(f"[DigitalTwin] Updated twin for {user}: {twin_data}")
                    else:
                        self.failed_updates += 1
                        return {"status": "error", "reason": "Failed to save twin data"}
            elif action == "get_twin":
                self.get_count += 1
                with self.lock:
                    twin = self.twins.get(user, {})
                    logger.info(f"[DigitalTwin] Retrieved twin for {user}")
                return {"status": "ok", "twin": twin}
            elif action == "delete_twin":
                self.delete_count += 1
                with self.lock:
                    if user in self.twins:
                        del self.twins[user]
                        if self.save_twins():
                            logger.info(f"[DigitalTwin] Deleted twin for {user}")
                        return {"status": "ok"}
                    else:
                        return {"status": "error", "reason": "User not found"}
            else:
                return {"status": "error", "reason": "Unknown action"}
        except Exception as e:
            logger.error(f"[DigitalTwin] Error handling query: {e}")
            with self.lock:
                self.error_count += 1
            return {"status": "error", "reason": str(e)}

    def run(self):
        """Main service loop"""
        logger.info("[DigitalTwin] Service loop started")
        while self.running:
            try:
                msg = self.socket.recv_string()
                query = json.loads(msg)
                resp = self.handle_query(query)
                self.socket.send_string(json.dumps(resp))
            except Exception as e:
                logger.error(f"[DigitalTwin] Error in service loop: {e}")
                with self.lock:
                    self.error_count += 1
                self.socket.send_string(json.dumps({"status": "error", "reason": str(e)}))

    def stop(self):
        """Stop the Digital Twin Agent"""
        logger.info("[DigitalTwin] Stopping agent...")
        self.running = False
        self.socket.close()
        self.context.term()
        logger.info("[DigitalTwin] Agent stopped")

if __name__ == "__main__":
    agent = DigitalTwinAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
