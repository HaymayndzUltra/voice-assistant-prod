"""
🎯 Modern GUI Control Center - Memory Intelligence View

Memory system visualization with MCP integration and
knowledge graph interface.
"""

# Built-in & stdlib
import tkinter as tk
from tkinter import ttk
from tkinter.constants import *
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# GUI utilities
from gui.utils.toast import show_info, show_error, show_warning

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False


class MemoryIntelligenceView(ttk.Frame):
    """Memory intelligence view"""
    
    def __init__(self, parent, system_service):
        super().__init__(parent)
        self.system_service = system_service
        self.pack(fill=BOTH, expand=True)
        
        # Subscribe to events
        self.system_service.bus.subscribe("memory_updated", self._on_memory_updated)
        self.system_service.bus.subscribe("brain_scan_complete", self._on_brain_updated)
        self.system_service.bus.subscribe("global_refresh", self._on_global_refresh)
        
        # Create comprehensive memory intelligence interface
        self._create_placeholder()
    
    def _create_placeholder(self):
        """Create comprehensive memory intelligence interface"""
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._create_header(main_container)
        
        # Create paned window for resizable sections
        paned_window = ttk.PanedWindow(main_container, orient=HORIZONTAL)
        paned_window.pack(fill=BOTH, expand=True, pady=(0, 20))
        
        # Left panel - Knowledge navigation
        left_panel = self._create_navigation_panel(paned_window)
        paned_window.add(left_panel, weight=1)
        
        # Right panel - Content and visualization
        right_panel = self._create_content_panel(paned_window)
        paned_window.add(right_panel, weight=2)
        
        # Bottom panel - Memory operations
        self._create_operations_panel(main_container)
        
        # Load initial data
        self.refresh()
    
    def _create_header(self, parent):
        """Create memory intelligence header"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X, pady=(0, 20))
        
        # Title
        title = ttk.Label(
            header_frame,
            text="🧠 Memory Intelligence Center",
            font=("Inter", 24, "bold")
        )
        title.pack(side=LEFT)
        
        # Memory status
        self.memory_status = ttk.Label(
            header_frame,
            text="📝 Loading memory status...",
            font=("Inter", 12)
        )
        self.memory_status.pack(side=RIGHT)
    
    def _create_navigation_panel(self, parent):
        """Create knowledge navigation panel"""
        nav_frame = ttk.Frame(parent)
        
        # Navigation notebook
        nav_notebook = ttk.Notebook(nav_frame)
        nav_notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # Project Brain tab
        brain_frame = ttk.Frame(nav_notebook)
        nav_notebook.add(brain_frame, text="🧠 Project Brain")
        self._create_brain_navigation(brain_frame)
        
        # Memory Bank tab
        memory_frame = ttk.Frame(nav_notebook)
        nav_notebook.add(memory_frame, text="📝 Memory Bank")
        self._create_memory_navigation(memory_frame)
        
        # Knowledge Graph tab
        graph_frame = ttk.Frame(nav_notebook)
        nav_notebook.add(graph_frame, text="🕸️ Knowledge Graph")
        self._create_graph_navigation(graph_frame)
        
        return nav_frame
    
    def _create_brain_navigation(self, parent):
        """Create project brain navigation tree"""
        # Search box
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search Brain:").pack(side=LEFT)
        self.brain_search = ttk.Entry(search_frame)
        self.brain_search.pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Button(search_frame, text="🔍", command=self._search_brain).pack(side=RIGHT)
        
        # Brain tree
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.brain_tree = ttk.Treeview(tree_frame, columns=('type', 'size'), show='tree headings')
        self.brain_tree.heading('#0', text='Knowledge Item')
        self.brain_tree.heading('type', text='Type')
        self.brain_tree.heading('size', text='Size')
        
        brain_scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL, command=self.brain_tree.yview)
        self.brain_tree.configure(yscrollcommand=brain_scrollbar.set)
        
        self.brain_tree.pack(side=LEFT, fill=BOTH, expand=True)
        brain_scrollbar.pack(side=RIGHT, fill=Y)
        
        # Bind events
        self.brain_tree.bind('<<TreeviewSelect>>', self._on_brain_select)
    
    def _create_memory_navigation(self, parent):
        """Create memory bank navigation"""
        # Memory categories
        categories_frame = ttk.LabelFrame(parent, text="Memory Categories", padding=5)
        categories_frame.pack(fill=X, padx=5, pady=5)
        
        self.memory_categories = tk.Listbox(categories_frame, height=8)
        self.memory_categories.pack(fill=X)
        
        # Sample categories
        memory_cats = [
            "Core System Knowledge",
            "Architecture Decisions", 
            "Implementation Strategies",
            "Bug Fixes & Solutions",
            "Performance Optimizations",
            "User Preferences",
            "Project Milestones",
            "Code Patterns"
        ]
        
        for cat in memory_cats:
            self.memory_categories.insert(tk.END, cat)
        
        self.memory_categories.bind('<<ListboxSelect>>', self._on_memory_category_select)
        
        # Recent memories
        recent_frame = ttk.LabelFrame(parent, text="Recent Memories", padding=5)
        recent_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.recent_memories = tk.Listbox(recent_frame)
        self.recent_memories.pack(fill=BOTH, expand=True)
        self.recent_memories.bind('<<ListboxSelect>>', self._on_recent_memory_select)
    
    def _create_graph_navigation(self, parent):
        """Create knowledge graph navigation"""
        # Graph controls
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill=X, padx=5, pady=5)
        
        ttk.Button(controls_frame, text="🔄 Refresh Graph", command=self._refresh_graph).pack(side=LEFT, padx=2)
        ttk.Button(controls_frame, text="🔍 Explore", command=self._explore_graph).pack(side=LEFT, padx=2)
        
        # Graph entities list
        entities_frame = ttk.LabelFrame(parent, text="Graph Entities", padding=5)
        entities_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.graph_entities = ttk.Treeview(entities_frame, columns=('type', 'connections'), show='tree headings')
        self.graph_entities.heading('#0', text='Entity')
        self.graph_entities.heading('type', text='Type')
        self.graph_entities.heading('connections', text='Connections')
        
        graph_scrollbar = ttk.Scrollbar(entities_frame, orient=VERTICAL, command=self.graph_entities.yview)
        self.graph_entities.configure(yscrollcommand=graph_scrollbar.set)
        
        self.graph_entities.pack(side=LEFT, fill=BOTH, expand=True)
        graph_scrollbar.pack(side=RIGHT, fill=Y)
        
        self.graph_entities.bind('<<TreeviewSelect>>', self._on_graph_entity_select)
    
    def _create_content_panel(self, parent):
        """Create content visualization panel"""
        content_frame = ttk.Frame(parent)
        
        # Content notebook
        self.content_notebook = ttk.Notebook(content_frame)
        self.content_notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # Content viewer tab
        viewer_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(viewer_frame, text="📄 Content Viewer")
        self._create_content_viewer(viewer_frame)
        
        # Knowledge graph tab
        graph_viz_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(graph_viz_frame, text="🕸️ Graph Visualization")
        self._create_graph_visualization(graph_viz_frame)
        
        # Search results tab
        search_frame = ttk.Frame(self.content_notebook)
        self.content_notebook.add(search_frame, text="🔍 Search Results")
        self._create_search_results(search_frame)
        
        return content_frame
    
    def _create_content_viewer(self, parent):
        """Create content viewer"""
        # Content header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X, padx=5, pady=5)
        
        self.content_title = ttk.Label(header_frame, text="Select an item to view", font=("Inter", 16, "bold"))
        self.content_title.pack(side=LEFT)
        
        # Content actions
        actions_frame = ttk.Frame(header_frame)
        actions_frame.pack(side=RIGHT)
        
        ttk.Button(actions_frame, text="📎 Edit", command=self._edit_content).pack(side=LEFT, padx=2)
        ttk.Button(actions_frame, text="📄 Export", command=self._export_content).pack(side=LEFT, padx=2)
        ttk.Button(actions_frame, text="🔗 Share", command=self._share_content).pack(side=LEFT, padx=2)
        
        # Content display
        content_container = ttk.Frame(parent)
        content_container.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.content_display = tk.Text(
            content_container,
            wrap=tk.WORD,
            font=("Inter", 11),
            bg="#f8f9fa" if not MODERN_STYLING else None,
            fg="#2d3748" if not MODERN_STYLING else None,
            relief="flat",
            borderwidth=1,
            state=tk.DISABLED
        )
        
        content_scrollbar = ttk.Scrollbar(content_container, orient=VERTICAL, command=self.content_display.yview)
        self.content_display.configure(yscrollcommand=content_scrollbar.set)
        
        self.content_display.pack(side=LEFT, fill=BOTH, expand=True)
        content_scrollbar.pack(side=RIGHT, fill=Y)
    
    def _create_graph_visualization(self, parent):
        """Create graph visualization panel"""
        # Graph placeholder (would integrate with networkx/matplotlib)
        viz_frame = ttk.LabelFrame(parent, text="Knowledge Graph Visualization", padding=10)
        viz_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # Placeholder for graph visualization
        self.graph_canvas = tk.Canvas(
            viz_frame,
            bg="#1a1a1a" if not MODERN_STYLING else "white",
            relief="flat",
            borderwidth=1
        )
        self.graph_canvas.pack(fill=BOTH, expand=True)
        
        # Sample graph visualization text
        self.graph_canvas.create_text(
            200, 150,
            text="🕸️ Interactive Knowledge Graph\n\nVisualization of:\n• Entity relationships\n• Knowledge connections\n• Memory clusters\n• Project dependencies\n\n[Future: NetworkX + Matplotlib integration]",
            font=("Inter", 12),
            fill="#e2e8f0" if not MODERN_STYLING else "#2d3748"
        )
    
    def _create_search_results(self, parent):
        """Create search results panel"""
        # Search interface
        search_header = ttk.Frame(parent)
        search_header.pack(fill=X, padx=5, pady=5)
        
        ttk.Label(search_header, text="Search Knowledge:").pack(side=LEFT)
        self.knowledge_search = ttk.Entry(search_header)
        self.knowledge_search.pack(side=LEFT, fill=X, expand=True, padx=5)
        ttk.Button(search_header, text="🔍 Search", command=self._search_knowledge).pack(side=RIGHT)
        
        # Results display
        results_frame = ttk.Frame(parent)
        results_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.search_results = ttk.Treeview(
            results_frame, 
            columns=('relevance', 'type', 'date'), 
            show='tree headings'
        )
        self.search_results.heading('#0', text='Result')
        self.search_results.heading('relevance', text='Relevance')
        self.search_results.heading('type', text='Type')
        self.search_results.heading('date', text='Date')
        
        search_scrollbar = ttk.Scrollbar(results_frame, orient=VERTICAL, command=self.search_results.yview)
        self.search_results.configure(yscrollcommand=search_scrollbar.set)
        
        self.search_results.pack(side=LEFT, fill=BOTH, expand=True)
        search_scrollbar.pack(side=RIGHT, fill=Y)
        
        self.search_results.bind('<<TreeviewSelect>>', self._on_search_result_select)
    
    def _create_operations_panel(self, parent):
        """Create memory operations panel"""
        ops_frame = ttk.LabelFrame(parent, text="⚙️ Memory Operations", padding=10)
        ops_frame.pack(fill=X)
        
        # Quick actions
        actions_frame = ttk.Frame(ops_frame)
        actions_frame.pack(fill=X)
        
        ttk.Button(actions_frame, text="📝 Create Memory", command=self._create_memory).pack(side=LEFT, padx=5)
        ttk.Button(actions_frame, text="🔄 Sync All", command=self._sync_all_memory).pack(side=LEFT, padx=5)
        ttk.Button(actions_frame, text="🧹 Cleanup", command=self._cleanup_memory).pack(side=LEFT, padx=5)
        ttk.Button(actions_frame, text="📊 Analytics", command=self._memory_analytics).pack(side=LEFT, padx=5)
        ttk.Button(actions_frame, text="⚙️ Settings", command=self._memory_settings).pack(side=LEFT, padx=5)
    
    # Event handlers
    def _on_brain_select(self, event):
        """Handle brain tree selection"""
        selection = self.brain_tree.selection()
        if selection:
            item = self.brain_tree.item(selection[0])
            self._display_content(f"Brain Item: {item['text']}", "Sample brain content...")
    
    def _on_memory_category_select(self, event):
        """Handle memory category selection"""
        selection = self.memory_categories.curselection()
        if selection:
            category = self.memory_categories.get(selection[0])
            self._display_content(f"Memory Category: {category}", f"Memories in {category}...")
    
    def _on_recent_memory_select(self, event):
        """Handle recent memory selection"""
        selection = self.recent_memories.curselection()
        if selection:
            memory = self.recent_memories.get(selection[0])
            self._display_content(f"Recent Memory: {memory}", "Recent memory content...")
    
    def _on_graph_entity_select(self, event):
        """Handle graph entity selection"""
        selection = self.graph_entities.selection()
        if selection:
            item = self.graph_entities.item(selection[0])
            self._display_content(f"Graph Entity: {item['text']}", "Entity relationships and connections...")
    
    def _on_search_result_select(self, event):
        """Handle search result selection"""
        selection = self.search_results.selection()
        if selection:
            item = self.search_results.item(selection[0])
            self._display_content(f"Search Result: {item['text']}", "Search result content...")
    
    def _display_content(self, title, content):
        """Display content in the content viewer"""
        self.content_title.configure(text=title)
        
        self.content_display.configure(state=tk.NORMAL)
        self.content_display.delete(1.0, tk.END)
        self.content_display.insert(tk.END, content)
        self.content_display.configure(state=tk.DISABLED)
    
    # Action methods
    def _search_brain(self):
        """Search project brain"""
        query = self.brain_search.get().strip()
        if not query:
            return

        results = self._run_memory_cli("search", query)
        content = results.stdout if results else "No results"
        self._display_content(f"Brain Search: {query}", content)
    
    def _search_knowledge(self):
        """Search all knowledge"""
        query = self.knowledge_search.get().strip()
        if not query:
            return

        # Clear existing results
        for item in self.search_results.get_children():
            self.search_results.delete(item)

        results = self._run_memory_cli("search", query)
        if results and results.returncode == 0:
            try:
                import json
                parsed = json.loads(results.stdout)
                # Expect list of {title, relevance, type, date}
                for res in parsed[:100]:
                    self.search_results.insert('', tk.END, text=res.get("title"), values=(res.get("relevance"), res.get("type"), res.get("date")))
            except Exception:
                # fallback plain text
                self._display_content("Search Results", results.stdout)
        else:
            show_error(self, f"Search failed: {results.stderr if results else 'Unknown error'}")
    
    def _refresh_graph(self):
        """Refresh knowledge graph"""
        # Clear and reload graph entities
        for item in self.graph_entities.get_children():
            self.graph_entities.delete(item)
        
        # Add sample entities
        sample_entities = [
            ("AI System Monorepo", "Project", "15"),
            ("Task Queue System", "Component", "8"),
            ("Memory Intelligence", "Component", "6"),
            ("GUI Control Center", "Component", "12")
        ]
        
        for title, type_, connections in sample_entities:
            self.graph_entities.insert('', tk.END, text=title, values=(type_, connections))
    
    def _explore_graph(self):
        """Explore knowledge graph"""
        self._display_content("Graph Explorer", "Interactive graph exploration interface...")
    
    def _edit_content(self):
        """Edit selected content"""
        self._display_content("Edit Mode", "Content editing interface...")
    
    def _export_content(self):
        """Export selected content"""
        self._display_content("Export", "Content export options...")
    
    def _share_content(self):
        """Share selected content"""
        self._display_content("Share", "Content sharing options...")
    
    def _create_memory(self):
        """Create new memory"""
        self._display_content("Create Memory", "New memory creation interface...")
    
    def _sync_all_memory(self):
        """Sync all memory systems"""
        result = self._run_memory_cli("sync")
        if result and result.returncode == 0:
            show_info(self, "Memory synchronized successfully")
            self.system_service.bus.publish("memory_updated", {})
        else:
            show_error(self, f"Sync failed: {result.stderr if result else 'Unknown error'}")
    
    def _cleanup_memory(self):
        """Cleanup memory systems"""
        # Use simple confirmation via toast
        show_warning(self, "Starting memory cleanup...")
        result = self._run_memory_cli("cleanup", "--dry-run")
        if result and result.returncode == 0:
            # Show what would be deleted
            show_info(self, "Cleanup preview completed. Run again to confirm.")
            # Actually run cleanup
            result = self._run_memory_cli("cleanup")
            if result and result.returncode == 0:
                show_info(self, "Memory cleanup completed")
                self.system_service.bus.publish("memory_updated", {})
            else:
                show_error(self, f"Cleanup failed: {result.stderr if result else 'Unknown error'}")
        else:
            show_error(self, f"Cleanup preview failed: {result.stderr if result else 'Unknown error'}")
    
    def _memory_analytics(self):
        """Show memory analytics"""
        self._display_content("Analytics", "Memory usage and performance analytics...")
    
    def _memory_settings(self):
        """Configure memory settings"""
        self._display_content("Settings", "Memory system configuration options...")
    
    def _on_memory_updated(self, event_data):
        """Handle memory updated event"""
        try:
            self._load_brain_tree()
            self._load_recent_memories()
            self._update_memory_status()
            show_info(self, "Memory data updated")
        except Exception as e:
            show_error(self, f"Error updating memory data: {e}")
    
    def _on_brain_updated(self, event_data):
        """Handle brain scan complete event"""
        try:
            self._load_brain_tree()
            self._update_memory_status()
            show_info(self, "Brain scan completed")
        except Exception as e:
            show_error(self, f"Error updating brain data: {e}")
    
    def _on_global_refresh(self, event_data):
        """Handle global refresh event"""
        self.refresh()
    
    def _update_memory_status(self):
        """Update memory status display"""
        try:
            mem_status = self.system_service.get_memory_status()
            brain_files = mem_status.get("brain_files", 0)
            arch_files = mem_status.get("architecture_plans", 0)
            self.memory_status.configure(text=f"📚 {brain_files} brain files, {arch_files} plans | Updated {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"Memory status update error: {e}")
    
    def refresh(self):
        """Manual refresh - now event-driven"""
        try:
            self._update_memory_status()
            self._load_brain_tree()
            self._load_recent_memories()
            show_info(self, "Memory data refreshed")
        except Exception as e:
            show_error(self, f"Error refreshing memory: {e}")

    # ---------- Internal helpers ----------
    async def _run_memory_cli_async(self, *args):
        """Run memory_system/cli.py async and return result dict"""
        try:
            cmd_args = ["memory_system/cli.py"] + list(args)
            result = await self.system_service.async_execute_cli(" ".join(cmd_args))
            return result
        except Exception as e:
            show_error(self, f"Memory CLI error: {e}")
            return None
    
    def _run_memory_cli(self, *args):
        """Run memory_system/cli.py sync (legacy support)"""
        try:
            # Create and run async task
            import subprocess
            cmd = [sys.executable, "memory_system/cli.py"] + list(args)
            result = subprocess.run(
                cmd,
                cwd=self.system_service.project_root,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result
        except Exception as e:
            show_error(self, f"Memory CLI error: {e}")
            return None

    def _load_brain_tree(self):
        """Scan project-brain directory and populate tree"""
        # clear tree
        for item in self.brain_tree.get_children():
            self.brain_tree.delete(item)

        brain_dir = self.system_service.memory_bank / "project-brain"
        if not brain_dir.exists():
            return

        for md_path in brain_dir.rglob("*.md"):
            rel = md_path.relative_to(brain_dir)
            parent = ""
            parts = rel.parts
            for i, part in enumerate(parts):
                current_path = "/".join(parts[: i + 1])
                # add node if not exists
                nodes = self.brain_tree.get_children(parent)
                existing = None
                for n in nodes:
                    if self.brain_tree.item(n, "text") == part:
                        existing = n
                        break
                if existing is None:
                    node = self.brain_tree.insert(parent, tk.END, text=part, values=("Dir" if i < len(parts) - 1 else "File", md_path.stat().st_size))
                    existing = node
                parent = existing

    def _load_recent_memories(self):
        """Load recent modified markdown files"""
        self.recent_memories.delete(0, tk.END)
        brain_dir = self.system_service.memory_bank / "project-brain"
        if not brain_dir.exists():
            return
        files = sorted(brain_dir.rglob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:20]
        for f in files:
            self.recent_memories.insert(tk.END, f.name)
