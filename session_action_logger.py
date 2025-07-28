#!/usr/bin/env python3
"""
Session Action Logger - Real-time Progress Tracking
===================================================

Logs every action in real-time for disconnect recovery.
Enables session resumption from exact interruption point.

Author: AI System Monorepo Task Continuity System  
Date: July 27, 2025
"""

import json
import os
import time
import atexit
import signal
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

class SessionActionLogger:
    """Real-time session progress tracking"""
    
    def __init__(self, task_id: str = None):
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.task_id = task_id or "general_session"
        self.progress_file = Path("session-progress.json")
        self.backup_file = Path("session-progress.json.backup")
        
        # Initialize session
        self.session_data = {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "start_time": datetime.now().isoformat(),
            "last_action_time": datetime.now().isoformat(),
            "status": "in_progress",
            "completed_steps": [],
            "next_planned_steps": [],
            "current_state": {},
            "tools_used": [],
            "files_modified": []
        }
        
        self._save_progress()
        self._setup_cleanup_handlers()
    
    def _setup_cleanup_handlers(self):
        """Setup handlers for graceful session termination"""
        atexit.register(self._cleanup_session)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle interruption signals"""
        self.mark_session_interrupted(f"Signal {signum} received")
        exit(0)
    
    def _save_progress(self):
        """Atomic save of session progress"""
        temp_file = f"{self.progress_file}.tmp"
        
        try:
            # Create backup
            if self.progress_file.exists():
                self.progress_file.rename(self.backup_file)
            
            # Write to temp file
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2, ensure_ascii=False)
            
            # Atomic move
            Path(temp_file).rename(self.progress_file)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not save session progress: {e}")
            # Try to restore backup
            if self.backup_file.exists():
                self.backup_file.rename(self.progress_file)
        finally:
            # Clean up temp file
            if Path(temp_file).exists():
                Path(temp_file).unlink()
    
    def log_action(self, action: str, tool_used: str = "", result: str = "", success: bool = True):
        """Log an action in real-time"""
        
        step_data = {
            "step": len(self.session_data["completed_steps"]) + 1,
            "action": action,
            "result": result[:200] if result else "",  # Limit result length
            "timestamp": datetime.now().isoformat(),
            "tool_used": tool_used,
            "success": success,
            "duration_ms": 0  # Can be calculated if needed
        }
        
        self.session_data["completed_steps"].append(step_data)
        self.session_data["last_action_time"] = datetime.now().isoformat()
        
        # Track tools used
        if tool_used and tool_used not in self.session_data["tools_used"]:
            self.session_data["tools_used"].append(tool_used)
        
        # Auto-detect file modifications
        self._detect_file_changes()
        
        # Save immediately for disconnect safety
        self._save_progress()
        
        # Print real-time feedback
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} Step {step_data['step']}: {action}")
        
    def _detect_file_changes(self):
        """Auto-detect recent file modifications"""
        
        cutoff_time = time.time() - 300  # Last 5 minutes
        recent_files = []
        
        for root, dirs, files in os.walk('.'):
            # Skip hidden and system directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                if file.startswith('.'):
                    continue
                    
                filepath = os.path.join(root, file)
                try:
                    if os.path.getmtime(filepath) > cutoff_time:
                        relative_path = os.path.relpath(filepath)
                        if relative_path not in self.session_data["files_modified"]:
                            recent_files.append(relative_path)
                except OSError:
                    continue
        
        # Add new files to tracking
        self.session_data["files_modified"].extend(recent_files)
        
        # Keep only last 50 files
        if len(self.session_data["files_modified"]) > 50:
            self.session_data["files_modified"] = self.session_data["files_modified"][-50:]
    
    def set_planned_steps(self, steps: List[str]):
        """Set the planned steps for this session"""
        self.session_data["next_planned_steps"] = steps
        self._save_progress()
        
        print(f"📋 Planned steps: {len(steps)} total")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step}")
    
    def update_current_state(self, state_updates: Dict[str, Any]):
        """Update current system state"""
        self.session_data["current_state"].update(state_updates)
        self._save_progress()
    
    def mark_task_complete(self, result: str = ""):
        """Mark the entire task as completed"""
        self.session_data["status"] = "completed"
        self.session_data["end_time"] = datetime.now().isoformat()
        self.session_data["final_result"] = result
        self._save_progress()
        
        print(f"🎉 Task completed: {self.task_id}")
        print(f"📊 Total steps: {len(self.session_data['completed_steps'])}")
        print(f"🔧 Tools used: {len(self.session_data['tools_used'])}")
        print(f"📁 Files modified: {len(self.session_data['files_modified'])}")
    
    def mark_session_interrupted(self, reason: str = ""):
        """Mark session as interrupted (for disconnect recovery)"""
        self.session_data["status"] = "interrupted"
        self.session_data["interruption_time"] = datetime.now().isoformat()
        self.session_data["interruption_reason"] = reason
        self._save_progress()
        
        print(f"⚠️  Session interrupted: {reason}")
        print(f"💾 Progress saved for recovery")
    
    def _cleanup_session(self):
        """Called on normal session end"""
        if self.session_data["status"] == "in_progress":
            self.mark_session_interrupted("Normal session end")
    
    @classmethod
    def get_interrupted_session(cls) -> Optional[Dict[str, Any]]:
        """Load interrupted session for recovery"""
        
        progress_file = Path("session-progress.json")
        if not progress_file.exists():
            return None
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get("status") in ["in_progress", "interrupted"]:
                return data
                
        except (json.JSONDecodeError, FileNotFoundError):
            # Try backup
            backup_file = Path("session-progress.json.backup")
            if backup_file.exists():
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    if data.get("status") in ["in_progress", "interrupted"]:
                        return data
                except json.JSONDecodeError:
                    pass
        
        return None
    
    @classmethod
    def generate_recovery_summary(cls, session_data: Dict[str, Any]) -> str:
        """Generate human-readable recovery summary"""
        
        task_id = session_data.get("task_id", "Unknown")
        completed_steps = session_data.get("completed_steps", [])
        planned_steps = session_data.get("next_planned_steps", [])
        last_action = session_data.get("last_action_time", "Unknown")
        tools_used = session_data.get("tools_used", [])
        files_modified = session_data.get("files_modified", [])
        
        summary = f"🔄 SESSION RECOVERY AVAILABLE\n"
        summary += f"=" * 40 + "\n"
        summary += f"📋 Task: {task_id}\n"
        summary += f"🕒 Last action: {last_action}\n"
        summary += f"📊 Progress: {len(completed_steps)} steps completed\n\n"
        
        if completed_steps:
            summary += "✅ COMPLETED STEPS:\n"
            for step in completed_steps[-5:]:  # Show last 5 steps
                status_icon = "✅" if step.get("success", True) else "❌"
                summary += f"  {status_icon} {step.get('action', 'Unknown action')}\n"
            
            if len(completed_steps) > 5:
                summary += f"  ... and {len(completed_steps) - 5} more steps\n"
            summary += "\n"
        
        if planned_steps:
            completed_count = len(completed_steps)
            remaining_steps = planned_steps[completed_count:] if completed_count < len(planned_steps) else []
            
            if remaining_steps:
                summary += "📋 REMAINING STEPS:\n"
                for i, step in enumerate(remaining_steps[:5], completed_count + 1):
                    summary += f"  {i}. {step}\n"
                summary += "\n"
        
        if tools_used:
            summary += f"🔧 Tools used: {', '.join(tools_used)}\n"
        
        if files_modified:
            summary += f"📁 Files modified: {len(files_modified)} files\n"
        
        summary += "\n💡 Ready to continue from interruption point!"
        
        return summary
    
    @classmethod
    def cleanup_completed_session(cls):
        """Remove completed session files"""
        
        files_to_remove = [
            "session-progress.json",
            "session-progress.json.backup"
        ]
        
        for filename in files_to_remove:
            filepath = Path(filename)
            if filepath.exists():
                filepath.unlink()
                
        print("🧹 Cleaned up completed session files")

# Example usage
if __name__ == "__main__":
    # Test the logger
    logger = SessionActionLogger("test_task")
    
    logger.set_planned_steps([
        "check_system_status",
        "deploy_containers", 
        "verify_connectivity"
    ])
    
    logger.log_action("check_system_status", "docker ps", "All systems running", True)
    logger.log_action("deploy_containers", "docker-compose up", "Containers started", True)
    
    # Simulate task completion
    logger.mark_task_complete("Test task completed successfully")
    
    print("\n" + "="*50)
    print("Recovery test:")
    
    # Test recovery
    recovery_data = SessionActionLogger.get_interrupted_session()
    if recovery_data:
        print(SessionActionLogger.generate_recovery_summary(recovery_data))
    else:
        print("No interrupted session found") 