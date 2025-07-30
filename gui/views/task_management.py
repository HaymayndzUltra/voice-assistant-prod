"""
🎯 Modern GUI Control Center - Task Management View

Task management interface with real-time queue visualization,
task creation, editing, and execution control.
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
        
        # Load initial data
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
        
        # Store notebook reference for auto-refresh
        self.notebook = notebook
        
        # Start auto-refresh
        self._start_auto_refresh()
    
    def _create_task_list(self, parent, queue_type):
        """Create task list for specific queue"""
        # Create treeview for tasks
        columns = ("ID", "Description", "Priority", "Status", "Progress", "Created")
        
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Treeview
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        tree.heading("ID", text="Task ID")
        tree.heading("Description", text="Description")
        tree.heading("Priority", text="Priority")
        tree.heading("Status", text="Status")
        tree.heading("Progress", text="Progress")
        tree.heading("Created", text="Created")
        
        tree.column("ID", width=150)
        tree.column("Description", width=400)
        tree.column("Priority", width=80)
        tree.column("Status", width=100)
        tree.column("Progress", width=80)
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
        
        # First row of buttons
        btn_frame1 = ttk.Frame(control_frame)
        btn_frame1.pack(fill=X, pady=(0, 5))
        
        # Quick action buttons
        ttk.Button(btn_frame1, text="➕ New Task", command=self._create_new_task).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame1, text="✏️ Edit Task", command=self._edit_task).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame1, text="🗑️ Delete Task", command=self._delete_task).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame1, text="▶️ Start Selected", command=self._start_selected_task).pack(side=LEFT, padx=5)
        
        # Second row of buttons
        btn_frame2 = ttk.Frame(control_frame)
        btn_frame2.pack(fill=X)
        
        ttk.Button(btn_frame2, text="🔄 Refresh", command=self.refresh).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame2, text="⏸️ Pause Queue", command=self._pause_queue).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame2, text="▶️ Resume Queue", command=self._resume_queue).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame2, text="📤 Export", command=self._export_tasks).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame2, text="🧹 Cleanup", command=self._cleanup_completed).pack(side=LEFT, padx=5)
    
    def _create_new_task(self):
        """Create new task dialog"""
        # Simple implementation for now
        from tkinter import simpledialog
        task_desc = simpledialog.askstring("New Task", "Enter task description:")
        if task_desc:
            try:
                import subprocess
                result = subprocess.run(
                    ["python3", "todo_manager.py", "new", task_desc],
                    cwd=str(self.system_service.project_root),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    self.refresh()
                    messagebox.showinfo("Task Created", f"✅ Created task: {task_desc}")
                    print(f"✅ Created task: {task_desc}")
                else:
                    messagebox.showerror("Task Creation Failed", f"Failed to create task: {result.stderr}")
                    print(f"❌ Failed to create task: {result.stderr}")
            except Exception as e:
                messagebox.showerror("Error", f"Error creating task: {e}")
                print(f"Error creating task: {e}")
    
    def _edit_task(self):
        """Edit selected task"""
        try:
            # Get selected task from current tab
            current_tab = self._get_current_tab()
            if not current_tab:
                messagebox.showwarning("No Selection", "Please select a task to edit")
                return
            
            tree = getattr(current_tab, 'tree', None)
            if not tree:
                return
                
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a task to edit")
                return
                
            # Get task ID from selection
            item = tree.item(selection[0])
            task_id = item['values'][0]  # First column is task ID
            
            # For now, show a simple message
            messagebox.showinfo("Edit Task", f"Edit functionality for task {task_id} coming soon!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error editing task: {e}")
            print(f"Error editing task: {e}")
    
    def _delete_task(self):
        """Delete selected task"""
        try:
            # Get selected task from current tab
            current_tab = self._get_current_tab()
            if not current_tab:
                messagebox.showwarning("No Selection", "Please select a task to delete")
                return
            
            tree = getattr(current_tab, 'tree', None)
            if not tree:
                return
                
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a task to delete")
                return
                
            # Get task ID from selection
            item = tree.item(selection[0])
            task_id = item['values'][0]  # First column is task ID
            task_desc = item['values'][1]  # Second column is description
            
            # Confirm deletion
            response = messagebox.askyesno(
                "Delete Task",
                f"Are you sure you want to delete task:\n\n{task_desc}?"
            )
            
            if response:
                import subprocess
                result = subprocess.run(
                    ["python3", "todo_manager.py", "delete", task_id],
                    cwd=str(self.system_service.project_root),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    messagebox.showinfo("Task Deleted", f"✅ Task deleted successfully")
                    self.refresh()
                else:
                    messagebox.showerror("Delete Failed", f"Failed to delete task: {result.stderr}")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error deleting task: {e}")
            print(f"Error deleting task: {e}")
    
    def _start_selected_task(self):
        """Start/move selected task to active queue"""
        try:
            # Get selected task from queue tab
            queue_tab = self.task_lists.get('queue')
            if not queue_tab:
                return
                
            tree = getattr(queue_tab, 'tree', None)
            if not tree:
                return
                
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a task from the queue to start")
                return
                
            # Get task ID from selection
            item = tree.item(selection[0])
            task_id = item['values'][0]
            task_desc = item['values'][1]
            
            messagebox.showinfo("Start Task", f"Moving task '{task_desc}' to active queue...")
            # TODO: Implement actual queue movement logic
            self.refresh()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error starting task: {e}")
            print(f"Error starting task: {e}")
    
    def _export_tasks(self):
        """Export tasks to file"""
        try:
            from tkinter import filedialog
            import json
            
            # Ask for file location
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:
                # Get all tasks
                all_tasks = {
                    "active": self.system_service.get_active_tasks(),
                    "queue": self.system_service.get_task_queue(),
                    "completed": self.system_service.get_completed_tasks()
                }
                
                # Export based on file extension
                if filename.endswith('.json'):
                    with open(filename, 'w') as f:
                        json.dump(all_tasks, f, indent=2)
                    messagebox.showinfo("Export Complete", f"✅ Tasks exported to {filename}")
                elif filename.endswith('.csv'):
                    import csv
                    with open(filename, 'w', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Queue', 'ID', 'Description', 'Status', 'Priority', 'Progress', 'Created'])
                        
                        for queue_type, tasks in all_tasks.items():
                            for task in tasks:
                                writer.writerow([
                                    queue_type,
                                    task.get('id', ''),
                                    task.get('description', ''),
                                    task.get('status', ''),
                                    task.get('priority', ''),
                                    task.get('progress', ''),
                                    task.get('created_at', '')
                                ])
                    messagebox.showinfo("Export Complete", f"✅ Tasks exported to {filename}")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error exporting tasks: {e}")
            print(f"Error exporting tasks: {e}")
    
    def _get_current_tab(self):
        """Get the currently selected tab frame"""
        try:
            # Find the notebook widget
            for widget in self.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Notebook):
                            current_tab_index = child.index(child.select())
                            tab_names = ['active', 'queue', 'done']
                            if 0 <= current_tab_index < len(tab_names):
                                return self.task_lists.get(tab_names[current_tab_index])
            return None
        except:
            return None
    
    def _pause_queue(self):
        """Pause autonomous queue"""
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "queue_cli.py", "pause"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                messagebox.showinfo("Queue Control", "✅ Queue paused successfully")
                print(f"✅ Queue paused: {result.stdout}")
            else:
                messagebox.showerror("Queue Control", f"Failed to pause queue: {result.stderr}")
                print(f"❌ Failed to pause queue: {result.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Error pausing queue: {e}")
            print(f"Error pausing queue: {e}")
    
    def _resume_queue(self):
        """Resume autonomous queue"""
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "queue_cli.py", "start", "--daemon"],
                cwd=str(self.system_service.project_root),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                messagebox.showinfo("Queue Control", "✅ Queue resumed successfully")
                print(f"✅ Queue resumed: {result.stdout}")
            else:
                messagebox.showerror("Queue Control", f"Failed to resume queue: {result.stderr}")
                print(f"❌ Failed to resume queue: {result.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Error resuming queue: {e}")
            print(f"Error resuming queue: {e}")
    
    def _cleanup_completed(self):
        """Cleanup completed tasks"""
        try:
            # Ask for confirmation
            response = messagebox.askyesno(
                "Cleanup Completed Tasks",
                "This will remove all completed tasks older than 7 days.\nDo you want to continue?"
            )
            
            if response:
                import subprocess
                result = subprocess.run(
                    ["python3", "todo_manager.py", "cleanup"],
                    cwd=str(self.system_service.project_root),
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    messagebox.showinfo("Cleanup", "✅ Completed tasks cleaned up successfully")
                    print(f"✅ Cleanup completed: {result.stdout}")
                    self.refresh()  # Refresh to show updated task list
                else:
                    messagebox.showerror("Cleanup", f"Failed to cleanup tasks: {result.stderr}")
                    print(f"❌ Failed to cleanup: {result.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Error cleaning up tasks: {e}")
            print(f"Error cleaning up tasks: {e}")
    
    def refresh(self):
        """Refresh view data"""
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
                # Get task fields with proper mappings
                task_id = task.get('id', task.get('task_id', 'Unknown'))
                description = task.get('description', 'No description')
                priority = task.get('priority', 'medium')
                status = task.get('status', 'unknown')
                progress = task.get('progress', 0)
                created = task.get('created_at', task.get('created', 'Unknown'))
                
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
                
                # Format progress as percentage
                progress_str = f"{progress}%"
                
                # Insert row with proper status display
                tree.insert('', 'end', values=(task_id, display_desc, priority.upper(), status.upper(), progress_str, formatted_date))
                
        except Exception as e:
            print(f"Error updating {queue_type} task list: {e}")
    
    def _start_auto_refresh(self):
        """Start auto-refresh timer"""
        self.auto_refresh_enabled = True
        self._schedule_refresh()
    
    def _schedule_refresh(self):
        """Schedule next refresh"""
        if hasattr(self, 'auto_refresh_enabled') and self.auto_refresh_enabled:
            # Refresh every 30 seconds
            self.after(30000, self._auto_refresh)
    
    def _auto_refresh(self):
        """Perform auto-refresh"""
        try:
            self.refresh()
            # Update status to show last refresh time
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M:%S")
            self.queue_status.configure(
                text=self.queue_status.cget("text") + f" | Last refresh: {current_time}"
            )
        except Exception as e:
            print(f"Error during auto-refresh: {e}")
        finally:
            # Schedule next refresh
            self._schedule_refresh()
    
    def destroy(self):
        """Clean up on destroy"""
        self.auto_refresh_enabled = False
        super().destroy()
