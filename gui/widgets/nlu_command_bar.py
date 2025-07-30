#!/usr/bin/env python3
"""
NLU Command Bar Widget
Natural Language Interface for GUI Control Center
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Callable, Optional

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False

class NLUCommandBar:
    """Natural Language command bar widget for GUI control"""
    
    def __init__(self, parent, nlu_service=None, event_bus=None):
        self.parent = parent
        self.nlu_service = nlu_service
        self.event_bus = event_bus
        
        # Create the command bar frame
        self.frame = ttk.Frame(parent)
        self.command_history = []
        self.history_index = -1
        self.is_processing = False
        
        self._create_widgets()
        self._setup_bindings()
        
    def _create_widgets(self):
        """Create the command bar widgets"""
        
        # Main container
        self.frame.pack(fill="x", padx=5, pady=3)
        
        # Command input frame
        input_frame = ttk.Frame(self.frame)
        input_frame.pack(fill="x")
        
        # NLU icon/label
        if MODERN_STYLING:
            self.icon_label = ttk.Label(input_frame, text="🤖", font=("Segoe UI", 12))
        else:
            self.icon_label = ttk.Label(input_frame, text="NLU:", font=("Arial", 10, "bold"))
        self.icon_label.pack(side="left", padx=(0, 5))
        
        # Command entry field
        if MODERN_STYLING:
            self.entry = ttk.Entry(input_frame, font=("Segoe UI", 10))
            # Note: placeholder_text not available in standard tkinter
        else:
            self.entry = ttk.Entry(input_frame, font=("Arial", 10))
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # Process button
        if MODERN_STYLING:
            self.process_btn = ttk.Button(input_frame, text="⚡", width=3, 
                                        bootstyle="success-outline")
        else:
            self.process_btn = ttk.Button(input_frame, text="Send", width=6)
        self.process_btn.pack(side="right")
        
        # Status frame
        status_frame = ttk.Frame(self.frame)
        status_frame.pack(fill="x", pady=(2, 0))
        
        # Status label
        self.status_label = ttk.Label(status_frame, text="Ready for natural language commands", 
                                    font=("Arial", 8))
        self.status_label.pack(side="left")
        
        # Intent display
        self.intent_label = ttk.Label(status_frame, text="", 
                                    font=("Arial", 8), foreground="blue")
        self.intent_label.pack(side="right")
        
        # Initially disable if no NLU service
        if not self.nlu_service:
            self._set_enabled(False)
            self.status_label.config(text="NLU Service not available", foreground="red")
    
    def _setup_bindings(self):
        """Setup event bindings"""
        
        # Enter key processing
        self.entry.bind("<Return>", self._on_enter_pressed)
        self.entry.bind("<KP_Enter>", self._on_enter_pressed)
        
        # Command history navigation
        self.entry.bind("<Up>", self._on_history_up)
        self.entry.bind("<Down>", self._on_history_down)
        
        # Button click
        self.process_btn.config(command=self._process_command)
        
        # Focus handling
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
    
    def _on_enter_pressed(self, event):
        """Handle Enter key press"""
        self._process_command()
        return "break"  # Prevent default handling
    
    def _on_history_up(self, event):
        """Navigate up in command history"""
        if self.command_history and self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            command = self.command_history[-(self.history_index + 1)]
            self.entry.delete(0, "end")
            self.entry.insert(0, command)
        return "break"
    
    def _on_history_down(self, event):
        """Navigate down in command history"""
        if self.history_index > 0:
            self.history_index -= 1
            command = self.command_history[-(self.history_index + 1)]
            self.entry.delete(0, "end")
            self.entry.insert(0, command)
        elif self.history_index == 0:
            self.history_index = -1
            self.entry.delete(0, "end")
        return "break"
    
    def _on_focus_in(self, event):
        """Handle focus in event"""
        if not self.nlu_service:
            self.status_label.config(text="NLU Service not available", foreground="red")
        else:
            self.status_label.config(text="Type your command...", foreground="blue")
    
    def _on_focus_out(self, event):
        """Handle focus out event"""
        if not self.is_processing:
            self.status_label.config(text="Ready for natural language commands", foreground="black")
    
    def _process_command(self):
        """Process the natural language command"""
        
        command_text = self.entry.get().strip()
        if not command_text:
            return
        
        if not self.nlu_service:
            self.status_label.config(text="NLU Service not available", foreground="red")
            return
        
        # Add to history
        if command_text not in self.command_history:
            self.command_history.append(command_text)
            # Keep only last 50 commands
            if len(self.command_history) > 50:
                self.command_history.pop(0)
        self.history_index = -1
        
        # Clear entry
        self.entry.delete(0, "end")
        
        # Show processing status
        self.is_processing = True
        self._set_enabled(False)
        self.status_label.config(text=f"Processing: {command_text[:30]}...", foreground="orange")
        self.intent_label.config(text="Analyzing...", foreground="orange")
        
        # Process in background thread
        def process_in_background():
            try:
                # Process with NLU service
                response = self.nlu_service.process_text(
                    command_text, 
                    callback=self._on_nlu_response
                )
                
                # Execute the command
                self._execute_nlu_command(response)
                
            except Exception as e:
                self.parent.after(0, lambda: self._on_nlu_error(str(e)))
            finally:
                self.parent.after(0, self._reset_processing_state)
        
        # Start processing thread
        thread = threading.Thread(target=process_in_background, daemon=True)
        thread.start()
    
    def _on_nlu_response(self, response):
        """Handle NLU response"""
        
        def update_ui():
            if hasattr(response, 'intent') and hasattr(response, 'confidence'):
                intent_text = f"{response.intent} ({response.confidence:.2f})"
                self.intent_label.config(text=intent_text, foreground="green")
                self.status_label.config(text=f"Intent: {response.intent}", foreground="green")
            else:
                self.intent_label.config(text="Unknown response", foreground="red")
        
        # Update UI in main thread
        self.parent.after(0, update_ui)
    
    def _on_nlu_error(self, error_msg):
        """Handle NLU processing error"""
        self.status_label.config(text=f"Error: {error_msg[:40]}", foreground="red")
        self.intent_label.config(text="Error", foreground="red")
    
    def _execute_nlu_command(self, response):
        """Execute the NLU command based on intent"""
        
        try:
            if not hasattr(response, 'intent'):
                return
            
            intent = response.intent
            entities = getattr(response, 'entities', [])
            
            # GUI Navigation Commands
            if intent == "[GUI] Open Dashboard":
                self._publish_event("switch_view", {"view": "dashboard"})
            elif intent == "[GUI] Show Tasks" or intent == "[Task] Create":
                self._publish_event("switch_view", {"view": "task_management"})
            elif intent == "[GUI] Open Memory":
                self._publish_event("switch_view", {"view": "memory_intelligence"})
            elif intent == "[GUI] Show Monitoring":
                self._publish_event("switch_view", {"view": "monitoring"})
            elif intent == "[GUI] Open Agents":
                self._publish_event("switch_view", {"view": "agent_control"})
            elif intent == "[GUI] Show Automation":
                self._publish_event("switch_view", {"view": "automation_control"})
            
            # Task Management Commands
            elif intent == "[Task] Create":
                # Extract task description from entities
                task_desc = "New task"
                for entity in entities:
                    if entity.get("entity") == "task_description":
                        task_desc = entity.get("value", "New task")
                        break
                self._publish_event("new_task", {"description": task_desc})
                
            elif intent == "[Task] Complete":
                self._publish_event("complete_task", {})
            
            # System Commands
            elif intent == "[System] Refresh":
                self._publish_event("global_refresh", {})
            elif intent == "[System] Help":
                self._show_help()
            elif intent == "[System] Exit":
                self._publish_event("app_exit", {})
            
            # Agent Control Commands  
            elif intent == "[Agent] Start":
                agent_ref = "all"
                for entity in entities:
                    if entity.get("entity") == "agent_reference":
                        agent_ref = entity.get("value", "all")
                        break
                self._publish_event("agent_action", {"action": "start", "agent": agent_ref})
                
            elif intent == "[Agent] Stop":
                agent_ref = "all"
                for entity in entities:
                    if entity.get("entity") == "agent_reference":
                        agent_ref = entity.get("value", "all")
                        break
                self._publish_event("agent_action", {"action": "stop", "agent": agent_ref})
            
            else:
                # Unknown intent
                self._publish_event("unknown_command", {"intent": intent, "entities": entities})
            
        except Exception as e:
            print(f"Error executing NLU command: {e}")
    
    def _publish_event(self, event_type, data):
        """Publish event through event bus"""
        if self.event_bus:
            self.event_bus.publish(event_type, data)
        else:
            print(f"📢 NLU Event: {event_type} - {data}")
    
    def _show_help(self):
        """Show NLU command help"""
        help_text = """
