import os
import platform
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
from src.core.base_agent import BaseAgent
import time
import psutil
from datetime import datetime

class UnifiedUtilsAgent(BaseAgent):
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