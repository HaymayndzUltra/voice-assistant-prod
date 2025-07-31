#!/usr/bin/env python3
"""
🤖 Enhanced Modern GUI Control Center - AI-Powered Main Entry Point

This is the enhanced version of main.py that includes AI-powered TODO generation.
Run this instead of main.py to get the AI-enhanced GUI experience.

FEATURES:
✅ Natural language command processing  
✅ AI-powered TODO generation
✅ Quick action buttons
✅ Intelligent system analysis
✅ All your existing GUI features

HOW TO USE:
1. Run: python3 main_enhanced.py
2. Type: "deploy production" in command bar
3. Watch: AI creates structured TODO with 7+ steps automatically
4. Enjoy: Your natural language → automatic TODO workflow!
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

# Import enhanced application
from app_enhanced import EnhancedModernGUIApplication
from styles.theme import ModernTheme
from services.dependency_check import check_dependencies
from gui.utils.toast import show_warning


def main():
    """Enhanced main application entry point with AI intelligence"""
    print("🤖 Starting AI-Enhanced GUI Control Center...")
    print("🧠 Features: Natural Language → Automatic TODO Generation")
    
    try:
        # Create enhanced application with AI intelligence
        if MODERN_STYLING:
            # Use ttkbootstrap for modern styling
            app = EnhancedModernGUIApplication(theme="darkly")
        else:
            # Fallback to standard tkinter
            app = EnhancedModernGUIApplication()
        
        # Check dependencies and show warnings if needed
        try:
            check_dependencies(lambda msg: show_warning(app.root, msg))
        except Exception as e:
            print(f"Warning: Dependency check failed: {e}")
        
        # Configure application
        app.configure_application()
        
        # Display startup information
        print("✅ Enhanced GUI Control Center initialized successfully!")
        print("\n🎯 AI FEATURES AVAILABLE:")
        print("   📝 Type 'deploy production' in command bar")
        print("   🚀 Click quick action buttons") 
        print("   🤖 Get AI-generated TODO steps automatically")
        print("   📊 See confidence scores and topic analysis")
        print("\n🎮 TRY THESE COMMANDS:")
        print("   • deploy production")
        print("   • fix docker issues")
        print("   • setup monitoring")
        print("   • check system security")
        print("   • optimize performance")
        print("\n🚀 Starting GUI...")
        
        # Start the GUI main loop
        app.run()
        
    except Exception as e:
        print(f"❌ Failed to start enhanced GUI application: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to basic GUI if available
        print("\n🔄 Attempting fallback to basic GUI...")
        try:
            from app import ModernGUIApplication
            basic_app = ModernGUIApplication()
            basic_app.configure_application()
            print("✅ Basic GUI started (without AI features)")
            basic_app.run()
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
            sys.exit(1)


if __name__ == "__main__":
    main()