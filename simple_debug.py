#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from typing import Union
"""
Simple Agent Debug Script
Runs a single agent with output capture to diagnose issues
"""

import os
import sys
import subprocess
import time

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Setup environment
os.environ["MACHINE_TYPE"] = "MAINPC"
os.environ["PYTHONPATH"] = f"{os.environ.get('PYTHONPATH', '')}:{SCRIPT_DIR}"
os.environ["MAIN_PC_IP"] = "localhost"
os.environ["PC2_IP"] = "localhost"
os.environ["BIND_ADDRESS"] = "0.0.0.0"
os.environ["SECURE_ZMQ"] = "0"
os.environ["USE_DUMMY_AUDIO"] = "true"
os.environ["ZMQ_REQUEST_TIMEOUT"] = "10000"
os.environ["DEBUG"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"

# Create necessary directories
for directory in ["logs", "data", "models", "cache", "certificates"]:
    os.makedirs(directory, exist_ok=True)

def find_agent_file(file_path):
    """Find the full path to an agent file"""
    if os.path.isabs(file_path):
        return file_path if os.path.exists(file_path) else None

    # Try multiple possible locations
    search_dirs = [
        os.path.join(SCRIPT_DIR, "main_pc_code", "agents"),
        os.path.join(SCRIPT_DIR, "main_pc_code", "FORMAINPC"),
        os.path.join(SCRIPT_DIR, "main_pc_code", "src", "core"),
        os.path.join(SCRIPT_DIR, "main_pc_code", "src", "memory"),
        os.path.join(SCRIPT_DIR, "main_pc_code", "src", "audio"),
        os.path.join(SCRIPT_DIR, "main_pc_code"),
        SCRIPT_DIR
    ]

    for directory in search_dirs:
        candidate_path = os.path.join(directory, file_path)
        if os.path.exists(candidate_path):
            return candidate_path

    return None

def debug_agent(file_path):
    """Debug a single agent by running it directly"""
    full_path = find_agent_file(file_path)
    if not full_path:
        print(f"Error: Could not find {file_path}")
        return

    print(f"Debugging agent: {full_path}")
    print("-" * 80)

    try:
        # Run the agent with output capture
        process = subprocess.Popen(
            [sys.executable, full_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Wait for the process to complete or timeout
        timeout = 30  # seconds
        start_time = time.time()

        while time.time() - start_time < timeout and process.poll() is None:
            # Check for output
            stdout_line = process.stdout.readline()
            if stdout_line:
                print(f"[STDOUT] {stdout_line.strip()}")

            stderr_line = process.stderr.readline()
            if stderr_line:
                print(f"[STDERR] {stderr_line.strip()}")

            time.sleep(0.1)

        # Check if the process terminated
        if process.poll() is not None:
            exit_code = process.returncode
            print(f"Process terminated with exit code {exit_code}")
        else:
            print(f"Process still running after {timeout} seconds, terminating...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                print("Process killed forcefully")

        # Get any remaining output
        stdout, stderr = process.communicate()
        if stdout:
            print(f"[STDOUT] {stdout.strip()}")
        if stderr:
            print(f"[STDERR] {stderr.strip()}")

    except Exception as e:
        print(f"Error debugging agent: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python simple_debug.py <agent_file_path>")
        print("Example: python simple_debug.py streaming_audio_capture.py")
        sys.exit(1)

    debug_agent(sys.argv[1])