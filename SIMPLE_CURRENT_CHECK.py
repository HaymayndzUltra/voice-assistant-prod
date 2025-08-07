#!/usr/bin/env python3
"""
SIMPLE CURRENT SYSTEM CHECK
===========================
Basic check of what's running RIGHT NOW without external dependencies
"""

import subprocess
import json
import socket
from pathlib import Path
import os

def check_port(host, port):
    """Check if a port is open"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            return result == 0
    except:
        return False

def main():
    print("🔍 SIMPLE CURRENT SYSTEM CHECK")
    print("=" * 50)
    
    # 1. Check key service ports
    print("\n🟢 CHECKING KEY SERVICE PORTS:")
    key_ports = [
        (5596, "Translation Proxy"),
        (7155, "GPU Scheduler"), 
        (8155, "GPU Scheduler Health"),
        (9000, "MainPC ObservabilityHub"),
        (9100, "PC2 ObservabilityHub"),
        (5600, "ZMQ Bridge"),
        (7220, "SystemDigitalTwin")
    ]
    
    active_services = 0
    for port, name in key_ports:
        is_open = check_port('localhost', port)
        status = "🟢 RUNNING" if is_open else "🔴 NOT RUNNING"
        print(f"   Port {port:4d} ({name:25s}): {status}")
        if is_open:
            active_services += 1
    
    print(f"\n📊 SUMMARY: {active_services}/{len(key_ports)} key services are running")
    
    # 2. Check Docker status
    print("\n🐳 CHECKING DOCKER STATUS:")
    try:
        result = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Status}}'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:  # More than just header
                print(f"   {len(lines)-1} Docker containers running")
                for line in lines[1:6]:  # Show first 5 containers
                    print(f"   📦 {line}")
            else:
                print("   🔴 No Docker containers running")
        else:
            print("   🔴 Docker not accessible")
    except:
        print("   🔴 Docker command failed")
    
    # 3. Check config files
    print("\n⚙️ CHECKING CONFIG FILES:")
    config_files = [
        "main_pc_code/config/startup_config.yaml",
        "pc2_code/config/startup_config.yaml",
        "services/cross_gpu_scheduler/app.py",
        "services/streaming_translation_proxy/proxy.py"
    ]
    
    for config_path in config_files:
        path = Path(config_path)
        if path.exists():
            size = path.stat().st_size
            print(f"   ✅ {config_path} ({size} bytes)")
        else:
            print(f"   ❌ {config_path} (missing)")
    
    # 4. Check processes
    print("\n🔄 CHECKING PYTHON PROCESSES:")
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            python_processes = []
            for line in result.stdout.split('\n'):
                if 'python' in line and any(keyword in line for keyword in ['app.py', 'proxy.py', 'agent', 'service']):
                    python_processes.append(line.split()[-1])  # Get command
            
            if python_processes:
                print(f"   Found {len(python_processes)} relevant Python processes:")
                for proc in python_processes[:5]:  # Show first 5
                    print(f"   🐍 {proc}")
            else:
                print("   🔴 No relevant Python processes found")
    except:
        print("   🔴 Process check failed")
    
    # 5. Generate immediate actions
    print("\n🎯 IMMEDIATE ACTIONS NEEDED:")
    
    if active_services == 0:
        print("   🚨 CRITICAL: No services are running!")
        print("   📝 Actions:")
        print("      1. Check if any agents are started")
        print("      2. Review startup scripts in main_pc_code/scripts/")
        print("      3. Check system logs for errors")
    elif active_services < 3:
        print("   ⚠️  WARNING: Limited services running")
        print("   📝 Actions:")
        print("      1. Start missing critical services")
        print("      2. Check service dependencies")
        print("      3. Review configuration files")
    else:
        print("   ✅ Good: Most services appear to be running")
        print("   📝 Actions:")
        print("      1. Verify service functionality")
        print("      2. Check service logs for errors")
        print("      3. Test cross-machine communication")
    
    # 6. Quick diagnostics
    print("\n🔧 QUICK DIAGNOSTICS:")
    print("   Run these commands for more details:")
    print("   💡 netstat -tlnp | grep -E '5596|7155|9000|9100'")
    print("   💡 docker ps --format 'table {{.Names}}\\t{{.Status}}'")
    print("   💡 ps aux | grep python | grep -E 'app.py|proxy.py|agent'")
    print("   💡 tail -20 /var/log/syslog | grep -i error")
    
    return active_services

if __name__ == "__main__":
    active_count = main()
    exit(0 if active_count > 0 else 1)