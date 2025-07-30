#!/usr/bin/env python
"""
Cascade Process Monitor
- Lists all Python processes
- Shows command lines for Python processes
- Helps identify background processes started by Cascade
"""
import os
import time
import psutil
from datetime import datetime

def format_time(seconds):
    """Format seconds into readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds/60:.1f}m"
    return f"{seconds/3600:.1f}h"

def format_size(bytes):
    """Format bytes into readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f}{unit}"
        bytes /= 1024
    return f"{bytes:.1f}TB"

def get_python_processes():
    """Get all running Python processes"""
    python_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'memory_info']):
        try:
            # Check if this is a Python process
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline']
                if cmdline and len(cmdline) > 1:
                    # Calculate runtime
                    runtime = time.time() - proc.info['create_time']
                    
                    # Get memory usage
                    memory = proc.info['memory_info'].rss if proc.info['memory_info'] else 0
                    
                    # Get script name (second argument in cmdline)
                    script = os.path.basename(cmdline[1]) if len(cmdline) > 1 else "unknown"
                    
                    # Store process info
                    python_processes.append({
                        'pid': proc.info['pid'],
                        'script': script,
                        'cmdline': ' '.join(cmdline),
                        'runtime': runtime,
                        'runtime_fmt': format_time(runtime),
                        'memory': memory,
                        'memory_fmt': format_size(memory)
                    })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # Sort by runtime (longest first)
    python_processes.sort(key=lambda x: x['runtime'], reverse=True)
    
    return python_processes

def main():
    """Main function"""
    print("\n" + "=" * 80)
    print(f"CASCADE PROCESS MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    processes = get_python_processes()
    
    if not processes:
        print("\nNo Python processes found.")
        return
    
    print(f"\nFound {len(processes)} Python processes:\n")
    
    # Print header
    print(f"{'PID':>8} {'AGE':>8} {'MEMORY':>10} {'SCRIPT':20} COMMAND")
    print("-" * 100)
    
    # Print processes
    for proc in processes:
        print(f"{proc['pid']:8d} {proc['runtime_fmt']:>8} {proc['memory_fmt']:>10} {proc['script']:20} {proc['cmdline'][:60]}{'...' if len(proc['cmdline']) > 60 else ''}")
    
    print("\nTo terminate a process: Stop-Process -Id <PID> -Force")
    print("To view process details: Get-Process -Id <PID> | Format-List *")
    print("=" * 80)

if __name__ == "__main__":
    main()
