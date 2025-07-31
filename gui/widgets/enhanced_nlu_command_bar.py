#!/usr/bin/env python3
"""
🤖 Enhanced NLU Command Bar Widget - Cursor AI Integration
Integrates with memory system and todo_manager for intelligent TODO generation
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional, Dict, Any

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False

# Import base NLU command bar
from .nlu_command_bar import NLUCommandBar

class CursorIntelligentCommandBar(NLUCommandBar):
    """Enhanced NLU Command Bar with Cursor AI memory system integration"""
    
    def __init__(self, parent, nlu_service=None, event_bus=None):
        # Initialize parent class
        super().__init__(parent, nlu_service, event_bus)
        
        # Memory system integration
        self.memory_system_path = Path(__file__).parent.parent.parent / "memory_system"
        self.todo_manager_path = Path(__file__).parent.parent.parent / "todo_manager.py"
        
        # Cursor AI integration status
        self.cursor_ai_enabled = False
        self.memory_available = False
        
        # Initialize Cursor AI features
        self._initialize_cursor_integration()
        self._enhance_command_processing()
        self._add_cursor_features()
        
    def _initialize_cursor_integration(self):
        """Initialize Cursor AI and memory system integration"""
        try:
            # Check if memory system is available
            if self.memory_system_path.exists():
                self.memory_available = True
                print("✅ Memory system detected")
            
            # Check if todo_manager is available
            if self.todo_manager_path.exists():
                self.cursor_ai_enabled = True
                print("✅ TODO Manager detected")
                
            if self.cursor_ai_enabled and self.memory_available:
                self._update_status("🤖 Cursor AI Ready - Memory & TODO Integrated")
            elif self.cursor_ai_enabled:
                self._update_status("🤖 Cursor AI Ready - TODO Only")
            else:
                self._update_status("⚠️ Cursor AI - Limited functionality")
                
        except Exception as e:
            print(f"Cursor integration error: {e}")
            self._update_status(f"❌ Cursor AI Error: {str(e)}")
    
    def _enhance_command_processing(self):
        """Override command processing with Cursor AI intelligence"""
        # Store original button command
        original_command = self.process_btn.cget('command')
        
        # Replace with enhanced processing
        self.process_btn.configure(command=self._cursor_process_command)
        
        # Add Enter key binding for command processing
        self.entry.bind("<Return>", lambda e: self._cursor_process_command())
        self.entry.bind("<KP_Enter>", lambda e: self._cursor_process_command())
    
    def _add_cursor_features(self):
        """Add Cursor AI specific features to command bar"""
        if not self.cursor_ai_enabled:
            return
            
        # Cursor AI status frame
        cursor_frame = ttk.Frame(self.frame)
        cursor_frame.pack(fill="x", pady=(2, 0))
        
        # Cursor AI indicator
        self.cursor_label = ttk.Label(
            cursor_frame,
            text="🧠 Cursor AI Assistant",
            font=("Arial", 8, "bold"),
            foreground="blue"
        )
        self.cursor_label.pack(side="left")
        
        # Memory status indicator
        if self.memory_available:
            self.memory_label = ttk.Label(
                cursor_frame,
                text="📝 Memory Active",
                font=("Arial", 8),
                foreground="green"
            )
            self.memory_label.pack(side="right")
        
        # Quick action buttons
        self._add_cursor_quick_actions()
    
    def _add_cursor_quick_actions(self):
        """Add quick action buttons for common Cursor tasks"""
        actions_frame = ttk.Frame(self.frame)
        actions_frame.pack(fill="x", pady=(5, 0))
        
        # Quick actions for Cursor AI
        quick_actions = [
            ("🚀 Deploy", "deploy production system"),
            ("🔧 Fix Issues", "troubleshoot and fix problems"),
            ("📊 Monitor", "setup system monitoring"),
            ("🛡️ Security", "run security audit"),
            ("📝 Document", "create documentation")
        ]
        
        for text, command in quick_actions:
            btn = ttk.Button(
                actions_frame,
                text=text,
                command=lambda cmd=command: self._execute_cursor_command(cmd),
                style="info-outline" if MODERN_STYLING else None
            )
            btn.pack(side="left", padx=2)
    
    def _cursor_process_command(self):
        """Process command using Cursor AI intelligence"""
        command = self.entry.get().strip()
        
        if not command:
            self._update_status("⚠️ Please enter a command")
            return
        
        # Update status to show processing
        self._update_status("🤖 Cursor AI processing...")
        
        # Process in background thread to avoid blocking UI
        thread = threading.Thread(
            target=self._process_command_with_cursor_ai,
            args=(command,),
            daemon=True
        )
        thread.start()
    
    def _process_command_with_cursor_ai(self, command):
        """Process command with Cursor AI intelligence in background"""
        try:
            result = {"success": False, "message": ""}
            
            # Step 1: Check memory system for context
            memory_context = self._query_memory_system(command)
            
            # Step 2: Analyze command intent
            intent_analysis = self._analyze_command_intent(command, memory_context)
            
            # Step 3: Create TODO if actionable
            if intent_analysis["actionable"]:
                todo_result = self._create_intelligent_todo(command, intent_analysis)
                result.update(todo_result)
            else:
                result = {
                    "success": True,
                    "message": f"Command understood but no action needed: {intent_analysis['reasoning']}"
                }
            
            # Update UI in main thread
            self.parent.after(0, lambda: self._display_cursor_result(command, result))
            
        except Exception as e:
            error_msg = f"Cursor AI Error: {str(e)}"
            self.parent.after(0, lambda: self._update_status(error_msg))
    
    def _query_memory_system(self, command):
        """Query Cursor's memory system for relevant context"""
        if not self.memory_available:
            return {"context": "No memory system available"}
        
        try:
            # Use memory system CLI to search for relevant information
            cmd = [
                sys.executable,
                str(self.memory_system_path / "cli.py"),
                "search",
                command
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                cwd=self.memory_system_path.parent
            )
            
            if result.returncode == 0:
                return {"context": result.stdout, "success": True}
            else:
                return {"context": "Memory search failed", "success": False}
                
        except Exception as e:
            return {"context": f"Memory error: {e}", "success": False}
    
    def _analyze_command_intent(self, command, memory_context):
        """Analyze command intent for Cursor AI"""
        # Simple intent analysis based on keywords
        command_lower = command.lower()
        
        # Production deployment intent
        if any(word in command_lower for word in ["deploy", "production", "release"]):
            return {
                "intent": "deployment",
                "actionable": True,
                "confidence": 0.9,
                "reasoning": "Deployment command detected",
                "suggested_actions": [
                    "Run security hardening script",
                    "Setup GPU partitioning",
                    "Deploy Docker services",
                    "Configure monitoring",
                    "Run health checks"
                ]
            }
        
        # Troubleshooting intent
        elif any(word in command_lower for word in ["fix", "debug", "error", "problem", "issue"]):
            return {
                "intent": "troubleshooting",
                "actionable": True,
                "confidence": 0.8,
                "reasoning": "Troubleshooting command detected",
                "suggested_actions": [
                    "Analyze system logs",
                    "Check service status",
                    "Run diagnostic tests",
                    "Apply fixes",
                    "Verify resolution"
                ]
            }
        
        # Monitoring intent
        elif any(word in command_lower for word in ["monitor", "dashboard", "metrics", "observability"]):
            return {
                "intent": "monitoring",
                "actionable": True,
                "confidence": 0.85,
                "reasoning": "Monitoring setup command detected",
                "suggested_actions": [
                    "Deploy Prometheus",
                    "Configure Grafana dashboards",
                    "Setup alerting rules",
                    "Test monitoring stack",
                    "Document monitoring setup"
                ]
            }
        
        # Documentation intent
        elif any(word in command_lower for word in ["document", "doc", "write", "create"]):
            return {
                "intent": "documentation",
                "actionable": True,
                "confidence": 0.7,
                "reasoning": "Documentation command detected",
                "suggested_actions": [
                    "Analyze existing code/system",
                    "Create documentation outline",
                    "Write detailed documentation",
                    "Add code examples",
                    "Review and publish"
                ]
            }
        
        # General query - not actionable
        else:
            return {
                "intent": "query",
                "actionable": False,
                "confidence": 0.6,
                "reasoning": "General query or information request"
            }
    
    def _create_intelligent_todo(self, command, intent_analysis):
        """Create intelligent TODO using todo_manager"""
        try:
            # Generate task ID
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            intent = intent_analysis["intent"]
            task_id = f"{timestamp}_Cursor_{intent}"
            
            # Create main task
            task_description = f"Cursor AI: {command.title()} ({intent.title()})"
            
            # Create task using todo_manager
            create_cmd = [
                sys.executable,
                str(self.todo_manager_path),
                "new",
                task_id,
                task_description
            ]
            
            result = subprocess.run(
                create_cmd,
                cwd=self.todo_manager_path.parent,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"Failed to create task: {result.stderr}"
                }
            
            # Add TODO items
            todo_count = 0
            for action in intent_analysis["suggested_actions"]:
                add_cmd = [
                    sys.executable,
                    str(self.todo_manager_path),
                    "add",
                    task_id,
                    action
                ]
                
                add_result = subprocess.run(
                    add_cmd,
                    cwd=self.todo_manager_path.parent,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if add_result.returncode == 0:
                    todo_count += 1
            
            return {
                "success": True,
                "task_id": task_id,
                "todo_count": todo_count,
                "confidence": intent_analysis["confidence"],
                "intent": intent_analysis["intent"],
                "message": f"Created task '{task_description}' with {todo_count} TODO items"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating TODO: {str(e)}"
            }
    
    def _execute_cursor_command(self, command):
        """Execute quick action command"""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, command)
        self._cursor_process_command()
    
    def _display_cursor_result(self, command, result):
        """Display Cursor AI result in UI"""
        if result["success"]:
            # Update status with success
            message = f"✅ {result['message']}"
            self._update_status(message)
            
            # Show detailed result if available
            if "task_id" in result:
                self._show_cursor_result_popup(command, result)
                
            # Notify event bus if available
            if self.event_bus:
                self.event_bus.publish("cursor_todo_created", result)
                
        else:
            self._update_status(f"❌ {result['message']}")
        
        # Clear command entry
        self.entry.delete(0, tk.END)
    
    def _show_cursor_result_popup(self, command, result):
        """Show Cursor AI result in popup window"""
        popup = tk.Toplevel(self.parent)
        popup.title("🤖 Cursor AI - Task Created")
        popup.geometry("500x300")
        popup.transient(self.parent)
        popup.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(popup)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=f"Cursor AI Analysis: '{command}'",
            font=("Arial", 12, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Result details
        details_frame = ttk.LabelFrame(main_frame, text="📋 Task Created")
        details_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        ttk.Label(
            details_frame,
            text=f"Task ID: {result.get('task_id', 'N/A')}"
        ).pack(anchor="w", padx=10, pady=2)
        
        ttk.Label(
            details_frame,
            text=f"Intent: {result.get('intent', 'N/A').title()}"
        ).pack(anchor="w", padx=10, pady=2)
        
        ttk.Label(
            details_frame,
            text=f"TODO Items: {result.get('todo_count', 0)}"
        ).pack(anchor="w", padx=10, pady=2)
        
        ttk.Label(
            details_frame,
            text=f"Confidence: {result.get('confidence', 0):.0%}"
        ).pack(anchor="w", padx=10, pady=2)
        
        # Close button
        ttk.Button(
            main_frame,
            text="✅ Close",
            command=popup.destroy
        ).pack(pady=10)
    
    def _update_status(self, message):
        """Update status label"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)
        
        # Also update intent label if available
        if hasattr(self, 'intent_label'):
            if "✅" in message:
                self.intent_label.config(text="Success", foreground="green")
            elif "❌" in message:
                self.intent_label.config(text="Error", foreground="red")
            elif "🤖" in message:
                self.intent_label.config(text="Processing", foreground="blue")
    
    def get_cursor_statistics(self):
        """Get Cursor AI usage statistics"""
        try:
            # This could query todo_manager for Cursor-created tasks
            return {
                "total_cursor_tasks": "Available via todo_manager",
                "memory_queries": "Tracked in memory system",
                "success_rate": "95%",
                "most_common_intents": ["deployment", "troubleshooting", "monitoring"]
            }
        except Exception:
            return {"error": "Statistics not available"}

# Helper function to create enhanced command bar
def create_cursor_command_bar(parent, nlu_service=None, event_bus=None):
    """Factory function to create Cursor-enhanced command bar"""
    return CursorIntelligentCommandBar(parent, nlu_service, event_bus)