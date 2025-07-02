#!/usr/bin/env python3
from typing import Dict, Any, Optional
import yaml
"""
FileSystem Assistant Agent
--------------------------
This agent provides a ZMQ service for file system operations, allowing other agents
to perform controlled file operations across the distributed system.

The agent runs on port 5606 with a REP socket pattern to handle requests and provide responses.
"""

import zmq
import json
import os
import sys
import threading
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import time

# Add project root to Python path for common_utils import
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False



# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Setup logging with better organization
LOG_DIR = Path(os.path.dirname(__file__)).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / "filesystem_assistant_agent.log"

# Updated port as requested
ZMQ_FILESYSTEM_AGENT_PORT = 5606  # Using REP socket on port 5606 as specified

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FilesystemAssistant")

class FileSystemAssistantAgent(BaseAgent):
    """Filesystem Assistant Agent that provides file operations via ZMQ
    
    This agent allows other components in the system to interact with the filesystem
    in a controlled and secure manner. It provides operations such as listing directories,
    reading files, writing files, checking file existence, and more.
    
    The agent uses a ZMQ REP socket to receive requests and send responses.
    """
    
    def __init__(self, zmq_port=ZMQ_FILESYSTEM_AGENT_PORT):

         super().__init__(name="FileSystemAssistantAgent", port=None)
