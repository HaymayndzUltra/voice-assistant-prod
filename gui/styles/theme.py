"""
🎯 Modern GUI Control Center - Theme and Styling System

This module provides comprehensive theming and styling for the GUI application,
supporting both ttkbootstrap modern themes and fallback standard tkinter styling.
"""

import tkinter as tk
from tkinter import font
from pathlib import Path

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    MODERN_STYLING = True
except ImportError:
    import tkinter.ttk as ttk
    MODERN_STYLING = False


class ModernTheme:
    """Modern theme configuration and styling"""
    
    # Color palette for modern dark theme
    COLORS = {
        "primary": "#3b82f6",      # Blue
        "secondary": "#6b7280",    # Gray
        "success": "#10b981",      # Green
        "warning": "#f59e0b",      # Amber  
        "danger": "#ef4444",       # Red
        "info": "#06b6d4",        # Cyan
        "light": "#f8fafc",       # Light gray
        "dark": "#1e293b",        # Dark blue-gray
        "background": "#0f172a",   # Very dark blue
        "surface": "#1e293b",     # Dark surface
        "on_surface": "#f1f5f9",  # Light text on dark
        "border": "#334155",      # Border color
        "accent": "#8b5cf6",      # Purple
    }
    
    # Typography
    FONTS = {
        "default": ("Inter", 10),
        "heading": ("Inter", 14, "bold"),
        "title": ("Inter", 16, "bold"),
        "display": ("Inter", 20, "bold"),
        "mono": ("Fira Code", 10),
        "small": ("Inter", 8),
    }
    
    @classmethod
    def apply_styles(cls, root, modern_styling=True):
        """Apply comprehensive styling to the application"""
        
        if modern_styling:
            cls._apply_modern_styles(root)
        else:
            cls._apply_fallback_styles(root)
    
    @classmethod
    def _apply_modern_styles(cls, root):
        """Apply modern ttkbootstrap styling"""
        try:
            # Configure modern theme
            style = ttk.Style()
            
            # Custom button styles
            style.configure(
                "Modern.TButton",
                font=cls.FONTS["default"],
                padding=(10, 8),
                borderwidth=1,
                relief="flat",
                focuscolor="none"
            )
            
            # Primary button style
            style.configure(
                "Primary.TButton", 
                font=cls.FONTS["default"],
                padding=(12, 10),
                borderwidth=0,
                relief="flat"
            )
            
            # Sidebar button style
            style.configure(
                "Sidebar.TButton",
                font=cls.FONTS["default"],
                padding=(8, 6),
                borderwidth=0,
                relief="flat",
                anchor="w"
            )
            
            # Frame styles
            style.configure(
                "Card.TFrame",
                relief="solid",
                borderwidth=1,
                padding=10
            )
            
            style.configure(
                "Sidebar.TFrame",
                relief="solid",
                borderwidth=1
            )
            
            # Label styles
            style.configure(
                "Heading.TLabel",
                font=cls.FONTS["heading"]
            )
            
            style.configure(
                "Title.TLabel", 
                font=cls.FONTS["title"]
            )
            
            style.configure(
                "Display.TLabel",
                font=cls.FONTS["display"]
            )
            
            # Entry styles
            style.configure(
                "Modern.TEntry",
                font=cls.FONTS["default"],
                padding=8,
                borderwidth=1,
                relief="solid"
            )
            
            # Treeview styles
            style.configure(
                "Modern.Treeview",
                font=cls.FONTS["default"],
                rowheight=25,
                borderwidth=1,
                relief="solid"
            )
            
            style.configure(
                "Modern.Treeview.Heading",
                font=cls.FONTS["heading"],
                padding=(8, 4)
            )
            
            # Notebook styles
            style.configure(
                "Modern.TNotebook",
                borderwidth=0,
                tabmargins=0
            )
            
            style.configure(
                "Modern.TNotebook.Tab",
                font=cls.FONTS["default"],
                padding=(12, 8),
                borderwidth=0
            )
            
            print("✅ Modern ttkbootstrap styling applied")
            
        except Exception as e:
            print(f"⚠️ Error applying modern styles: {e}")
            cls._apply_fallback_styles(root)
    
    @classmethod
    def _apply_fallback_styles(cls, root):
        """Apply fallback styling for standard tkinter"""
        try:
            style = ttk.Style()
            
            # Use a modern-looking theme
            available_themes = style.theme_names()
            if "clam" in available_themes:
                style.theme_use("clam")
            elif "alt" in available_themes:
                style.theme_use("alt")
            
            # Configure colors
            style.configure(
                "TFrame",
                background="#2d3748",
                borderwidth=1,
                relief="solid"
            )
            
            style.configure(
                "TLabel",
                background="#2d3748", 
                foreground="#e2e8f0",
                font=cls.FONTS["default"]
            )
            
            style.configure(
                "TButton",
                background="#4a5568",
                foreground="#e2e8f0",
                font=cls.FONTS["default"],
                padding=(10, 6),
                borderwidth=1,
                relief="raised"
            )
            
            style.map(
                "TButton",
                background=[
                    ("active", "#5a6578"),
                    ("pressed", "#3a4558")
                ],
                foreground=[("active", "#ffffff")]
            )
            
            # Primary button style
            style.configure(
                "Primary.TButton",
                background="#3182ce",
                foreground="#ffffff",
                font=cls.FONTS["default"],
                padding=(12, 8)
            )
            
            style.map(
                "Primary.TButton",
                background=[
                    ("active", "#2c5282"),
                    ("pressed", "#2a4f7c")
                ]
            )
            
            # Heading styles
            style.configure(
                "Heading.TLabel",
                font=cls.FONTS["heading"],
                background="#2d3748",
                foreground="#f7fafc"
            )
            
            style.configure(
                "Title.TLabel",
                font=cls.FONTS["title"], 
                background="#2d3748",
                foreground="#f7fafc"
            )
            
            # Entry styles
            style.configure(
                "TEntry",
                font=cls.FONTS["default"],
                fieldbackground="#4a5568",
                foreground="#e2e8f0",
                borderwidth=1,
                relief="solid"
            )
            
            # Treeview styles
            style.configure(
                "Treeview",
                font=cls.FONTS["default"],
                background="#4a5568",
                foreground="#e2e8f0",
                fieldbackground="#4a5568",
                borderwidth=1,
                relief="solid",
                rowheight=25
            )
            
            style.configure(
                "Treeview.Heading",
                font=cls.FONTS["heading"],
                background="#2d3748",
                foreground="#f7fafc",
                borderwidth=1,
                relief="raised"
            )
            
            # Notebook styles
            style.configure(
                "TNotebook",
                background="#2d3748",
                borderwidth=0
            )
            
            style.configure(
                "TNotebook.Tab",
                background="#4a5568",
                foreground="#e2e8f0", 
                font=cls.FONTS["default"],
                padding=(12, 8),
                borderwidth=1,
                relief="raised"
            )
            
            style.map(
                "TNotebook.Tab",
                background=[
                    ("selected", "#3182ce"),
                    ("active", "#5a6578")
                ],
                foreground=[("selected", "#ffffff")]
            )
            
            # Configure root window
            root.configure(bg="#1a202c")
            
            print("✅ Fallback tkinter styling applied")
            
        except Exception as e:
            print(f"⚠️ Error applying fallback styles: {e}")
    
    @classmethod
    def get_color(cls, color_name):
        """Get color value by name"""
        return cls.COLORS.get(color_name, "#000000")
    
    @classmethod
    def get_font(cls, font_name):
        """Get font configuration by name"""
        return cls.FONTS.get(font_name, cls.FONTS["default"])
    
    @classmethod
    def create_custom_style(cls, style_name, **kwargs):
        """Create a custom style configuration"""
        try:
            style = ttk.Style()
            style.configure(style_name, **kwargs)
            return True
        except Exception as e:
            print(f"Error creating custom style {style_name}: {e}")
            return False
