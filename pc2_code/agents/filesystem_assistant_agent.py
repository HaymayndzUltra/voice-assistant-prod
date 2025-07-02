#!/usr/bin/env python3
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
import yaml # Added for network config loading

# Add project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import base agent and config loaders
from main_pc_code.src.core.base_agent import BaseAgent
from pc2_code.agents.utils.config_loader import Config # Assuming this is used for general PC2 config

# Import common utilities if available
try:
    # Assuming this module exists and provides `create_socket`
    from common_utils.zmq_helper import create_socket
    USE_COMMON_UTILS = True
except ImportError as e:
    print(f"Import error: {e}. Some common utilities might not be available.")
    USE_COMMON_UTILS = False

# Load network configuration
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = os.path.join(project_root, "config", "network_config.yaml")
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
            "secure_zmq": False,
            "ports": {} # Ensure ports key exists for .get("ports", {})
        }

network_config = load_network_config()

# Get machine IPs from network config
MAIN_PC_IP = network_config.get("main_pc_ip", "192.168.100.16")
PC2_IP = network_config.get("pc2_ip", "192.168.100.17")
BIND_ADDRESS = network_config.get("bind_address", "0.0.0.0")

# Load PC2 specific configuration (if any specific config needed from Config class)
# config = Config().get_config() # This was here in the original, but not explicitly used in this agent's logic snippet.
                               # Keeping it commented if it's not directly needed by this agent.

# Updated port as requested
ZMQ_FILESYSTEM_AGENT_PORT = 5606  # Using REP socket on port 5606 as specified

