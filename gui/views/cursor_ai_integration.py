"""
🤖 Modern GUI Control Center - Cursor AI Integration View

Specialized view for Cursor AI agent interaction with prompt conversion,
context management, and AI workflow optimization.
"""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter.constants import *
import json
import sys
import os

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from barok_to_prompt_converter import BarokToPromptConverter

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False


class CursorAIIntegrationView(ttk.Frame):
    """Cursor AI integration view"""
    
    def __init__(self, parent, system_service):
        super().__init__(parent)
        self.system_service = system_service
        self.pack(fill=BOTH, expand=True)
        
        # Initialize converter
        self.converter = BarokToPromptConverter()
        
        # Prompt history
        self.prompt_history = []
        
        # Create interface
        self._create_interface()
    
    def _create_interface(self):
        """Create Cursor AI integration interface"""
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self._create_header(main_container)
        
        # Create paned window for layout
        paned = ttk.PanedWindow(main_container, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, pady=(20, 0))
        
        # Left pane - Input and conversion
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        self._create_input_section(left_frame)
        
        # Right pane - Context and history
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        self._create_context_section(right_frame)
    
    def _create_header(self, parent):
        """Create header section"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=X)
        
        # Title
        title = ttk.Label(
            header_frame,
            text="🤖 Cursor AI Integration Center",
            font=("Inter", 24, "bold")
        )
        title.pack(side=LEFT)
        
        # Status
        self.ai_status = ttk.Label(
            header_frame,
            text="✅ AI Ready",
            font=("Inter", 12)
        )
        self.ai_status.pack(side=RIGHT)
    
    def _create_input_section(self, parent):
        """Create input and conversion section"""
        # Input frame
        input_frame = ttk.LabelFrame(parent, text="💬 Barok Input Converter", padding=15)
        input_frame.pack(fill=BOTH, expand=True, padx=(0, 10))
        
        # Instructions
        instructions = ttk.Label(
            input_frame,
            text="Type your request in any language/format (Filipino/English/Barok):",
            font=("Inter", 10),
            foreground="gray"
        )
        instructions.pack(anchor=W, pady=(0, 10))
        
        # Input text area
        input_container = ttk.Frame(input_frame)
        input_container.pack(fill=BOTH, expand=True)
        
        self.input_text = tk.Text(
            input_container,
            height=6,
            wrap=tk.WORD,
            font=("Inter", 11),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None
        )
        self.input_text.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(input_container, command=self.input_text.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.input_text.configure(yscrollcommand=scrollbar.set)
        
        # Quick examples
        examples_frame = ttk.Frame(input_frame)
        examples_frame.pack(fill=X, pady=(10, 0))
        
        ttk.Label(examples_frame, text="Quick examples:", font=("Inter", 9)).pack(side=LEFT)
        
        example_buttons = [
            ("Fix error", "ayusin yung error sa code"),
            ("Create button", "gawa ng button para save"),
            ("Add feature", "dagdag ng bagong feature")
        ]
        
        for label, text in example_buttons:
            ttk.Button(
                examples_frame,
                text=label,
                command=lambda t=text: self._insert_example(t),
                width=12
            ).pack(side=LEFT, padx=(5, 0))
        
        # Convert button
        convert_btn = ttk.Button(
            input_frame,
            text="🔄 Convert to AI Prompt",
            command=self._convert_input,
            bootstyle="primary" if MODERN_STYLING else None
        )
        convert_btn.pack(fill=X, pady=(15, 10))
        
        # Output section
        output_label = ttk.Label(input_frame, text="🎯 Converted Cursor AI Prompt:", font=("Inter", 10, "bold"))
        output_label.pack(anchor=W, pady=(10, 5))
        
        # Output text area
        output_container = ttk.Frame(input_frame)
        output_container.pack(fill=BOTH, expand=True)
        
        self.output_text = tk.Text(
            output_container,
            height=12,
            wrap=tk.WORD,
            font=("Fira Code", 10),
            bg="#1a202c" if not MODERN_STYLING else None,
            fg="#90cdf4" if not MODERN_STYLING else None
        )
        self.output_text.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Output scrollbar
        output_scrollbar = ttk.Scrollbar(output_container, command=self.output_text.yview)
        output_scrollbar.pack(side=RIGHT, fill=Y)
        self.output_text.configure(yscrollcommand=output_scrollbar.set)
        
        # Action buttons
        action_frame = ttk.Frame(input_frame)
        action_frame.pack(fill=X, pady=(10, 0))
        
        ttk.Button(
            action_frame,
            text="📋 Copy Prompt",
            command=self._copy_prompt
        ).pack(side=LEFT, padx=(0, 5))
        
        ttk.Button(
            action_frame,
            text="💾 Save to History",
            command=self._save_to_history
        ).pack(side=LEFT, padx=(0, 5))
        
        ttk.Button(
            action_frame,
            text="🚀 Send to Cursor",
            command=self._send_to_cursor,
            bootstyle="success" if MODERN_STYLING else None
        ).pack(side=LEFT)
    
    def _create_context_section(self, parent):
        """Create context and history section"""
        # Create notebook
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=BOTH, expand=True, padx=(10, 0))
        
        # Context tab
        context_frame = ttk.Frame(notebook)
        notebook.add(context_frame, text="📍 Current Context")
        self._create_context_display(context_frame)
        
        # History tab
        history_frame = ttk.Frame(notebook)
        notebook.add(history_frame, text="📜 Prompt History")
        self._create_history_display(history_frame)
        
        # Templates tab
        templates_frame = ttk.Frame(notebook)
        notebook.add(templates_frame, text="📝 Templates")
        self._create_templates_display(templates_frame)
    
    def _create_context_display(self, parent):
        """Create current context display"""
        # Active files
        files_frame = ttk.LabelFrame(parent, text="📂 Active Files", padding=10)
        files_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        self.active_files_list = tk.Listbox(
            files_frame,
            height=6,
            font=("Fira Code", 9),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None
        )
        self.active_files_list.pack(fill=BOTH, expand=True)
        
        # Add sample files
        sample_files = [
            "gui/views/cursor_ai_integration.py",
            "gui/scripts/barok_to_prompt_converter.py",
            "todo_manager.py",
            "queue_cli.py"
        ]
        for file in sample_files:
            self.active_files_list.insert(tk.END, file)
        
        # Current task
        task_frame = ttk.LabelFrame(parent, text="📋 Current Task", padding=10)
        task_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.current_task_text = tk.Text(
            task_frame,
            height=4,
            wrap=tk.WORD,
            font=("Inter", 9),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None
        )
        self.current_task_text.pack(fill=BOTH, expand=True)
        self.current_task_text.insert(tk.END, "Current task: GUI Integration\nStatus: In Progress\nPriority: High")
        self.current_task_text.configure(state=tk.DISABLED)
        
        # AI Stats
        stats_frame = ttk.LabelFrame(parent, text="📊 AI Session Stats", padding=10)
        stats_frame.pack(fill=X, padx=10, pady=(0, 10))
        
        stats_text = "Prompts Generated: 12\nSuccess Rate: 92%\nAvg Response Time: 2.3s"
        ttk.Label(stats_frame, text=stats_text, font=("Inter", 9)).pack()
    
    def _create_history_display(self, parent):
        """Create prompt history display"""
        # History list
        history_container = ttk.Frame(parent)
        history_container.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Treeview for history
        columns = ("Time", "Original", "Intent")
        self.history_tree = ttk.Treeview(
            history_container,
            columns=columns,
            show="headings",
            height=15
        )
        
        # Configure columns
        self.history_tree.heading("Time", text="Time")
        self.history_tree.heading("Original", text="Original Input")
        self.history_tree.heading("Intent", text="Intent")
        
        self.history_tree.column("Time", width=100)
        self.history_tree.column("Original", width=200)
        self.history_tree.column("Intent", width=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(history_container, orient=VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.history_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Bind selection
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_select)
        
        # Control buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=X, padx=10, pady=(0, 10))
        
        ttk.Button(
            control_frame,
            text="🔄 Reload Selected",
            command=self._reload_from_history
        ).pack(side=LEFT, padx=(0, 5))
        
        ttk.Button(
            control_frame,
            text="🗑️ Clear History",
            command=self._clear_history
        ).pack(side=LEFT)
    
    def _create_templates_display(self, parent):
        """Create prompt templates display"""
        # Template categories
        categories_frame = ttk.Frame(parent)
        categories_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Label(categories_frame, text="Category:", font=("Inter", 10)).pack(side=LEFT)
        
        self.template_category = ttk.Combobox(
            categories_frame,
            values=["Bug Fixes", "Feature Development", "Refactoring", "Testing", "Documentation"],
            width=20
        )
        self.template_category.set("Feature Development")
        self.template_category.pack(side=LEFT, padx=(10, 0))
        
        # Templates list
        templates_frame = ttk.LabelFrame(parent, text="📝 Available Templates", padding=10)
        templates_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.templates_list = tk.Listbox(
            templates_frame,
            height=12,
            font=("Inter", 9),
            bg="#2d3748" if not MODERN_STYLING else None,
            fg="#e2e8f0" if not MODERN_STYLING else None
        )
        self.templates_list.pack(fill=BOTH, expand=True)
        
        # Sample templates
        templates = [
            "Create CRUD operations for [model]",
            "Add validation to [form/input]",
            "Implement error handling for [feature]",
            "Optimize performance of [function]",
            "Add unit tests for [component]",
            "Refactor [module] for better maintainability"
        ]
        
        for template in templates:
            self.templates_list.insert(tk.END, template)
        
        # Use template button
        ttk.Button(
            parent,
            text="📝 Use Selected Template",
            command=self._use_template,
            bootstyle="primary" if MODERN_STYLING else None
        ).pack(padx=10, pady=(0, 10))
    
    # Event handlers
    def _insert_example(self, text):
        """Insert example text"""
        self.input_text.delete(1.0, tk.END)
        self.input_text.insert(tk.END, text)
    
    def _convert_input(self):
        """Convert barok input to AI prompt"""
        try:
            # Get input
            barok_input = self.input_text.get(1.0, tk.END).strip()
            
            if not barok_input:
                messagebox.showwarning("No Input", "Please enter some text to convert")
                return
            
            # Convert
            result = self.converter.convert_to_prompt(barok_input)
            cursor_prompt = self.converter.generate_cursor_prompt(result)
            
            # Display output
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, cursor_prompt)
            
            # Store result
            self.last_conversion = result
            
            # Update status
            self.ai_status.configure(text=f"✅ Converted: {result['intent'].title()} task")
            
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Error converting input: {e}")
    
    def _copy_prompt(self):
        """Copy converted prompt to clipboard"""
        try:
            prompt = self.output_text.get(1.0, tk.END).strip()
            if prompt:
                self.clipboard_clear()
                self.clipboard_append(prompt)
                messagebox.showinfo("Copied", "Prompt copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Error copying: {e}")
    
    def _save_to_history(self):
        """Save current conversion to history"""
        try:
            if hasattr(self, 'last_conversion'):
                from datetime import datetime
                
                # Add to history
                self.prompt_history.append(self.last_conversion)
                
                # Add to tree
                time_str = datetime.now().strftime("%H:%M:%S")
                self.history_tree.insert('', 'end', values=(
                    time_str,
                    self.last_conversion['original'][:50] + "..." if len(self.last_conversion['original']) > 50 else self.last_conversion['original'],
                    self.last_conversion['intent'].title()
                ))
                
                messagebox.showinfo("Saved", "Prompt saved to history!")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving to history: {e}")
    
    def _send_to_cursor(self):
        """Send prompt to Cursor AI"""
        try:
            prompt = self.output_text.get(1.0, tk.END).strip()
            if not prompt:
                messagebox.showwarning("No Prompt", "Please convert input first")
                return
            
            # In real implementation, this would integrate with Cursor API
            messagebox.showinfo(
                "Send to Cursor",
                "Prompt ready to send!\n\n"
                "In production, this would:\n"
                "1. Send prompt to Cursor AI\n"
                "2. Attach current context\n"
                "3. Monitor AI response\n"
                "4. Update task status"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Error sending to Cursor: {e}")
    
    def _on_history_select(self, event):
        """Handle history selection"""
        pass
    
    def _reload_from_history(self):
        """Reload selected history item"""
        try:
            selection = self.history_tree.selection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a history item")
                return
            
            # Get index
            item = self.history_tree.item(selection[0])
            values = item['values']
            
            # Find in history
            for hist in self.prompt_history:
                if hist['original'][:50] in values[1]:
                    # Reload
                    self.input_text.delete(1.0, tk.END)
                    self.input_text.insert(tk.END, hist['original'])
                    
                    cursor_prompt = self.converter.generate_cursor_prompt(hist)
                    self.output_text.delete(1.0, tk.END)
                    self.output_text.insert(tk.END, cursor_prompt)
                    
                    self.last_conversion = hist
                    break
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error reloading: {e}")
    
    def _clear_history(self):
        """Clear prompt history"""
        response = messagebox.askyesno("Clear History", "Clear all prompt history?")
        if response:
            self.prompt_history.clear()
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
    
    def _use_template(self):
        """Use selected template"""
        try:
            selection = self.templates_list.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a template")
                return
            
            template = self.templates_list.get(selection[0])
            self.input_text.delete(1.0, tk.END)
            self.input_text.insert(tk.END, template)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error using template: {e}")
    
    def refresh(self):
        """Refresh view data"""
        # Update active files from cursor state
        # Update current task
        # Update AI stats
        pass