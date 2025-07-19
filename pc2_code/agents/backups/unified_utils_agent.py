import os
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
from common.config_manager import get_service_ip, get_service_url, get_redis_url


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, os.path.abspath(join_path("pc2_code", ".."))))
from common.utils.path_env import get_path, join_path, get_file_path

import time# Add the project root to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import config parser utility
try:
from pc2_code.agents.utils.config_parser import parse_agent_args
    except ImportError as e:
        print(f"Import error: {e}")
    _agent_args 
from main_pc_code.src.core.base_agent import BaseAgent
from main_pc_code.utils.config_loader import load_config
from common.env_helpers import get_env

# Load configuration at the module level
config = load_config()= parse_agent_args()
except ImportError:
    class DummyArgs(BaseAgent):
        host = 'localhost'
    _agent_args = DummyArgs()

# Configure logging
log_file_path = join_path("logs", "unified_utils_agent.log")
log_directory = os.path.dirname(log_file_path)
os.makedirs(log_directory, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('UnifiedUtilsAgent')

# Default ZMQ ports (will be overridden by configuration)
UTILS_AGENT_PORT = 7118  # Default, will be overridden by configuration
UTILS_AGENT_HEALTH_PORT = 8118  # Default health check port

class UnifiedUtilsAgent:
    def __init__(self, port=None, health_check_port=None, host="0.0.0.0"):
         super().__init__(name="DummyArgs", port=None)
self.main_port = port if port is not None else UTILS_AGENT_PORT
        self.health_port = health_check_port if health_check_port is not None else UTILS_AGENT_HEALTH_PORT
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://*:{self.main_port}")
        self.running = True
        logger.info(f"UnifiedUtilsAgent initialized on port {self.main_port}")

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
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Error running Windows Disk Cleanup: {str(e)}"
            result["errors"].append(str(e))
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

    def _health_check(self) -> dict:
        return {
            'status': 'success',
            'agent': 'UnifiedUtilsAgent',
            'timestamp': datetime.now().isoformat(),
            'port': self.main_port
        }

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
            return self._health_check()
        else:
            return {'status': 'error', 'message': f'Unknown action: {action}'}

    def run(self):
        logger.info(f"UnifiedUtilsAgent starting on port {self.main_port}")
        try:
            while self.running:
                try:
                    request = self.socket.recv_json()
                    logger.debug(f"Received request: {request}")
                    response = self.handle_request(request)
                    self.socket.send_json(response)
                except zmq.error.ZMQError as e:
                    logger.error(f"ZMQ error in run loop: {e}")
                    try:
                        self.socket.send_json({'status': 'error', 'error': str(e)})
                    except:
                        pass
                except Exception as e:
                    logger.error(f"Error in run loop: {e}")
                    try:
                        self.socket.send_json({'status': 'error', 'error': str(e)})
                    except:
                        pass
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        logger.info("Cleaning up resources...")
        self.running = False
        if hasattr(self, 'socket'):
            self.socket.close()
        if hasattr(self, 'context'):
            self.context.term()
        logger.info("Cleanup complete")


    def _get_health_status(self) -> dict:

        """Return health status information."""

        base_status = super()._get_health_status()

        # Add any additional health information specific to DummyArgs

        base_status.update({

            'service': 'DummyArgs',

            'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0,

            'additional_info': {}

        })

        return base_status

    def stop(self):
        self.running = False



if __name__ == "__main__":
    # Standardized main execution block
    agent = None
    try:
        agent = DummyArgs()
        agent.run()
    except KeyboardInterrupt:
        print(f"Shutting down {agent.name if agent else 'agent'}...")
    except Exception as e:
        import traceback
        print(f"An unexpected error occurred in {agent.name if agent else 'agent'}: {e}")
        traceback.print_exc()
    finally:
        if agent and hasattr(agent, 'cleanup'):
            print(f"Cleaning up {agent.name}...")
            agent.cleanup()