🤖 NLU Commands Help:

Navigation:
• "open dashboard" - Go to dashboard view
• "show tasks" - Go to task management
• "open memory" - Go to memory intelligence  
• "show monitoring" - Go to system monitoring
• "open agents" - Go to agent control
• "show automation" - Go to automation control

Task Management:
• "create task [description]" - Create new task
• "new task [description]" - Create new task
• "mark done" - Complete current task

System:
• "refresh" - Refresh current view
• "help" - Show this help
• "exit" - Exit application

Agent Control:
• "start agent [name]" - Start specific agent
• "stop agent [name]" - Stop specific agent
• "agent status" - Show agent status
"""
        
        # Show help in a popup or publish help event
        self._publish_event("show_help", {"content": help_text})
    
    def _reset_processing_state(self):
        """Reset processing state"""
        self.is_processing = False
        self._set_enabled(True)
        
        # Reset status after delay
        def delayed_reset():
            time.sleep(3)
            if not self.is_processing:
                self.parent.after(0, lambda: self.status_label.config(
                    text="Ready for natural language commands", foreground="black"))
        
        thread = threading.Thread(target=delayed_reset, daemon=True)
        thread.start()
    
    def _set_enabled(self, enabled: bool):
        """Enable/disable the command bar"""
        state = "normal" if enabled else "disabled"
        self.entry.config(state=state)
        self.process_btn.config(state=state)
    
    def set_nlu_service(self, nlu_service):
        """Set the NLU service"""
        self.nlu_service = nlu_service
        if nlu_service:
            self._set_enabled(True)
            self.status_label.config(text="NLU Service connected", foreground="green")
        else:
            self._set_enabled(False)
            self.status_label.config(text="NLU Service not available", foreground="red")
    
    def focus(self):
        """Focus the command entry"""
        self.entry.focus_set()
    
    def get_frame(self):
        """Get the command bar frame"""
        return self.frame
