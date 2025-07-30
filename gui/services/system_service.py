"""
🎯 Modern GUI Control Center - System Service Integration

This module provides system integration services for the GUI application,
connecting to the autonomous task queue system, agent management, memory
intelligence, and monitoring systems.
"""

import json
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import subprocess
import sys
import asyncio
from gui.services.async_runner import AsyncRunner, RunResult
from gui.services.event_bus import EventBus
from watchdog.observers import Observer  # type: ignore
from watchdog.events import FileSystemEventHandler  # type: ignore


class SystemService:
    """Main system service for GUI integration"""
    
    def __init__(self, tk_root=None):
        """Initialize system service"""
        self.project_root = Path(__file__).parent.parent.parent
        self.memory_bank = self.project_root / "memory-bank"
        self.queue_system = self.memory_bank / "queue-system"
        
        # State
        self._running = True
        self._last_update = None
        self._system_health = {}
        self._cached_data = {}
        
        # Event bus
        self.bus = EventBus(tk_root) if tk_root is not None else None

        # Initialize services
        self._initialize_paths()
        self._update_system_health()

        # Start file watchers
        self._start_watchers()

    def _initialize_paths(self):
        """Initialize required paths"""
        try:
            # Ensure required directories exist
            self.memory_bank.mkdir(exist_ok=True)
            self.queue_system.mkdir(exist_ok=True)
            
            # Ensure required files exist
            self._ensure_file_exists(self.queue_system / "tasks_active.json", [])
            self._ensure_file_exists(self.queue_system / "tasks_queue.json", [])
            self._ensure_file_exists(self.queue_system / "tasks_done.json", [])
            self._ensure_file_exists(self.queue_system / "tasks_interrupted.json", [])
            
        except Exception as e:
            print(f"⚠️ Error initializing paths: {e}")
    
    def _ensure_file_exists(self, file_path: Path, default_content: Any):
        """Ensure a file exists with default content"""
        try:
            if not file_path.exists():
                with open(file_path, 'w') as f:
                    json.dump(default_content, f, indent=2)
        except Exception as e:
            print(f"⚠️ Error creating file {file_path}: {e}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        try:
            health_data = {
                "overall_status": "healthy",
                "components": {},
                "last_check": datetime.now().isoformat(),
                "issues": [],
                "warnings": []
            }
            
            # Check task queue system
            queue_health = self._check_queue_system_health()
            health_data["components"]["task_queue"] = queue_health
            
            # Check agent system
            agent_health = self._check_agent_system_health()
            health_data["components"]["agents"] = agent_health
            
            # Check memory system
            memory_health = self._check_memory_system_health()
            health_data["components"]["memory"] = memory_health
            
            # Check CLI system
            cli_health = self._check_cli_system_health()
            health_data["components"]["cli"] = cli_health
            
            # Determine overall status
            component_statuses = [comp["status"] for comp in health_data["components"].values()]
            
            if any(status == "error" for status in component_statuses):
                health_data["overall_status"] = "error"
            elif any(status == "warning" for status in component_statuses):
                health_data["overall_status"] = "warning"
            else:
                health_data["overall_status"] = "healthy"
            
            # Collect issues and warnings
            for component, data in health_data["components"].items():
                if data.get("issues"):
                    health_data["issues"].extend([f"{component}: {issue}" for issue in data["issues"]])
                if data.get("warnings"):
                    health_data["warnings"].extend([f"{component}: {warning}" for warning in data["warnings"]])
            
            self._system_health = health_data
            return health_data
            
        except Exception as e:
            return {
                "overall_status": "error",
                "components": {},
                "last_check": datetime.now().isoformat(),
                "issues": [f"System health check failed: {e}"],
                "warnings": []
            }
    
    def _check_queue_system_health(self) -> Dict[str, Any]:
        """Check task queue system health"""
        try:
            health = {
                "status": "healthy",
                "issues": [],
                "warnings": [],
                "metrics": {}
            }
            
            # Check if queue files exist and are readable
            queue_files = [
                "tasks_active.json",
                "tasks_queue.json", 
                "tasks_done.json",
                "tasks_interrupted.json"
            ]
            
            for file_name in queue_files:
                file_path = self.queue_system / file_name
                if not file_path.exists():
                    health["issues"].append(f"Missing queue file: {file_name}")
                    health["status"] = "error"
                else:
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            health["metrics"][file_name] = len(data) if isinstance(data, list) else 1
                    except Exception as e:
                        health["issues"].append(f"Cannot read {file_name}: {e}")
                        health["status"] = "error"
            
            return health
            
        except Exception as e:
            return {
                "status": "error",
                "issues": [f"Queue system check failed: {e}"],
                "warnings": [],
                "metrics": {}
            }
    
    def _check_agent_system_health(self) -> Dict[str, Any]:
        """Check agent system health"""
        try:
            health = {
                "status": "healthy", 
                "issues": [],
                "warnings": [],
                "metrics": {}
            }
            
            # Check for agent scan results
            scan_results_file = self.memory_bank / "agent-scan-results.json"
            if scan_results_file.exists():
                try:
                    with open(scan_results_file, 'r') as f:
                        scan_data = json.load(f)
                        health["metrics"]["total_agents"] = scan_data.get("summary", {}).get("total_agents", 0)
                        health["metrics"]["total_directories"] = scan_data.get("summary", {}).get("total_directories", 0)
                        
                        # Check for critical issues from scan
                        if scan_data.get("summary", {}).get("critical_issues", 0) > 0:
                            health["warnings"].append("Critical issues found in agent scan")
                            health["status"] = "warning"
                            
                except Exception as e:
                    health["warnings"].append(f"Cannot read agent scan results: {e}")
                    health["status"] = "warning"
            else:
                health["warnings"].append("No agent scan results found")
                health["status"] = "warning"
            
            return health
            
        except Exception as e:
            return {
                "status": "error",
                "issues": [f"Agent system check failed: {e}"],
                "warnings": [],
                "metrics": {}
            }
    
    def _check_memory_system_health(self) -> Dict[str, Any]:
        """Check memory system health"""
        try:
            health = {
                "status": "healthy",
                "issues": [],
                "warnings": [],
                "metrics": {}
            }
            
            # Check CLI system
            cli_file = self.project_root / "memory_system" / "cli.py"
            if cli_file.exists():
                health["metrics"]["cli_available"] = True
            else:
                health["issues"].append("Memory system CLI not found")
                health["status"] = "error"
            
            # Check memory bank structure
            memory_dirs = ["project-brain", "architecture-plans", "queue-system"]
            for dir_name in memory_dirs:
                dir_path = self.memory_bank / dir_name
                if dir_path.exists():
                    health["metrics"][f"{dir_name}_available"] = True
                else:
                    health["warnings"].append(f"Memory directory missing: {dir_name}")
                    if health["status"] == "healthy":
                        health["status"] = "warning"
            
            return health
            
        except Exception as e:
            return {
                "status": "error",
                "issues": [f"Memory system check failed: {e}"],
                "warnings": [],
                "metrics": {}
            }
    
    def _check_cli_system_health(self) -> Dict[str, Any]:
        """Check CLI system health"""
        try:
            health = {
                "status": "healthy",
                "issues": [],
                "warnings": [],
                "metrics": {}
            }
            
            # Test CLI availability
            try:
                result = subprocess.run(
                    [sys.executable, "memory_system/cli.py", "--help"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    health["metrics"]["cli_responsive"] = True
                else:
                    health["warnings"].append("CLI not responsive")
                    health["status"] = "warning"
                    
            except subprocess.TimeoutExpired:
                health["warnings"].append("CLI response timeout")
                health["status"] = "warning"
            except Exception as e:
                health["issues"].append(f"CLI test failed: {e}")
                health["status"] = "error"
            
            return health
            
        except Exception as e:
            return {
                "status": "error",
                "issues": [f"CLI system check failed: {e}"],
                "warnings": [],
                "metrics": {}
            }
    
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get currently active tasks"""
        try:
            active_tasks_file = self.queue_system / "tasks_active.json"
            if active_tasks_file.exists():
                with open(active_tasks_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading active tasks: {e}")
            return []
    
    def get_task_queue(self) -> List[Dict[str, Any]]:
        """Get queued tasks"""
        try:
            queue_file = self.queue_system / "tasks_queue.json"
            if queue_file.exists():
                with open(queue_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading task queue: {e}")
            return []
    
    def get_completed_tasks(self) -> List[Dict[str, Any]]:
        """Get completed tasks"""
        try:
            done_file = self.queue_system / "tasks_done.json"
            if done_file.exists():
                with open(done_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"Error loading completed tasks: {e}")
            return []
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get agent system status"""
        try:
            scan_results_file = self.memory_bank / "agent-scan-results.json"
            if scan_results_file.exists():
                with open(scan_results_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading agent status: {e}")
            return {}
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get memory system status"""
        try:
            # Get project brain status
            brain_dir = self.memory_bank / "project-brain"
            brain_files = list(brain_dir.rglob("*.md")) if brain_dir.exists() else []
            
            # Get architecture plans
            arch_dir = self.memory_bank / "architecture-plans"
            arch_files = list(arch_dir.glob("*.json")) if arch_dir.exists() else []
            
            return {
                "brain_files": len(brain_files),
                "architecture_plans": len(arch_files),
                "last_update": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error loading memory status: {e}")
            return {}
    
    def execute_cli_command(self, command: str) -> Dict[str, Any]:
        """Execute a CLI command and return results"""
        try:
            cmd_parts = command.split()
            full_cmd = [sys.executable, "memory_system/cli.py"] + cmd_parts
            
            result = subprocess.run(
                full_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timeout",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": -1
            }

    # ------------------------------------------------------------------
    # Async variant using AsyncRunner
    # ------------------------------------------------------------------
    async def async_execute_cli(self, command: str) -> Dict[str, Any]:
        """Async version suitable for non-blocking calls from views."""
        cmd_parts = command.split()
        full_cmd = [sys.executable, "memory_system/cli.py"] + cmd_parts

        result: RunResult = await AsyncRunner().run(*full_cmd, cwd=self.project_root, timeout=60)

        return {
            "success": result.success,
            "output": result.stdout,
            "error": result.stderr,
            "return_code": result.returncode,
        }
    
    def _update_system_health(self):
        """Update system health in background"""
        def update_loop():
            while self._running:
                try:
                    self.get_system_health()
                    time.sleep(30)  # Update every 30 seconds
                except Exception as e:
                    print(f"Health update error: {e}")
                    time.sleep(60)  # Wait longer on error
        
        # Start background thread
        health_thread = threading.Thread(target=update_loop, daemon=True)
        health_thread.start()

    # ------------------------------------------------------------------
    # Watchdog integration
    # ------------------------------------------------------------------
    def _start_watchers(self):
        if self.bus is None:
            return  # need tk_root for safe callbacks

        class _Handler(FileSystemEventHandler):
            def __init__(self, parent):
                self.parent = parent

            def on_modified(self, event):
                if event.is_directory:
                    return
                path = Path(event.src_path)
                if path.name.startswith("tasks_") and path.suffix == ".json":
                    self.parent.bus.publish("tasks_updated")
                elif path.name == "agent-scan-results.json":
                    self.parent.bus.publish("agent_status_changed")

        handler = _Handler(self)
        observer = Observer()
        observer.schedule(handler, str(self.queue_system), recursive=False)
        observer.schedule(handler, str(self.memory_bank), recursive=False)
        observer.daemon = True
        observer.start()
    
    def stop(self):
        """Stop the system service"""
        self._running = False
