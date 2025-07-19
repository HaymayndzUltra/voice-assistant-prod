#!/usr/bin/env python3
"""
Container Startup Wrapper - Smart Import Fix
Fixes import path issues at runtime without rebuilding containers
"""

import os
import sys

# Fix import paths for container environment  
app_root = "/app"
if app_root not in sys.path:
    sys.path.insert(0, app_root)

# Now import the actual startup script
sys.path.insert(0, "/app/main_pc_code/scripts")

if __name__ == "__main__":
    # Import and run the actual startup script with fixed paths
    from start_system import main
    main() 