"""
🎯 Modern GUI Control Center - Agent Control View

Agent management interface with health monitoring and
control for 294 discovered agents across MainPC and PC2.
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
        try:
            selection = self.agent_tree.selection()
            if not selection:
                return
                
            # Get the selected item
            item = selection[0]
            
            # Try to get stored agent data
            try:
                agent_data = self.agent_tree.set(item, "agent_data")
                if isinstance(agent_data, str):
                    # If it's stored as string, it might be a placeholder
                    agent_values = self.agent_tree.item(item)['values']
                    agent_name = agent_values[0] if agent_values else "Unknown"
                    self._show_agent_details(agent_name, None)
                else:
                    # We have full agent data
                    self._show_agent_details(agent_data.get("name", "Unknown"), agent_data)
            except:
                # Fallback to just using the name from the tree
                agent_values = self.agent_tree.item(item)['values']
                agent_name = agent_values[0] if agent_values else "Unknown"
                self._show_agent_details(agent_name, None)
                
        except Exception as e:
            print(f"Error handling agent selection: {e}")
    
    def _show_agent_details(self, agent_name, agent_data):
        """Show detailed agent information"""
        try:
            # Get agent data from system service if not provided
            if agent_data is None:
                agent_status = self.system_service.get_agent_status()
                agents = agent_status.get("agents", [])
                for agent in agents:
                    if agent.get("name") == agent_name:
                        agent_data = agent
                        break
            
            # Update details display
            self.agent_details.configure(state=tk.NORMAL)
            self.agent_details.delete(1.0, tk.END)
            
            # Build details text
            details_text = f"🤖 AGENT: {agent_name}\n\n"
            
            if agent_data:
                # Basic information
                details_text += f"📝 ID: {agent_data.get('id', 'N/A')}\n"
                details_text += f"🏷️ Type: {agent_data.get('type', 'N/A')}\n"
                details_text += f"📂 Category: {agent_data.get('category', 'N/A').title()}\n"
                details_text += f"📊 Status: {agent_data.get('status', 'unknown').title()}\n"
                details_text += f"💚 Health: {agent_data.get('health', 'unknown').title()}\n\n"
                
                # Connection info
                details_text += "🔌 CONNECTION INFO:\n"
                details_text += f"   • Port: {agent_data.get('port', 'N/A')}\n"
                if agent_data.get('pid'):
                    details_text += f"   • Process ID: {agent_data.get('pid')}\n"
                details_text += "\n"
                
                # Performance metrics
                if agent_data.get('cpu_usage') is not None or agent_data.get('memory_usage') is not None:
                    details_text += "📈 PERFORMANCE:\n"
                    if agent_data.get('cpu_usage') is not None:
                        details_text += f"   • CPU Usage: {agent_data.get('cpu_usage')}%\n"
                    if agent_data.get('memory_usage') is not None:
                        details_text += f"   • Memory: {agent_data.get('memory_usage')} MB\n"
                    if agent_data.get('uptime'):
                        uptime_hours = agent_data.get('uptime', 0) / 3600
                        details_text += f"   • Uptime: {uptime_hours:.1f} hours\n"
                    details_text += "\n"
                
                # Issues/warnings
                issues = agent_data.get('issues', [])
                if issues:
                    details_text += "⚠️ ISSUES:\n"
                    for issue in issues:
                        details_text += f"   • {issue}\n"
                    details_text += "\n"
                
                # Last check
                if agent_data.get('last_check'):
                    details_text += f"🕐 Last Check: {agent_data.get('last_check')}\n"
                
            else:
                details_text = f"No detailed information available for {agent_name}\n\n"
                details_text += "ℹ️ Run a health check or rescan to gather agent information."
            
            self.agent_details.insert(tk.END, details_text)
            self.agent_details.configure(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error showing agent details: {e}")
    
    # Control methods
    def _start_agent(self):
        """Start selected agent"""
        try:
            selection = self.agent_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an agent to start")
                return
                
            agent_name = self.agent_tree.item(selection[0])['values'][0]
            
            # For now, show info message - actual agent start would require agent-specific scripts
            messagebox.showinfo(
                "Start Agent", 
                f"Starting agent '{agent_name}' would require:\n\n"
                f"1. Locating the agent's start script\n"
                f"2. Checking port availability\n"
                f"3. Starting the agent process\n\n"
                f"This functionality needs to be implemented based on your agent architecture."
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error starting agent: {e}")
    
    def _stop_agent(self):
        """Stop selected agent"""
        try:
            selection = self.agent_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an agent to stop")
                return
                
            agent_name = self.agent_tree.item(selection[0])['values'][0]
            
            # Confirm stop
            response = messagebox.askyesno(
                "Stop Agent",
                f"Are you sure you want to stop agent '{agent_name}'?"
            )
            
            if response:
                # For now, show info message
                messagebox.showinfo(
                    "Stop Agent",
                    f"Stopping agent '{agent_name}' would require:\n\n"
                    f"1. Finding the agent's process ID\n"
                    f"2. Sending stop signal\n"
                    f"3. Verifying clean shutdown\n\n"
                    f"This functionality needs to be implemented based on your agent architecture."
                )
                
        except Exception as e:
            messagebox.showerror("Error", f"Error stopping agent: {e}")
    
    def _restart_agent(self):
        """Restart selected agent"""
        try:
            selection = self.agent_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select an agent to restart")
                return
                
            agent_name = self.agent_tree.item(selection[0])['values'][0]
            
            messagebox.showinfo(
                "Restart Agent",
                f"Restarting agent '{agent_name}'...\n\n"
                f"This would stop the agent and start it again."
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error restarting agent: {e}")
    
    def _cleanup_conflicts(self):
        """Cleanup port conflicts"""
        try:
            response = messagebox.askyesno(
                "Cleanup Port Conflicts",
                "This will:\n\n"
                "• Identify agents with port conflicts\n"
                "• Stop conflicting agents\n"
                "• Reassign ports where possible\n\n"
                "Continue?"
            )
            
            if response:
                # Get agent data
                agent_status = self.system_service.get_agent_status()
                agents = agent_status.get("agents", [])
                
                # Find agents with port conflicts
                conflicts = [a for a in agents if a.get("issues") and any("conflict" in str(i).lower() for i in a["issues"])]
                
                if conflicts:
                    messagebox.showinfo(
                        "Port Conflicts Found",
                        f"Found {len(conflicts)} agents with port conflicts:\n\n" +
                        "\n".join([f"• {a['name']} (Port {a.get('port', 'N/A')})" for a in conflicts[:5]]) +
                        ("\n..." if len(conflicts) > 5 else "") +
                        "\n\nManual intervention required to resolve conflicts."
                    )
                else:
                    messagebox.showinfo("No Conflicts", "No port conflicts found!")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error cleaning up conflicts: {e}")
    
    def _rescan_agents(self):
        """Rescan all agents"""
        try:
            response = messagebox.askyesno(
                "Rescan Agents",
                "This will rescan all agent directories to discover new agents.\n\n"
                "This may take a few moments. Continue?"
            )
            
            if response:
                messagebox.showinfo(
                    "Agent Scan",
                    "Agent scanning would:\n\n"
                    "• Search all configured directories\n"
                    "• Identify agent files\n"
                    "• Check agent health\n"
                    "• Update agent_scan_results.json\n\n"
                    "For now, refreshing with existing data..."
                )
                
                # Refresh the view
                self.refresh()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error rescanning agents: {e}")
    
    def refresh(self):
        """Refresh view data"""
        try:
            # Load agent data from system service
            agent_status = self.system_service.get_agent_status()
            
            # Update overview cards
            self._update_overview_cards(agent_status)
            
            # Update agent list
            self._update_agent_list(agent_status)
            
            # Update summary
            total_agents = agent_status.get("total_agents", len(agent_status.get("agents", [])))
            active_agents = agent_status.get("active_agents", 0)
            port_conflicts = agent_status.get("port_conflicts", 0)
            
            if port_conflicts > 0:
                self.agent_summary.configure(
                    text=f"📊 {total_agents} agents discovered | {active_agents} active | ⚠️ {port_conflicts} port conflicts"
                )
            else:
                self.agent_summary.configure(
                    text=f"📊 {total_agents} agents discovered | {active_agents} active | ✅ No conflicts"
                )
            
        except Exception as e:
            print(f"Error refreshing agent data: {e}")
            self.agent_summary.configure(text="❌ Error loading agent data")
    
    def _update_overview_cards(self, agent_status):
        """Update overview cards with agent data"""
        try:
            # Get total agents count
            total_agents = agent_status.get("total_agents", len(agent_status.get("agents", [])))
            self.overview_cards["total"].value_label.configure(text=str(total_agents))
            
            # Count active/online agents
            agents = agent_status.get("agents", [])
            online_count = sum(1 for agent in agents if agent.get("status") == "active")
            self.overview_cards["online"].value_label.configure(text=str(online_count))
            
            # Port conflicts from the data
            port_conflicts = agent_status.get("port_conflicts", 0)
            self.overview_cards["conflicts"].value_label.configure(text=str(port_conflicts))
            
            # Count agents with issues
            issues_count = sum(1 for agent in agents if agent.get("issues"))
            self.overview_cards["issues"].value_label.configure(text=str(issues_count))
            
        except Exception as e:
            print(f"Error updating overview cards: {e}")
    
    def _update_agent_list(self, agent_status):
        """Update agent list treeview"""
        try:
            # Clear existing items
            for item in self.agent_tree.get_children():
                self.agent_tree.delete(item)
            
            # Get agents data from the correct structure
            agents = agent_status.get("agents", [])
            
            # Add agents to treeview
            for agent in agents:
                try:
                    name = agent.get("name", "Unknown")
                    status = agent.get("status", "unknown")
                    health = agent.get("health", "unknown")
                    port = agent.get("port", "N/A")
                    category = agent.get("category", "unknown")
                    
                    # Determine status display based on status and health
                    if status == "active":
                        if health == "healthy":
                            status_display = "🟢 Healthy"
                        elif health == "warning":
                            status_display = "🟡 Warning"
                        else:
                            status_display = "🔴 Error"
                    elif status == "inactive":
                        status_display = "⚪ Inactive"
                    else:
                        status_display = "❓ Unknown"
                    
                    # Format port display
                    port_display = str(port) if port != "N/A" else "N/A"
                    
                    # Add issues indicator if present
                    if agent.get("issues"):
                        port_display += " ⚠️"
                    
                    # Insert row with agent data
                    item = self.agent_tree.insert('', 'end', values=(
                        name, 
                        status_display, 
                        port_display, 
                        category.title()
                    ))
                    
                    # Store full agent data for details display
                    self.agent_tree.set(item, "agent_data", agent)
                    
                except Exception as e:
                    print(f"Error processing agent {agent}: {e}")
                    continue
            
            # If no agents found, show message
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
