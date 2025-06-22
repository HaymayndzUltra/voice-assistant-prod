#!/usr/bin/env python3
"""
Test script to check if we can import the necessary modules
"""

import os
import sys
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

# Test imports
print("\nTesting imports...")

try:
    print("Trying to import utils.config_parser...")
    import utils.config_parser
    print("Successfully imported utils.config_parser")
except ImportError as e:
    print(f"Failed to import utils.config_parser: {e}")

try:
    print("\nTrying to import src.core.base_agent...")
    import src.core.base_agent
    print("Successfully imported src.core.base_agent")
except ImportError as e:
    print(f"Failed to import src.core.base_agent: {e}")

try:
    print("\nTrying to import config.system_config...")
    import config.system_config
    print("Successfully imported config.system_config")
except ImportError as e:
    print(f"Failed to import config.system_config: {e}")

# List Python paths
print("\nPython sys.path:")
for p in sys.path:
    print(f"  {p}")

print("\nTest complete") 