"""
🎯 Modern GUI Control Center - Monitoring View

Real-time system monitoring with charts and analytics.
"""

# Built-in & stdlib
import tkinter as tk
from tkinter import ttk
from tkinter.constants import *
import subprocess, os, time, sys, pathlib

# GUI utilities
from gui.utils.toast import show_info, show_error, show_warning

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False


class MonitoringView(ttk.Frame):
    """System monitoring view"""
    
    def __init__(self, parent, system_service):
        super().__init__(parent)
        self.system_service = system_service
        self.pack(fill=BOTH, expand=True)
        
        # Subscribe to events
        self.system_service.bus.subscribe("tasks_updated", self._on_tasks_updated)
        self.system_service.bus.subscribe("agent_status_changed", self._on_agents_updated)
        self.system_service.bus.subscribe("metrics_tick", self._on_metrics_updated)
        
        # Create placeholder layout
        self._create_placeholder()
        
        # Start metrics timer (only for CPU/RAM)
        self._start_metrics_timer()
    
    def _create_placeholder(self):
        """Create comprehensive monitoring dashboard"""
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._create_header(main_container)
        
        # Metrics overview
        self._create_metrics_overview(main_container)
        
        # Performance charts section
        self._create_charts_section(main_container)
        
        # Real-time logs section
        self._create_logs_section(main_container)
        
        # Load initial data
        self.refresh()
    
    def _create_header(self, parent):
        """Create monitoring dashboard header"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X, pady=(0, 20))
        
        # Title
        title = ttk.Label(
            header_frame,
            text="📊 System Monitoring Dashboard",
            font=("Inter", 24, "bold")
        )
        title.pack(side=LEFT)
        
        # Real-time indicator
        self.monitoring_status = ttk.Label(
            header_frame,
            text="🟢 Real-time monitoring active",
            font=("Inter", 12)
        )
        self.monitoring_status.pack(side=RIGHT)
    
    def _create_metrics_overview(self, parent):
        """Create system metrics overview cards"""
        metrics_frame = ttk.LabelFrame(parent, text="📊 System Metrics Overview", padding=15)
        metrics_frame.pack(fill=X, pady=(0, 20))
        
        # Configure grid
        for i in range(5):
            metrics_frame.grid_columnconfigure(i, weight=1)
        
        # Metrics cards
        self.metric_cards = {}
        metrics_data = [
            ("cpu", "💻", "CPU Usage", "0%", "info"),
            ("memory", "🧠", "Memory", "0MB", "warning"),
            ("tasks", "📋", "Tasks/Hour", "0", "primary"),
            ("agents", "🤖", "Active Agents", "0", "success"),
            ("uptime", "⏱️", "Uptime", "0h", "secondary")
        ]
        
        for i, (key, icon, title, value, color) in enumerate(metrics_data):
            card = self._create_metric_card(metrics_frame, icon, title, value, color)
            card.grid(row=0, column=i, padx=(0, 10 if i < 4 else 0), sticky="ew")
            self.metric_cards[key] = card
    
    def _create_metric_card(self, parent, icon, title, value, color):
        """Create individual metric card"""
        if MODERN_STYLING:
            card_frame = ttk.Frame(parent, bootstyle=f"{color}-inverse", padding=12)
        else:
            card_frame = ttk.Frame(parent, padding=12, relief="solid", borderwidth=1)
        
        # Icon
        icon_label = ttk.Label(card_frame, text=icon, font=("Inter", 18))
        icon_label.pack()
        
        # Value
        value_label = ttk.Label(card_frame, text=value, font=("Inter", 16, "bold"))
        value_label.pack(pady=(3, 0))
        
        # Title
        title_label = ttk.Label(card_frame, text=title, font=("Inter", 10))
        title_label.pack()
        
        # Store reference
        card_frame.value_label = value_label
        return card_frame
    
    def _create_charts_section(self, parent):
        """Create performance charts section"""
        charts_frame = ttk.LabelFrame(parent, text="📈 Performance Analytics", padding=15)
        charts_frame.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Create notebook for different chart views
        charts_notebook = ttk.Notebook(charts_frame)
        charts_notebook.pack(fill=BOTH, expand=True)
        
        # Task execution trends
        task_trends_frame = ttk.Frame(charts_notebook)
        charts_notebook.add(task_trends_frame, text="📋 Task Trends")
        self._create_task_trends_chart(task_trends_frame)
        
        # System performance
        perf_frame = ttk.Frame(charts_notebook)
        charts_notebook.add(perf_frame, text="💻 Performance")
        self._create_performance_chart(perf_frame)
        
        # Agent health
        agent_health_frame = ttk.Frame(charts_notebook)
        charts_notebook.add(agent_health_frame, text="🤖 Agent Health")
        self._create_agent_health_chart(agent_health_frame)
    
    def _create_task_trends_chart(self, parent):
        """Create task execution trends chart"""
        # Placeholder for matplotlib chart
        chart_frame = ttk.Frame(parent)
        chart_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Text-based chart for now (can be replaced with matplotlib)
        self.task_trends_display = tk.Text(
            chart_frame,
            height=15,
            wrap=tk.WORD,
            font=("Fira Code", 10),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1,
            state=tk.DISABLED
        )
        
        scrollbar = ttk.Scrollbar(chart_frame, orient=VERTICAL, command=self.task_trends_display.yview)
        self.task_trends_display.configure(yscrollcommand=scrollbar.set)
        
        self.task_trends_display.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
    
    def _create_performance_chart(self, parent):
        """Create system performance chart"""
        perf_frame = ttk.Frame(parent)
        perf_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        self.performance_display = tk.Text(
            perf_frame,
            height=15,
            wrap=tk.WORD,
            font=("Fira Code", 10),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1,
            state=tk.DISABLED
        )
        
        scrollbar2 = ttk.Scrollbar(perf_frame, orient=VERTICAL, command=self.performance_display.yview)
        self.performance_display.configure(yscrollcommand=scrollbar2.set)
        
        self.performance_display.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar2.pack(side=RIGHT, fill=Y)
    
    def _create_agent_health_chart(self, parent):
        """Create agent health monitoring chart"""
        health_frame = ttk.Frame(parent)
        health_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        self.agent_health_display = tk.Text(
            health_frame,
            height=15,
            wrap=tk.WORD,
            font=("Fira Code", 10),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1,
            state=tk.DISABLED
        )
        
        scrollbar3 = ttk.Scrollbar(health_frame, orient=VERTICAL, command=self.agent_health_display.yview)
        self.agent_health_display.configure(yscrollcommand=scrollbar3.set)
        
        self.agent_health_display.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar3.pack(side=RIGHT, fill=Y)
    
    def _create_logs_section(self, parent):
        """Create real-time logs section"""
        logs_frame = ttk.LabelFrame(parent, text="📜 Real-time System Logs", padding=15)
        logs_frame.pack(fill=X, pady=(0, 10))
        
        # Logs display
        self.logs_display = tk.Text(
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
        
        log_scrollbar = ttk.Scrollbar(logs_frame, orient=VERTICAL, command=self.logs_display.yview)
        self.logs_display.configure(yscrollcommand=log_scrollbar.set)
        
        self.logs_display.pack(side=LEFT, fill=BOTH, expand=True)
        log_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Control buttons
        log_controls = ttk.Frame(logs_frame)
        log_controls.pack(fill=X, pady=(10, 0))
        
        ttk.Button(log_controls, text="🔄 Refresh", command=self.refresh).pack(side=LEFT, padx=5)
        ttk.Button(log_controls, text="🧹 Clear", command=self._clear_logs).pack(side=LEFT, padx=5)
        ttk.Button(log_controls, text="💾 Export", command=self._export_logs).pack(side=LEFT, padx=5)
    
    def _clear_logs(self):
        """Clear logs display"""
        self.logs_display.configure(state=tk.NORMAL)
        self.logs_display.delete(1.0, tk.END)
        self.logs_display.configure(state=tk.DISABLED)
    
    def _export_logs(self):
        """Export logs to file"""
        try:
            log_txt = self.logs_display.get(1.0, tk.END)
            out_path = pathlib.Path.home() / f"system_logs_{int(time.time())}.txt"
            out_path.write_text(log_txt)
            show_info(self, f"Logs exported to {out_path}")
        except Exception as e:
            show_error(self, f"Export failed: {e}")
    
    def _start_metrics_timer(self):
        """Start periodic timer for CPU/RAM metrics only"""
        self._update_system_metrics()
        # Schedule next metrics update (10 seconds)
        self.after(10_000, self._start_metrics_timer)
    
    def _on_tasks_updated(self, **kwargs):
        """Handle tasks updated event"""
        try:
            self._update_task_trends()
            self._update_metrics()
        except Exception as e:
            show_error(self, f"Error updating task data: {e}")
    
    def _on_agents_updated(self, **kwargs):
        """Handle agent status changed event"""
        try:
            self._update_agent_health()
            self._update_metrics()
        except Exception as e:
            show_error(self, f"Error updating agent data: {e}")
    
    def _on_metrics_updated(self, **kwargs):
        """Handle metrics tick event"""
        try:
            self._update_performance_metrics()
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M:%S")
            self.monitoring_status.configure(text=f"🟢 Real-time monitoring active - {current_time}")
        except Exception as e:
            show_error(self, f"Error updating metrics: {e}")
            self.monitoring_status.configure(text="❌ Monitoring error")
    
    def refresh(self):
        """Manual refresh - now event-driven"""
        try:
            # Trigger events for updates
            self.system_service.bus.publish("tasks_updated", {})
            self.system_service.bus.publish("agent_status_changed", {})
            self.system_service.bus.publish("metrics_tick", {})
            self._update_logs()
            show_info(self, "Monitoring data refreshed")
        except Exception as e:
            show_error(self, f"Error refreshing monitoring: {e}")
    
    def _update_system_metrics(self):
        """Update CPU/RAM metrics only"""
        try:
            # Emit metrics tick event with current CPU/RAM data
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            self.system_service.bus.publish("metrics_tick", {
                "cpu": cpu_percent,
                "memory": memory.percent,
                "memory_used": memory.used // (1024**2),  # MB
                "timestamp": time.time()
            })
        except ImportError:
            # psutil not available
            pass
        except Exception as e:
            print(f"Error updating system metrics: {e}")
    
    def _update_metrics(self):
        """Update system metrics cards"""
        try:
            import psutil
            import time
            
            # CPU Usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.metric_cards["cpu"].value_label.configure(text=f"{cpu_percent:.1f}%")
            
            # Memory Usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / (1024 * 1024)
            self.metric_cards["memory"].value_label.configure(text=f"{memory_mb:.0f}MB")
            
            # Tasks per hour (from system service)
            active_tasks = len(self.system_service.get_active_tasks())
            completed_tasks = len(self.system_service.get_completed_tasks())
            tasks_per_hour = completed_tasks  # Simplified calculation
            self.metric_cards["tasks"].value_label.configure(text=str(tasks_per_hour))
            
            # Active agents (from agent status)
            agent_status = self.system_service.get_agent_status()
            total_agents = agent_status.get("summary", {}).get("total_agents", 0)
            self.metric_cards["agents"].value_label.configure(text=str(total_agents))
            
            # System uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600
            self.metric_cards["uptime"].value_label.configure(text=f"{uptime_hours:.1f}h")
            
        except ImportError:
            # Fallback if psutil not available
            self.metric_cards["cpu"].value_label.configure(text="N/A")
            self.metric_cards["memory"].value_label.configure(text="N/A")
            self.metric_cards["uptime"].value_label.configure(text="N/A")
        except Exception as e:
            print(f"Error updating metrics: {e}")
    
    def _update_charts(self):
        """Update performance charts"""
        try:
            # Update task trends
            self._update_task_trends()
            
            # Update performance metrics
            self._update_performance_metrics()
            
            # Update agent health
            self._update_agent_health()
            
        except Exception as e:
            print(f"Error updating charts: {e}")
    
    def _update_task_trends(self):
        """Update task execution trends"""
        try:
            self.task_trends_display.configure(state=tk.NORMAL)
            self.task_trends_display.delete(1.0, tk.END)
            
            # Get task data
            active_tasks = self.system_service.get_active_tasks()
            completed_tasks = self.system_service.get_completed_tasks()
            
            # Create text-based trend visualization
            trends_text = "📈 TASK EXECUTION TRENDS\n\n"
            trends_text += f"Active Tasks: {len(active_tasks)}\n"
            trends_text += f"Completed Tasks: {len(completed_tasks)}\n\n"
            
            # Simple bar chart representation
            trends_text += "Task Status Distribution:\n"
            active_bar = "█" * min(len(active_tasks), 20)
            completed_bar = "█" * min(len(completed_tasks), 20)
            
            trends_text += f"Active:    [{active_bar:<20}] {len(active_tasks)}\n"
            trends_text += f"Completed: [{completed_bar:<20}] {len(completed_tasks)}\n\n"
            
            # Recent task activity
            trends_text += "Recent Task Activity:\n"
            for i, task in enumerate(active_tasks[:5]):
                status_icon = "🔄" if task.get("status") == "in_progress" else "⏳"
                desc = task.get("description", "Unknown")[:40] + "..." if len(task.get("description", "")) > 40 else task.get("description", "Unknown")
                trends_text += f"{status_icon} {desc}\n"
            
            if not active_tasks:
                trends_text += "✨ No active tasks - system ready for new work!\n"
            
            self.task_trends_display.insert(tk.END, trends_text)
            self.task_trends_display.configure(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error updating task trends: {e}")
    
    def _update_performance_metrics(self):
        """Update system performance metrics"""
        try:
            self.performance_display.configure(state=tk.NORMAL)
            self.performance_display.delete(1.0, tk.END)
            
            perf_text = "💻 SYSTEM PERFORMANCE METRICS\n\n"
            
            try:
                import psutil
                
                # CPU Information
                cpu_count = psutil.cpu_count()
                cpu_freq = psutil.cpu_freq()
                perf_text += f"CPU Cores: {cpu_count}\n"
                if cpu_freq:
                    perf_text += f"CPU Frequency: {cpu_freq.current:.0f} MHz\n"
                
                # Memory Information
                memory = psutil.virtual_memory()
                perf_text += f"Total Memory: {memory.total / (1024**3):.1f} GB\n"
                perf_text += f"Available Memory: {memory.available / (1024**3):.1f} GB\n"
                perf_text += f"Memory Usage: {memory.percent}%\n\n"
                
                # Disk Information
                disk = psutil.disk_usage('/')
                perf_text += f"Disk Total: {disk.total / (1024**3):.1f} GB\n"
                perf_text += f"Disk Free: {disk.free / (1024**3):.1f} GB\n"
                perf_text += f"Disk Usage: {(disk.used / disk.total) * 100:.1f}%\n\n"
                
                # Network Information
                net_io = psutil.net_io_counters()
                perf_text += f"Bytes Sent: {net_io.bytes_sent / (1024**2):.1f} MB\n"
                perf_text += f"Bytes Received: {net_io.bytes_recv / (1024**2):.1f} MB\n"
                
            except ImportError:
                perf_text += "psutil not available - install for detailed metrics\n"
                perf_text += "pip install psutil\n\n"
                perf_text += "Basic system information:\n"
                perf_text += "- Task queue system: Operational\n"
                perf_text += "- Memory system: Operational\n"
                perf_text += "- GUI system: Operational\n"
            
            self.performance_display.insert(tk.END, perf_text)
            self.performance_display.configure(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error updating performance metrics: {e}")
    
    def _update_agent_health(self):
        """Update agent health monitoring"""
        try:
            self.agent_health_display.configure(state=tk.NORMAL)
            self.agent_health_display.delete(1.0, tk.END)
            
            # Get agent status
            agent_status = self.system_service.get_agent_status()
            
            health_text = "🤖 AGENT HEALTH MONITORING\n\n"
            
            summary = agent_status.get("summary", {})
            if summary:
                health_text += f"Total Agents: {summary.get('total_agents', 0)}\n"
                health_text += f"Total Directories: {summary.get('total_directories', 0)}\n"
                health_text += f"Critical Issues: {summary.get('critical_issues', 0)}\n"
                health_text += f"Port Conflicts: {summary.get('port_conflicts', 0)}\n\n"
                
                # Health status visualization
                total_agents = summary.get('total_agents', 294)
                critical_issues = summary.get('critical_issues', 0)
                healthy_agents = total_agents - critical_issues
                
                health_percentage = (healthy_agents / total_agents * 100) if total_agents > 0 else 0
                
                health_text += "Agent Health Distribution:\n"
                healthy_bar = "█" * int(health_percentage / 5)
                issue_bar = "█" * int((100 - health_percentage) / 5)
                
                health_text += f"Healthy:  [{healthy_bar:<20}] {healthy_agents}\n"
                health_text += f"Issues:   [{issue_bar:<20}] {critical_issues}\n\n"
                
                # Status indicators
                if health_percentage >= 90:
                    health_text += "🟢 Overall Status: EXCELLENT\n"
                elif health_percentage >= 75:
                    health_text += "🟡 Overall Status: GOOD\n"
                elif health_percentage >= 50:
                    health_text += "🟠 Overall Status: WARNING\n"
                else:
                    health_text += "🔴 Overall Status: CRITICAL\n"
                
            else:
                health_text += "No agent health data available.\n"
                health_text += "Run agent scan to collect health information.\n"
            
            self.agent_health_display.insert(tk.END, health_text)
            self.agent_health_display.configure(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error updating agent health: {e}")
    
    def _update_logs(self):
        """Tail system log file and display recent lines"""
        try:
            log_file = self.system_service.project_root / "system.log"
            self.logs_display.configure(state=tk.NORMAL)
            self.logs_display.delete(1.0, tk.END)

            if log_file.exists():
                lines = log_file.read_text().splitlines()[-200:]
                for line in lines:
                    self.logs_display.insert(tk.END, line + "\n")
            else:
                self.logs_display.insert(tk.END, "Log file not found.\n")

            self.logs_display.configure(state=tk.DISABLED)
        except Exception as e:
            print(f"Error updating logs: {e}")
