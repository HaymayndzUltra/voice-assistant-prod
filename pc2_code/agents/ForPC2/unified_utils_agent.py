import os
from typing import Dict, Any, Optional
import yaml
import platform
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys
import zmq
import json
import threading
import time
from common.config_manager import get_service_ip, get_service_url, get_redis_url


# Import path manager for containerization-friendly paths
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[2]  # points to repo root
sys.path.insert(0, str(BASE_DIR))
from common.utils.path_env import get_path, join_path, get_file_path
# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility
try:
    from common.core.base_agent import BaseAgent
    from pc2_code.agents.utils.config_loader import Config

    # Load configuration at the module level
    config = Config().get_config()
except ImportError as e:
    print(f"Import error: {e}")
    config = None

# Configure logging
log_directory = os.path.join('logs')
os.makedirs(log_directory, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('UnifiedUtilsAgent')

# Load configuration at the module level
def load_network_config():
    """Load the network configuration from the central YAML file."""
    config_path = join_path("config", "network_config.yaml")
    try:
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading network config: {e}")
        # Default fallback values
        return {
            "main_pc_ip": os.environ.get("MAIN_PC_IP", get_service_ip("mainpc")),
            "pc2_ip": os.environ.get("PC2_IP", get_service_ip("pc2")),
            "bind_address": os.environ.get("BIND_ADDRESS", "0.0.0.0"),
            "secure_zmq": False,
            "ports": {
                "utils_agent": int(os.environ.get("UTILS_AGENT_PORT", 7118)),
                "utils_health": int(os.environ.get("UTILS_AGENT_HEALTH_PORT", 8118)),
                "error_bus": int(os.environ.get("ERROR_BUS_PORT", 7150))
            }
        }

# Load network configuration
network_config = load_network_config()

# Get configuration values
MAIN_PC_IP = network_config.get("main_pc_ip", os.environ.get("MAIN_PC_IP", get_service_ip("mainpc")))
PC2_IP = network_config.get("pc2_ip", os.environ.get("PC2_IP", get_service_ip("pc2")))
BIND_ADDRESS = network_config.get("bind_address", os.environ.get("BIND_ADDRESS", "0.0.0.0"))
UTILS_AGENT_PORT = network_config.get("ports", {}).get("utils_agent", int(os.environ.get("UTILS_AGENT_PORT", 7118)))
UTILS_AGENT_HEALTH_PORT = network_config.get("ports", {}).get("utils_health", int(os.environ.get("UTILS_AGENT_HEALTH_PORT", 8118)))
ERROR_BUS_PORT = network_config.get("ports", {}).get("error_bus", int(os.environ.get("ERROR_BUS_PORT", 7150)))

class UnifiedUtilsAgent(BaseAgent):
    """
    UnifiedUtilsAgent: Provides utility functions for system maintenance and cleanup.
    """
    def __init__(self, port=None, health_check_port=None, host="0.0.0.0"):
        # Initialize agent state before BaseAgent
        self.running = True
        self.request_count = 0
        self.main_pc_connections = {}
        self.start_time = time.time()
        
        # Call BaseAgent's constructor
        super().__init__(
            name="UnifiedUtilsAgent", 
            port=port if port else UTILS_AGENT_PORT,
            health_check_port=health_check_port if health_check_port else UTILS_AGENT_HEALTH_PORT
        )
        
        # Set up error reporting
        self.setup_error_reporting()
        
        logger.info(f"UnifiedUtilsAgent initialized on port {self.port}")

    def setup_error_reporting(self):
        """Set up error reporting to the central Error Bus."""
        try:
            self.error_bus_host = PC2_IP
            self.error_bus_port = ERROR_BUS_PORT
            self.error_bus_endpoint = f"tcp://{self.error_bus_host}:{self.error_bus_port}"
            self.error_bus_pub = self.context.socket(zmq.PUB)
            self.error_bus_pub.connect(self.error_bus_endpoint)
            logger.info(f"Connected to Error Bus at {self.error_bus_endpoint}")
        except Exception as e:
            logger.error(f"Failed to set up error reporting: {e}")
    
    def report_error(self, error_type, message, severity="ERROR"):
        """Report an error to the central Error Bus."""
        try:
            if hasattr(self, 'error_bus_pub'):
                error_report = {
                    "timestamp": datetime.now().isoformat(),
                    "agent": self.name,
                    "type": error_type,
                    "message": message,
                    "severity": severity
                }
                self.error_bus_pub.send_multipart([
                    b"ERROR",
                    json.dumps(error_report).encode('utf-8')
                ])
                logger.info(f"Reported error: {error_type} - {message}")
        except Exception as e:
            logger.error(f"Failed to report error: {e}")

    def cleanup_temp_files(self, temp_dir: str = "agents/temp") -> dict:
        """Clean up temporary files."""
        result = {"files_removed": 0, "errors": []}
        try:
            temp_path = Path(temp_dir)
            if temp_path.exists():
                for file in temp_path.glob("*"):
                    try:
                        file.unlink()
                        result["files_removed"] += 1
                    except Exception as e:
                        result["errors"].append(str(e))
            logging.info(f"Temp files cleaned: {result['files_removed']} files removed.")
        except Exception as e:
            result["errors"].append(str(e))
            self.report_error("TEMP_FILES_CLEANUP_ERROR", str(e))
        return result

    def cleanup_logs(self, log_dir: str = "agents/logs", days_old: int = 7) -> dict:
        """Clean up log files older than days_old."""
        result = {"files_removed": 0, "errors": []}
        try:
            log_path = Path(log_dir)
            if log_path.exists():
                for file in log_path.glob("*.log"):
                    try:
                        if (datetime.now() - datetime.fromtimestamp(file.stat().st_mtime)).days > days_old:
                            file.unlink()
                            result["files_removed"] += 1
                    except Exception as e:
                        result["errors"].append(str(e))
            logging.info(f"Old logs cleaned: {result['files_removed']} files removed.")
        except Exception as e:
            result["errors"].append(str(e))
            self.report_error("LOGS_CLEANUP_ERROR", str(e))
        return result

    def cleanup_cache(self, cache_dir: str = "agents/cache", days_old: int = 1) -> dict:
        """Clean up cache files older than days_old."""
        result = {"files_removed": 0, "errors": []}
        try:
            cache_path = Path(cache_dir)
            if cache_path.exists():
                for file in cache_path.glob("*"):
                    try:
                        if (datetime.now() - datetime.fromtimestamp(file.stat().st_mtime)).days > days_old:
                            file.unlink()
                            result["files_removed"] += 1
                    except Exception as e:
                        result["errors"].append(str(e))
            logging.info(f"Cache cleaned: {result['files_removed']} files removed.")
        except Exception as e:
            result["errors"].append(str(e))
            self.report_error("CACHE_CLEANUP_ERROR", str(e))
        return result

    def cleanup_browser_cache(self) -> dict:
        """Clean browser caches for Chrome, Firefox, and Edge."""
        result = {"browsers_cleaned": 0, "files_removed": 0, "bytes_freed": 0, "errors": []}
        try:
            chrome_cache_dirs = []
            firefox_cache_dirs = []
            edge_cache_dirs = []
            sys_platform = platform.system()
            if sys_platform == "Windows":
                chrome_cache_dirs.append(os.path.expandvars("%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Cache"))
                firefox_cache_dirs.append(os.path.expandvars("%LOCALAPPDATA%\\Mozilla\\Firefox\\Profiles"))
                edge_cache_dirs.append(os.path.expandvars("%LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\Default\\Cache"))
            elif sys_platform == "Darwin":
                chrome_cache_dirs.append(os.path.expanduser("~/Library/Caches/Google/Chrome"))
                firefox_cache_dirs.append(os.path.expanduser("~/Library/Caches/Firefox"))
            elif sys_platform == "Linux":
                chrome_cache_dirs.append(os.path.expanduser("~/.cache/google-chrome"))
                firefox_cache_dirs.append(os.path.expanduser("~/.cache/mozilla/firefox"))
            all_cache_dirs = chrome_cache_dirs + firefox_cache_dirs + edge_cache_dirs
            for cache_dir in all_cache_dirs:
                if os.path.exists(cache_dir):
                    try:
                        before_size = self._get_dir_size(cache_dir)
                        files_removed = 0
                        for root, dirs, files in os.walk(cache_dir, topdown=True):
                            for file in files:
                                try:
                                    file_path = os.path.join(root, file)
                                    if os.path.isfile(file_path):
                                        os.unlink(file_path)
                                        files_removed += 1
                                except Exception as e:
                                    result["errors"].append(f"Error removing {file_path}: {str(e)}")
                        after_size = self._get_dir_size(cache_dir)
                        bytes_freed = before_size - after_size
                        result["browsers_cleaned"] += 1
                        result["files_removed"] += files_removed
                        result["bytes_freed"] += bytes_freed
                    except Exception as e:
                        result["errors"].append(f"Error cleaning cache directory {cache_dir}: {str(e)}")
            logging.info(f"Browser caches cleaned: {result['browsers_cleaned']} browsers, {result['files_removed']} files removed, {result['bytes_freed']} bytes freed.")
        except Exception as e:
            result["errors"].append(str(e))
            self.report_error("BROWSER_CACHE_CLEANUP_ERROR", str(e))
        return result

    def _get_dir_size(self, dir_path: str) -> int:
        total = 0
        for dirpath, dirnames, filenames in os.walk(dir_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total += os.path.getsize(fp)
        return total

    def run_windows_disk_cleanup(self) -> dict:
        """Run Windows Disk Cleanup utility."""
        result = {"status": "success", "message": "", "errors": []}
        if platform.system() != "Windows":
            result["status"] = "error"
            result["message"] = "Windows Disk Cleanup is only available on Windows"
            return result
        try:
            subprocess.run(["cleanmgr.exe", "/sagerun:1"], check=True)
            result["message"] = "Windows Disk Cleanup completed successfully"
            logging.info(result["message"])
        except subprocess.CalledProcessError as e:
            result["status"] = "error"
            result["message"] = f"Error running Windows Disk Cleanup: {str(e)}"
            result["errors"].append(str(e))
            self.report_error("WINDOWS_DISK_CLEANUP_ERROR", str(e))
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Error running Windows Disk Cleanup: {str(e)}"
            result["errors"].append(str(e))
            self.report_error("WINDOWS_DISK_CLEANUP_ERROR", str(e))
        return result

    def cleanup_system(self) -> dict:
        """Run all cleanup utilities and aggregate results."""
        results = {
            "temp_files": self.cleanup_temp_files(),
            "logs": self.cleanup_logs(),
            "cache": self.cleanup_cache(),
            "browser_cache": self.cleanup_browser_cache(),
        }
        if platform.system() == "Windows":
            results["windows_disk_cleanup"] = self.run_windows_disk_cleanup()
        return results

    def _get_health_status(self) -> Dict[str, Any]:
        """Return health status information. Overrides BaseAgent's _get_health_status."""
        # Get base status from parent class
        base_status = super()._get_health_status()
        
        # Add UnifiedUtilsAgent specific health info
        base_status.update({
            'status': 'ok',
            'agent': 'UnifiedUtilsAgent',
            'timestamp': datetime.now().isoformat(),
            'port': self.port,
            'uptime_seconds': time.time() - self.start_time,
            'request_count': self.request_count
        })
        
        return base_status

    def handle_request(self, request: dict) -> dict:
        action = request.get('action', '')
        if action == 'cleanup_temp_files':
            return self.cleanup_temp_files()
        elif action == 'cleanup_logs':
            return self.cleanup_logs()
        elif action == 'cleanup_cache':
            return self.cleanup_cache()
        elif action == 'cleanup_browser_cache':
            return self.cleanup_browser_cache()
        elif action == 'run_windows_disk_cleanup':
            return self.run_windows_disk_cleanup()
        elif action == 'cleanup_system':
            return self.cleanup_system()
        elif action == 'health_check':
            return self._get_health_status()
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def run(self):
        logger.info(f"UnifiedUtilsAgent starting on port {self.port}")
        try:
            while self.running:
                try:
                    if self.socket.poll(timeout=1000) != 0:  # 1 second timeout
                        request = self.socket.recv_json()
                        logger.debug(f"Received request: {request}")
                        response = self.handle_request(request)
                        self.socket.send_json(response)
                        self.request_count += 1
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in run loop: {e}")
                    self.report_error("ZMQ_ERROR", str(e))
                    try:
                        self.socket.send_json({'status': 'error', 'error': str(e)})
                    except:
                        pass
                    time.sleep(1)  # Avoid tight loop on error
                except Exception as e:
                    logger.error(f"Error in run loop: {e}")
                    self.report_error("RUN_LOOP_ERROR", str(e))
                    try:
                        self.socket.send_json({'status': 'error', 'error': str(e)})
                    except:
                        pass
                    time.sleep(1)  # Avoid tight loop on error
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        logger.info("Cleaning up resources...")
        self.running = False
        
        # Close main socket
        if hasattr(self, 'socket'):
            try:
                self.socket.close()
                logger.info("Closed main socket")
            except Exception as e:
                logger.error(f"Error closing main socket: {e}")
        
        # Close error bus socket
        if hasattr(self, 'error_bus_pub'):
            try:
                self.error_bus_pub.close()
                logger.info("Closed error bus socket")
            except Exception as e:
                logger.error(f"Error closing error bus socket: {e}")
        
        # Close any connections to other services
        for service_name, socket in self.main_pc_connections.items():
            try:
                socket.close()
                logger.info(f"Closed connection to {service_name}")
            except Exception as e:
                logger.error(f"Error closing connection to {service_name}: {e}")
        
        # Call parent cleanup
        try:
            super().cleanup()
            logger.info("Called parent cleanup")
        except Exception as e:
            logger.error(f"Error in parent cleanup: {e}")
        
        logger.info("Cleanup complete")

    def stop(self):
        self.running = False

    def connect_to_main_pc_service(self, service_name: str):
        if not hasattr(self, 'main_pc_connections'):
            self.main_pc_connections = {}
            
        # Get service details from config
        service_ports = network_config.get('ports', {})
        if service_name not in service_ports:
            logger.error(f"Service {service_name} not found in network configuration")
            return None
            
        port = service_ports[service_name]
        socket = self.context.socket(zmq.REQ)
        socket.connect(f"tcp://{MAIN_PC_IP}:{port}")
        self.main_pc_connections[service_name] = socket
        logger.info(f"Connected to {service_name} on MainPC at {MAIN_PC_IP}:{port}")
        return socket

if __name__ == "__main__":
    # Standardized main execution block for PC2 agents
    agent = None
    try:
        agent = UnifiedUtilsAgent()
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