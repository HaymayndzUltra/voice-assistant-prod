import os
import platform
import shutil
import logging
import time
import threading
import zmq
import json
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
from typing import Dict, Any
from src.core.base_agent import BaseAgent

# Add project root to Python path for common_utils import
import sys
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import common utilities if available
try:
    from common_utils.zmq_helper import create_socket
import psutil
from datetime import datetime
    USE_COMMON_UTILS = True
except ImportError:
    USE_COMMON_UTILS = False

class UnifiedUtilsAgent(BaseAgent):
    def __init__(self, port=5700, name="UnifiedUtilsAgent"):
        """Initialize the UnifiedUtilsAgent with proper health check support."""
        super().__init__(port=port, name=name)
        self.last_cleanup_time = None
        logging.info(f"{self.name} initialized with health check on port {self.health_check_port}")
    
    def _get_health_status(self) -> Dict[str, Any]:
        """Override health status to include utility agent specific information."""
        base_status = super()._get_health_status()
        
        # Add utility agent specific health information
        base_status.update({
            "agent_type": "utility",
            "last_cleanup_time": self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
            "system_platform": platform.system(),
            "python_version": platform.python_version()
        })
        
        return base_status
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming requests with proper health check support."""
        action = request.get("action", "")
        
        # Handle health check requests
        if action in ["ping", "health", "health_check"]:
            return self._get_health_status()
        
        # Handle utility actions
        elif action == "cleanup_temp":
            return {"status": "success", "result": self.cleanup_temp_files()}
        
        elif action == "cleanup_logs":
            days = request.get("days", 7)
            return {"status": "success", "result": self.cleanup_logs(days_old=days)}
        
        elif action == "cleanup_cache":
            days = request.get("days", 1)
            return {"status": "success", "result": self.cleanup_cache(days_old=days)}
        
        elif action == "cleanup_browser":
            return {"status": "success", "result": self.cleanup_browser_cache()}
        
        elif action == "cleanup_system":
            result = self.cleanup_system()
            self.last_cleanup_time = datetime.now()
            return {"status": "success", "result": result}
        
        # Unknown action
        return {"status": "error", "message": f"Unknown action: {action}"}

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


    def health_check(self):
        '''
        Performs a health check on the agent, returning a dictionary with its status.
        '''
        try:
            # Basic health check logic
            is_healthy = True # Assume healthy unless a check fails
            
            # TODO: Add agent-specific health checks here.
            # For example, check if a required connection is alive.
            # if not self.some_service_connection.is_alive():
            #     is_healthy = False

            status_report = {
                "status": "healthy" if is_healthy else "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": time.time() - self.start_time if hasattr(self, 'start_time') else -1,
                "system_metrics": {
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                },
                "agent_specific_metrics": {} # Placeholder for agent-specific data
            }
            return status_report
        except Exception as e:
            # It's crucial to catch exceptions to prevent the health check from crashing
            return {
                "status": "unhealthy",
                "agent_name": self.name if hasattr(self, 'name') else self.__class__.__name__,
                "error": f"Health check failed with exception: {str(e)}"
            }

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    
    # Create and run the agent
    agent = UnifiedUtilsAgent()
    try:
        agent.run()
    except KeyboardInterrupt:
        logging.info("Agent stopped by user")
    finally:
        agent.cleanup() 