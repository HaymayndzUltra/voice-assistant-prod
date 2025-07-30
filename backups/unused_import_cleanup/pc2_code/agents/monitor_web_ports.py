import zmq
import time
import sys
import logging
from datetime import datetime
from common.core.base_agent import BaseAgent
from common.env_helpers import get_env
from common.config_manager import get_service_ip, get_service_url, get_redis_url

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "web_ports_monitor.log")),
        logging.StreamHandler()
    ]
)

class WebPortMonitor:
    def __init__(self):

        super().__init__(*args, **kwargs)        self.context = zmq.Context()
        self.ports = {
            'unified_web': 5604,
            'autonomous_web': 5605
        }
        self.sockets = {}
        self.setup_sockets()

    def setup_sockets(self):
        for name, port in self.ports.items():
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.connect(f"tcp://localhost:{port}")
            self.sockets[name] = socket

    def check_port(self, name, socket):
        try:
            socket.send_string("HEALTH_CHECK")
            try:
                response = socket.recv_string(flags=zmq.NOBLOCK)
                logging.info(f"✅ {name} (Port {self.ports[name]}) is responding")
                return True
            except zmq.error.Again:
                logging.warning(f"⚠️ {name} (Port {self.ports[name]}) is not responding")
                return False
        except Exception as e:
            logging.error(f"❌ {name} (Port {self.ports[name]}) error: {e}")
            return False

    def monitor(self):
        while True:
            logging.info("\n=== Web Ports Status Check ===")
            for name, socket in self.sockets.items():
                self.check_port(name, socket)
            time.sleep(30)  # Check every 30 seconds

    def cleanup(self):
        for socket in self.sockets.values():
            socket.close()
        self.context.term()

def main():
    monitor = WebPortMonitor()
    try:
        monitor.monitor()
    except KeyboardInterrupt:
        logging.info("Monitoring stopped by user")
    finally:
        monitor.cleanup()

if __name__ == "__main__":
    main() 