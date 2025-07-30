"""
🎯 Modern GUI Control Center - Task Management View

Task management interface with real-time queue visualization,
task creation, editing, and execution control.
"""

# Built-in & stdlib
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.constants import *
import subprocess
import sys

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False


class TaskManagementView(ttk.Frame):
    """Task management view"""
    
    def __init__(self, parent, system_service):
        super().__init__(parent)
        self.system_service = system_service
        self.pack(fill=BOTH, expand=True)
        
        # Create placeholder layout
        self._create_placeholder()
    
    def _create_placeholder(self):
        """Create full task management interface"""
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._create_header(main_container)
        
        # Task queue sections
        self._create_queue_sections(main_container)
        
        # Control panel
        self._create_control_panel(main_container)
        
        # Subscribe to task updates
        if hasattr(self.system_service, "bus") and self.system_service.bus:
            self.system_service.bus.subscribe("tasks_updated", lambda **_: self.refresh())

        # Initial load
        self.refresh()
    
    def _create_header(self, parent):
        """Create task management header"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X, pady=(0, 20))
        
        # Title
        title = ttk.Label(
            header_frame,
            text="📋 Task Management System",
            font=("Inter", 24, "bold")
        )
        title.pack(side=LEFT)
        
        # Queue status
        self.queue_status = ttk.Label(
            header_frame,
            text="🔄 Loading...",
            font=("Inter", 12)
        )
        self.queue_status.pack(side=RIGHT)
    
    def _create_queue_sections(self, parent):
        """Create task queue visualization sections"""
        # Create notebook for different queues
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Active tasks tab
        active_frame = ttk.Frame(notebook)
        notebook.add(active_frame, text="🔄 Active Tasks")
        self._create_task_list(active_frame, "active")
        
        # Queue tab
        queue_frame = ttk.Frame(notebook)
        notebook.add(queue_frame, text="⏳ Queue")
        self._create_task_list(queue_frame, "queue")
        
        # Completed tab
        done_frame = ttk.Frame(notebook)
        notebook.add(done_frame, text="✅ Completed")
        self._create_task_list(done_frame, "done")
        
        # Store references
        self.task_lists = {
            "active": active_frame,
            "queue": queue_frame,
            "done": done_frame
        }
    
    def _create_task_list(self, parent, queue_type):
        """Create task list for specific queue"""
        # Create treeview for tasks
        columns = ("ID", "Description", "Status", "Created")
        
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Treeview
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        tree.heading("ID", text="Task ID")
        tree.heading("Description", text="Description")
        tree.heading("Status", text="Status")
        tree.heading("Created", text="Created")
        
        tree.column("ID", width=200)
        tree.column("Description", width=400)
        tree.column("Status", width=100)
        tree.column("Created", width=150)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        v_scrollbar.pack(side=RIGHT, fill=Y)
        h_scrollbar.pack(side=BOTTOM, fill=X)
        
        # Store reference
        setattr(parent, 'tree', tree)
    
    def _create_control_panel(self, parent):
        """Create task control panel"""
        control_frame = ttk.LabelFrame(parent, text="⚡ Task Controls", padding=15)
        control_frame.pack(fill=X)
        
        # Buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=X)
        
        # Quick action buttons
        ttk.Button(btn_frame, text="➕ New Task", command=self._create_new_task).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🔄 Refresh", command=self.refresh).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="⏸️ Pause Queue", command=self._pause_queue).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="▶️ Resume Queue", command=self._resume_queue).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🧹 Cleanup", command=self._cleanup_completed).pack(side=LEFT, padx=5)
    
    def _create_new_task(self):
        """Create a new task using todo_manager CLI"""
        from tkinter import simpledialog

        task_desc = simpledialog.askstring("New Task", "Enter task description:")
        if not task_desc:
            return  # User cancelled

        try:
            cmd = [sys.executable, "todo_manager.py", "new", task_desc]
            result = subprocess.run(
                cmd,
                cwd=self.system_service.project_root,
                capture_output=True,
                text=True,
                timeout=20,
            )

            if result.returncode == 0:
                messagebox.showinfo("Task Created", f"✅ Task added: {task_desc}")
                self.refresh()
            else:
                messagebox.showerror("Task Creation Failed", result.stderr or "Unknown error")
        except subprocess.TimeoutExpired:
            messagebox.showerror("Timeout", "todo_manager did not respond in time.")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _pause_queue(self):
        """Pause the task queue using queue_cli"""
        try:
            cmd = [sys.executable, "queue_cli.py", "pause"]
            result = subprocess.run(
                cmd,
                cwd=self.system_service.project_root,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                messagebox.showinfo("Queue Paused", "⏸️ Task queue paused.")
                self.refresh()
            else:
                messagebox.showerror("Pause Failed", result.stderr or "Unknown error")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _resume_queue(self):
        """Resume/start the task queue using queue_cli"""
        try:
            cmd = [sys.executable, "queue_cli.py", "start"]
            result = subprocess.run(
                cmd,
                cwd=self.system_service.project_root,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                messagebox.showinfo("Queue Started", "▶️ Task queue running.")
                self.refresh()
            else:
                messagebox.showerror("Start Failed", result.stderr or "Unknown error")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _cleanup_completed(self):
        """Remove completed tasks using todo_manager CLI"""
        if not messagebox.askyesno("Confirm Cleanup", "Delete all completed tasks? This action cannot be undone."):
            return

        try:
            cmd = [sys.executable, "todo_manager.py", "cleanup", "--completed"]
            result = subprocess.run(
                cmd,
                cwd=self.system_service.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                messagebox.showinfo("Cleanup Complete", "🧹 Completed tasks removed.")
                self.refresh()
            else:
                messagebox.showerror("Cleanup Failed", result.stderr or "Unknown error")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def refresh(self):
        """Refresh view data and schedule next auto-refresh"""
        try:
            # Load task data from system service
            active_tasks = self.system_service.get_active_tasks()
            queue_tasks = self.system_service.get_task_queue()
            completed_tasks = self.system_service.get_completed_tasks()
            
            # Update task lists
            self._update_task_list("active", active_tasks)
            self._update_task_list("queue", queue_tasks)
            self._update_task_list("done", completed_tasks)
            
            # Update status
            total_tasks = len(active_tasks) + len(queue_tasks)
            self.queue_status.configure(text=f"📊 {len(active_tasks)} active, {len(queue_tasks)} queued, {len(completed_tasks)} completed")
            
        except Exception as e:
            print(f"Error refreshing task data: {e}")
            self.queue_status.configure(text="❌ Error loading tasks")

        # No need for periodic polling – EventBus will trigger on changes
    
    def _update_task_list(self, queue_type, tasks):
        """Update specific task list with data"""
        try:
            if queue_type not in self.task_lists:
                return
                
            tree = getattr(self.task_lists[queue_type], 'tree', None)
            if not tree:
                return
                
            # Clear existing items
            for item in tree.get_children():
                tree.delete(item)
            
            # Add new items
            for task in tasks:
                task_id = task.get('task_id', 'Unknown')
                description = task.get('description', 'No description')
                status = task.get('status', 'unknown')
                created = task.get('created_at', 'Unknown')
                
                # Truncate long descriptions for display
                if len(description) > 50:
                    display_desc = description[:47] + "..."
                else:
                    display_desc = description
                
                # Format created date
                if 'T' in str(created):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        formatted_date = str(created)
                else:
                    formatted_date = str(created)
                
                # Insert row
                tree.insert('', 'end', values=(task_id, display_desc, status.upper(), formatted_date))
                
        except Exception as e:
            print(f"Error updating {queue_type} task list: {e}")
