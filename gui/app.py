"""
🎯 Modern GUI Control Center - Main Application Controller

This module implements the main application controller using MVP (Model-View-Presenter)
architecture with modern Tkinter styling and real-time system integration.
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

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False

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
    from widgets.enhanced_nlu_command_bar import CursorIntelligentCommandBar
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


class ModernGUIApplication:
    """Main GUI application controller"""
    
    def __init__(self, theme="darkly"):
        """Initialize the modern GUI application"""
        self.theme_name = theme if MODERN_STYLING else None
        self.root = None
        self.main_frame = None
        self.sidebar = None
        self.content_area = None
        self.current_view = None
        
        # Services (initialized after root window)
        self.system_service = None
        self.nlu_service = None
        
        # Views
        self.views = {}
        
        # State
        self.app_state = {
            "current_view": "dashboard",
            "sidebar_collapsed": False,
            "window_geometry": "1400x900",
            "last_update": None
        }
        
        # Initialize application
        self._create_root_window()
        self._initialize_services()
        self._setup_styles()
        self._create_main_layout()
        self._create_views()
        self._setup_bindings()
        
    def _create_root_window(self):
        """Create and configure the root window"""
        if MODERN_STYLING:
            self.root = ttk.Window(themename=self.theme_name)
        else:
            self.root = tk.Tk()
            
        # Window configuration
        self.root.title("🎯 Modern GUI Control Center - AI System Monorepo")
        self.root.geometry(self.app_state["window_geometry"])
        self.root.minsize(1200, 800)
        
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1400 // 2)
        y = (self.root.winfo_screenheight() // 2) - (900 // 2)
        self.root.geometry(f"1400x900+{x}+{y}")
        
        # Configure window properties
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _initialize_services(self):
        """Initialize services after root window is created"""
        # System Service
        self.system_service = SystemService(self.root)
        
        # Initialize NLU Integration Service
        try:
            self.nlu_service = get_nlu_service(self.system_service.bus)
            self.nlu_service.start()
            print("🤖 NLU Integration Service initialized")
        except Exception as e:
            print(f"⚠️ NLU Service initialization failed: {e}")
            self.nlu_service = None
        
    def _setup_styles(self):
        """Setup modern styling for the application"""
        if MODERN_STYLING:
            # ttkbootstrap handles most styling automatically
            style = ttk.Style()
        else:
            # Configure manual styling for standard tkinter
            style = ttk.Style()
            style.theme_use('clam')  # Use a more modern theme
            
        # Apply custom theme configurations
        ModernTheme.apply_styles(self.root, MODERN_STYLING)
        
    def _create_main_layout(self):
        """Create the main application layout"""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=BOTH, expand=True, padx=2, pady=2)
        
        # Create sidebar
        self._create_sidebar()
        
        # Create content area
        self._create_content_area()
        
    def _create_sidebar(self):
        """Create the navigation sidebar"""
        sidebar_width = 250 if not self.app_state["sidebar_collapsed"] else 60
        
        self.sidebar = ttk.Frame(self.main_frame, width=sidebar_width)
        self.sidebar.pack(side=LEFT, fill=Y, padx=(0, 2))
        self.sidebar.pack_propagate(False)
        
        # Sidebar header
        header_frame = ttk.Frame(self.sidebar)
        header_frame.pack(fill=X, padx=10, pady=10)
        
        # Logo and title
        if not self.app_state["sidebar_collapsed"]:
            title_label = ttk.Label(
                header_frame, 
                text="🎯 Control Center", 
                font=("Inter", 16, "bold")
            )
            title_label.pack()
            
            # Collapse button
            collapse_btn = ttk.Button(
                header_frame,
                text="❮",
                width=3,
                command=self._toggle_sidebar
            )
            collapse_btn.pack(anchor=E, pady=(5, 0))
        else:
            # Expand button
            expand_btn = ttk.Button(
                header_frame,
                text="❯",
                width=3,
                command=self._toggle_sidebar
            )
            expand_btn.pack()
        
        # Navigation buttons
        self._create_navigation_buttons()
        
    def _create_navigation_buttons(self):
        """Create navigation buttons in sidebar"""
        nav_frame = ttk.Frame(self.sidebar)
        nav_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Navigation items
        nav_items = [
            ("🏠", "Dashboard", "dashboard"),
            ("📋", "Tasks", "task_management"),
            ("🤖", "Agents", "agent_control"),
            ("🧠", "Memory", "memory_intelligence"),
            ("📊", "Monitor", "monitoring"),
            ("🔄", "Automation", "automation_control"),
        ]
        
        self.nav_buttons = {}
        
        for icon, label, view_id in nav_items:
            btn_frame = ttk.Frame(nav_frame)
            btn_frame.pack(fill=X, pady=2)
            
            if self.app_state["sidebar_collapsed"]:
                # Icon-only buttons
                btn = ttk.Button(
                    btn_frame,
                    text=icon,
                    width=4,
                    command=lambda v=view_id: self._switch_view(v)
                )
            else:
                # Full buttons with icon and text
                btn = ttk.Button(
                    btn_frame,
                    text=f"{icon} {label}",
                    width=20,
                    command=lambda v=view_id: self._switch_view(v)
                )
            
            btn.pack(fill=X)
            self.nav_buttons[view_id] = btn
            
            # Highlight current view
            if view_id == self.app_state["current_view"]:
                if MODERN_STYLING:
                    btn.configure(bootstyle="primary")
                else:
                    btn.configure(style="Selected.TButton")
    
    def _create_content_area(self):
        """Create the main content area"""
        self.content_area = ttk.Frame(self.main_frame)
        self.content_area.pack(side=RIGHT, fill=BOTH, expand=True)
        
        # Content header
        self._create_content_header()
        
        # NLU Command Bar
        self._create_nlu_command_bar()
        
        # Content body (where views will be displayed)
        self.content_body = ttk.Frame(self.content_area)
        self.content_body.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
    def _create_content_header(self):
        """Create the content area header"""
        header_frame = ttk.Frame(self.content_area)
        header_frame.pack(fill=X, padx=10, pady=10)
        
        # Current view title
        self.view_title = ttk.Label(
            header_frame,
            text="Dashboard",
            font=("Inter", 20, "bold")
        )
        self.view_title.pack(side=LEFT)
        
        # Status indicators
        status_frame = ttk.Frame(header_frame)
        status_frame.pack(side=RIGHT)
        
        # System status indicator
        self.status_indicator = ttk.Label(
            status_frame,
            text="🟢 System Online",
            font=("Inter", 12)
        )
        self.status_indicator.pack(side=RIGHT, padx=10)
        
        # Last update time
        self.last_update_label = ttk.Label(
            status_frame,
            text="Updated: Just now",
            font=("Inter", 10),
            foreground="gray"
        )
        self.last_update_label.pack(side=RIGHT, padx=10)
        
    def _create_nlu_command_bar(self):
        """Create the NLU command bar for natural language input"""
        try:
            # Get NLU service instance
            nlu_service = get_nlu_service()
            
            # Create enhanced Cursor AI command bar
            self.nlu_command_bar = CursorIntelligentCommandBar(
                self.content_area,
                nlu_service=nlu_service,
                event_bus=self.system_service.bus if hasattr(self, 'system_service') else None
            )
            # Note: Command bar packs itself in _create_widgets(), no need to pack again
            
            # Subscribe to NLU events
            if hasattr(self, 'system_service') and self.system_service.bus:
                self.system_service.bus.subscribe("nlu_command_processed", self._handle_nlu_command)
                self.system_service.bus.subscribe("nlu_error", self._handle_nlu_error)
                self.system_service.bus.subscribe("cursor_todo_created", self._handle_cursor_todo_created)
                
        except Exception as e:
            print(f"Warning: Could not initialize NLU command bar: {e}")
            # Create fallback simple command bar
            self._create_simple_command_bar()
            
    def _create_simple_command_bar(self):
        """Create a simple command bar fallback"""
        command_frame = ttk.Frame(self.content_area)
        command_frame.pack(fill=X, padx=10, pady=5)
        
        ttk.Label(command_frame, text="Command:").pack(side=LEFT, padx=(0, 5))
        
        self.simple_command_entry = ttk.Entry(command_frame)
        self.simple_command_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        
        ttk.Button(command_frame, text="Execute", command=self._execute_simple_command).pack(side=LEFT)
        
    def _execute_simple_command(self):
        """Execute simple command (placeholder)"""
        command = self.simple_command_entry.get()
        if command:
            print(f"Executing command: {command}")
            self.simple_command_entry.delete(0, 'end')
            
    def _handle_nlu_command(self, event_data):
        """Handle processed NLU command"""
        intent = event_data.get('intent')
        params = event_data.get('params', {})
        
        # Route commands to appropriate handlers
        if intent == 'navigate_view':
            view_name = params.get('view')
            if view_name in self.views:
                self.show_view(view_name)
        elif intent == 'create_task':
            task_name = params.get('task_name', 'New Task')
            self.system_service.bus.publish("new_task", {"name": task_name})
        elif intent == 'refresh_view':
            self._refresh_current_view()
        # Add more intent handling as needed
        
    def _handle_nlu_error(self, event_data):
        """Handle NLU processing errors"""
        error_msg = event_data.get('error', 'Unknown NLU error')
        print(f"NLU Error: {error_msg}")
        
    def _create_views(self):
        """Create all application views"""
        try:
            # Dashboard view
            self.views["dashboard"] = DashboardView(self.content_body, self.system_service)
            
            # Task management view
            self.views["task_management"] = TaskManagementView(self.content_body, self.system_service)
            
            # Agent control view
            self.views["agent_control"] = AgentControlView(self.content_body, self.system_service)
            
            # Memory intelligence view
            self.views["memory_intelligence"] = MemoryIntelligenceView(self.content_body, self.system_service)
            
            # Monitoring view
            self.views["monitoring"] = MonitoringView(self.content_body, self.system_service)
            
            # Automation control view
            self.views["automation_control"] = AutomationControlView(self.content_body, self.system_service)
            
            # Show initial view
            self._switch_view("dashboard")
            
        except Exception as e:
            print(f"❌ Views failed to load: {e}")
            import traceback
            traceback.print_exc()
            # Create minimal dashboard view as fallback
            self._create_minimal_dashboard()
    
    def _create_minimal_dashboard(self):
        """Create a minimal dashboard view as fallback"""
        minimal_frame = ttk.Frame(self.content_body)
        minimal_frame.pack(fill=BOTH, expand=True)
        
        # Welcome message
        welcome_label = ttk.Label(
            minimal_frame,
            text="🎯 Modern GUI Control Center",
            font=("Inter", 24, "bold")
        )
        welcome_label.pack(pady=50)
        
        info_label = ttk.Label(
            minimal_frame,
            text="System initialized successfully!\nViews are loading...",
            font=("Inter", 14),
            justify="center"
        )
        info_label.pack(pady=20)
        
        self.views["dashboard"] = minimal_frame
        
    def _setup_bindings(self):
        """Setup keyboard shortcuts and event bindings"""
        # Essential shortcuts
        self.root.bind("<Control-q>", lambda e: self._on_closing())
        self.root.bind("<F11>", lambda e: self._toggle_fullscreen())
        self.root.bind("<Control-r>", lambda e: self._refresh_current_view())
        
        # Event-driven shortcuts
        self.root.bind("<Control-n>", lambda e: self.system_service.bus.publish("new_task", {}))
        self.root.bind("<F5>", lambda e: self.system_service.bus.publish("global_refresh", {}))
        self.root.bind("<Control-t>", lambda e: self._switch_view("task_management"))
        self.root.bind("<Control-d>", lambda e: self._switch_view("dashboard"))
        self.root.bind("<Control-a>", lambda e: self._switch_view("agent_control"))
        self.root.bind("<Control-m>", lambda e: self._switch_view("memory_intelligence"))
        self.root.bind("<Control-Shift-m>", lambda e: self._switch_view("monitoring"))
        self.root.bind("<Control-u>", lambda e: self._switch_view("automation_control"))
        
        # Window events
        self.root.bind("<Configure>", self._on_window_configure)
        
    def _toggle_sidebar(self):
        """Toggle sidebar collapse/expand"""
        self.app_state["sidebar_collapsed"] = not self.app_state["sidebar_collapsed"]
        
        # Recreate sidebar with new state
        self.sidebar.destroy()
        self._create_sidebar()
        
    def _switch_view(self, view_id):
        """Switch to a different view"""
        if view_id not in self.views:
            messagebox.showerror("Error", f"View '{view_id}' not found!")
            return
            
        # Hide current view
        if self.current_view:
            self.current_view.pack_forget()
            
        # Update state
        self.app_state["current_view"] = view_id
        
        # Show new view
        self.current_view = self.views[view_id]
        self.current_view.pack(fill=BOTH, expand=True)
        
        # Update view title
        view_titles = {
            "dashboard": "Dashboard",
            "task_management": "Task Management",
            "agent_control": "Agent Control",
            "memory_intelligence": "Memory Intelligence",
            "monitoring": "System Monitoring",
            "automation_control": "Automation Control"
        }
        
        self.view_title.configure(text=view_titles.get(view_id, "Unknown View"))
        
        # Update navigation button styles
        self._update_nav_button_styles(view_id)
        
        # Refresh the view
        if hasattr(self.current_view, 'refresh'):
            self.current_view.refresh()
            
    def _update_nav_button_styles(self, active_view):
        """Update navigation button styles to show active view"""
        for view_id, button in self.nav_buttons.items():
            if view_id == active_view:
                if MODERN_STYLING:
                    button.configure(bootstyle="primary")
                else:
                    button.configure(state="active")
            else:
                if MODERN_STYLING:
                    button.configure(bootstyle="secondary")
                else:
                    button.configure(state="normal")
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        current_state = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not current_state)
        
    def _refresh_current_view(self):
        """Refresh the current view"""
        if self.current_view and hasattr(self.current_view, 'refresh'):
            self.current_view.refresh()
            
        # Update last update time
        current_time = datetime.now().strftime("%H:%M:%S")
        self.last_update_label.configure(text=f"Updated: {current_time}")
        
    def _on_window_configure(self, event):
        """Handle window resize events"""
        if event.widget == self.root:
            # Save window geometry
            self.app_state["window_geometry"] = self.root.geometry()
            
    def _on_closing(self):
        """Handle application closing"""
        try:
            # Save application state
            self._save_app_state()
            
            # Stop any background threads
            if hasattr(self.system_service, 'stop'):
                self.system_service.stop()
                
            # Destroy the window
            self.root.destroy()
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.root.destroy()
    
    def _save_app_state(self):
        """Save application state to file"""
        try:
            state_file = Path("memory-bank/gui-app-state.json")
            state_file.parent.mkdir(exist_ok=True)
            
            with open(state_file, 'w') as f:
                json.dump(self.app_state, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save app state: {e}")
    
    def configure_application(self):
        """Configure the application after initialization"""
        # Load previous state if available
        self._load_app_state()
        
        # Start background services
        self._start_background_services()
        
    def _load_app_state(self):
        """Load application state from file"""
        try:
            state_file = Path("memory-bank/gui-app-state.json")
            if state_file.exists():
                with open(state_file, 'r') as f:
                    saved_state = json.load(f)
                    self.app_state.update(saved_state)
                    
        except Exception as e:
            print(f"Warning: Could not load app state: {e}")
    
    def _start_background_services(self):
        """Start background services for real-time updates"""
        def update_loop():
            """Background update loop"""
            while True:
                try:
                    # Update system status
                    self._update_system_status()
                    
                    # Sleep for 5 seconds
                    threading.Event().wait(5)
                    
                except Exception as e:
                    print(f"Background update error: {e}")
                    threading.Event().wait(10)  # Wait longer on error
        
        # Start background thread
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
        
    def _update_system_status(self):
        """Update system status indicators"""
        try:
            # Get system health from service
            system_health = self.system_service.get_system_health()
            
            # Update status indicator
            if system_health.get("overall_status") == "healthy":
                status_text = "🟢 System Online"
                status_color = "green"
            elif system_health.get("overall_status") == "warning":
                status_text = "🟡 System Warning"
                status_color = "orange"
            else:
                status_text = "🔴 System Issues"
                status_color = "red"
                
            # Update UI from main thread
            self.root.after(0, lambda: self.status_indicator.configure(
                text=status_text,
                foreground=status_color
            ))
            
        except Exception as e:
            print(f"Status update error: {e}")
    
    def _handle_cursor_todo_created(self, **kwargs):
        """Handle Cursor AI TODO creation events"""
        try:
            print(f"✅ Cursor AI created TODO: {kwargs.get('task_id', 'Unknown')}")
            
            # Refresh task management view if it's currently visible
            if (hasattr(self, 'current_view') and 
                hasattr(self.current_view, 'refresh') and
                self.current_view.__class__.__name__ == 'TaskManagementView'):
                self.current_view.refresh()
                
        except Exception as e:
            print(f"Error handling Cursor TODO creation: {e}")
    
    def run(self):
        """Start the GUI application main loop"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\n🛑 Application interrupted by user")
            self._on_closing()
        except Exception as e:
            print(f"❌ Application error: {e}")
            import traceback
            traceback.print_exc()
