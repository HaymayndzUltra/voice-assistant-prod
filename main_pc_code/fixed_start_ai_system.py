#!/usr/bin/env python3
"""
AI System Startup Script

This script serves as the main entry point for launching the entire AI system.
It performs critical prerequisite checks before handing off to the main system launcher.

1. Checks for a running PostgreSQL database.
2. Provides clear error messages if dependencies are not met.
3. Executes the system_launcher.py to start all agents.
"""

import socket
import subprocess
import sys
from pathlib import Path
from common.env_helpers import get_env

DB_HOST = get_env("BIND_ADDRESS", "0.0.0.0")
DB_PORT = 5432

def check_database_connection(host: str, port: int) -> bool:
    """Check if a TCP connection to the database can be established."""
    print(f"--- Checking for PostgreSQL database on {host}:{port} ---")
    try:
        with socket.create_connection((host, port), timeout=3):
            print("Database connection successful.")
            return True
    except (OSError, ConnectionError):
        print("[CRITICAL ERROR] Database connection failed.", file=sys.stderr)
        print(f"Please ensure a PostgreSQL server is running and accessible on {host}:{port}.", file=sys.stderr)
        return False

def main():
    """
    Main entry point. Checks for the database and then launches the AI system.
    """
    if not check_database_connection(DB_HOST, DB_PORT):
        sys.exit(1)

    print("\n--- Starting AI System ---")
    
    base_dir = Path(__file__).resolve().parent
    launcher_script_path = base_dir / "system_launcher.py"

    if not launcher_script_path.exists():
        print(f"[CRITICAL ERROR] System launcher not found at: {launcher_script_path}", file=sys.stderr)
        sys.exit(1)

    try:
        # We execute from the script's directory to ensure relative paths are correct.
        result = subprocess.run(
            [sys.executable, str(launcher_script_path)],
            cwd=base_dir,
            check=False
        )
        
        if result.returncode == 0:
            print("\n--- AI System Shutdown Complete ---")
        else:
            print(f"\n--- AI System exited with error code: {result.returncode} ---", file=sys.stderr)
            
        sys.exit(result.returncode)

    except KeyboardInterrupt:
        print("\n--- AI System launch interrupted by user. ---")
        sys.exit(1)
    except Exception as e:
        print(f"[CRITICAL ERROR] An unexpected error occurred while launching the system: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()