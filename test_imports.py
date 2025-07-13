#!/usr/bin/env python3
"""
Test script to diagnose import issues in the containerized environment.
"""

import os
import sys
import importlib

def check_module(module_name):
    """Try to import a module and report success or failure."""
    try:
        module = importlib.import_module(module_name)
        print(f"✅ Successfully imported {module_name}")
        return module
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
        return None

def check_file_exists(path):
    """Check if a file exists and report."""
    if os.path.exists(path):
        print(f"✅ File exists: {path}")
        return True
    else:
        print(f"❌ File does not exist: {path}")
        return False

def create_minimal_path_manager():
    """Create a minimal path_manager.py file."""
    os.makedirs("utils", exist_ok=True)
    
    # Create __init__.py if it doesn't exist
    if not os.path.exists("utils/__init__.py"):
        with open("utils/__init__.py", "w") as f:
            f.write("# Auto-generated __init__.py\n")
    
    # Create a minimal path_manager.py
    with open("utils/path_manager.py", "w") as f:
        f.write("""
# Minimal path_manager.py for debugging
import os

class PathManager:
    @staticmethod
    def get_project_root():
        return os.getcwd()
        
    @staticmethod
    def get_file_path(file_path):
        return os.path.join(os.getcwd(), file_path)

def get_project_root():
    return os.getcwd()
""")
    print("Created minimal path_manager.py")

def main():
    """Run diagnostics."""
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Environment variables: {dict(os.environ)}")
    
    print("\nChecking for critical files:")
    check_file_exists("utils/path_manager.py")
    check_file_exists("utils/__init__.py")
    check_file_exists("common/core/base_agent.py")
    check_file_exists("main_pc_code/utils/network_utils.py")
    
    # Create minimal path_manager if it doesn't exist
    if not os.path.exists("utils/path_manager.py"):
        create_minimal_path_manager()
    
    print("\nTrying to import modules:")
    check_module("utils")
    check_module("utils.path_manager")
    check_module("common.core.base_agent")
    check_module("main_pc_code.utils.network_utils")
    
    # Try to fix the path
    print("\nAdding current directory to sys.path and trying again:")
    sys.path.insert(0, os.getcwd())
    check_module("utils")
    check_module("utils.path_manager")

if __name__ == "__main__":
    main() 