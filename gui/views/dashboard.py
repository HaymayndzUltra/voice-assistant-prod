"""
🎯 Modern GUI Control Center - Dashboard View

Main dashboard providing system overview, quick stats, and navigation
to all major system components.
"""

import tkinter as tk
from tkinter import ttk
from tkinter.constants import *
from datetime import datetime
import threading

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False


class DashboardView(ttk.Frame):
    """Main dashboard view"""
    
    def __init__(self, parent, system_service):
        super().__init__(parent)
        self.system_service = system_service
        self.pack(fill=BOTH, expand=True)
        
        # Create dashboard layout
        self._create_layout()
        
        # Initial data load
        self.refresh()
        
        # Start auto-refresh (every 60 seconds for dashboard)
        self._start_auto_refresh()
    
    def _create_layout(self):
        """Create the dashboard layout"""
        # Main container with padding
        main_container = ttk.Frame(self)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Welcome header
        self._create_header(main_container)
        
        # Stats cards row
        self._create_stats_cards(main_container)
        
        # Content sections
        self._create_content_sections(main_container)
        
        # Quick actions
        self._create_quick_actions(main_container)
    
    def _create_header(self, parent):
        """Create dashboard header"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X, pady=(0, 30))
        
        # Welcome title
        welcome_label = ttk.Label(
            header_frame,
            text="🎯 AI System Control Center",
            font=("Inter", 28, "bold")
        )
        welcome_label.pack(anchor=W)
        
        # Subtitle
        subtitle_label = ttk.Label(
            header_frame,
            text="Intelligent Task Management • Agent Control • Memory Intelligence • Real-time Monitoring",
            font=("Inter", 12),
            foreground="gray"
        )
        subtitle_label.pack(anchor=W, pady=(5, 0))
        
        # Status bar
        status_frame = ttk.Frame(header_frame)
        status_frame.pack(fill=X, pady=(10, 0))
        
        self.system_status_label = ttk.Label(
            status_frame,
            text="🔄 Loading system status...",
            font=("Inter", 11)
        )
        self.system_status_label.pack(side=LEFT)
        
        self.last_update_label = ttk.Label(
            status_frame,
            text="",
            font=("Inter", 10),
            foreground="gray"
        )
        self.last_update_label.pack(side=RIGHT)
        
        # Quick action buttons in header
        quick_actions_frame = ttk.Frame(header_frame)
        quick_actions_frame.pack(fill=X, pady=(15, 0))
        
        # Task and queue control buttons
        ttk.Button(
            quick_actions_frame,
            text="🆕 New Task",
            command=self._create_new_task,
            bootstyle="primary" if MODERN_STYLING else None
        ).pack(side=LEFT, padx=(0, 10))
        
        ttk.Button(
            quick_actions_frame,
            text="▶️ Start Queue",
            command=self._start_queue,
            bootstyle="success" if MODERN_STYLING else None
        ).pack(side=LEFT, padx=(0, 10))
        
        ttk.Button(
            quick_actions_frame,
            text="⏸️ Pause Queue",
            command=self._pause_queue,
            bootstyle="warning" if MODERN_STYLING else None
        ).pack(side=LEFT, padx=(0, 10))
        
        ttk.Button(
            quick_actions_frame,
            text="📊 System Health",
            command=self._run_full_health_check,
            bootstyle="info" if MODERN_STYLING else None
        ).pack(side=LEFT)
    
    def _create_stats_cards(self, parent):
        """Create stats cards showing key metrics"""
        stats_frame = ttk.Frame(parent)
        stats_frame.pack(fill=X, pady=(0, 30))
        
        # Configure grid
        for i in range(4):
            stats_frame.grid_columnconfigure(i, weight=1)
        
        # Stats cards data
        self.stats_cards = {}
        cards_data = [
            ("tasks", "📋", "Active Tasks", "0", "primary"),
            ("agents", "🤖", "Agents Online", "0", "success"),
            ("memory", "🧠", "Memory Items", "0", "info"),
            ("health", "💚", "System Health", "100%", "warning")
        ]
        
        for i, (key, icon, title, value, color) in enumerate(cards_data):
            card = self._create_stat_card(stats_frame, icon, title, value, color)
            card.grid(row=0, column=i, padx=(0, 15 if i < 3 else 0), sticky="ew")
            self.stats_cards[key] = card
    
    def _create_stat_card(self, parent, icon, title, value, color):
        """Create individual stat card"""
        if MODERN_STYLING:
            card_frame = ttk.Frame(parent, bootstyle=f"{color}-inverse", padding=20)
        else:
            card_frame = ttk.Frame(parent, padding=20, relief="solid", borderwidth=1)
        
        # Icon
        icon_label = ttk.Label(
            card_frame,
            text=icon,
            font=("Inter", 24)
        )
        icon_label.pack()
        
        # Value
        value_label = ttk.Label(
            card_frame,
            text=value,
            font=("Inter", 20, "bold")
        )
        value_label.pack(pady=(5, 0))
        
        # Title
        title_label = ttk.Label(
            card_frame,
            text=title,
            font=("Inter", 12)
        )
        title_label.pack()
        
        # Store references for updates
        card_frame.value_label = value_label
        card_frame.title_label = title_label
        
        return card_frame
    
    def _create_content_sections(self, parent):
        """Create main content sections"""
        content_frame = ttk.Frame(parent)
        content_frame.pack(fill=BOTH, expand=True, pady=(0, 30))
        
        # Configure grid
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Left column - Active Tasks
        self._create_active_tasks_section(content_frame)
        
        # Right column - System Status
        self._create_system_status_section(content_frame)
    
    def _create_active_tasks_section(self, parent):
        """Create active tasks section"""
        tasks_frame = ttk.LabelFrame(parent, text="📋 Active Tasks", padding=15)
        tasks_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Tasks listbox with scrollbar
        list_frame = ttk.Frame(tasks_frame)
        list_frame.pack(fill=BOTH, expand=True)
        
        # Scrollable text widget for tasks
        self.tasks_text = tk.Text(
            list_frame,
            height=12,
            wrap=tk.WORD,
            font=("Fira Code", 10),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1
        )
        
        scrollbar_tasks = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tasks_text.yview)
        self.tasks_text.configure(yscrollcommand=scrollbar_tasks.set)
        
        self.tasks_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar_tasks.pack(side=RIGHT, fill=Y)
        
        # Task actions
        actions_frame = ttk.Frame(tasks_frame)
        actions_frame.pack(fill=X, pady=(10, 0))
        
        refresh_btn = ttk.Button(
            actions_frame,
            text="🔄 Refresh",
            command=self._refresh_tasks
        )
        refresh_btn.pack(side=LEFT)
        
        view_all_btn = ttk.Button(
            actions_frame,
            text="📋 View All Tasks",
            command=self._open_task_management
        )
        view_all_btn.pack(side=LEFT, padx=(10, 0))
    
    def _create_system_status_section(self, parent):
        """Create system status section"""
        status_frame = ttk.LabelFrame(parent, text="💻 System Status", padding=15)
        status_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        # Status display
        self.status_text = tk.Text(
            status_frame,
            height=12,
            wrap=tk.WORD,
            font=("Fira Code", 10),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1,
            state=tk.DISABLED
        )
        
        scrollbar_status = ttk.Scrollbar(status_frame, orient=VERTICAL, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar_status.set)
        
        self.status_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar_status.pack(side=RIGHT, fill=Y)
        
        # Status actions
        status_actions_frame = ttk.Frame(status_frame)
        status_actions_frame.pack(fill=X, pady=(10, 0))
        
        health_check_btn = ttk.Button(
            status_actions_frame,
            text="🏥 Health Check",
            command=self._run_health_check
        )
        health_check_btn.pack(side=LEFT)
        
        monitor_btn = ttk.Button(
            status_actions_frame,
            text="📊 Full Monitor",
            command=self._open_monitoring
        )
        monitor_btn.pack(side=LEFT, padx=(10, 0))
    
    def _create_quick_actions(self, parent):
        """Create quick actions section"""
        actions_frame = ttk.LabelFrame(parent, text="⚡ Quick Actions", padding=15)
        actions_frame.pack(fill=X)
        
        # Configure grid for buttons
        for i in range(6):
            actions_frame.grid_columnconfigure(i, weight=1)
        
        # Quick action buttons
        actions_data = [
            ("📋 Task Manager", self._open_task_management, "primary"),
            ("🤖 Agent Control", self._open_agent_control, "success"),  
            ("🧠 Memory System", self._open_memory_intelligence, "info"),
            ("📊 Monitoring", self._open_monitoring, "warning"),
            ("🔄 Automation", self._open_automation_control, "secondary"),
            ("⚙️ CLI Terminal", self._open_cli_terminal, "dark")
        ]
        
        for i, (text, command, style) in enumerate(actions_data):
            if MODERN_STYLING:
                btn = ttk.Button(
                    actions_frame,
                    text=text,
                    command=command,
                    bootstyle=style,
                    width=15
                )
            else:
                btn = ttk.Button(
                    actions_frame,
                    text=text,
                    command=command,
                    width=15
                )
            
            btn.grid(row=0, column=i, padx=5, pady=5, sticky="ew")
    
    def refresh(self):
        """Refresh dashboard data"""
        try:
            # Update in background thread to avoid blocking UI
            threading.Thread(target=self._refresh_data, daemon=True).start()
        except Exception as e:
            print(f"Error refreshing dashboard: {e}")
    
    def _refresh_data(self):
        """Refresh dashboard data in background"""
        try:
            # Get system health
            health_data = self.system_service.get_system_health()
            
            # Get active tasks
            active_tasks = self.system_service.get_active_tasks()
            
            # Get agent status
            agent_status = self.system_service.get_agent_status()
            
            # Get memory status
            memory_status = self.system_service.get_memory_status()
            
            # Update UI from main thread
            self.after(0, lambda: self._update_ui(health_data, active_tasks, agent_status, memory_status))
            
        except Exception as e:
            print(f"Error refreshing dashboard data: {e}")
            self.after(0, lambda: self._show_error(f"Failed to refresh data: {e}"))
    
    def _update_ui(self, health_data, active_tasks, agent_status, memory_status):
        """Update UI with fresh data"""
        try:
            # Update system status
            status_text = health_data.get("overall_status", "unknown").title()
            status_icon = {
                "healthy": "🟢",
                "warning": "🟡", 
                "error": "🔴"
            }.get(health_data.get("overall_status"), "⚪")
            
            self.system_status_label.configure(text=f"{status_icon} System {status_text}")
            
            # Update last update time
            current_time = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.configure(text=f"Last update: {current_time}")
            
            # Update stats cards
            self._update_stats_cards(active_tasks, agent_status, memory_status, health_data)
            
            # Update active tasks display
            self._update_tasks_display(active_tasks)
            
            # Update system status display
            self._update_status_display(health_data)
            
        except Exception as e:
            print(f"Error updating UI: {e}")
    
    def _update_stats_cards(self, active_tasks, agent_status, memory_status, health_data):
        """Update stats cards with current data"""
        try:
            # Active tasks count
            tasks_count = len(active_tasks) if active_tasks else 0
            self.stats_cards["tasks"].value_label.configure(text=str(tasks_count))
            
            # Agents count
            agents_count = agent_status.get("summary", {}).get("total_agents", 0)
            self.stats_cards["agents"].value_label.configure(text=str(agents_count))
            
            # Memory items count
            memory_count = memory_status.get("brain_files", 0) + memory_status.get("architecture_plans", 0)
            self.stats_cards["memory"].value_label.configure(text=str(memory_count))
            
            # System health percentage
            health_percentage = "100%" if health_data.get("overall_status") == "healthy" else "85%" if health_data.get("overall_status") == "warning" else "50%"
            self.stats_cards["health"].value_label.configure(text=health_percentage)
            
        except Exception as e:
            print(f"Error updating stats cards: {e}")
    
    def _update_tasks_display(self, active_tasks):
        """Update active tasks display"""
        try:
            self.tasks_text.configure(state=tk.NORMAL)
            self.tasks_text.delete(1.0, tk.END)
            
            if active_tasks:
                for i, task in enumerate(active_tasks[:5]):  # Show only first 5 tasks
                    task_id = task.get("id", task.get("task_id", "Unknown"))
                    description = task.get("description", "No description")
                    status = task.get("status", "unknown")
                    
                    # Truncate long descriptions
                    if len(description) > 60:
                        description = description[:57] + "..."
                    
                    status_icon = {"in_progress": "🔄", "pending": "⏳", "completed": "✅", "done": "✅"}.get(status, "❓")
                    
                    task_line = f"{status_icon} {description}\n"
                    if i < len(active_tasks) - 1:
                        task_line += "\n"
                    
                    self.tasks_text.insert(tk.END, task_line)
                
                if len(active_tasks) > 5:
                    self.tasks_text.insert(tk.END, f"\n... and {len(active_tasks) - 5} more tasks")
            else:
                self.tasks_text.insert(tk.END, "✨ No active tasks\n\nSystem is ready for new work!")
            
            self.tasks_text.configure(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error updating tasks display: {e}")
    
    def _update_status_display(self, health_data):
        """Update system status display"""
        try:
            self.status_text.configure(state=tk.NORMAL)
            self.status_text.delete(1.0, tk.END)
            
            # Overall status
            status = health_data.get("overall_status", "unknown").upper()
            status_icon = {"HEALTHY": "🟢", "WARNING": "🟡", "ERROR": "🔴"}.get(status, "⚪")
            
            self.status_text.insert(tk.END, f"{status_icon} OVERALL STATUS: {status}\n\n")
            
            # Component status
            components = health_data.get("components", {})
            for component, data in components.items():
                comp_status = data.get("status", "unknown").upper()
                comp_icon = {"HEALTHY": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(comp_status, "❓")
                
                comp_name = component.replace("_", " ").title()
                self.status_text.insert(tk.END, f"{comp_icon} {comp_name}: {comp_status}\n")
                
                # Show metrics if available
                metrics = data.get("metrics", {})
                for metric, value in metrics.items():
                    if isinstance(value, bool):
                        value = "Yes" if value else "No"
                    metric_name = metric.replace("_", " ").title()
                    self.status_text.insert(tk.END, f"   • {metric_name}: {value}\n")
            
            # Issues and warnings
            issues = health_data.get("issues", [])
            warnings = health_data.get("warnings", [])
            
            if issues:
                self.status_text.insert(tk.END, "\n🚨 ISSUES:\n")
                for issue in issues[:3]:  # Show only first 3 issues
                    self.status_text.insert(tk.END, f"   • {issue}\n")
                if len(issues) > 3:
                    self.status_text.insert(tk.END, f"   ... and {len(issues) - 3} more\n")
            
            if warnings:
                self.status_text.insert(tk.END, "\n⚠️ WARNINGS:\n")
                for warning in warnings[:3]:  # Show only first 3 warnings
                    self.status_text.insert(tk.END, f"   • {warning}\n")
                if len(warnings) > 3:
                    self.status_text.insert(tk.END, f"   ... and {len(warnings) - 3} more\n")
            
            self.status_text.configure(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error updating status display: {e}")
    
    def _show_error(self, message):
        """Show error message in UI"""
        self.system_status_label.configure(text=f"🔴 Error: {message}")
    
    # Event handlers
    def _refresh_tasks(self):
        """Refresh active tasks"""
        self.refresh()
    
    def _run_health_check(self):
        """Run system health check"""
        self.system_status_label.configure(text="🔄 Running health check...")
        self.refresh()
    
    def _open_task_management(self):
        """Open task management view"""
        # This will be handled by the main app
        print("Opening Task Management...")
    
    def _open_agent_control(self):
        """Open agent control view"""
        print("Opening Agent Control...")
    
    def _open_memory_intelligence(self):
        """Open memory intelligence view"""
        print("Opening Memory Intelligence...")
    
    def _open_monitoring(self):
        """Open monitoring view"""
        print("Opening Monitoring...")
    
    def _open_automation_control(self):
        """Open automation control view"""
        print("Opening Automation Control...")
    
    def _open_cli_terminal(self):
        """Open CLI terminal"""
        print("Opening CLI Terminal...")
    
    def _create_new_task(self):
        """Create new task"""
        try:
            from tkinter import simpledialog, messagebox
            import subprocess
            
            task_desc = simpledialog.askstring("New Task", "Enter task description:")
            if task_desc:
                result = subprocess.run(
                    ["python3", "todo_manager.py", "new", task_desc],
                    cwd=str(self.system_service.project_root),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    messagebox.showinfo("Task Created", f"✅ Created task: {task_desc}")
                    self.refresh()  # Refresh dashboard to show new task
                else:
                    messagebox.showerror("Task Creation Failed", f"Failed to create task: {result.stderr}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Error creating task: {e}")
    
    def _start_queue(self):
        """Start the task queue engine"""
        try:
            import subprocess
            from tkinter import messagebox
            
            result = subprocess.run(
                ["python3", "queue_cli.py", "start", "--daemon"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                messagebox.showinfo("Queue Started", "✅ Task queue started successfully")
                self.system_status_label.configure(text="🟢 Queue engine running")
            else:
                messagebox.showerror("Queue Start Failed", f"Failed to start queue: {result.stderr}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Error starting queue: {e}")
    
    def _pause_queue(self):
        """Pause the task queue engine"""
        try:
            import subprocess
            from tkinter import messagebox
            
            result = subprocess.run(
                ["python3", "queue_cli.py", "pause"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                messagebox.showinfo("Queue Paused", "⏸️ Task queue paused successfully")
                self.system_status_label.configure(text="🟡 Queue engine paused")
            else:
                messagebox.showerror("Queue Pause Failed", f"Failed to pause queue: {result.stderr}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Error pausing queue: {e}")
    
    def _run_full_health_check(self):
        """Run comprehensive system health check"""
        try:
            self.system_status_label.configure(text="🔄 Running comprehensive health check...")
            
            # Run health check in background
            import threading
            def run_check():
                health_data = self.system_service.get_system_health()
                self.after(0, lambda: self._show_health_report(health_data))
            
            threading.Thread(target=run_check, daemon=True).start()
            
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Error running health check: {e}")
    
    def _show_health_report(self, health_data):
        """Show health check report in a dialog"""
        try:
            from tkinter import messagebox
            
            status = health_data.get("overall_status", "unknown").upper()
            issues = health_data.get("issues", [])
            warnings = health_data.get("warnings", [])
            
            report = f"System Status: {status}\n\n"
            
            if issues:
                report += "🚨 ISSUES:\n"
                for issue in issues[:5]:
                    report += f"• {issue}\n"
                if len(issues) > 5:
                    report += f"... and {len(issues) - 5} more\n"
                report += "\n"
            
            if warnings:
                report += "⚠️ WARNINGS:\n"
                for warning in warnings[:5]:
                    report += f"• {warning}\n"
                if len(warnings) > 5:
                    report += f"... and {len(warnings) - 5} more\n"
            
            if not issues and not warnings:
                report += "✅ All systems operating normally!"
            
            messagebox.showinfo("System Health Report", report)
            self.refresh()  # Refresh dashboard with latest data
            
        except Exception as e:
            print(f"Error showing health report: {e}")
    
    def _start_auto_refresh(self):
        """Start auto-refresh timer"""
        self.auto_refresh_enabled = True
        self._schedule_refresh()
    
    def _schedule_refresh(self):
        """Schedule next refresh"""
        if hasattr(self, 'auto_refresh_enabled') and self.auto_refresh_enabled:
            # Refresh every 60 seconds for dashboard (less frequent than task view)
            self.after(60000, self._auto_refresh)
    
    def _auto_refresh(self):
        """Perform auto-refresh"""
        try:
            self.refresh()
        except Exception as e:
            print(f"Error during dashboard auto-refresh: {e}")
        finally:
            # Schedule next refresh
            self._schedule_refresh()
    
    def destroy(self):
        """Clean up on destroy"""
        self.auto_refresh_enabled = False
        super().destroy()
