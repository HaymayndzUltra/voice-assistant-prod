#!/usr/bin/env python3
"""
Fix Task Router Port Conflict
----------------------------
Finds and kills any processes using port 7000 (TaskRouter port)
"""
import os
import subprocess
import sys

def find_process_using_port(port):
    """Find the process ID using a specific port."""
    try:
        # For Linux/MacOS
        if os.name != 'nt':
            cmd = f"lsof -i :{port} -t"
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            if result:
                return [int(pid) for pid in result.split('\n')]
        # For Windows
        else:
            cmd = f"netstat -ano | findstr :{port}"
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            if result:
                lines = result.split('\n')
                pids = []
                for line in lines:
                    if f":{port}" in line:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pids.append(int(parts[4]))
                return pids
    except subprocess.CalledProcessError:
        pass
    return []

def kill_process(pid):
    """Kill a process by its PID."""
    try:
        # For Linux/MacOS
        if os.name != 'nt':
            subprocess.run(['kill', '-9', str(pid)])
            return True
        # For Windows
        else:
            subprocess.run(['taskkill', '/F', '/PID', str(pid)])
            return True
    except subprocess.CalledProcessError:
        return False

def main():
    port = 7000
    print(f"Looking for processes using port {port}...")
    
    pids = find_process_using_port(port)
    
    if not pids:
        print(f"No processes found using port {port}")
        return
    
    print(f"Found {len(pids)} process(es) using port {port}: {pids}")
    
    for pid in pids:
        print(f"Killing process {pid}...")
        if kill_process(pid):
            print(f"Successfully killed process {pid}")
        else:
            print(f"Failed to kill process {pid}")
    
    # Verify
    remaining_pids = find_process_using_port(port)
    if remaining_pids:
        print(f"Warning: Some processes still using port {port}: {remaining_pids}")
    else:
        print(f"Port {port} is now free")

if __name__ == "__main__":
    main() 