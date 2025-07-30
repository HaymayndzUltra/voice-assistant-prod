"""
🎯 Modern GUI Control Center - Agent Control View

Agent management interface with health monitoring and
control for 294 discovered agents across MainPC and PC2.
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


class AgentControlView(ttk.Frame):
    """Agent control view"""
    
    def __init__(self, parent, system_service):
        super().__init__(parent)
        self.system_service = system_service
        self.pack(fill=BOTH, expand=True)
        
        # Create placeholder layout
        self._create_placeholder()
    
    def _create_placeholder(self):
        """Create comprehensive agent control interface"""
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._create_header(main_container)
        
        # Agent overview cards
        self._create_overview_cards(main_container)
        
        # Agent list and details
        self._create_agent_interface(main_container)
        
        # Control panel
        self._create_control_panel(main_container)
        
        # Load initial data
        self.refresh()
    
    def _create_header(self, parent):
        """Create agent control header"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X, pady=(0, 20))
        
        # Title
        title = ttk.Label(
            header_frame,
            text="🤖 Agent Control Panel",
            font=("Inter", 24, "bold")
        )
        title.pack(side=LEFT)
        
        # Agent status summary
        self.agent_summary = ttk.Label(
            header_frame,
            text="🔄 Loading agent data...",
            font=("Inter", 12)
        )
        self.agent_summary.pack(side=RIGHT)
    
    def _create_overview_cards(self, parent):
        """Create agent overview cards"""
        cards_frame = ttk.Frame(parent)
        cards_frame.pack(fill=X, pady=(0, 20))
        
        # Configure grid
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)
        
        # Overview cards
        self.overview_cards = {}
        cards_data = [
            ("total", "🤖", "Total Agents", "294", "primary"),
            ("online", "🟢", "Online", "0", "success"),
            ("conflicts", "⚠️", "Port Conflicts", "0", "warning"),
            ("issues", "🔴", "Issues", "0", "danger")
        ]
        
        for i, (key, icon, title, value, color) in enumerate(cards_data):
            card = self._create_overview_card(cards_frame, icon, title, value, color)
            card.grid(row=0, column=i, padx=(0, 15 if i < 3 else 0), sticky="ew")
            self.overview_cards[key] = card
    
    def _create_overview_card(self, parent, icon, title, value, color):
        """Create individual overview card"""
        if MODERN_STYLING:
            card_frame = ttk.Frame(parent, bootstyle=f"{color}-inverse", padding=15)
        else:
            card_frame = ttk.Frame(parent, padding=15, relief="solid", borderwidth=1)
        
        # Icon
        icon_label = ttk.Label(card_frame, text=icon, font=("Inter", 20))
        icon_label.pack()
        
        # Value
        value_label = ttk.Label(card_frame, text=value, font=("Inter", 18, "bold"))
        value_label.pack(pady=(5, 0))
        
        # Title
        title_label = ttk.Label(card_frame, text=title, font=("Inter", 11))
        title_label.pack()
        
        # Store references
        card_frame.value_label = value_label
        return card_frame
    
    def _create_agent_interface(self, parent):
        """Create agent list and details interface"""
        # Create paned window for list and details
        paned = ttk.PanedWindow(parent, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Left pane - Agent list
        list_frame = ttk.LabelFrame(paned, text="📋 Agent List", padding=10)
        paned.add(list_frame, weight=1)
        
        # Agent treeview
        self._create_agent_treeview(list_frame)
        
        # Right pane - Agent details
        details_frame = ttk.LabelFrame(paned, text="🔍 Agent Details", padding=10)
        paned.add(details_frame, weight=1)
        
        # Agent details display
        self._create_agent_details(details_frame)
    
    def _create_agent_treeview(self, parent):
        """Create agent list treeview"""
        # Treeview columns
        columns = ("Name", "Status", "Port", "Directory")
        
        # Create treeview
        self.agent_tree = ttk.Treeview(parent, columns=columns, show="headings", height=12)
        
        # Configure columns
        self.agent_tree.heading("Name", text="Agent Name")
        self.agent_tree.heading("Status", text="Status")
        self.agent_tree.heading("Port", text="Port")
        self.agent_tree.heading("Directory", text="Directory")
        
        self.agent_tree.column("Name", width=200)
        self.agent_tree.column("Status", width=80)
        self.agent_tree.column("Port", width=80)
        self.agent_tree.column("Directory", width=150)
        
        # Scrollbars
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True)
        
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.agent_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=HORIZONTAL, command=self.agent_tree.xview)
        self.agent_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack
        self.agent_tree.pack(side=LEFT, fill=BOTH, expand=True)
        v_scrollbar.pack(side=RIGHT, fill=Y)
        h_scrollbar.pack(side=BOTTOM, fill=X)
        
        # Bind selection event
        self.agent_tree.bind("<<TreeviewSelect>>", self._on_agent_select)
    
    def _create_agent_details(self, parent):
        """Create agent details display"""
        # Agent details text widget
        self.agent_details = tk.Text(
            parent,
            height=12,
            wrap=tk.WORD,
            font=("Fira Code", 10),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1,
            state=tk.DISABLED
        )
        
        # Scrollbar for details
        details_frame = ttk.Frame(parent)
        details_frame.pack(fill=BOTH, expand=True)
        
        scrollbar_details = ttk.Scrollbar(details_frame, orient=VERTICAL, command=self.agent_details.yview)
        self.agent_details.configure(yscrollcommand=scrollbar_details.set)
        
        self.agent_details.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar_details.pack(side=RIGHT, fill=Y)
    
    def _create_control_panel(self, parent):
        """Create agent control panel"""
        control_frame = ttk.LabelFrame(parent, text="⚡ Agent Controls", padding=15)
        control_frame.pack(fill=X)
        
        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=X)
        
        # Agent control buttons
        ttk.Button(btn_frame, text="🔄 Refresh", command=self.refresh).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🚀 Start Agent", command=self._start_agent).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="⏹️ Stop Agent", command=self._stop_agent).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🔁 Restart Agent", command=self._restart_agent).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🧹 Cleanup Conflicts", command=self._cleanup_conflicts).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🔍 Scan All", command=self._rescan_agents).pack(side=LEFT, padx=5)
    
    def _on_agent_select(self, event):
        """Handle agent selection"""
        selection = self.agent_tree.selection()
        if selection:
            item = self.agent_tree.item(selection[0])
            agent_name = item['values'][0]
            self._show_agent_details(agent_name)
    
    def _show_agent_details(self, agent_name):
        """Show detailed agent information"""
        try:
            # Get agent data from system service
            agent_status = self.system_service.get_agent_status()
            agent_data = None
            
            # Find agent in scan results
            agents = agent_status.get("agents", [])
            for agent in agents:
                if agent.get("name") == agent_name:
                    agent_data = agent
                    break
            
            # Update details display
            self.agent_details.configure(state=tk.NORMAL)
            self.agent_details.delete(1.0, tk.END)
            
            if agent_data:
                details_text = f"🤖 AGENT: {agent_name}\n\n"
                details_text += f"📁 Directory: {agent_data.get('directory', 'Unknown')}\n"
                details_text += f"🔌 Port: {agent_data.get('port', 'Unknown')}\n"
                details_text += f"🟢 Status: {agent_data.get('status', 'Unknown')}\n"
                details_text += f"📄 File Size: {agent_data.get('file_size', 'Unknown')}\n"
                details_text += f"📝 Functions: {agent_data.get('function_count', 0)}\n"
                details_text += f"🏗️ Classes: {agent_data.get('class_count', 0)}\n\n"
                
                # Configuration details
                config = agent_data.get('config', {})
                if config:
                    details_text += "⚙️ CONFIGURATION:\n"
                    for key, value in config.items():
                        details_text += f"   • {key}: {value}\n"
                    details_text += "\n"
                
                # Health check info
                health = agent_data.get('health_check', {})
                if health:
                    details_text += "🏥 HEALTH CHECK:\n"
                    details_text += f"   • Available: {health.get('available', False)}\n"
                    details_text += f"   • Last Check: {health.get('last_check', 'Never')}\n"
                
            else:
                details_text = f"No detailed information available for {agent_name}"
            
            self.agent_details.insert(tk.END, details_text)
            self.agent_details.configure(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error showing agent details: {e}")
    
    # Control methods
    def _start_agent(self):
        """Start selected agent"""
        selection = self.agent_tree.selection()
        if selection:
            agent_name = self.agent_tree.item(selection[0])['values'][0]
            self._run_agent_cli("start", agent_name)

    def _run_agent_cli(self, command: str, *args):
        """Utility to run agent_cli.py commands"""
        try:
            cmd = [sys.executable, "agent_cli.py", command] + list(args)
            result = subprocess.run(
                cmd,
                cwd=self.system_service.project_root,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self._log(f"✅ Agent command succeeded: {command} {' '.join(args)}")
                self.refresh()
            else:
                self._log(f"❌ Agent command failed: {result.stderr}")
                messagebox.showerror("Agent Error", result.stderr or "Unknown error")
        except subprocess.TimeoutExpired:
            messagebox.showerror("Timeout", "Agent command timed out.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _log(self, msg: str):
        print(msg)
    
    def _stop_agent(self):
        """Stop selected agent"""
        selection = self.agent_tree.selection()
        if selection:
            agent_name = self.agent_tree.item(selection[0])['values'][0]
            self._run_agent_cli("stop", agent_name)
    
    def _restart_agent(self):
        """Restart selected agent"""
        selection = self.agent_tree.selection()
        if selection:
            agent_name = self.agent_tree.item(selection[0])['values'][0]
            self._run_agent_cli("restart", agent_name)
    
    def _cleanup_conflicts(self):
        """Cleanup port conflicts"""
        self._run_agent_cli("cleanup-conflicts")
    
    def _rescan_agents(self):
        """Rescan all agents"""
        self._run_agent_cli("scan")
    
    def refresh(self):
        """Refresh view data and schedule next update"""
        try:
            # Load agent data from system service
            agent_status = self.system_service.get_agent_status()
            
            # Update overview cards
            self._update_overview_cards(agent_status)
            
            # Update agent list
            self._update_agent_list(agent_status)
            
            # Update summary
            total_agents = agent_status.get("summary", {}).get("total_agents", 0)
            total_dirs = agent_status.get("summary", {}).get("total_directories", 0)
            critical_issues = agent_status.get("summary", {}).get("critical_issues", 0)
            
            self.agent_summary.configure(text=f"📊 {total_agents} agents in {total_dirs} directories, {critical_issues} critical issues")
            
        except Exception as e:
            print(f"Error refreshing agent data: {e}")
            self.agent_summary.configure(text="❌ Error loading agent data")

        # schedule auto-refresh 60s
        self.after(60_000, self.refresh)
    
    def _update_overview_cards(self, agent_status):
        """Update overview cards with agent data"""
        try:
            summary = agent_status.get("summary", {})
            
            # Total agents
            total_agents = summary.get("total_agents", 294)
            self.overview_cards["total"].value_label.configure(text=str(total_agents))
            
            # Online agents count
            agents_list = agent_status.get("agents", [])
            online_count = sum(1 for a in agents_list if a.get("status") in ("running", "online"))
            self.overview_cards["online"].value_label.configure(text=str(online_count))
            
            # Port conflicts
            port_conflicts = summary.get("port_conflicts", 0)
            self.overview_cards["conflicts"].value_label.configure(text=str(port_conflicts))
            
            # Issues
            total_issues = summary.get("critical_issues", 0) + summary.get("warnings", 0)
            self.overview_cards["issues"].value_label.configure(text=str(total_issues))
            
        except Exception as e:
            print(f"Error updating overview cards: {e}")
    
    def _update_agent_list(self, agent_status):
        """Update agent list treeview"""
        try:
            # Clear existing items
            for item in self.agent_tree.get_children():
                self.agent_tree.delete(item)
            
            # Get agents data
            agents = agent_status.get("agents", [])
            
            # If agents is empty, try to get from different structure
            if not agents:
                # Try to get from scan results structure
                scan_results = agent_status.get("scan_results", {})
                for directory, dir_data in scan_results.items():
                    if isinstance(dir_data, dict) and "agents" in dir_data:
                        agents.extend(dir_data["agents"])
            
            # Add agents to treeview
            for agent in agents[:50]:  # Limit to first 50 for performance
                try:
                    name = agent.get("name", "Unknown")
                    status = agent.get("status", "Unknown")
                    port = agent.get("port", "N/A")
                    directory = agent.get("directory", "Unknown")
                    
                    # Shorten directory path for display
                    if len(directory) > 30:
                        directory = "..." + directory[-27:]
                    
                    # Determine status display
                    status_display = "Unknown"
                    if status == "running":
                        status_display = "🟢 Online"
                    elif status == "stopped":
                        status_display = "🔴 Offline"
                    elif status == "error":
                        status_display = "❌ Error"
                    else:
                        status_display = "⚪ Unknown"
                    
                    # Insert row
                    self.agent_tree.insert('', 'end', values=(name, status_display, port, directory))
                    
                except Exception as e:
                    print(f"Error processing agent {agent}: {e}")
                    continue
            
            # If still no agents, show placeholder
            if not self.agent_tree.get_children():
                self.agent_tree.insert('', 'end', values=(
                    "No agents found", 
                    "⚪ N/A", 
                    "N/A", 
                    "Run agent scan to discover agents"
                ))
                
        except Exception as e:
            print(f"Error updating agent list: {e}")
            # Add error message to treeview
            self.agent_tree.insert('', 'end', values=(
                "Error loading agents", 
                "❌ Error", 
                "N/A", 
                str(e)
            ))
