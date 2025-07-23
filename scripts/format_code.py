#!/usr/bin/env python3
"""
Code formatting script for the AI System Monorepo.
This script formats Python code using Black and isort.
"""

import subprocess
import sys
from pathlib import Path

def run_command(command: list[str]) -> bool:
    """Run a command and return success status."""
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {' '.join(command)} - Success")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {' '.join(command)} - Failed")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main formatting function."""
    print("🔧 Starting code formatting for AI System Monorepo...")
    
    # Get repository root
    repo_root = Path(__file__).parent.parent
    
    # Directories to format
    target_dirs = [
        "main_pc_code",
        "pc2_code", 
        "common",
        "utils",
        "scripts"
    ]
    
    # Filter to only existing directories
    existing_dirs = [d for d in target_dirs if (repo_root / d).exists()]
    
    if not existing_dirs:
        print("❌ No target directories found to format")
        return 1
    
    success = True
    
    # Format with Black
    print("\n📝 Formatting with Black...")
    for directory in existing_dirs:
        if not run_command(["black", str(repo_root / directory)]):
            success = False
    
    # Sort imports with isort
    print("\n📦 Sorting imports with isort...")
    for directory in existing_dirs:
        if not run_command(["isort", str(repo_root / directory)]):
            success = False
    
    # Run flake8 for linting
    print("\n🔍 Checking with flake8...")
    for directory in existing_dirs:
        if not run_command(["flake8", str(repo_root / directory)]):
            success = False
    
    if success:
        print("\n✅ All formatting completed successfully!")
        return 0
    else:
        print("\n❌ Some formatting operations failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 