from src.core.base_agent import BaseAgent
import zmq
import json
import os
import threading
import logging

# ZMQ timeout settings
ZMQ_REQUEST_TIMEOUT = 5000  # 5 seconds timeout for requests

LOG_PATH = "filesystem_assistant_agent.log"
ZMQ_FILESYSTEM_AGENT_PORT = 5594  # Changed from 5597 to avoid conflict with digital twin agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

class FileSystemAssistantAgent(BaseAgent):
    def __init__(self, port: int = None, **kwargs):
        super().__init__(port=port, name="FilesystemAssistantAgent")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.setsockopt(zmq.RCVTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.setsockopt(zmq.SNDTIMEO, ZMQ_REQUEST_TIMEOUT)
        self.socket.bind(f"tcp://127.0.0.1:{zmq_port}")
        self.lock = threading.Lock()
        self.running = True
        logging.info(f"[FileSystemAssistant] Agent started on port {zmq_port}")

    def handle_query(self, query):
        action = query.get("action")
        path = query.get("path")
        if action == "list_dir":
            if not path or not os.path.isdir(path):
                return {"status": "error", "reason": "Invalid directory path"}
            try:
                with self.lock:
                    files = os.listdir(path)
                return {"status": "ok", "files": files}
            except Exception as e:
                logging.error(f"[FileSystemAssistant] Error listing dir: {e}")
                return {"status": "error", "reason": str(e)}
        elif action == "read_file":
            if not path or not os.path.isfile(path):
                return {"status": "error", "reason": "Invalid file path"}
            try:
                with self.lock:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                return {"status": "ok", "content": content}
            except Exception as e:
                logging.error(f"[FileSystemAssistant] Error reading file: {e}")
                return {"status": "error", "reason": str(e)}
        elif action == "write_file":
            content = query.get("content", "")
            try:
                with self.lock:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                logging.info(f"[FileSystemAssistant] Wrote to file: {path}")
                return {"status": "ok"}
            except Exception as e:
                logging.error(f"[FileSystemAssistant] Error writing file: {e}")
                return {"status": "error", "reason": str(e)}
        elif action == "delete_file":
            try:
                with self.lock:
                    if os.path.isfile(path):
                        os.remove(path)
                        logging.info(f"[FileSystemAssistant] Deleted file: {path}")
                        return {"status": "ok"}
                    else:
                        return {"status": "error", "reason": "File not found"}
            except Exception as e:
                logging.error(f"[FileSystemAssistant] Error deleting file: {e}")
                return {"status": "error", "reason": str(e)}
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
                logging.error(f"[FileSystemAssistant] Error: {e}")
                self.socket.send_string(json.dumps({"status": "error", "reason": str(e)}))

if __name__ == "__main__":
    agent = FileSystemAssistantAgent()
    agent.run()

    def _perform_initialization(self):
        """Initialize agent components."""
        try:
            # Add your initialization code here
            pass
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            raise