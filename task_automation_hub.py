#!/usr/bin/env python3
"""
Task Automation Hub - Central Integration Controller
===================================================

Integrates all task continuity components for full automation.
Hooks into AI actions and provides seamless task tracking.

Author: AI System Monorepo Task Continuity System
Date: July 27, 2025  
"""

import json
import os
import sys
import threading
import atexit
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

# Import our components
from task_state_manager import TaskStateManager
from session_action_logger import SessionActionLogger
from todo_completion_detector import TodoCompletionDetector

class TaskAutomationHub:
    """Central hub for automatic task continuity"""
    
    def __init__(self):
        self.tsm = TaskStateManager()
        self.current_logger: Optional[SessionActionLogger] = None
        self.todo_detector = TodoCompletionDetector()
        self.active_task_id: Optional[str] = None
        self.lock = threading.Lock()
        
        # Register for cleanup
        atexit.register(self.cleanup)
        
        # Check for session recovery
        self._check_session_recovery()
    
    def _check_session_recovery(self):
        """Check if there's an interrupted session to recover"""
        
        recovery_data = SessionActionLogger.get_interrupted_session()
        if recovery_data:
            print("🔄 INTERRUPTED SESSION DETECTED!")
            print(SessionActionLogger.generate_recovery_summary(recovery_data))
            print("\n💡 Use start_task_recovery() to continue or start_new_task() for fresh start")
    
    def start_new_task(self, task_id: str, title: str, planned_steps: List[str] = None) -> SessionActionLogger:
        """Start a new task with automatic tracking"""
        
        with self.lock:
            # Clean up any previous logger
            if self.current_logger:
                self.current_logger.mark_task_complete("Starting new task")
            
            # Clear any existing recovery session
            SessionActionLogger.cleanup_completed_session()
            
            # Create new logger
            self.current_logger = SessionActionLogger(task_id)
            self.active_task_id = task_id
            
            if planned_steps:
                self.current_logger.set_planned_steps(planned_steps)
            
            print(f"🚀 Started task tracking: {title}")
            print(f"📋 Task ID: {task_id}")
            
            return self.current_logger
    
    def start_task_recovery(self) -> Optional[SessionActionLogger]:
        """Continue from interrupted session"""
        
        recovery_data = SessionActionLogger.get_interrupted_session()
        if not recovery_data:
            print("❌ No interrupted session found")
            return None
        
        with self.lock:
            task_id = recovery_data.get("task_id", "recovered_task")
            
            # Create new logger with recovery context
            self.current_logger = SessionActionLogger(task_id)
            self.active_task_id = task_id
            
            # Restore planning context
            planned_steps = recovery_data.get("next_planned_steps", [])
            completed_count = len(recovery_data.get("completed_steps", []))
            
            if planned_steps and completed_count < len(planned_steps):
                remaining_steps = planned_steps[completed_count:]
                self.current_logger.set_planned_steps(remaining_steps)
            
            print(f"🔄 Resumed task: {task_id}")
            print(f"📊 Continuing from step {completed_count + 1}")
            
            return self.current_logger
    
    def log_action(self, action: str, tool_used: str = "", result: str = "", success: bool = True):
        """Log an action with automatic tracking"""
        
        if not self.current_logger:
            # Auto-start general session if none exists
            self.current_logger = SessionActionLogger("auto_session")
            self.active_task_id = "auto_session"
        
        self.current_logger.log_action(action, tool_used, result, success)
    
    def auto_detect_and_log_todo_completion(self, todo_data: Dict[str, Any]) -> bool:
        """Automatically process todo completion and update task state"""
        
        # Process through todo detector
        was_processed = self.todo_detector.process_todo_completion(todo_data)
        
        if was_processed:
            # If we have an active logger, mark this as a step
            if self.current_logger:
                self.current_logger.log_action(
                    action=f"completed_todo_{todo_data.get('id', 'unknown')}",
                    result=f"Todo '{todo_data.get('content', '')}' marked complete",
                    success=True
                )
        
        return was_processed
    
    def hook_todo_write_tool(self, original_todo_write_func: Callable) -> Callable:
        """Create a wrapper for todo_write tool that auto-detects completions"""
        
        def wrapped_todo_write(*args, **kwargs):
            # Call original function
            result = original_todo_write(*args, **kwargs)
            
            # Extract todo data from arguments
            try:
                # Assume first argument is merge flag, second is todos list
                if len(args) >= 2:
                    todos = args[1]
                elif 'todos' in kwargs:
                    todos = kwargs['todos']
                else:
                    return result
                
                # Process each todo for completion detection
                for todo in todos:
                    if todo.get('status') == 'completed':
                        self.auto_detect_and_log_todo_completion(todo)
                        
            except Exception as e:
                print(f"⚠️  Warning: Could not process todo completion: {e}")
            
            return result
        
        return wrapped_todo_write
    
    def hook_tool_execution(self, tool_name: str, parameters: Dict[str, Any], result: Any) -> Any:
        """Hook for any tool execution to auto-log actions"""
        
        # Extract meaningful info from tool execution
        action_desc = self._generate_action_description(tool_name, parameters)
        result_desc = self._extract_result_summary(result)
        success = self._determine_success(result)
        
        # Log the action
        self.log_action(action_desc, tool_name, result_desc, success)
        
        return result
    
    def _generate_action_description(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Generate human-readable action description"""
        
        # Tool-specific descriptions
        tool_descriptions = {
            'run_terminal_cmd': lambda p: f"executed command: {p.get('command', 'unknown')[:50]}",
            'edit_file': lambda p: f"edited file: {p.get('target_file', 'unknown')}",
            'read_file': lambda p: f"read file: {p.get('target_file', 'unknown')}",
            'create_file': lambda p: f"created file: {p.get('target_file', 'unknown')}",
            'grep_search': lambda p: f"searched for: {p.get('query', 'unknown')[:30]}",
            'codebase_search': lambda p: f"searched codebase: {p.get('query', 'unknown')[:50]}",
            'list_dir': lambda p: f"listed directory: {p.get('relative_workspace_path', '.')}",
            'file_search': lambda p: f"searched files: {p.get('query', 'unknown')[:30]}"
        }
        
        if tool_name in tool_descriptions:
            try:
                return tool_descriptions[tool_name](parameters)
            except Exception:
                pass
        
        # Default description
        return f"used tool: {tool_name}"
    
    def _extract_result_summary(self, result: Any) -> str:
        """Extract meaningful summary from tool result"""
        
        if isinstance(result, dict):
            # Look for common result fields
            if 'output' in result:
                output = str(result['output'])
                return output[:100] + ('...' if len(output) > 100 else '')
            elif 'content' in result:
                content = str(result['content'])
                return f"Content: {content[:50]}" + ('...' if len(content) > 50 else '')
            elif 'message' in result:
                return str(result['message'])[:100]
            elif 'error' in result:
                return f"Error: {result['error']}"
        
        elif isinstance(result, str):
            return result[:100] + ('...' if len(result) > 100 else '')
        
        return "Completed successfully"
    
    def _determine_success(self, result: Any) -> bool:
        """Determine if the action was successful"""
        
        if isinstance(result, dict):
            # Check for explicit success/error indicators
            if 'success' in result:
                return bool(result['success'])
            elif 'error' in result:
                return False
            elif 'status' in result:
                return result['status'] in ['success', 'ok', 'completed']
        
        # Default to success if no error indicators
        return True
    
    def complete_current_task(self, result: str = "", impact: str = "", tools_created: List[str] = None):
        """Mark current task as completed and store in task state"""
        
        if not self.current_logger:
            print("⚠️  No active task to complete")
            return
        
        task_id = self.active_task_id
        
        # Mark session complete
        self.current_logger.mark_task_complete(result)
        
        # Extract info for task state storage
        session_data = self.current_logger.session_data
        
        # Store in persistent task state
        self.tsm.store_completed_task(
            task_id=task_id,
            title=task_id.replace('_', ' ').title(),
            impact=impact or self._generate_impact_summary(session_data),
            tools_created=tools_created or self._extract_tools_from_session(session_data),
            solution_summary=result,
            session_id=session_data.get("session_id", "unknown")
        )
        
        # Clean up
        SessionActionLogger.cleanup_completed_session()
        self.current_logger = None
        self.active_task_id = None
        
        print(f"🎉 Task '{task_id}' completed and stored permanently!")
    
    def _generate_impact_summary(self, session_data: Dict[str, Any]) -> str:
        """Generate impact summary from session data"""
        
        steps = len(session_data.get("completed_steps", []))
        tools_used = len(session_data.get("tools_used", []))
        files_modified = len(session_data.get("files_modified", []))
        
        impact_parts = []
        if steps > 0:
            impact_parts.append(f"{steps} actions completed")
        if tools_used > 0:
            impact_parts.append(f"{tools_used} tools utilized")
        if files_modified > 0:
            impact_parts.append(f"{files_modified} files modified")
        
        return ', '.join(impact_parts) if impact_parts else "Task completed successfully"
    
    def _extract_tools_from_session(self, session_data: Dict[str, Any]) -> List[str]:
        """Extract created tools from session data"""
        
        files_modified = session_data.get("files_modified", [])
        tool_files = []
        
        for file_path in files_modified:
            filename = os.path.basename(file_path)
            
            # Check if it looks like a tool
            if (filename.endswith(('.sh', '.py', '.ps1', '.bat')) or 
                'script' in filename.lower() or 
                'tool' in filename.lower() or
                'setup' in filename.lower() or
                'cleanup' in filename.lower()):
                tool_files.append(filename)
        
        return tool_files
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current automation status"""
        
        status = {
            "active_task": self.active_task_id,
            "logger_active": self.current_logger is not None,
            "recovery_available": SessionActionLogger.get_interrupted_session() is not None
        }
        
        if self.current_logger:
            session_data = self.current_logger.session_data
            status.update({
                "steps_completed": len(session_data.get("completed_steps", [])),
                "tools_used": len(session_data.get("tools_used", [])),
                "files_modified": len(session_data.get("files_modified", [])),
                "last_action": session_data.get("last_action_time", "unknown")
            })
        
        return status
    
    def cleanup(self):
        """Cleanup on exit"""
        if self.current_logger and self.current_logger.session_data.get("status") == "in_progress":
            self.current_logger.mark_session_interrupted("Application exit")

# Global automation hub instance
automation_hub = TaskAutomationHub()

# Convenience functions for easy integration
def start_task(task_id: str, title: str = "", planned_steps: List[str] = None) -> SessionActionLogger:
    """Start a new task with tracking"""
    return automation_hub.start_new_task(task_id, title or task_id.replace('_', ' ').title(), planned_steps)

def log_action(action: str, tool_used: str = "", result: str = "", success: bool = True):
    """Log an action"""
    automation_hub.log_action(action, tool_used, result, success)

def complete_task(result: str = "", impact: str = "", tools_created: List[str] = None):
    """Complete current task"""
    automation_hub.complete_current_task(result, impact, tools_created)

def continue_interrupted_task() -> Optional[SessionActionLogger]:
    """Continue from interrupted session"""
    return automation_hub.start_task_recovery()

def get_status() -> Dict[str, Any]:
    """Get automation status"""
    return automation_hub.get_current_status()

# Example integration
if __name__ == "__main__":
    print("🤖 Task Automation Hub - Testing")
    
    # Start a test task
    logger = start_task("test_automation", "Test Automation System", [
        "initialize_system",
        "run_tests", 
        "verify_results"
    ])
    
    # Log some actions
    log_action("initialize_system", "setup.py", "System initialized", True)
    log_action("run_tests", "pytest", "All tests passed", True)
    log_action("verify_results", "manual_check", "Results verified", True)
    
    # Complete task
    complete_task("Test automation system working correctly", 
                  "Full automation pipeline verified", 
                  ["task_automation_hub.py"])
    
    print(f"\n📊 Final status: {get_status()}") 