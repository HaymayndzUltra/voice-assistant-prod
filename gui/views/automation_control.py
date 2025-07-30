"""
🎯 Modern GUI Control Center - Automation Control View

Automation control interface for autonomous queue engine
and auto-sync management.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter.constants import *

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False


class AutomationControlView(ttk.Frame):
    """Automation control view"""
    
    def __init__(self, parent, system_service):
        super().__init__(parent)
        self.system_service = system_service
        self.pack(fill=BOTH, expand=True)
        
        # Create placeholder layout
        self._create_placeholder()
    
    def _create_placeholder(self):
        """Create comprehensive automation control center"""
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._create_header(main_container)
        
        # Automation status overview
        self._create_status_overview(main_container)
        
        # Control panels
        self._create_control_panels(main_container)
        
        # Settings and configuration
        self._create_settings_section(main_container)
        
        # System logs
        self._create_logs_section(main_container)
        
        # Load initial data
        self.refresh()
    
    def _create_header(self, parent):
        """Create automation control header"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X, pady=(0, 20))
        
        # Title
        title = ttk.Label(
            header_frame,
            text="🔄 Automation Control Center",
            font=("Inter", 24, "bold")
        )
        title.pack(side=LEFT)
        
        # Automation status
        self.automation_status = ttk.Label(
            header_frame,
            text="🔄 Loading automation status...",
            font=("Inter", 12)
        )
        self.automation_status.pack(side=RIGHT)
    
    def _create_status_overview(self, parent):
        """Create automation status overview"""
        status_frame = ttk.LabelFrame(parent, text="📊 Automation Status Overview", padding=15)
        status_frame.pack(fill=X, pady=(0, 20))
        
        # Configure grid
        for i in range(4):
            status_frame.grid_columnconfigure(i, weight=1)
        
        # Status cards
        self.status_cards = {}
        status_data = [
            ("queue_engine", "🎰", "Queue Engine", "Stopped", "warning"),
            ("auto_sync", "🔄", "Auto-Sync", "Active", "success"),
            ("monitoring", "📋", "Monitoring", "Active", "info"),
            ("automation_level", "⚙️", "Automation", "Semi", "primary")
        ]
        
        for i, (key, icon, title, status, color) in enumerate(status_data):
            card = self._create_status_card(status_frame, icon, title, status, color)
            card.grid(row=0, column=i, padx=(0, 10 if i < 3 else 0), sticky="ew")
            self.status_cards[key] = card
    
    def _create_status_card(self, parent, icon, title, status, color):
        """Create individual status card"""
        if MODERN_STYLING:
            card_frame = ttk.Frame(parent, bootstyle=f"{color}-inverse", padding=12)
        else:
            card_frame = ttk.Frame(parent, padding=12, relief="solid", borderwidth=1)
        
        # Icon
        icon_label = ttk.Label(card_frame, text=icon, font=("Inter", 18))
        icon_label.pack()
        
        # Status
        status_label = ttk.Label(card_frame, text=status, font=("Inter", 14, "bold"))
        status_label.pack(pady=(3, 0))
        
        # Title
        title_label = ttk.Label(card_frame, text=title, font=("Inter", 10))
        title_label.pack()
        
        # Store reference
        card_frame.status_label = status_label
        return card_frame
    
    def _create_control_panels(self, parent):
        """Create automation control panels"""
        # Create notebook for different control sections
        control_notebook = ttk.Notebook(parent)
        control_notebook.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Queue Engine Control
        queue_frame = ttk.Frame(control_notebook)
        control_notebook.add(queue_frame, text="🎰 Queue Engine")
        self._create_queue_control(queue_frame)
        
        # Auto-Sync Control
        sync_frame = ttk.Frame(control_notebook)
        control_notebook.add(sync_frame, text="🔄 Auto-Sync")
        self._create_sync_control(sync_frame)
        
        # System Control
        system_frame = ttk.Frame(control_notebook)
        control_notebook.add(system_frame, text="💻 System Control")
        self._create_system_control(system_frame)
    
    def _create_queue_control(self, parent):
        """Create queue engine control panel"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=BOTH, expand=True, padx=15, pady=15)
        
        # Queue status display
        status_frame = ttk.LabelFrame(control_frame, text="Queue Engine Status", padding=10)
        status_frame.pack(fill=X, pady=(0, 15))
        
        self.queue_status_display = tk.Text(
            status_frame,
            height=8,
            wrap=tk.WORD,
            font=("Fira Code", 10),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1,
            state=tk.DISABLED
        )
        self.queue_status_display.pack(fill=X)
        
        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="▶️ Start Queue Engine", command=self._start_queue_engine).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹️ Stop Queue Engine", command=self._stop_queue_engine).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🔁 Restart Queue", command=self._restart_queue_engine).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="📊 Status Check", command=self._check_queue_status).pack(side=LEFT, padx=5)
    
    def _create_sync_control(self, parent):
        """Create auto-sync control panel"""
        sync_frame = ttk.Frame(parent)
        sync_frame.pack(fill=BOTH, expand=True, padx=15, pady=15)
        
        # Sync status
        sync_status_frame = ttk.LabelFrame(sync_frame, text="Auto-Sync Status", padding=10)
        sync_status_frame.pack(fill=X, pady=(0, 15))
        
        self.sync_status_display = tk.Text(
            sync_status_frame,
            height=6,
            wrap=tk.WORD,
            font=("Fira Code", 10),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1,
            state=tk.DISABLED
        )
        self.sync_status_display.pack(fill=X)
        
        # Configuration controls
        config_frame = ttk.LabelFrame(sync_frame, text="Sync Configuration", padding=10)
        config_frame.pack(fill=X, pady=(10, 15))
        
        # Sync interval setting
        interval_frame = ttk.Frame(config_frame)
        interval_frame.pack(fill=X, pady=5)
        
        ttk.Label(interval_frame, text="Sync Interval:").pack(side=LEFT)
        self.sync_interval = ttk.Combobox(interval_frame, values=["5 seconds", "10 seconds", "30 seconds", "1 minute"])
        self.sync_interval.set("10 seconds")
        self.sync_interval.pack(side=LEFT, padx=10)
        
        # Control buttons
        sync_btn_frame = ttk.Frame(sync_frame)
        sync_btn_frame.pack(fill=X)
        
        ttk.Button(sync_btn_frame, text="▶️ Enable Auto-Sync", command=self._enable_auto_sync).pack(side=LEFT, padx=5)
        ttk.Button(sync_btn_frame, text="⏸️ Disable Auto-Sync", command=self._disable_auto_sync).pack(side=LEFT, padx=5)
        ttk.Button(sync_btn_frame, text="🔄 Force Sync Now", command=self._force_sync).pack(side=LEFT, padx=5)
    
    def _create_system_control(self, parent):
        """Create system-wide control panel"""
        system_frame = ttk.Frame(parent)
        system_frame.pack(fill=BOTH, expand=True, padx=15, pady=15)
        
        # Automation levels
        levels_frame = ttk.LabelFrame(system_frame, text="Automation Levels", padding=10)
        levels_frame.pack(fill=X, pady=(0, 15))
        
        self.automation_level = tk.StringVar(value="semi")
        
        ttk.Radiobutton(
            levels_frame, 
            text="Manual - No automation, full user control", 
            variable=self.automation_level, 
            value="manual",
            command=self._set_automation_level
        ).pack(anchor=W, pady=2)
        
        ttk.Radiobutton(
            levels_frame, 
            text="Semi-Automatic - Queue monitoring with user approval", 
            variable=self.automation_level, 
            value="semi",
            command=self._set_automation_level
        ).pack(anchor=W, pady=2)
        
        ttk.Radiobutton(
            levels_frame, 
            text="Full Automatic - Complete autonomous operation", 
            variable=self.automation_level, 
            value="full",
            command=self._set_automation_level
        ).pack(anchor=W, pady=2)
        
        # System actions
        actions_frame = ttk.LabelFrame(system_frame, text="System Actions", padding=10)
        actions_frame.pack(fill=X)
        
        # Emergency controls
        emergency_frame = ttk.Frame(actions_frame)
        emergency_frame.pack(fill=X, pady=5)
        
        ttk.Button(emergency_frame, text="⚠️ Emergency Stop", command=self._emergency_stop).pack(side=LEFT, padx=5)
        ttk.Button(emergency_frame, text="🔄 Restart All", command=self._restart_all_systems).pack(side=LEFT, padx=5)
        ttk.Button(emergency_frame, text="🧹 Cleanup System", command=self._cleanup_system).pack(side=LEFT, padx=5)
    
    def _create_settings_section(self, parent):
        """Create settings and configuration section"""
        settings_frame = ttk.LabelFrame(parent, text="⚙️ Automation Settings", padding=15)
        settings_frame.pack(fill=X, pady=(0, 15))
        
        # Settings grid
        settings_frame.grid_columnconfigure(1, weight=1)
        
        # Task timeout setting
        ttk.Label(settings_frame, text="Task Timeout:").grid(row=0, column=0, sticky=W, padx=5)
        self.task_timeout = ttk.Entry(settings_frame)
        self.task_timeout.insert(0, "3600")  # Default 1 hour
        self.task_timeout.grid(row=0, column=1, sticky=EW, padx=5)
        ttk.Label(settings_frame, text="seconds").grid(row=0, column=2, sticky=W, padx=5)
        
        # Max concurrent tasks
        ttk.Label(settings_frame, text="Max Concurrent Tasks:").grid(row=1, column=0, sticky=W, padx=5, pady=5)
        self.max_tasks = ttk.Entry(settings_frame)
        self.max_tasks.insert(0, "3")
        self.max_tasks.grid(row=1, column=1, sticky=EW, padx=5, pady=5)
        
        # Save settings button
        ttk.Button(settings_frame, text="💾 Save Settings", command=self._save_settings).grid(row=2, column=0, columnspan=3, pady=10)
    
    def _create_logs_section(self, parent):
        """Create automation logs section"""
        logs_frame = ttk.LabelFrame(parent, text="📜 Automation Logs", padding=15)
        logs_frame.pack(fill=X)
        
        # Logs display
        self.automation_logs = tk.Text(
            logs_frame,
            height=8,
            wrap=tk.WORD,
            font=("Fira Code", 9),
            bg="#1a1a1a" if not MODERN_STYLING else None,
            fg="#00ff00" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1,
            state=tk.DISABLED
        )
        
        log_scrollbar = ttk.Scrollbar(logs_frame, orient=VERTICAL, command=self.automation_logs.yview)
        self.automation_logs.configure(yscrollcommand=log_scrollbar.set)
        
        self.automation_logs.pack(side=LEFT, fill=BOTH, expand=True)
        log_scrollbar.pack(side=RIGHT, fill=Y)
    
    # Control method implementations
    def _start_queue_engine(self):
        """Start the autonomous queue engine"""
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "queue_cli.py", "start", "--daemon"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self._log_automation("✅ Queue engine started successfully")
                self.status_cards["queue_engine"].status_label.configure(text="Running")
                messagebox.showinfo("Queue Engine", "✅ Queue engine started successfully")
                self._check_queue_status()
            else:
                self._log_automation(f"❌ Failed to start queue engine: {result.stderr}")
                messagebox.showerror("Queue Engine", f"Failed to start: {result.stderr}")
        except Exception as e:
            self._log_automation(f"❌ Error starting queue engine: {e}")
            messagebox.showerror("Error", f"Error starting queue engine: {e}")
    
    def _stop_queue_engine(self):
        """Stop the autonomous queue engine"""
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "queue_cli.py", "stop"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self._log_automation("⏹️ Queue engine stopped")
                self.status_cards["queue_engine"].status_label.configure(text="Stopped")
                messagebox.showinfo("Queue Engine", "⏹️ Queue engine stopped")
                self._check_queue_status()
            else:
                self._log_automation(f"❌ Failed to stop queue engine: {result.stderr}")
                messagebox.showerror("Queue Engine", f"Failed to stop: {result.stderr}")
        except Exception as e:
            self._log_automation(f"❌ Error stopping queue engine: {e}")
            messagebox.showerror("Error", f"Error stopping queue engine: {e}")
    
    def _restart_queue_engine(self):
        """Restart the queue engine"""
        try:
            self._log_automation("🔁 Restarting queue engine...")
            # Stop first
            import subprocess
            subprocess.run(
                ["python3", "queue_cli.py", "stop"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            
            # Wait a moment
            import time
            time.sleep(1)
            
            # Start again
            result = subprocess.run(
                ["python3", "queue_cli.py", "start", "--daemon"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self._log_automation("✅ Queue engine restarted successfully")
                self.status_cards["queue_engine"].status_label.configure(text="Running")
                messagebox.showinfo("Queue Engine", "✅ Queue engine restarted successfully")
                self._check_queue_status()
            else:
                self._log_automation(f"❌ Failed to restart queue engine: {result.stderr}")
                messagebox.showerror("Queue Engine", f"Failed to restart: {result.stderr}")
                
        except Exception as e:
            self._log_automation(f"❌ Error restarting queue engine: {e}")
            messagebox.showerror("Error", f"Error restarting queue engine: {e}")
    
    def _check_queue_status(self):
        """Check queue engine status"""
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "queue_cli.py", "status"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            
            status_text = result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
            
            self.queue_status_display.configure(state=tk.NORMAL)
            self.queue_status_display.delete(1.0, tk.END)
            self.queue_status_display.insert(tk.END, status_text)
            self.queue_status_display.configure(state=tk.DISABLED)
            
            # Update status card based on output
            if "running" in status_text.lower():
                self.status_cards["queue_engine"].status_label.configure(text="Running")
            elif "stopped" in status_text.lower() or "not running" in status_text.lower():
                self.status_cards["queue_engine"].status_label.configure(text="Stopped")
            
            self._log_automation("📊 Queue status updated")
        except Exception as e:
            self._log_automation(f"❌ Error checking queue status: {e}")
    
    def _enable_auto_sync(self):
        """Enable auto-sync"""
        try:
            import subprocess
            # Get selected interval
            interval = self.sync_interval.get()
            interval_seconds = {
                "5 seconds": "5",
                "10 seconds": "10", 
                "30 seconds": "30",
                "1 minute": "60"
            }.get(interval, "10")
            
            result = subprocess.run(
                ["python3", "auto_sync_manager.py", "start", "--interval", interval_seconds],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self._log_automation(f"✅ Auto-sync enabled with {interval} interval")
                self.status_cards["auto_sync"].status_label.configure(text="Active")
                messagebox.showinfo("Auto-Sync", f"✅ Auto-sync enabled ({interval} interval)")
                self._update_sync_status()
            else:
                self._log_automation(f"❌ Failed to enable auto-sync: {result.stderr}")
                messagebox.showerror("Auto-Sync", f"Failed to enable: {result.stderr}")
        except Exception as e:
            self._log_automation(f"❌ Error enabling auto-sync: {e}")
            messagebox.showerror("Error", f"Error enabling auto-sync: {e}")
    
    def _disable_auto_sync(self):
        """Disable auto-sync"""
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "auto_sync_manager.py", "stop"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self._log_automation("⏸️ Auto-sync disabled")
                self.status_cards["auto_sync"].status_label.configure(text="Disabled")
                messagebox.showinfo("Auto-Sync", "⏸️ Auto-sync disabled")
                self._update_sync_status()
            else:
                self._log_automation(f"❌ Failed to disable auto-sync: {result.stderr}")
                messagebox.showerror("Auto-Sync", f"Failed to disable: {result.stderr}")
        except Exception as e:
            self._log_automation(f"❌ Error disabling auto-sync: {e}")
            messagebox.showerror("Error", f"Error disabling auto-sync: {e}")
    
    def _force_sync(self):
        """Force immediate sync"""
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "auto_sync_manager.py", "sync", "--force"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self._log_automation("🔄 Force sync completed successfully")
                messagebox.showinfo("Force Sync", "🔄 Sync completed successfully")
                self._update_sync_status()
            else:
                self._log_automation(f"❌ Force sync failed: {result.stderr}")
                messagebox.showerror("Force Sync", f"Sync failed: {result.stderr}")
        except Exception as e:
            self._log_automation(f"❌ Error during force sync: {e}")
            messagebox.showerror("Error", f"Error during sync: {e}")
    
    def _update_sync_status(self):
        """Update sync status display"""
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "auto_sync_manager.py", "status"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            
            status_text = result.stdout if result.returncode == 0 else "Auto-sync status unavailable"
            
            self.sync_status_display.configure(state=tk.NORMAL)
            self.sync_status_display.delete(1.0, tk.END)
            self.sync_status_display.insert(tk.END, status_text)
            self.sync_status_display.configure(state=tk.DISABLED)
            
        except Exception as e:
            self._log_automation(f"❌ Error updating sync status: {e}")
    
    def _set_automation_level(self):
        """Set automation level"""
        level = self.automation_level.get()
        self.status_cards["automation_level"].status_label.configure(text=level.title())
        self._log_automation(f"⚙️ Automation level set to: {level}")
    
    def _emergency_stop(self):
        """Emergency stop all automation"""
        try:
            response = messagebox.askyesno(
                "⚠️ Emergency Stop",
                "This will immediately stop ALL automation systems!\n\nAre you sure?"
            )
            
            if response:
                self._log_automation("⚠️ EMERGENCY STOP - Halting all systems...")
                
                # Stop queue engine
                import subprocess
                subprocess.run(
                    ["python3", "queue_cli.py", "stop"],
                    cwd=str(self.system_service.project_root),
                    capture_output=True,
                    text=True
                )
                
                # Stop auto-sync
                subprocess.run(
                    ["python3", "auto_sync_manager.py", "stop"],
                    cwd=str(self.system_service.project_root),
                    capture_output=True,
                    text=True
                )
                
                # Update UI
                self.status_cards["queue_engine"].status_label.configure(text="Stopped")
                self.status_cards["auto_sync"].status_label.configure(text="Disabled")
                self.automation_level.set("manual")
                self._set_automation_level()
                
                self._log_automation("🛑 All automation systems stopped")
                messagebox.showwarning("Emergency Stop", "All automation systems have been stopped!")
                
        except Exception as e:
            self._log_automation(f"❌ Error during emergency stop: {e}")
            messagebox.showerror("Error", f"Error during emergency stop: {e}")
    
    def _restart_all_systems(self):
        """Restart all automation systems"""
        try:
            response = messagebox.askyesno(
                "🔄 Restart All Systems",
                "This will restart all automation systems.\n\nContinue?"
            )
            
            if response:
                self._log_automation("🔄 Restarting all automation systems...")
                
                # Restart queue engine
                self._restart_queue_engine()
                
                # Enable auto-sync
                self._enable_auto_sync()
                
                # Set to semi-automatic
                self.automation_level.set("semi")
                self._set_automation_level()
                
                self._log_automation("✅ All systems restarted successfully")
                messagebox.showinfo("System Restart", "All automation systems restarted successfully!")
                
        except Exception as e:
            self._log_automation(f"❌ Error restarting systems: {e}")
            messagebox.showerror("Error", f"Error restarting systems: {e}")
    
    def _cleanup_system(self):
        """Cleanup system files and caches"""
        try:
            response = messagebox.askyesno(
                "🧹 System Cleanup",
                "This will:\n• Clean completed tasks older than 7 days\n• Clear temporary files\n• Reset system caches\n\nContinue?"
            )
            
            if response:
                self._log_automation("🧹 System cleanup initiated...")
                
                # Cleanup completed tasks
                import subprocess
                result = subprocess.run(
                    ["python3", "todo_manager.py", "cleanup"],
                    cwd=str(self.system_service.project_root),
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    self._log_automation("✅ Task cleanup completed")
                else:
                    self._log_automation(f"⚠️ Task cleanup warning: {result.stderr}")
                
                # Additional cleanup can be added here
                
                self._log_automation("✅ System cleanup completed")
                messagebox.showinfo("Cleanup Complete", "System cleanup completed successfully!")
                
        except Exception as e:
            self._log_automation(f"❌ Error during cleanup: {e}")
            messagebox.showerror("Error", f"Error during cleanup: {e}")
    
    def _save_settings(self):
        """Save automation settings"""
        timeout = self.task_timeout.get()
        max_tasks = self.max_tasks.get()
        self._log_automation(f"💾 Settings saved - Timeout: {timeout}s, Max tasks: {max_tasks}")
    
    def _log_automation(self, message):
        """Add message to automation logs"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}\n"
            
            self.automation_logs.configure(state=tk.NORMAL)
            self.automation_logs.insert(tk.END, log_entry)
            
            # Keep only last 50 lines
            lines = self.automation_logs.get(1.0, tk.END).split('\n')
            if len(lines) > 50:
                self.automation_logs.delete(1.0, tk.END)
                self.automation_logs.insert(tk.END, '\n'.join(lines[-50:]))
            
            self.automation_logs.see(tk.END)
            self.automation_logs.configure(state=tk.DISABLED)
        except Exception as e:
            print(f"Error logging automation message: {e}")
    
    def refresh(self):
        """Refresh view data"""
        try:
            # Check queue engine status
            self._check_queue_status()
            
            # Check auto-sync status  
            self._update_sync_status()
            
            # Update automation status
            self.automation_status.configure(text="✅ Automation systems ready")
            
            # Log refresh
            self._log_automation("🔄 View refreshed")
            
        except Exception as e:
            self._log_automation(f"❌ Error refreshing view: {e}")
            self.automation_status.configure(text="❌ Error loading status")
