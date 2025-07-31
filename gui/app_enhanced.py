"""
🎯 Enhanced Modern GUI Control Center - Main Application Controller

This module extends the original app.py with AI-powered intelligent TODO integration.
Now supports natural language commands that automatically create structured TODO tasks.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter.constants import *
import threading
import time
from pathlib import Path
import json
from datetime import datetime
import sys

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False

# Import existing GUI components
try:
    from styles.theme import ModernTheme
    from views.dashboard import DashboardView
    from views.task_management import TaskManagementView
    from views.agent_control import AgentControlView
    from views.memory_intelligence import MemoryIntelligenceView
    from views.monitoring import MonitoringView
    from views.automation_control import AutomationControlView
    from services.system_service import SystemService
    from services.event_bus import EventBus
    from services.async_runner import AsyncRunner
    from services.nlu_integration import get_nlu_service
    from widgets.nlu_command_bar import NLUCommandBar
    
    # Import AI intelligence system
    from services.intelligent_todo_service import IntelligentTodoService
except ImportError:
    from .styles.theme import ModernTheme
    from .views.dashboard import DashboardView
    from .views.task_management import TaskManagementView
    from .views.agent_control import AgentControlView
    from .views.memory_intelligence import MemoryIntelligenceView
    from .views.monitoring import MonitoringView
    from .views.automation_control import AutomationControlView
    from .services.system_service import SystemService
    from .services.nlu_integration import get_nlu_service
    from .widgets.nlu_command_bar import NLUCommandBar
    
    # Import AI intelligence system
    from .services.intelligent_todo_service import IntelligentTodoService


class EnhancedNLUCommandBar(NLUCommandBar):
    """Enhanced NLU Command Bar with AI-powered TODO generation"""
    
    def __init__(self, parent, nlu_service=None, event_bus=None):
        super().__init__(parent, nlu_service, event_bus)
        
        # Initialize intelligent TODO service
        try:
            self.todo_service = IntelligentTodoService()
            self.ai_enabled = True
            self._update_status("🤖 AI Intelligence: Ready")
        except Exception as e:
            self.ai_enabled = False
            self._update_status(f"⚠️ AI Intelligence: {str(e)}")
        
        # Add AI features to existing command bar
        self._enhance_command_processing()
        self._add_quick_actions()
    
    def _enhance_command_processing(self):
        """Enhance existing command processing with AI intelligence"""
        # Store original process method
        self._original_process = self._process_command if hasattr(self, '_process_command') else None
        
        # Override with AI-enhanced processing
        self.process_btn.configure(command=self._ai_process_command)
        
        # Add AI status indicator
        self._add_ai_status_indicator()
    
    def _add_ai_status_indicator(self):
        """Add AI status indicator to command bar"""
        ai_status_frame = ttk.Frame(self.frame)
        ai_status_frame.pack(fill="x", pady=(2, 0))
        
        # AI status label
        self.ai_status_label = ttk.Label(
            ai_status_frame,
            text="🤖 AI-Powered TODO Generation: Ready",
            font=("Arial", 8),
            foreground="green" if self.ai_enabled else "red"
        )
        self.ai_status_label.pack(side="left")
        
        # Confidence indicator
        self.confidence_label = ttk.Label(
            ai_status_frame,
            text="",
            font=("Arial", 8),
            foreground="blue"
        )
        self.confidence_label.pack(side="right")
    
    def _add_quick_actions(self):
        """Add quick action buttons for common commands"""
        if not self.ai_enabled:
            return
            
        quick_frame = ttk.Frame(self.frame)
        quick_frame.pack(fill="x", pady=(5, 0))
        
        # Quick action buttons
        quick_actions = [
            ("🚀 Deploy Production", "deploy production"),
            ("🔧 Fix Docker", "fix docker issues"),
            ("📊 Setup Monitoring", "setup monitoring dashboard"),
            ("🛡️ Security Check", "run security audit")
        ]
        
        for text, command in quick_actions:
            btn = ttk.Button(
                quick_frame,
                text=text,
                command=lambda cmd=command: self._execute_quick_command(cmd),
                style="success-outline" if MODERN_STYLING else None
            )
            btn.pack(side="left", padx=2)
    
    def _ai_process_command(self):
        """AI-enhanced command processing"""
        command = self.entry.get().strip()
        
        if not command:
            self._update_status("⚠️ Please enter a command")
            return
        
        if not self.ai_enabled:
            # Fallback to original processing
            if self._original_process:
                self._original_process()
            return
        
        # Process with AI intelligence
        self._update_status("🤖 Processing with AI...")
        self.confidence_label.config(text="")
        
        try:
            # Get AI response and create TODO
            result = self.todo_service.process_gui_command(command)
            
            if result['success']:
                # Update status with success
                message = f"✅ {result['message']}"
                self._update_status(message)
                
                # Show confidence if available
                if 'ai_confidence' in result:
                    self.confidence_label.config(
                        text=f"Confidence: {result['ai_confidence']}"
                    )
                
                # Show detailed result in popup
                self._show_result_popup(command, result)
                
                # Notify event bus
                if self.event_bus:
                    self.event_bus.publish("ai_todo_created", result)
                
            else:
                self._update_status(f"❌ {result['message']}")
                
        except Exception as e:
            self._update_status(f"❌ AI Error: {str(e)}")
        
        # Clear command entry
        self.entry.delete(0, tk.END)
    
    def _execute_quick_command(self, command):
        """Execute quick action command"""
        self.entry.delete(0, tk.END)
        self.entry.insert(0, command)
        self._ai_process_command()
    
    def _show_result_popup(self, command, result):
        """Show detailed AI result in popup"""
        popup = tk.Toplevel(self.parent)
        popup.title("🤖 AI TODO Creation Result")
        popup.geometry("600x400")
        popup.transient(self.parent)
        popup.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(popup)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text=f"AI Analysis: '{command}'",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # AI Response details
        if 'ai_response' in result:
            ai_response = result['ai_response']
            
            # Analysis info
            info_frame = ttk.LabelFrame(main_frame, text="🧠 AI Analysis")
            info_frame.pack(fill="x", pady=(0, 10))
            
            ttk.Label(
                info_frame,
                text=f"Topic: {ai_response['analysis']['topic']}"
            ).pack(anchor="w", padx=10, pady=2)
            
            ttk.Label(
                info_frame,
                text=f"Confidence: {ai_response['analysis']['confidence']}"
            ).pack(anchor="w", padx=10, pady=2)
            
            # Suggested actions
            if 'immediate_actions' in ai_response:
                actions_frame = ttk.LabelFrame(main_frame, text="📋 Generated TODO Items")
                actions_frame.pack(fill="both", expand=True, pady=(0, 10))
                
                # Scrollable text area
                import tkinter.scrolledtext as scrolledtext
                actions_text = scrolledtext.ScrolledText(
                    actions_frame,
                    height=10,
                    font=("Courier", 9)
                )
                actions_text.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Add actions to text area
                for i, action in enumerate(ai_response['immediate_actions'], 1):
                    actions_text.insert(tk.END, f"{i}. {action}\n")
                
                actions_text.config(state="disabled")
        
        # Result info
        result_frame = ttk.LabelFrame(main_frame, text="✅ Creation Result")
        result_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(
            result_frame,
            text=f"Task ID: {result.get('task_id', 'N/A')}"
        ).pack(anchor="w", padx=10, pady=2)
        
        ttk.Label(
            result_frame,
            text=f"TODO Count: {result.get('todo_count', 0)}"
        ).pack(anchor="w", padx=10, pady=2)
        
        # Close button
        ttk.Button(
            main_frame,
            text="🔽 Close",
            command=popup.destroy
        ).pack(pady=10)
    
    def _update_status(self, message):
        """Update AI status label"""
        if hasattr(self, 'ai_status_label'):
            self.ai_status_label.config(text=message)


class EnhancedModernGUIApplication:
    """Enhanced GUI application with AI-powered TODO integration"""
    
    def __init__(self, theme="darkly"):
        """Initialize the enhanced GUI application"""
        self.theme_name = theme if MODERN_STYLING else None
        self.root = None
        self.main_frame = None
        self.sidebar = None
        self.content_area = None
        self.current_view = None
        
        # Services (initialized after root window)
        self.system_service = None
        self.nlu_service = None
        self.todo_service = None
        
        # Views
        self.views = {}
        
        # State
        self.app_state = {
            "current_view": "dashboard",
            "sidebar_collapsed": False,
            "window_geometry": "1400x900",
            "last_update": None,
            "ai_enabled": False
        }
        
        # Initialize application
        self._create_root_window()
        self._initialize_services()
        self._setup_styles()
        self._create_main_layout()
        self._create_views()
        self._setup_bindings()
        
        print("✅ Enhanced GUI with AI Intelligence initialized!")
    
    def _create_root_window(self):
        """Create and configure the root window"""
        if MODERN_STYLING:
            self.root = ttk.Window(themename=self.theme_name)
        else:
            self.root = tk.Tk()
            
        # Window configuration
        self.root.title("🤖 Enhanced GUI Control Center - AI-Powered TODO System")
        self.root.geometry(self.app_state["window_geometry"])
        self.root.minsize(1200, 800)
        
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Configure window properties
        if not MODERN_STYLING:
            self.root.configure(bg="#2b2b2b")
    
    def _initialize_services(self):
        """Initialize system services including AI intelligence"""
        print("🔧 Initializing enhanced services...")
        
        # Initialize system service
        self.system_service = SystemService()
        
        # Initialize AI TODO service
        try:
            self.todo_service = IntelligentTodoService()
            self.app_state["ai_enabled"] = True
            print("✅ AI Intelligence Service: Ready")
        except Exception as e:
            print(f"⚠️ AI Intelligence Service: {e}")
            self.app_state["ai_enabled"] = False
        
        # Initialize NLU service
        try:
            self.nlu_service = get_nlu_service()
            print("✅ NLU Service: Ready")
        except Exception as e:
            print(f"⚠️ NLU Service: {e}")
    
    def _setup_styles(self):
        """Setup modern styling"""
        if not MODERN_STYLING:
            # Apply custom dark theme for standard tkinter
            self.theme = ModernTheme(self.root)
            self.theme.apply_dark_theme()
    
    def _create_main_layout(self):
        """Create the main application layout"""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=True)
        
        # Create sidebar and content area
        self._create_sidebar()
        self._create_content_area()
        self._create_enhanced_command_bar()
    
    def _create_sidebar(self):
        """Create navigation sidebar"""
        self.sidebar = ttk.Frame(self.main_frame, width=200)
        self.sidebar.pack(side=LEFT, fill=Y, padx=(10, 5), pady=10)
        self.sidebar.pack_propagate(False)
        
        # Logo/Title
        title_frame = ttk.Frame(self.sidebar)
        title_frame.pack(fill=X, pady=(0, 20))
        
        title_label = ttk.Label(
            title_frame,
            text="🤖 AI Control Center",
            font=("Arial", 12, "bold")
        )
        title_label.pack()
        
        # AI Status indicator
        if self.app_state["ai_enabled"]:
            ai_indicator = ttk.Label(
                title_frame,
                text="🧠 AI Intelligence: Active",
                font=("Arial", 8),
                foreground="green"
            )
        else:
            ai_indicator = ttk.Label(
                title_frame,
                text="⚠️ AI Intelligence: Disabled",
                font=("Arial", 8),
                foreground="red"
            )
        ai_indicator.pack()
        
        # Navigation buttons
        nav_buttons = [
            ("📊 Dashboard", "dashboard"),
            ("📋 Task Management", "task_management"),
            ("🤖 Agent Control", "agent_control"),
            ("🧠 Memory Intelligence", "memory_intelligence"),
            ("📈 Monitoring", "monitoring"),
            ("⚙️ Automation Control", "automation_control")
        ]
        
        for text, view_name in nav_buttons:
            btn = ttk.Button(
                self.sidebar,
                text=text,
                command=lambda v=view_name: self.switch_view(v),
                style="info" if MODERN_STYLING else None
            )
            btn.pack(fill=X, pady=2)
    
    def _create_content_area(self):
        """Create main content area"""
        self.content_area = ttk.Frame(self.main_frame)
        self.content_area.pack(side=RIGHT, fill=BOTH, expand=True, padx=(5, 10), pady=10)
    
    def _create_enhanced_command_bar(self):
        """Create enhanced command bar with AI intelligence"""
        try:
            nlu_service = get_nlu_service()
            
            # Create enhanced command bar with AI TODO integration
            self.nlu_command_bar = EnhancedNLUCommandBar(
                self.content_area,
                nlu_service=nlu_service,
                event_bus=self.system_service.bus if hasattr(self.system_service, 'bus') else None
            )
            self.nlu_command_bar.frame.pack(fill=X, padx=10, pady=5)
            
            # Subscribe to AI TODO events
            if hasattr(self.system_service, 'bus'):
                self.system_service.bus.subscribe("ai_todo_created", self._handle_ai_todo_created)
                
        except Exception as e:
            print(f"Warning: Could not initialize enhanced command bar: {e}")
            # Create fallback simple command bar
            self._create_simple_command_bar()
    
    def _create_simple_command_bar(self):
        """Create simple fallback command bar"""
        cmd_frame = ttk.Frame(self.content_area)
        cmd_frame.pack(fill=X, padx=10, pady=5)
        
        ttk.Label(cmd_frame, text="Command:").pack(side=LEFT, padx=(0, 5))
        
        self.simple_entry = ttk.Entry(cmd_frame)
        self.simple_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        
        ttk.Button(
            cmd_frame,
            text="Process",
            command=self._process_simple_command
        ).pack(side=RIGHT)
    
    def _process_simple_command(self):
        """Process command in simple mode"""
        command = self.simple_entry.get().strip()
        if command and self.todo_service:
            result = self.todo_service.process_gui_command(command)
            messagebox.showinfo("Command Result", result['message'])
            self.simple_entry.delete(0, tk.END)
    
    def _create_views(self):
        """Create all application views"""
        # Dashboard
        self.views['dashboard'] = DashboardView(self.content_area, self.system_service)
        
        # Task Management (enhanced with AI integration)
        self.views['task_management'] = TaskManagementView(self.content_area, self.system_service)
        
        # Other views
        self.views['agent_control'] = AgentControlView(self.content_area, self.system_service)
        self.views['memory_intelligence'] = MemoryIntelligenceView(self.content_area, self.system_service)
        self.views['monitoring'] = MonitoringView(self.content_area, self.system_service)
        self.views['automation_control'] = AutomationControlView(self.content_area, self.system_service)
        
        # Start with dashboard
        self.switch_view('dashboard')
    
    def _setup_bindings(self):
        """Setup keyboard shortcuts and event bindings"""
        self.root.bind("<Control-q>", lambda e: self.quit_application())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Control-r>", lambda e: self.refresh_current_view())
        
        # Window close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.quit_application)
    
    def switch_view(self, view_name):
        """Switch to specified view"""
        if self.current_view:
            self.current_view.pack_forget()
        
        if view_name in self.views:
            self.current_view = self.views[view_name]
            self.current_view.pack(fill=BOTH, expand=True)
            self.app_state["current_view"] = view_name
            
            # Refresh view if it has refresh method
            if hasattr(self.current_view, 'refresh'):
                self.current_view.refresh()
    
    def _handle_ai_todo_created(self, event_data):
        """Handle AI TODO creation event"""
        # Refresh task management view if it's currently visible
        if (self.app_state["current_view"] == "task_management" and 
            hasattr(self.views['task_management'], 'refresh')):
            self.views['task_management'].refresh()
    
    def refresh_current_view(self):
        """Refresh the current view"""
        if self.current_view and hasattr(self.current_view, 'refresh'):
            self.current_view.refresh()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        self.root.attributes('-fullscreen', not self.root.attributes('-fullscreen'))
    
    def quit_application(self):
        """Gracefully quit the application"""
        if messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
            self.root.quit()
            self.root.destroy()
    
    def configure_application(self):
        """Configure application after initialization"""
        # Any additional configuration can go here
        pass
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()


# For backward compatibility with original main.py
ModernGUIApplication = EnhancedModernGUIApplication