#!/usr/bin/env python3
"""
Simple test script to verify Python environment
"""

import os
import sys
import platform

def main():
    """Print basic system information and Python path"""
    print("=== System Information ===")
    print(f"Python version: {platform.python_version()}")
    print(f"Platform: {platform.platform()}")
    print(f"Working directory: {os.getcwd()}")
    print("\n=== Python Path ===")
    for path in sys.path:
        print(f"  - {path}")
    
    print("\n=== Environment Variables ===")
    for key, value in sorted(os.environ.items()):
        if key.startswith("PYTHON") or key in ["PATH", "TEST_MODE"]:
            print(f"  - {key}: {value}")
    
    print("\n=== Directory Contents ===")
    for item in sorted(os.listdir(".")):
        if os.path.isdir(item):
            print(f"  - {item}/ (dir)")
        else:
            print(f"  - {item}")
    
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main() 