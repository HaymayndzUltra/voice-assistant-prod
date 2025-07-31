#!/usr/bin/env python3
"""
🧠 Memory-Integrated Command Bar Widget - Proper Integration
Integrates with existing memory_system architecture and todo_manager
"""

import tkinter as tk
from tkinter import ttk
import threading
import subprocess
import sys
import os
from pathlib import Path
from typing import Callable, Optional, Dict, Any
import json

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False

# Import base NLU command bar
from .nlu_command_bar import NLUCommandBar

class MemoryIntegratedCommandBar(NLUCommandBar):
    """NLU Command Bar with proper memory system integration"""
    
    def __init__(self, parent, nlu_service=None, event_bus=None):
        # Initialize parent class
        super().__init__(parent, nlu_service, event_bus)
        
        # Memory system paths
        self.project_root = Path(__file__).parent.parent.parent
        self.memory_cli = self.project_root / "memory_system" / "cli.py"
        self.todo_manager = self.project_root / "todo_manager.py"
        
        # Integration status
        self.memory_system_available = False
        self.todo_manager_available = False
        
        # Initialize integration
        self._check_system_availability()
        self._enhance_command_processing()
        self._add_memory_features()
        
    def _check_system_availability(self):
        """Check availability of memory system and todo manager"""
        try:
            # Check memory system
            if self.memory_cli.exists():
                self.memory_system_available = True
                print("✅ Memory system CLI detected")
            
            # Check todo manager
            if self.todo_manager.exists():
                self.todo_manager_available = True
                print("✅ TODO Manager detected")
                
            if self.memory_system_available and self.todo_manager_available:
                self._update_status("🧠 Memory System Ready - Full Integration")
            elif self.todo_manager_available:
                self._update_status("📝 TODO Manager Ready - Limited Memory")
            else:
                self._update_status("⚠️ Limited functionality - Missing components")
                
        except Exception as e:
            print(f"System check error: {e}")
            self._update_status(f"❌ System Error: {str(e)}")
    
    def _enhance_command_processing(self):
        """Override command processing with memory system integration"""
        # Replace button command
        self.process_btn.configure(command=self._memory_process_command)
        
        # Add Enter key binding
        self.entry.bind("<Return>", lambda e: self._memory_process_command())
        self.entry.bind("<KP_Enter>", lambda e: self._memory_process_command())
    
    def _add_memory_features(self):
        """Add memory system specific features"""
        if not (self.memory_system_available or self.todo_manager_available):
            return
            
        # Memory integration status frame
        memory_frame = ttk.Frame(self.frame)
        memory_frame.pack(fill="x", pady=(2, 0))
        
        # Memory system indicator
        if self.memory_system_available:
            self.memory_label = ttk.Label(
                memory_frame,
                text="🧠 Memory System Active",
                font=("Arial", 8, "bold"),
                foreground="blue"
            )
            self.memory_label.pack(side="left")
        
        # TODO manager indicator  
        if self.todo_manager_available:
            self.todo_label = ttk.Label(
                memory_frame,
                text="📝 TODO Manager",
                font=("Arial", 8),
                foreground="green"
            )
            self.todo_label.pack(side="right")
        
        # Memory-enhanced quick actions
        self._add_memory_quick_actions()
    
    def _add_memory_quick_actions(self):
        """Add quick actions that use memory system capabilities"""
        actions_frame = ttk.Frame(self.frame)
        actions_frame.pack(fill="x", pady=(5, 0))
        
        # Memory-powered quick actions
        quick_actions = [
            ("🔍 Search Memory", "search memory"),
            ("🏗️ Architecture Plan", "create architecture plan"),
            ("🚀 Deploy", "deploy production"),
            ("📊 Monitor", "monitor system"),
            ("🧹 Cleanup", "cleanup memory")
        ]
        
        for text, command in quick_actions:
            btn = ttk.Button(
                actions_frame,
                text=text,
                command=lambda cmd=command: self._execute_memory_command(cmd),
                style="info-outline" if MODERN_STYLING else None
            )
            btn.pack(side="left", padx=2)
    
    def _memory_process_command(self):
        """Process command using memory system intelligence"""
        command = self.entry.get().strip()
        
        if not command:
            self._update_status("⚠️ Please enter a command")
            return
        
        # Update status to show processing
        self._update_status("🧠 Processing with memory system...")
        
        # Process in background thread
        thread = threading.Thread(
            target=self._process_with_memory_system,
            args=(command,),
            daemon=True
        )
        thread.start()
    
    def _process_with_memory_system(self, command):
        """Process command using actual memory system"""
        try:
            result = {"success": False, "message": ""}
            
            # Step 1: Search memory for relevant context
            memory_context = self._search_memory(command)
            
            # Step 2: Analyze command for actionable intent
            intent_analysis = self._analyze_command_intent(command, memory_context)
            
            # Step 3: Execute appropriate action
            if intent_analysis["actionable"]:
                if intent_analysis["action_type"] == "memory_search":
                    result = self._execute_memory_search(command)
                elif intent_analysis["action_type"] == "architecture_plan":
                    result = self._execute_architecture_plan(command)
                elif intent_analysis["action_type"] == "todo_creation":
                    result = self._create_memory_informed_todo(command, memory_context, intent_analysis)
                elif intent_analysis["action_type"] == "system_monitor":
                    result = self._execute_system_monitor()
                else:
                    result = self._create_memory_informed_todo(command, memory_context, intent_analysis)
            else:
                result = {
                    "success": True,
                    "message": f"Query processed: {intent_analysis['reasoning']}"
                }
            
            # Update UI in main thread
            self.parent.after(0, lambda: self._display_memory_result(command, result))
            
        except Exception as e:
            error_msg = f"Memory system error: {str(e)}"
            self.parent.after(0, lambda: self._update_status(error_msg))
    
    def _search_memory(self, query):
        """Search memory system for relevant context"""
        if not self.memory_system_available:
            return {"results": [], "success": False}
        
        try:
            cmd = [
                sys.executable,
                str(self.memory_cli),
                "search",
                query,
                "--limit", "5"
            ]
            
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.project_root,
                env=env
            )
            
            if result.returncode == 0:
                try:
                    search_results = json.loads(result.stdout)
                    return {"results": search_results, "success": True}
                except json.JSONDecodeError:
                    return {"results": [], "success": False, "error": "Invalid JSON response"}
            else:
                return {"results": [], "success": False, "error": result.stderr}
                
        except Exception as e:
            return {"results": [], "success": False, "error": str(e)}
    
    def _analyze_command_intent(self, command, memory_context):
        """Analyze command intent with memory context"""
        command_lower = command.lower()
        
        # Search memory intent
        if any(word in command_lower for word in ["search", "find", "look", "memory"]):
            return {
                "intent": "memory_search",
                "actionable": True,
                "action_type": "memory_search",
                "confidence": 0.9,
                "reasoning": "Memory search command detected"
            }
        
        # Architecture planning intent
        elif any(word in command_lower for word in ["architecture", "plan", "design", "arch"]):
            return {
                "intent": "architecture_planning",
                "actionable": True,
                "action_type": "architecture_plan", 
                "confidence": 0.85,
                "reasoning": "Architecture planning command detected"
            }
        
        # System monitoring intent
        elif any(word in command_lower for word in ["monitor", "status", "dashboard", "health"]):
            return {
                "intent": "system_monitoring",
                "actionable": True,
                "action_type": "system_monitor",
                "confidence": 0.8,
                "reasoning": "System monitoring command detected"
            }
        
        # Production deployment intent (create TODO)
        elif any(word in command_lower for word in ["deploy", "production", "release"]):
            return {
                "intent": "deployment",
                "actionable": True,
                "action_type": "todo_creation",
                "confidence": 0.9,
                "reasoning": "Deployment command detected",
                "suggested_todos": [
                    "Review deployment checklist from memory",
                    "Run pre-deployment security checks",
                    "Execute production deployment scripts",
                    "Monitor deployment progress",
                    "Verify post-deployment health"
                ]
            }
        
        # Troubleshooting intent (create TODO)
        elif any(word in command_lower for word in ["fix", "debug", "problem", "issue", "error"]):
            return {
                "intent": "troubleshooting",
                "actionable": True,
                "action_type": "todo_creation",
                "confidence": 0.85,
                "reasoning": "Troubleshooting command detected",
                "suggested_todos": [
                    "Search memory for similar issues",
                    "Collect diagnostic information",
                    "Analyze system logs and metrics", 
                    "Apply fix based on memory context",
                    "Test and verify resolution"
                ]
            }
        
        # General query
        else:
            return {
                "intent": "general_query",
                "actionable": False,
                "confidence": 0.6,
                "reasoning": "General query or information request"
            }
    
    def _execute_memory_search(self, query):
        """Execute memory search and display results"""
        search_result = self._search_memory(query)
        
        if search_result["success"] and search_result["results"]:
            return {
                "success": True,
                "message": f"Found {len(search_result['results'])} results in memory",
                "results": search_result["results"],
                "action_type": "memory_search"
            }
        else:
            return {
                "success": False,
                "message": f"Memory search failed: {search_result.get('error', 'No results found')}"
            }
    
    def _execute_architecture_plan(self, description):
        """Execute architecture planning using memory system"""
        if not self.memory_system_available:
            return {
                "success": False,
                "message": "Architecture planning requires memory system"
            }
        
        try:
            cmd = [
                sys.executable,
                str(self.memory_cli),
                "arch-mode",
                "plan",
                description
            ]
            
            env = os.environ.copy()
            env["PYTHONPATH"] = str(self.project_root)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root,
                env=env
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "Architecture plan created successfully",
                    "output": result.stdout,
                    "action_type": "architecture_plan"
                }
            else:
                return {
                    "success": False,
                    "message": f"Architecture planning failed: {result.stderr}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Architecture planning error: {str(e)}"
            }
    
    def _execute_system_monitor(self):
        """Execute system monitoring"""
        if not self.memory_system_available:
            return {
                "success": False,
                "message": "System monitoring requires memory system"
            }
        
        # For GUI, we'll return success and suggest opening monitor
        return {
            "success": True,
            "message": "System monitoring available - use 'memory_system/cli.py monitor' to launch dashboard",
            "action_type": "system_monitor"
        }
    
    def _create_memory_informed_todo(self, command, memory_context, intent_analysis):
        """Create TODO using memory context and existing todo_manager"""
        if not self.todo_manager_available:
            return {
                "success": False,
                "message": "TODO creation requires todo_manager"
            }
        
        try:
            # Generate task ID
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            intent = intent_analysis["intent"]
            task_id = f"{timestamp}_Memory_{intent}"
            
            # Create task description with memory context
            task_description = f"Memory-Informed: {command.title()}"
            if memory_context["results"]:
                task_description += f" (Found {len(memory_context['results'])} memory references)"
            
            # Create main task
            create_cmd = [
                sys.executable,
                str(self.todo_manager),
                "new",
                task_id,
                task_description
            ]
            
            result = subprocess.run(
                create_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "message": f"Failed to create task: {result.stderr}"
                }
            
            # Add TODO items (include memory references)
            todo_count = 0
            todos = intent_analysis.get("suggested_todos", [])
            
            # Add memory context as first TODO if available
            if memory_context["results"]:
                memory_todo = f"Review memory references: {', '.join([r['title'] for r in memory_context['results'][:3]])}"
                todos.insert(0, memory_todo)
            
            for todo in todos:
                add_cmd = [
                    sys.executable,
                    str(self.todo_manager),
                    "add",
                    task_id,
                    todo
                ]
                
                add_result = subprocess.run(
                    add_cmd,
                    cwd=self.project_root,
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
                "memory_references": len(memory_context["results"]),
                "confidence": intent_analysis["confidence"],
                "intent": intent_analysis["intent"],
                "message": f"Created memory-informed task with {todo_count} TODOs and {len(memory_context['results'])} memory references"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating memory-informed TODO: {str(e)}"
            }
    
    def _execute_memory_command(self, command):
        """Execute quick action command"""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, command)
        self._memory_process_command()
    
    def _display_memory_result(self, command, result):
        """Display memory system result in UI"""
        if result["success"]:
            # Update status with success
            message = f"✅ {result['message']}"
            self._update_status(message)
            
            # Show detailed result if available
            if "task_id" in result or result.get("action_type") == "memory_search":
                self._show_memory_result_popup(command, result)
                
            # Notify event bus if available
            if self.event_bus:
                self.event_bus.publish("memory_command_processed", result)
                
        else:
            self._update_status(f"❌ {result['message']}")
        
        # Clear command entry
        self.entry.delete(0, tk.END)
    
    def _show_memory_result_popup(self, command, result):
        """Show memory system result in popup window"""
        popup = tk.Toplevel(self.parent)
        popup.title("🧠 Memory System Result")
        popup.geometry("600x400")
        popup.transient(self.parent)
        popup.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(popup)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=f"Memory System: '{command}'",
            font=("Arial", 12, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Result content based on action type
        if result.get("action_type") == "memory_search" and "results" in result:
            self._show_search_results(main_frame, result["results"])
        elif "task_id" in result:
            self._show_todo_result(main_frame, result)
        elif result.get("action_type") == "architecture_plan":
            self._show_architecture_result(main_frame, result)
        else:
            # Generic result display
            result_text = tk.Text(main_frame, height=10, wrap="word")
            result_text.insert("1.0", result["message"])
            result_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Close button
        ttk.Button(
            main_frame,
            text="✅ Close",
            command=popup.destroy
        ).pack(pady=10)
    
    def _show_search_results(self, parent, results):
        """Show memory search results"""
        results_frame = ttk.LabelFrame(parent, text="🔍 Memory Search Results")
        results_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Scrollable text area
        import tkinter.scrolledtext as scrolledtext
        results_text = scrolledtext.ScrolledText(
            results_frame,
            height=12,
            font=("Courier", 9)
        )
        results_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add search results
        for i, result in enumerate(results, 1):
            results_text.insert(tk.END, f"{i}. {result['title']} ({result['relevance']})\n")
            results_text.insert(tk.END, f"   Path: {result['path']}\n")
            results_text.insert(tk.END, f"   Type: {result['type']}\n\n")
        
        results_text.config(state="disabled")
    
    def _show_todo_result(self, parent, result):
        """Show TODO creation result"""
        todo_frame = ttk.LabelFrame(parent, text="📋 Memory-Informed TODO Created")
        todo_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Task details
        details = [
            f"Task ID: {result.get('task_id', 'N/A')}",
            f"Intent: {result.get('intent', 'N/A').title()}",
            f"TODO Items: {result.get('todo_count', 0)}",
            f"Memory References: {result.get('memory_references', 0)}",
            f"Confidence: {result.get('confidence', 0):.0%}"
        ]
        
        for detail in details:
            ttk.Label(todo_frame, text=detail).pack(anchor="w", padx=10, pady=2)
    
    def _show_architecture_result(self, parent, result):
        """Show architecture planning result"""
        arch_frame = ttk.LabelFrame(parent, text="🏗️ Architecture Plan")
        arch_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        import tkinter.scrolledtext as scrolledtext
        arch_text = scrolledtext.ScrolledText(
            arch_frame,
            height=12,
            font=("Courier", 9)
        )
        arch_text.pack(fill="both", expand=True, padx=10, pady=10)
        arch_text.insert("1.0", result.get("output", "Architecture plan created successfully"))
        arch_text.config(state="disabled")
    
    def _update_status(self, message):
        """Update status label"""
        if hasattr(self, 'status_label'):
            self.status_label.config(text=message)

# Factory function for easy integration
def create_memory_integrated_command_bar(parent, nlu_service=None, event_bus=None):
    """Factory function to create memory-integrated command bar"""
    return MemoryIntegratedCommandBar(parent, nlu_service, event_bus)