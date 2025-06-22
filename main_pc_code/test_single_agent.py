#!/usr/bin/env python3
"""
Test script to run a single agent with the correct PYTHONPATH
"""

import os
import sys
import subprocess
from pathlib import Path

# Set up paths
CURRENT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = CURRENT_DIR.parent

# Set PYTHONPATH
os.environ["PYTHONPATH"] = f"{PROJECT_ROOT}:{CURRENT_DIR}:{os.environ.get('PYTHONPATH', '')}"
print(f"PYTHONPATH set to: {os.environ['PYTHONPATH']}")

# Create symlinks for backward compatibility
try:
    os.symlink(CURRENT_DIR / "utils", PROJECT_ROOT / "utils", target_is_directory=True)
    print("Created symlink for utils")
except FileExistsError:
    print("utils symlink already exists")
except Exception as e:
    print(f"Error creating utils symlink: {e}")

try:
    os.symlink(CURRENT_DIR / "src", PROJECT_ROOT / "src", target_is_directory=True)
    print("Created symlink for src")
except FileExistsError:
    print("src symlink already exists")
except Exception as e:
    print(f"Error creating src symlink: {e}")

try:
    os.symlink(CURRENT_DIR / "config", PROJECT_ROOT / "config", target_is_directory=True)
    print("Created symlink for config")
except FileExistsError:
    print("config symlink already exists")
except Exception as e:
    print(f"Error creating config symlink: {e}")

# Create logs directory
os.makedirs("logs", exist_ok=True)
print("Created logs directory")

# Try to kill existing processes on port 8570
try:
    print("Attempting to kill processes using port 8570...")
    os.system("lsof -t -i:8570 | xargs -r kill -9")
    print("Killed processes using port 8570")
except Exception as e:
    print(f"Error killing processes: {e}")

# Use a different port
alternative_port = 9570
print(f"Using alternative port {alternative_port}")

# Run a single agent - the task router which is the core service
task_router_path = CURRENT_DIR / "src" / "core" / "task_router.py"
if task_router_path.exists():
    print(f"Found task_router.py at {task_router_path}")
    try:
        cmd = [sys.executable, str(task_router_path), "--port", str(alternative_port)]
        print(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            env=dict(os.environ),
            cwd=str(PROJECT_ROOT)
        )
        print(f"Started task router with PID: {process.pid}")
        # Wait for the process
        print("Press Ctrl+C to stop the task router")
        process.wait()
    except KeyboardInterrupt:
        print("Stopping task router...")
        process.terminate()
    except Exception as e:
        print(f"Error running task router: {e}")
else:
    print(f"Task router not found at {task_router_path}")
    # Try to find it
    for path in Path(CURRENT_DIR).rglob("task_router.py"):
        print(f"Found task_router.py at: {path}")

print("Test complete") 