# Setup logging
LOG_DIR = project_root / "logs" # Use project_root for consistency
LOG_DIR.mkdir(exist_ok=True)
LOG_PATH = LOG_DIR / "filesystem_assistant_agent.log"

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
        # Call BaseAgent's constructor first. This sets self.name, self.port, self.running, self.start_time.
        super().__init__(name="FileSystemAssistantAgent", port=zmq_port)

        # Use the port determined by BaseAgent or passed in
        self.port = self.port if self.port else zmq_port
        self.health_port = self.port + 1 # Consistent health port definition

        logger.info("=" * 80)
        logger.info(f"Initializing {self.name} on port {self.port}")
        logger.info("=" * 80)

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        
        # Initialize health check socket
        try:
            if USE_COMMON_UTILS:
                # Assuming create_socket signature takes bind_address
                self.health_socket = create_socket(self.context, zmq.REP, server=True, bind_address=f"tcp://0.0.0.0:{self.health_port}")
            else:
                self.health_socket = self.context.socket(zmq.REP)
                self.health_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout for polling
                self.health_socket.bind(f"tcp://0.0.0.0:{self.health_port}")
            logger.info(f"Health check socket bound to port {self.health_port}")
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to bind health check socket to {self.health_port}: {e}")
            raise # Critical error, agent cannot start properly
        except Exception as e:
            logger.error(f"Unexpected error during health socket setup: {e}", exc_info=True)
            raise

        # Bind the main REP socket
        self.socket.bind(f"tcp://0.0.0.0:{self.port}")
        logger.info(f"{self.name} main socket bound to port {self.port} with REP socket")

        self.lock = threading.Lock()
        # self.running is managed by BaseAgent
        # self.start_time is managed by BaseAgent (time.time())

        # Track usage statistics
        self.request_count = 0
        self.error_count = 0
        self.last_request_time = None
        
        # Start health check thread
        self._start_health_check_thread() # Renamed to be consistent with BaseAgent pattern

        logger.info(f"{self.name} initialized successfully.")
        logger.info(f"Working directory: {os.getcwd()}")

    def _start_health_check_thread(self): # Renamed for clarity and consistency
        """Start health check thread."""
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True) # Ensure it's a daemon thread
        self.health_thread.start()
        logger.info("Health check thread started")
    
    def _health_check_loop(self):
        """Background loop to handle health check requests."""
        logger.info("Health check loop started")
        
        while self.running: # Use self.running from BaseAgent
            try:
                # Check for health check requests with timeout
                if self.health_socket.poll(100) == 0: # 100ms timeout, zmq.POLLIN is default for poll()
                    continue
                
                # Receive request (content is usually not important for health checks)
                _ = self.health_socket.recv()
                
                # Get health data (calls the overridden _get_health_status)
                health_data = self._get_health_status()
                
                # Send response
                self.health_socket.send_json(health_data)
                
            except zmq.error.Again: # Timeout, no request received
                pass
            except Exception as e:
                logger.error(f"Error in health check loop: {e}", exc_info=True)
                time.sleep(1) # Sleep longer on error

    def _get_health_status(self) -> Dict[str, Any]:
        """Get the current health status of the agent. Overrides BaseAgent's method."""
        base_status = super()._get_health_status() # Get base status from BaseAgent
        
        # Add FileSystemAssistantAgent specific health info
        uptime_seconds = time.time() - self.start_time # Use time.time() for uptime calculation
        
        base_status.update({
            "agent": self.name,
            "status": "ok", # Overall status, refine if specific checks fail
            "timestamp": datetime.now().isoformat(), # For human-readable timestamp
            "uptime_seconds": uptime_seconds,
            "uptime_human": str(timedelta(seconds=int(uptime_seconds))), # Convert to human-readable
            "metrics": {
                "request_count": self.request_count,
                "error_count": self.error_count,
                "last_request_time": self.last_request_time.isoformat() if self.last_request_time else None,
                "health_thread_alive": self.health_thread.is_alive() if hasattr(self, 'health_thread') else False,
            }
        })
        return base_status

    def handle_query(self, query: Dict[str, Any]) -> Dict[str, Any]: # Added type hints for clarity
        """Process incoming file operation requests"""
        try:
            self.request_count += 1
            self.last_request_time = datetime.now()
            
            # Extract action and path from query
            action = query.get("action")
            path = query.get("path")
            
            logger.info(f"Received request: {action} on {path}")
            
            # Directory listing operation
            if action == "list_dir":
                if not path:
                    return {"status": "error", "reason": "Missing directory path"}
                # Ensure path is within a permitted root if security is paramount
                if not os.path.isdir(path):
                    return {"status": "error", "reason": "Path is not a valid directory or does not exist"}
                try:
                    with self.lock:
                        entries = []
                        for item in os.listdir(path):
                            item_path = os.path.join(path, item)
                            entry = {
                                "name": item,
                                "is_dir": os.path.isdir(item_path),
                                "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None,
                                "modified_timestamp": os.path.getmtime(item_path),
                                "modified_human": datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat()
                            }
                            entries.append(entry)
                    return {"status": "ok", "entries": entries}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error listing directory '{path}': {e}", exc_info=True)
                    return {"status": "error", "reason": str(e)}
            
            # File reading operation
            elif action == "read_file":
                if not path:
                    return {"status": "error", "reason": "Missing file path"}
                if not os.path.isfile(path):
                    return {"status": "error", "reason": "Path is not a valid file or does not exist"}
                try:
                    with self.lock:
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                    return {"status": "ok", "content": content, "size": os.path.getsize(path)}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error reading file '{path}': {e}", exc_info=True)
                    return {"status": "error", "reason": str(e)}
            
            # Write file operation
            elif action == "write_file":
                content = query.get("content")
                mode = query.get("mode", "w")  # Default to write mode, but allow append with "a"
                if not path or content is None: # content can be empty string, check for None
                    return {"status": "error", "reason": "Missing path or content"}
                if mode not in ["w", "a", "wb", "ab"]: # Basic validation for mode
                    return {"status": "error", "reason": f"Invalid write mode: {mode}"}
                
                try:
                    # Make sure directory exists
                    directory = os.path.dirname(path)
                    if directory and not os.path.exists(directory):
                        os.makedirs(directory, exist_ok=True)
                        
                    with self.lock:
                        if 'b' in mode: # If binary mode, content should be bytes
                            if not isinstance(content, bytes):
                                # If content is string, attempt to encode (default to utf-8)
                                try:
                                    content_bytes = content.encode(query.get("encoding", "utf-8"))
                                except Exception:
                                    return {"status": "error", "reason": "Content must be bytes for binary write, or a string with valid encoding."}
                            else:
                                content_bytes = content
                            with open(path, mode) as f:
                                f.write(content_bytes)
                        else: # Text mode
                            if not isinstance(content, str):
                                return {"status": "error", "reason": "Content must be string for text write."}
                            with open(path, mode, encoding="utf-8") as f: # Default to utf-8
                                f.write(content)
                    
                    return {"status": "ok", "path": path, "size": os.path.getsize(path)}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error writing file '{path}' in mode '{mode}': {e}", exc_info=True)
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
                if not path:
                    return {"status": "error", "reason": "Missing path"}
                if not os.path.exists(path):
                    return {"status": "ok", "message": f"Path {path} does not exist, nothing to delete"} # Already gone
                
                recursive = query.get("recursive", False) # Allow recursive directory delete
                
                try:
                    with self.lock:
                        if os.path.isfile(path):
                            os.remove(path)
                            return {"status": "ok", "message": f"File {path} deleted successfully"}
                        elif os.path.isdir(path):
                            if not os.listdir(path): # Directory is empty
                                os.rmdir(path)
                                return {"status": "ok", "message": f"Empty directory {path} deleted successfully"}
                            elif recursive:
                                shutil.rmtree(path)
                                return {"status": "ok", "message": f"Directory {path} and its contents deleted successfully (recursive)"}
                            else:
                                return {"status": "error", "reason": "Directory is not empty, use recursive=True to delete contents"}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error deleting path '{path}': {e}", exc_info=True)
                    return {"status": "error", "reason": str(e)}
                
            # Get file info
            elif action == "get_info":
                if not path:
                    return {"status": "error", "reason": "Missing path"}
                if not os.path.exists(path):
                    return {"status": "error", "reason": "Path does not exist"}
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
                        "created_timestamp": stat.st_ctime, # Creation time (platform dependent)
                        "modified_timestamp": stat.st_mtime, # Last modification time
                        "accessed_timestamp": stat.st_atime, # Last access time
                        "created_human": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_human": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "accessed_human": datetime.fromtimestamp(stat.st_atime).isoformat()
                    }
                    return info
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error getting file info for '{path}': {e}", exc_info=True)
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
                            
                            shutil.copy2(source, destination) # copy2 preserves metadata
                            return {"status": "ok", "message": f"File copied from {source} to {destination}"}
                        elif os.path.isdir(source):
                            # Copy directory, destination must not exist for copytree
                            if not os.path.exists(destination):
                                shutil.copytree(source, destination)
                                return {"status": "ok", "message": f"Directory copied from {source} to {destination}"}
                            else:
                                return {"status": "error", "reason": "Destination directory already exists for directory copy"}
                        else:
                            return {"status": "error", "reason": "Source is not a file or directory"}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error copying from '{source}' to '{destination}': {e}", exc_info=True)
                    return {"status": "error", "reason": str(e)}

            # Move/Rename file or directory
            elif action == "move":
                source = path
                destination = query.get("destination")
                if not source or not destination:
                    return {"status": "error", "reason": "Missing source or destination path"}
                if not os.path.exists(source):
                    return {"status": "error", "reason": "Source path does not exist"}
                
                try:
                    with self.lock:
                        shutil.move(source, destination) # Handles both files and directories, rename too
                        return {"status": "ok", "message": f"Moved/Renamed '{source}' to '{destination}'"}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error moving '{source}' to '{destination}': {e}", exc_info=True)
                    return {"status": "error", "reason": str(e)}

            # Create directory
            elif action == "create_dir":
                if not path:
                    return {"status": "error", "reason": "Missing directory path"}
                try:
                    with self.lock:
                        os.makedirs(path, exist_ok=True) # Creates intermediate directories if needed
                        return {"status": "ok", "message": f"Directory '{path}' created (or already exists)"}
                except Exception as e:
                    self.error_count += 1
                    logger.error(f"Error creating directory '{path}': {e}", exc_info=True)
                    return {"status": "error", "reason": str(e)}
            
            # Unknown action
            else:
                return {"status": "error", "reason": f"Unknown action: {action}"}
                
        except Exception as e:
            self.error_count += 1
            logger.error(f"Unexpected error in handle_query: {e}", exc_info=True)
            return {"status": "error", "reason": f"Unexpected error: {str(e)}"}
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status information. Alias for _get_health_status."""
        return self._get_health_status()
        
    def run(self):
        """Main request handling loop. Overrides BaseAgent's run method."""
        logger.info(f"{self.name} Starting main request handling loop on port {self.port}")
        
        while self.running: # Use self.running from BaseAgent
            try:
                # Wait for next request (timeout for graceful shutdown)
                request_json = self.socket.recv_string(flags=zmq.NOBLOCK) # Use NOBLOCK and poll to allow exit
                # If no message, continue (timeout will be handled by poll)
                
                logger.info(f"Received request: {request_json[:100]}..." 
                           if len(request_json) > 100 else f"Received request: {request_json}")
                
                # Parse request
                request = json.loads(request_json)
                
                # Process request
                response = self.handle_query(request)
                
                # Send response
                self.socket.send_string(json.dumps(response))
            
            except zmq.Again: # No message received within timeout
                # This is normal when using NOBLOCK with no pending messages
                time.sleep(0.01) # Small sleep to prevent tight loop
                continue
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}", exc_info=True)
                self.error_count += 1
                try: # Attempt to send error response
                    self.socket.send_string(json.dumps({"status": "error", "reason": "Invalid JSON format"}))
                except zmq.error.ZMQError as send_error:
                    logger.error(f"Failed to send JSON error response: {send_error}")
            except Exception as e:
                logger.error(f"Error in main request handling loop: {e}", exc_info=True)
                self.error_count += 1
                try: # Attempt to send error response
                    self.socket.send_string(json.dumps({"status": "error", "reason": f"Unexpected server error: {str(e)}"}))
                except zmq.error.ZMQError as send_error:
                    logger.error(f"Failed to send error response: {send_error}")
        logger.info(f"{self.name} main request handling loop exited.")
    
    def cleanup(self):
        """Clean up resources before shutdown. Overrides BaseAgent's cleanup method."""
        logger.info(f"Cleaning up {self.name} resources...")
        self.running = False # Signal threads to stop

        # Wait for health thread to finish
        if hasattr(self, 'health_thread') and self.health_thread and self.health_thread.is_alive():
            logger.info("Waiting for health check thread to terminate...")
            self.health_thread.join(timeout=2)
            if self.health_thread.is_alive():
                logger.warning("Health check thread did not terminate gracefully.")
        
        # Close ZMQ sockets
        try:
            for sock in [self.socket, self.health_socket]:
                if hasattr(self, 'context') and sock and not sock.closed:
                    sock.close()
                    logger.info(f"Closed ZMQ socket: {sock}")
        except Exception as e:
            logger.error(f"Error closing ZMQ sockets: {e}", exc_info=True)
        
        # Terminate ZMQ context
        try:
            if hasattr(self, 'context') and self.context and not self.context.closed:
                self.context.term()
                logger.info("ZMQ context terminated.")
        except Exception as e:
            logger.error(f"Error terminating ZMQ context: {e}", exc_info=True)
        
        logger.info(f"{self.name} cleanup complete.")
        super().cleanup() # Call parent's cleanup

    def stop(self):
        """Stop the agent gracefully. Alias for cleanup."""
        logger.info(f"{self.name} Stopping agent (calling cleanup)...")
        self.cleanup()

    def connect_to_main_pc_service(self, service_name: str) -> Optional[zmq.Socket]:
        """
        Connect to a service on the main PC using the network configuration.
        
        Args:
            service_name: Name of the service in the network config ports section
        
        Returns:
            ZMQ socket connected to the service, or None if connection fails or service not found.
        """
        if not hasattr(self, 'main_pc_connections'):
            self.main_pc_connections = {} # Initialize if not exists
            
        if service_name not in network_config.get("ports", {}):
            logger.error(f"Service {service_name} not found in network configuration ports section.")
            return None
            
        port = network_config.get("ports")[service_name]
        
        # Check if a connection already exists
        if service_name in self.main_pc_connections:
            # For simplicity, return existing socket. In production, add validation if it's still active.
            return self.main_pc_connections[service_name]
            
        # Create a new socket for this connection
        socket = self.context.socket(zmq.REQ)
        
        # Apply secure ZMQ if available and enabled (assuming secure ZMQ setup is handled globally)
        # from main_pc_code.src.network.secure_zmq import configure_secure_client, start_auth
        # This agent needs to know if secure ZMQ is enabled globally and configure it.
        # For this example, assuming it's not explicitly managed in FileSystemAssistantAgent.
        
        try:
            # Connect to the service
            connect_address = f"tcp://{MAIN_PC_IP}:{port}"
            socket.connect(connect_address)
            logger.info(f"Connected to {service_name} on MainPC at {connect_address}")
            self.main_pc_connections[service_name] = socket
            return socket
        except zmq.error.ZMQError as e:
            logger.error(f"Failed to connect to {service_name} at {connect_address}: {e}", exc_info=True)
            socket.close() # Close the socket if connection fails
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred while connecting to {service_name}: {e}", exc_info=True)
            if socket and not socket.closed:
                socket.close()
            return None


if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = FileSystemAssistantAgent()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'} on PC2 due to keyboard interrupt...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'} on PC2: {e}")
        traceback.print_exc()
    finally:
        if agent: # Check if agent object was successfully created
            # The agent's cleanup method will now be called by the run() method's finally block,
            # or directly if run() was interrupted earlier.
            # We call it explicitly here as a safeguard if the agent object was created but run() wasn't entered.
            # It's also safe to call cleanup() multiple times as it checks if sockets are closed.
            print(f"Cleaning up {agent.name} on PC2...")
            agent.cleanup()