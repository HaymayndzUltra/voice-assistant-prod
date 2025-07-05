#!/usr/bin/env python3
"""
Robust Agent Process Cleanup Utility

This script finds and terminates all agent-related processes to ensure a clean environment
before starting agents. It handles various edge cases like zombie processes and lingering sockets.
"""

import os
import sys
import time
import signal
import socket
import logging
import argparse
import subprocess
from typing import List, Dict, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('cleanup')

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

def find_agent_processes() -> List[Dict]:
    """
    Find all Python processes that might be related to agents.
    
    Returns:
        List of dictionaries containing process information
    """
    processes = []
    
    try:
        # Use ps command to find all Python processes
        cmd = ["ps", "-eo", "pid,ppid,user,command"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the output
        lines = result.stdout.strip().split('\n')
        for line in lines[1:]:  # Skip header
            parts = line.strip().split(None, 3)
            if len(parts) < 4:
                continue
                
            pid, ppid, user, command = parts
            
            # Check if this is a Python process related to agents
            if ('python' in command and 
                ('agent' in command.lower() or 
                 'model_manager' in command.lower() or
                 'coordinator' in command.lower() or
                 'system_digital_twin' in command.lower())):
                
                processes.append({
                    'pid': int(pid),
                    'ppid': int(ppid),
                    'user': user,
                    'command': command
                })
    except Exception as e:
        logger.error(f"Error finding agent processes: {e}")
    
    return processes

def check_port_in_use(port: int) -> Tuple[bool, int]:
    """
    Check if a port is in use and get the PID using it.
    
    Args:
        port: Port number to check
        
    Returns:
        Tuple of (is_in_use, pid)
    """
    try:
        # Try to bind to the port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return False, 0
    except socket.error:
        # Port is in use, try to find the PID
        try:
            cmd = ["lsof", "-i", f":{port}", "-t"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout.strip():
                return True, int(result.stdout.strip())
            return True, 0
        except Exception:
            return True, 0

def find_blocked_ports() -> Dict[int, int]:
    """
    Find ports that are blocked by processes.
    
    Returns:
        Dictionary mapping port numbers to PIDs
    """
    blocked_ports = {}
    
    # Check common agent ports
    common_ports = [
        5570,  # ModelManagerAgent
        7120,  # SystemDigitalTwin
        26002, # CoordinatorAgent
        5612,  # ChainOfThoughtAgent
        7000,  # GoTToTAgent
        # Add health check ports
        5571, 7121, 26003, 5613, 7001
    ]
    
    for port in common_ports:
        in_use, pid = check_port_in_use(port)
        if in_use:
            blocked_ports[port] = pid
            logger.info(f"Port {port} is in use by PID {pid}")
    
    return blocked_ports

def kill_process(pid: int, force: bool = False) -> bool:
    """
    Kill a process by PID.
    
    Args:
        pid: Process ID to kill
        force: Whether to use SIGKILL instead of SIGTERM
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if force:
            os.kill(pid, signal.SIGKILL)
            logger.info(f"Sent SIGKILL to process {pid}")
        else:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to process {pid}")
        return True
    except ProcessLookupError:
        logger.warning(f"Process {pid} not found")
        return False
    except PermissionError:
        logger.error(f"Permission denied when trying to kill process {pid}")
        return False
    except Exception as e:
        logger.error(f"Error killing process {pid}: {e}")
        return False

def cleanup_zmq_sockets() -> None:
    """
    Clean up any lingering ZMQ socket files.
    """
    try:
        # Check for ZMQ socket files in /tmp
        cmd = ["find", "/tmp", "-name", "*.zmq", "-o", "-name", "*.ipc"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        for file_path in result.stdout.strip().split('\n'):
            if file_path:
                try:
                    os.remove(file_path)
                    logger.info(f"Removed socket file: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing socket file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning up ZMQ sockets: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Clean up agent processes and ports")
    parser.add_argument("--force", action="store_true", help="Use SIGKILL instead of SIGTERM")
    parser.add_argument("--wait", type=int, default=5, help="Wait time in seconds after SIGTERM before using SIGKILL")
    args = parser.parse_args()
    
    logger.info("Starting agent cleanup process")
    
    # First pass: Find processes and send SIGTERM
    processes = find_agent_processes()
    if not processes:
        logger.info("No agent processes found")
    else:
        logger.info(f"Found {len(processes)} agent processes")
        
        # Send SIGTERM to all processes
        for process in processes:
            pid = process['pid']
            command = process['command']
            logger.info(f"Terminating process {pid}: {command}")
            kill_process(pid, force=args.force)
    
    # Check for blocked ports
    blocked_ports = find_blocked_ports()
    if blocked_ports:
        logger.info(f"Found {len(blocked_ports)} blocked ports")
        
        # Try to kill processes blocking ports
        for port, pid in blocked_ports.items():
            if pid > 0:
                logger.info(f"Terminating process {pid} blocking port {port}")
                kill_process(pid, force=args.force)
    
    # Wait for processes to terminate
    if not args.force and processes:
        logger.info(f"Waiting {args.wait} seconds for processes to terminate")
        time.sleep(args.wait)
        
        # Second pass: Check if processes are still running and use SIGKILL
        remaining = find_agent_processes()
        if remaining:
            logger.info(f"Found {len(remaining)} remaining processes, using SIGKILL")
            for process in remaining:
                pid = process['pid']
                kill_process(pid, force=True)
    
    # Clean up ZMQ sockets
    cleanup_zmq_sockets()
    
    # Final check
    final_processes = find_agent_processes()
    final_ports = find_blocked_ports()
    
    if not final_processes and not final_ports:
        logger.info("All agent processes and ports have been cleaned up successfully")
        return 0
    else:
        logger.warning(f"Cleanup incomplete: {len(final_processes)} processes and {len(final_ports)} ports still active")
        return 1

if __name__ == "__main__":
    sys.exit(main())
