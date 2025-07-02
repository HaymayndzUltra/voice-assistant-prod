import os
import platform
import psutil
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from main_pc_code.src.core.base_agent import BaseAgent

class UnifiedMonitor(BaseAgent):
    def __init__(self, port: Optional[int] = None, **kwargs):
        super().__init__(port=port, name="UnifiedMonitor")
        # Initialize monitoring configuration
        self.monitoring_config = {
            "cpu_threshold": 80,  # percent
            "memory_threshold": 80,  # percent
            "disk_threshold": 90,  # percent
            "update_interval": 10  # seconds
        }
        
        # Initialize resource history
        self.resource_history: Dict[float, Dict[str, Any]] = {}
        
        # Initialize logging
        self.logger = logging.getLogger("UnifiedMonitor")
        
        # Ensure psutil is available
        self._ensure_dependencies()
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("Unified Monitor initialized")

    def _ensure_dependencies(self):
        """Ensure all required dependencies are installed"""
        try:
            import psutil
    except ImportError as e:
        print(f"Import error: {e}")
            self.logger.info("All required dependencies are installed")
            self.psutil_available = True
        except ImportError:
            self.logger.warning("psutil is not installed. Some functionality will be limited.")
            self.logger.warning("Install psutil with: pip install psutil")
            self.psutil_available = False

    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version()
        }
        
        if self.psutil_available:
            info.update({
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": {str(part.mountpoint): {
                    "total": part.total,
                    "used": part.used,
                    "free": part.free,
                    "percent": part.percent
                } for part in psutil.disk_partitions() if part.fstype}
            })
        
        return info

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information"""
        if not self.psutil_available:
            return {"error": "psutil is not available"}
        
        memory = psutil.virtual_memory()
        return {
            "total": memory.total,
            "available": memory.available,
            "used": memory.used,
            "free": memory.free,
            "percent": memory.percent
        }

    def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage information"""
        if not self.psutil_available:
            return {"error": "psutil is not available"}
        
        disk_usage = {}
        for part in psutil.disk_partitions():
            if part.fstype:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disk_usage[part.mountpoint] = {
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    }
                except PermissionError:
                    disk_usage[part.mountpoint] = {"error": "Permission denied"}
        
        return disk_usage

    def _get_process_info(self, sort_by="memory_percent", limit=10) -> List[Dict[str, Any]]:
        """Get information about running processes"""
        if not self.psutil_available:
            return [{"error": "psutil is not available"}]
        
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        processes.sort(key=lambda x: x.get(sort_by, 0), reverse=True)
        return processes[:limit]

    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Collect system metrics
                metrics = {
                    "timestamp": time.time(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory": self._get_memory_usage(),
                    "disk": self._get_disk_usage(),
                    "network": psutil.net_io_counters()._asdict()
                }
                
                # Store in history
                self.resource_history[metrics["timestamp"]] = metrics
                
                # Keep only last hour of data
                cutoff_time = metrics["timestamp"] - 3600
                self.resource_history = {ts: data for ts, data in self.resource_history.items() if ts >= cutoff_time}
                
                # Check thresholds
                self._check_thresholds(metrics)
                
                # Sleep until next update
                time.sleep(self.monitoring_config["update_interval"])
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(5)  # Wait before retrying

    def _check_thresholds(self, metrics: Dict[str, Any]):
        """Check if any metrics exceed thresholds"""
        alerts = []
        
        # Check CPU
        if metrics["cpu_percent"] > self.monitoring_config["cpu_threshold"]:
            alerts.append(f"CPU usage high: {metrics['cpu_percent']}% > {self.monitoring_config['cpu_threshold']}%")
        
        # Check memory
        if metrics["memory"]["percent"] > self.monitoring_config["memory_threshold"]:
            alerts.append(f"Memory usage high: {metrics['memory']['percent']}% > {self.monitoring_config['memory_threshold']}%")
        
        # Check disk
        for mount, usage in metrics["disk"].items():
            if usage["percent"] > self.monitoring_config["disk_threshold"]:
                alerts.append(f"Disk usage high on {mount}: {usage['percent']}% > {self.monitoring_config['disk_threshold']}%")
        
        # Log alerts
        for alert in alerts:
            self.logger.warning(alert)
            # TODO: Send alert to notification system

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        return {
            "system_info": self._get_system_info(),
            "memory_usage": self._get_memory_usage(),
            "disk_usage": self._get_disk_usage(),
            "processes": self._get_process_info()
        } 