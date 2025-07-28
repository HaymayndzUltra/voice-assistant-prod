#!/usr/bin/env python3
"""
Task State Manager - Automated Task Continuity System
====================================================

Tracks completed tasks across AI sessions to prevent repetition.
Integrates with existing todo_write system and maintains persistent state.

Author: AI System Monorepo Task Continuity System
Date: July 27, 2025
"""

import json
import os
import shutil
import fcntl
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

class TaskStateManager:
    """Manages completed tasks across AI sessions"""
    
    def __init__(self, workspace_root: str = None):
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.task_state_file = self.workspace_root / "task-state.json"
        self.backup_file = self.workspace_root / "task-state.json.backup"
        self.lock_file = self.workspace_root / "task-state.json.lock"
        
        # System architecture context
        self.architecture_context = {
            "repository": "AI_System_Monorepo",
            "type": "monorepo_dual_machine",
            "mainpc_agents": 54,
            "pc2_agents": 23,
            "total_agents": 77,
            "mainpc_sot": "main_pc_code/config/startup_config.yaml",
            "pc2_sot": "pc2_code/config/startup_config.yaml"
        }
        
        self._ensure_files_exist()
    
    def _ensure_files_exist(self):
        """Create initial files if they don't exist"""
        if not self.task_state_file.exists():
            initial_state = {
                "system_info": {
                    "created_at": datetime.now().isoformat(),
                    "architecture": self.architecture_context,
                    "version": "1.0.0"
                },
                "completed_tasks": [],
                "active_tools": [],
                "pending_tasks": [],
                "session_history": []
            }
            self._safe_save(initial_state)
    
    def _safe_save(self, data: Dict[str, Any]):
        """Atomic save with backup protection"""
        temp_file = f"{self.task_state_file}.tmp"
        
        try:
            # Create backup if file exists
            if self.task_state_file.exists():
                shutil.copy2(self.task_state_file, self.backup_file)
            
            # Write to temp file
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic move
            os.rename(temp_file, self.task_state_file)
            
        except Exception as e:
            # Restore from backup if available
            if self.backup_file.exists():
                shutil.copy2(self.backup_file, self.task_state_file)
            raise Exception(f"Failed to save task state: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def _safe_load(self) -> Dict[str, Any]:
        """Load with fallback to backup"""
        try:
            with open(self.task_state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Try backup
            if self.backup_file.exists():
                try:
                    with open(self.backup_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except json.JSONDecodeError:
                    pass
            
            # Return default structure
            return {
                "system_info": {
                    "created_at": datetime.now().isoformat(),
                    "architecture": self.architecture_context,
                    "version": "1.0.0"
                },
                "completed_tasks": [],
                "active_tools": [],
                "pending_tasks": [],
                "session_history": []
            }
    
    def with_file_lock(self, operation):
        """Execute operation with file locking"""
        try:
            with open(self.lock_file, 'w') as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return operation()
        except IOError:
            raise Exception("Another session is currently updating task state")
        finally:
            if self.lock_file.exists():
                os.remove(self.lock_file)
    
    def store_completed_task(self, 
                           task_id: str,
                           title: str, 
                           user_request: str = "",
                           impact: str = "",
                           tools_created: List[str] = None,
                           solution_summary: str = "",
                           session_id: str = None) -> bool:
        """Store a completed task"""
        
        def _store():
            data = self._safe_load()
            
            # Check if task already exists
            for task in data["completed_tasks"]:
                if task["id"] == task_id:
                    return False  # Already stored
            
            completed_task = {
                "id": task_id,
                "title": title,
                "user_request": user_request,
                "completed_date": datetime.now().date().isoformat(),
                "completed_time": datetime.now().isoformat(),
                "session_id": session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "impact": impact,
                "tools_created": tools_created or [],
                "solution_summary": solution_summary,
                "status": "completed"
            }
            
            data["completed_tasks"].append(completed_task)
            
            # Add tools to active tools list
            for tool in (tools_created or []):
                if tool not in [t["name"] for t in data["active_tools"]]:
                    data["active_tools"].append({
                        "name": tool,
                        "created_for": task_id,
                        "created_date": datetime.now().date().isoformat(),
                        "status": "available"
                    })
            
            self._safe_save(data)
            return True
        
        return self.with_file_lock(_store)
    
    def add_pending_task(self, task_id: str, title: str, explanation: str, user_request: str = ""):
        """Add a pending task"""
        
        def _add():
            data = self._safe_load()
            
            # Check if already exists
            for task in data["pending_tasks"]:
                if task["id"] == task_id:
                    return False
            
            pending_task = {
                "id": task_id,
                "title": title,
                "explanation": explanation,
                "user_request": user_request,
                "added_date": datetime.now().date().isoformat(),
                "priority": "normal",
                "status": "pending"
            }
            
            data["pending_tasks"].append(pending_task)
            self._safe_save(data)
            return True
        
        return self.with_file_lock(_add)
    
    def remove_pending_task(self, task_id: str):
        """Remove a pending task (when completed)"""
        
        def _remove():
            data = self._safe_load()
            data["pending_tasks"] = [t for t in data["pending_tasks"] if t["id"] != task_id]
            self._safe_save(data)
        
        return self.with_file_lock(_remove)
    
    def is_task_completed(self, task_id: str) -> bool:
        """Check if a task is already completed"""
        data = self._safe_load()
        return any(task["id"] == task_id for task in data["completed_tasks"])
    
    def get_completed_tasks(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get recent completed tasks"""
        data = self._safe_load()
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date()
        
        recent_tasks = []
        for task in data["completed_tasks"]:
            task_date = datetime.fromisoformat(task["completed_date"]).date()
            if task_date >= cutoff_date:
                recent_tasks.append(task)
        
        return sorted(recent_tasks, key=lambda x: x["completed_date"], reverse=True)
    
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get all pending tasks with explanations"""
        data = self._safe_load()
        return data["pending_tasks"]
    
    def get_active_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools created in previous sessions"""
        data = self._safe_load()
        
        # Validate tools still exist
        validated_tools = []
        for tool in data["active_tools"]:
            tool_path = self.workspace_root / tool["name"]
            if tool_path.exists():
                validated_tools.append(tool)
            else:
                tool["status"] = "missing"
                validated_tools.append(tool)
        
        return validated_tools
    
    def get_session_summary(self) -> str:
        """Generate session startup summary"""
        data = self._safe_load()
        recent_tasks = self.get_completed_tasks(days_back=7)
        pending_tasks = self.get_pending_tasks()
        active_tools = self.get_active_tools()
        
        summary = "🚀 AI SYSTEM SESSION STARTUP\n"
        summary += "=" * 50 + "\n\n"
        
        # Architecture context
        arch = data["system_info"]["architecture"]
        summary += f"🏗️ SYSTEM ARCHITECTURE:\n"
        summary += f"  • Repository: {arch['repository']}\n"
        summary += f"  • Type: {arch['type']}\n"
        summary += f"  • MainPC: {arch['mainpc_agents']} agents (SOT: {arch['mainpc_sot']})\n"
        summary += f"  • PC2: {arch['pc2_agents']} agents (SOT: {arch['pc2_sot']})\n"
        summary += f"  • Total: {arch['total_agents']} agents\n\n"
        
        # Recent completions
        if recent_tasks:
            summary += "✅ RECENT COMPLETIONS (Last 7 days):\n"
            for task in recent_tasks[:5]:  # Show max 5 recent
                summary += f"  • {task['title']} ({task['completed_date']})\n"
                if task['impact']:
                    summary += f"    Impact: {task['impact']}\n"
            summary += "\n"
        
        # Pending tasks
        if pending_tasks:
            summary += "⏳ PENDING TASKS:\n"
            for task in pending_tasks:
                summary += f"  📌 {task['title']}\n"
                summary += f"     {task['explanation']}\n"
            summary += "\n"
        else:
            summary += "✅ NO PENDING TASKS\n\n"
        
        # Available tools
        available_tools = [t for t in active_tools if t["status"] == "available"]
        if available_tools:
            summary += "🔧 AVAILABLE TOOLS:\n"
            for tool in available_tools:
                summary += f"  • {tool['name']} (created for: {tool['created_for']})\n"
            summary += "\n"
        
        summary += "💡 Ready for new tasks! Context loaded from previous sessions.\n"
        
        return summary 