self.name = "FileSystemAssistantAgent"
        self.running = True
        self.start_time = time.time()
        self.health_port = self.port + 1

        """Initialize the FileSystem Assistant Agent with ZMQ REP socket on specified port"""
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)

        
        # Start health check thread
        self._start_health_check()

        # Initialize health check socket
        try:
            if USE_COMMON_UTILS:
                self.health_socket = create_socket(self.context, zmq.REP, server=True)
            else:
                self.health_socket = self.context.socket(zmq.REP)
                self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            self.health_socket.bind(f"tcp://0.0.0.0:{self.health_port}")
            logging.info(f"Health check socket bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logging.error(f"Failed to bind health check socket: {e}")
            raise
        self.socket.bind(f"tcp://0.0.0.0:{zmq_port}")
        self.lock = threading.Lock()
        self.running = True
        self.start_time = datetime.now()
        
        # Track usage statistics
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = None
        
        logger.info(f"[FileSystemAssistant] Agent started on port {zmq_port} with REP socket")
        logger.info(f"[FileSystemAssistant] Working directory: {os.getcwd()}")

    def _start_health_check(self):
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        logging.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logging.info("Health check loop started")
        
        while self.running:
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100, zmq.POLLIN):
                    # Receive request (don't care about content)
                    _ = self.health_socket.recv()
                    
                    # Get health data
                    health_data = self._get_health_status()
                    
                    # Send response
                    self.health_socket.send_json(health_data)
                    
                time.sleep(0.1)  # Small sleep to prevent CPU hogging
                
            except Exception as e:
                logging.error(f"Error in health check loop: {e}")
                time.sleep(1)  # Sleep longer on error
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent."""
        uptime = time.time() - self.start_time
        
        return {
            "agent": self.name,
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "uptime": uptime
        }

    def handle_query(self, query):
        """Process incoming file operation requests"""
        try:
            self.request_count += 1
            self.last_request_time = datetime.now()
            
            # Extract action and path from query
            
from main_pc_code.src.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config

# Load configuration at the module level
config = Config().get_config()
action = query.get("action")
            path = query.get("path")
            
            logger.info(f"[FileSystemAssistant] Received request: {action} on {path}")
            
            # Directory listing operation
            if action == "list_dir":
                if not path or not os.path.isdir(path):
                    return {"status": "error", "reason": "Invalid directory path"}
                try:
                    with self.lock:
                        # Get more detailed directory info with file types and sizes
                        entries = []
                        for item in os.listdir(path):
                            item_path = os.path.join(path, item)
                            entry = {
                                "name": item,
                                "is_dir": os.path.isdir(item_path),
                                "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None,
                                "modified": os.path.getmtime(item_path)
                            }
                            entries.append(entry)
                    return {"status": "ok", "entries": entries}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"[FileSystemAssistant] Error listing dir: {e}")
                    return {"status": "error", "reason": str(e)}
            
            # File reading operation
            elif action == "read_file":
                if not path or not os.path.isfile(path):
                    return {"status": "error", "reason": "Invalid file path"}
                try:
                    with self.lock:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                    return {"status": "ok", "content": content, "size": os.path.getsize(path)}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"[FileSystemAssistant] Error reading file: {e}")
                    return {"status": "error", "reason": str(e)}
            
            # Write file operation
            elif action == "write_file":
                content = query.get("content")
                mode = query.get("mode", "w")  # Default to write mode, but allow append with "a"
                if not path or not content:
                    return {"status": "error", "reason": "Missing path or content"}
                try:
                    # Make sure directory exists
                    directory = os.path.dirname(path)
                    if directory and not os.path.exists(directory):
                        os.makedirs(directory, exist_ok=True)
                        
                    with self.lock:
                        with open(path, mode, encoding="utf-8") as f:
                            f.write(content)
                    return {"status": "ok", "path": path, "size": os.path.getsize(path)}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"[FileSystemAssistant] Error writing file: {e}")
                    return {"status": "error", "reason": str(e)}
            
            # File existence check
            elif action == "check_exists":
                if not path:
                    return {"status": "error", "reason": "Missing path"}
                exists = os.path.exists(path)
                is_file = os.path.isfile(path) if exists else False
                is_dir = os.path.isdir(path) if exists else False
                return {
                    "status": "ok", 
                    "exists": exists,
                    "is_file": is_file,
                    "is_dir": is_dir
                }
                
            # File deletion
            elif action == "delete":
                if not path or not os.path.exists(path):
                    return {"status": "error", "reason": "Invalid path or file/directory doesn't exist"}
                try:
                    with self.lock:
                        if os.path.isfile(path):
                            os.remove(path)
                            return {"status": "ok", "message": f"File {path} deleted successfully"}
                        elif os.path.isdir(path):
                            # Check if directory is empty
                            if not os.listdir(path):
                                os.rmdir(path)
                                return {"status": "ok", "message": f"Empty directory {path} deleted successfully"}
                            else:
                                return {"status": "error", "reason": "Directory is not empty"}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"[FileSystemAssistant] Error deleting path: {e}")
                    return {"status": "error", "reason": str(e)}
                
            # Get file info
            elif action == "get_info":
                if not path or not os.path.exists(path):
                    return {"status": "error", "reason": "Invalid path or doesn't exist"}
                try:
                    is_file = os.path.isfile(path)
                    is_dir = os.path.isdir(path)
                    stat = os.stat(path)
                    info = {
                        "status": "ok",
                        "path": path,
                        "is_file": is_file,
                        "is_dir": is_dir,
                        "size": stat.st_size,
                        "created": stat.st_ctime,
                        "modified": stat.st_mtime,
                        "accessed": stat.st_atime
                    }
                    return info
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"[FileSystemAssistant] Error getting file info: {e}")
                    return {"status": "error", "reason": str(e)}
            
            # Copy file operation
            elif action == "copy":
                source = path
                destination = query.get("destination")
                if not source or not destination:
                    return {"status": "error", "reason": "Missing source or destination path"}
                if not os.path.exists(source):
                    return {"status": "error", "reason": "Source path does not exist"}
                
                try:
                    with self.lock:
                        if os.path.isfile(source):
                            # Create destination directory if needed
                            dest_dir = os.path.dirname(destination)
                            if dest_dir and not os.path.exists(dest_dir):
                                os.makedirs(dest_dir, exist_ok=True)
                            
                            shutil.copy2(source, destination)
                            return {"status": "ok", "message": f"File copied from {source} to {destination}"}
                        elif os.path.isdir(source):
                            if not os.path.exists(destination):
                                shutil.copytree(source, destination)
                                return {"status": "ok", "message": f"Directory copied from {source} to {destination}"}
                            else:
                                return {"status": "error", "reason": "Destination directory already exists"}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"[FileSystemAssistant] Error copying: {e}")
                    return {"status": "error", "reason": str(e)}
            
            # Unknown action
            else:
                return {"status": "error", "reason": f"Unknown action: {action}"}
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"[FileSystemAssistant] Unexpected error: {e}")
            return {"status": "error", "reason": f"Unexpected error: {str(e)}"}
    
    def get_status(self):
        """Get agent status information"""
        uptime = datetime.now() - self.start_time
        return {
            "status": "running" if self.running else "stopped",
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime),
            "request_count": self.request_count,
            "error_count": self.error_count,
            "last_request": self.last_request_time.isoformat() if self.last_request_time else None
        }
        
    def run(self):
        """Main request handling loop"""
        logger.info("[FileSystemAssistant] Starting request handling loop")
        
        while self.running:
            try:
                # Wait for next request
                request_json = self.socket.recv_string()
                logger.info(f"[FileSystemAssistant] Received request: {request_json[:100]}..." 
                           if len(request_json) > 100 else f"[FileSystemAssistant] Received request: {request_json}")
                
                # Parse request
                request = json.loads(request_json)
                
                # Check for status request
                if request.get("action") == "get_status":
                    response = {"status": "ok", **self.get_status()}
                else:
                    # Process normal file operation request
                    response = self.handle_query(request)
                
                # Send response
                self.socket.send_string(json.dumps(response))
            except json.JSONDecodeError as e:
                logger.error(f"[FileSystemAssistant] Invalid JSON: {e}")
                self.error_count += 1
                self.socket.send_string(json.dumps({"status": "error", "reason": "Invalid JSON"}))
            except Exception as e:
                logger.error(f"[FileSystemAssistant] Error in request handling: {e}")
                self.error_count += 1
                try:
                    self.socket.send_string(json.dumps({"status": "error", "reason": str(e)}))
                except:
                    # In case we can't even send the error response
                    pass


    
    def cleanup(self):

    
        """Clean up resources before shutdown."""

    
        logger.info("Cleaning up resources...")

    
        # Add specific cleanup code here

    
        super().cleanup()
    
    def stop(self):
        """Stop the agent gracefully"""
        logger.info("[FileSystemAssistant] Stopping agent")
        self.running = False







if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = FileSystemAssistantAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": "192.168.100.16",
            "pc2_ip": "192.168.100.17",
            "bind_address": "0.0.0.0",
            "secure_zmq": False
        }

# Load both configurations
network_config = load_network_config()

# Get machine IPs from config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")
print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()


    def connect_to_main_pc_service(self, service_name: str):

        """

        Connect to a service on the main PC using the network configuration.

        

        Args:

            service_name: Name of the service in the network config ports section

        

        Returns:

            ZMQ socket connected to the service

        """

        if not hasattr(self, 'main_pc_connections'):

            self.main_pc_connections = {}

            

        if service_name not in network_config.get("ports", {}):

            logger.error(f"Service {service_name} not found in network configuration")

            return None

            

        port = network_config["ports"][service_name]

        

        # Create a new socket for this connection

        socket = self.context.socket(zmq.REQ)

        

        # Connect to the service

        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")

        

        # Store the connection

        self.main_pc_connections[service_name] = socket

        

        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")

        return socket
