#!/usr/bin/env python3
"""
🎯 GUI Integration Demo
Shows how natural language commands become intelligent TODOs
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from gui.services.intelligent_todo_service import IntelligentTodoService
    from memory_system.ai_cursor_intelligence import AIProductionIntelligence
except ImportError as e:
    print(f"Import error: {e}")
    # Create fallback classes for demo
    class IntelligentTodoService:
        def process_gui_command(self, cmd):
            return {
                'success': True,
                'message': f"Mock: Would create TODO for '{cmd}'",
                'ai_response': {
                    'analysis': {'confidence': '95%', 'topic': 'production_deployment'},
                    'immediate_actions': [
                        f"Step 1: Analyze {cmd}",
                        f"Step 2: Execute {cmd}",
                        f"Step 3: Verify {cmd}"
                    ]
                }
            }
        
        def get_command_suggestions(self, partial):
            return ['deploy production', 'fix docker', 'setup monitoring']

class GUIIntegrationDemo:
    """Demo GUI showing AI command integration"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎯 AI-Powered GUI Command Demo")
        self.root.geometry("800x600")
        self.root.configure(bg='#2b2b2b')
        
        # Initialize services
        self.todo_service = IntelligentTodoService()
        
        self._create_widgets()
        self._setup_bindings()
    
    def _create_widgets(self):
        """Create demo interface"""
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = tk.Label(
            main_frame,
            text="🤖 AI-Powered Command Interface Demo",
            font=("Arial", 16, "bold"),
            bg='#2b2b2b',
            fg='white'
        )
        title.pack(pady=(0, 20))
        
        # Command input section
        self._create_command_section(main_frame)
        
        # Results display section
        self._create_results_section(main_frame)
        
        # Example commands section
        self._create_examples_section(main_frame)
    
    def _create_command_section(self, parent):
        """Create command input section"""
        cmd_frame = ttk.LabelFrame(parent, text="💬 Natural Language Command Input")
        cmd_frame.pack(fill="x", pady=(0, 20))
        
        # Command entry
        entry_frame = ttk.Frame(cmd_frame)
        entry_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(entry_frame, text="Command:", font=("Arial", 10, "bold")).pack(side="left")
        
        self.command_entry = ttk.Entry(entry_frame, font=("Arial", 11))
        self.command_entry.pack(side="left", fill="x", expand=True, padx=(10, 10))
        
        # Process button
        self.process_btn = ttk.Button(
            entry_frame,
            text="🚀 Process Command",
            command=self._process_command
        )
        self.process_btn.pack(side="right")
        
        # Suggestions display
        self.suggestions_var = tk.StringVar()
        suggestions_label = tk.Label(
            cmd_frame,
            textvariable=self.suggestions_var,
            font=("Arial", 9),
            fg="blue"
        )
        suggestions_label.pack(padx=10, pady=(0, 10))
    
    def _create_results_section(self, parent):
        """Create results display section"""
        results_frame = ttk.LabelFrame(parent, text="🎯 AI Processing Results")
        results_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Results text area
        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            height=15,
            font=("Courier", 9),
            bg='#1e1e1e',
            fg='#ffffff',
            insertbackground='white'
        )
        self.results_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Clear button
        clear_btn = ttk.Button(
            results_frame,
            text="🗑️ Clear Results",
            command=self._clear_results
        )
        clear_btn.pack(pady=(0, 10))
    
    def _create_examples_section(self, parent):
        """Create example commands section"""
        examples_frame = ttk.LabelFrame(parent, text="💡 Example Commands")
        examples_frame.pack(fill="x")
        
        examples = [
            "deploy production",
            "fix docker issues", 
            "setup monitoring",
            "check system security",
            "optimize performance"
        ]
        
        buttons_frame = ttk.Frame(examples_frame)
        buttons_frame.pack(padx=10, pady=10)
        
        for example in examples:
            btn = ttk.Button(
                buttons_frame,
                text=f"📝 {example}",
                command=lambda cmd=example: self._load_example(cmd)
            )
            btn.pack(side="left", padx=5)
    
    def _setup_bindings(self):
        """Setup event bindings"""
        # Enter key to process command
        self.command_entry.bind("<Return>", lambda e: self._process_command())
        
        # Real-time suggestions as user types
        self.command_entry.bind("<KeyRelease>", self._update_suggestions)
    
    def _process_command(self):
        """Process the entered command"""
        command = self.command_entry.get().strip()
        
        if not command:
            self._add_result("⚠️ Please enter a command first!")
            return
        
        self._add_result(f"\n🤖 PROCESSING COMMAND: '{command}'")
        self._add_result("=" * 50)
        
        try:
            # Process command through AI intelligence
            result = self.todo_service.process_gui_command(command)
            
            # Display AI analysis
            if 'ai_response' in result:
                ai_response = result['ai_response']
                self._add_result(f"🧠 AI ANALYSIS:")
                self._add_result(f"   Topic: {ai_response['analysis']['topic']}")
                self._add_result(f"   Confidence: {ai_response['analysis']['confidence']}")
                
                # Display suggested actions
                if 'immediate_actions' in ai_response:
                    self._add_result(f"\n📋 SUGGESTED ACTIONS:")
                    for i, action in enumerate(ai_response['immediate_actions'], 1):
                        self._add_result(f"   {i}. {action}")
            
            # Display TODO creation result
            self._add_result(f"\n✅ RESULT: {result['message']}")
            
            if result.get('task_id'):
                self._add_result(f"📝 Task ID: {result['task_id']}")
                self._add_result(f"📊 TODO Count: {result.get('todo_count', 0)}")
            
        except Exception as e:
            self._add_result(f"❌ ERROR: {str(e)}")
        
        self._add_result("\n" + "="*50 + "\n")
        
        # Clear command entry
        self.command_entry.delete(0, tk.END)
    
    def _update_suggestions(self, event):
        """Update command suggestions as user types"""
        partial = self.command_entry.get()
        
        if len(partial) > 2:  # Start suggesting after 2 characters
            try:
                suggestions = self.todo_service.get_command_suggestions(partial)
                if suggestions:
                    suggestion_text = "💡 Suggestions: " + " | ".join(suggestions[:3])
                    self.suggestions_var.set(suggestion_text)
                else:
                    self.suggestions_var.set("")
            except Exception:
                self.suggestions_var.set("")
        else:
            self.suggestions_var.set("")
    
    def _load_example(self, command):
        """Load example command into entry"""
        self.command_entry.delete(0, tk.END)
        self.command_entry.insert(0, command)
        self.command_entry.focus()
    
    def _add_result(self, text):
        """Add text to results display"""
        self.results_text.insert(tk.END, text + "\n")
        self.results_text.see(tk.END)
    
    def _clear_results(self):
        """Clear results display"""
        self.results_text.delete(1.0, tk.END)
    
    def run(self):
        """Start the demo"""
        # Add welcome message
        welcome = """
🎯 AI-Powered GUI Command Demo

This demo shows how natural language commands in your GUI
automatically become intelligent, structured TODO tasks.

TRY IT:
1. Type a command like "deploy production"
2. See AI analysis and suggested actions
3. Watch as TODOs are automatically created
4. Use example buttons for quick testing

FEATURES DEMONSTRATED:
✅ Natural language processing
✅ AI-powered command analysis  
✅ Automatic TODO generation
✅ Command suggestions/autocomplete
✅ Real-time feedback

Type a command above to get started! 🚀
        """
        
        self._add_result(welcome)
        
        # Focus on command entry
        self.command_entry.focus()
        
        # Start GUI
        self.root.mainloop()

if __name__ == "__main__":
    print("🚀 Starting GUI Integration Demo...")
    demo = GUIIntegrationDemo()
    demo.run()