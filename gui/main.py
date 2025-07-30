#!/usr/bin/env python3
"""
🎯 Modern GUI Control Center - Main Application Entry Point

Advanced Tkinter-based GUI system that integrates all autonomous systems
into a unified, modern control center with real-time monitoring, agent 
management, and intelligent automation.

Author: AI System Monorepo Team
Created: 2025-07-30
"""

import sys
import tkinter as tk
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    print("⚠️ ttkbootstrap not found. Using standard tkinter styling.")
    import tkinter.ttk as ttk
    MODERN_STYLING = False

from app import ModernGUIApplication
from styles.theme import ModernTheme


def main():
    """Main application entry point"""
    print("🚀 Starting Modern GUI Control Center...")
    
    try:
        # Create main application
        if MODERN_STYLING:
            # Use ttkbootstrap for modern styling
            app = ModernGUIApplication(theme="darkly")
        else:
            # Fallback to standard tkinter
            app = ModernGUIApplication()
        
        # Configure application
        app.configure_application()
        
        # Start the GUI main loop
        print("✅ GUI Control Center initialized successfully!")
        app.run()
        
    except Exception as e:
        print(f"❌ Failed to start GUI application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
