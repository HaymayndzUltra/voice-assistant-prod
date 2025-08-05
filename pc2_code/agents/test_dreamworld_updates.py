import zmq
import time
import json
import logging
from datetime import datetime
from common.env_helpers import get_env

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager

# Configure logging
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "dreamworld_test.log"),
        logging.StreamHandler()
    ]
)

class DreamWorldTester:
    def __init__(self):
        self.context = None  # Using pool
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{get_env('BIND_ADDRESS', '0.0.0.0')}:5599")  # New port
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.received_updates = []

    def listen_for_updates(self, timeout=5):
        start_time = time.time()
        logging.info("Listening for dream world updates...")
        
        while time.time() - start_time < timeout:
            try:
                message = self.sub_socket.recv_string(flags=zmq.NOBLOCK)
                self.received_updates.append(message)
                logging.info(f"Received update: {message}")
            except zmq.error.Again:
                time.sleep(0.1)
                continue
            except Exception as e:
                logging.error(f"Error receiving update: {e}")
                break

    def cleanup(self):
        self.sub_
        self.
def main():
    tester = DreamWorldTester()
    try:
        tester.listen_for_updates()
        
        # Print summary
        logging.info("\nTest Summary:")
        if tester.received_updates:
            logging.info(f"✅ Successfully received {len(tester.received_updates)} updates")
            for update in tester.received_updates:
                logging.info(f"  - {update}")
        else:
            logging.warning("⚠️ No updates received within timeout period")
            
    except Exception as e:
        logging.error(f"Test failed: {e}")
    finally:
        tester.cleanup()

if __name__ == "__main__":
    main() 