#!/usr/bin/env python3
"""
BASIC SERVICE STARTER
====================
Simple script to start the essential services we've created
"""

import subprocess
import time
import sys
from pathlib import Path

def start_service(directory, command, service_name):
    """Start a service in a specific directory"""
    print(f"🚀 Starting {service_name}...")
    
    # Check if directory exists
    if not Path(directory).exists():
        print(f"❌ Directory {directory} not found")
        return False
    
    # Check if main file exists
    main_file = command.split()[-1]  # Get the Python file
    if not (Path(directory) / main_file).exists():
        print(f"❌ File {main_file} not found in {directory}")
        return False
    
    try:
        # Start the service
        process = subprocess.Popen(
            command.split(), 
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Give it a moment to start
        time.sleep(3)
        
        # Check if it's still running
        if process.poll() is None:
            print(f"✅ {service_name} started successfully (PID: {process.pid})")
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {service_name} failed to start")
            if stderr:
                print(f"   Error: {stderr.decode()[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Failed to start {service_name}: {e}")
        return False

def main():
    print("🔧 BASIC SERVICE STARTER")
    print("=" * 40)
    
    # Define services to start
    services = [
        {
            "directory": "services/streaming_translation_proxy",
            "command": "python3 proxy.py",
            "name": "Translation Proxy",
            "port": 5596
        },
        {
            "directory": "services/cross_gpu_scheduler", 
            "command": "python3 app.py",
            "name": "GPU Scheduler",
            "port": 7155
        }
    ]
    
    started_services = 0
    
    for service in services:
        if start_service(service["directory"], service["command"], service["name"]):
            started_services += 1
        else:
            print(f"⚠️  Skipping {service['name']} due to startup failure")
        
        print()  # Empty line for readability
    
    print(f"📊 SUMMARY: {started_services}/{len(services)} services started successfully")
    
    if started_services > 0:
        print("\n🔍 VERIFICATION:")
        print("   Run this to check if services are accessible:")
        print("   python3 SIMPLE_CURRENT_CHECK.py")
        
        print("\n🌐 TEST ENDPOINTS:")
        for service in services:
            if service["name"] in ["Translation Proxy", "GPU Scheduler"]:
                port = service["port"]
                print(f"   curl http://localhost:{port}/health")
        
        print(f"\n⚠️  Services started in background. Use 'ps aux | grep python' to see them.")
        print("   To stop: 'pkill -f proxy.py' or 'pkill -f app.py'")
        
    else:
        print("\n💡 TROUBLESHOOTING:")
        print("   1. Check if Python dependencies are installed")
        print("   2. Verify file permissions")
        print("   3. Check for port conflicts: netstat -tlnp")
        print("   4. Review error messages above")
        
        print("\n🔧 MANUAL STARTUP:")
        print("   Try starting services manually:")
        for service in services:
            print(f"   cd {service['directory']} && {service['command']}")
    
    return started_services

if __name__ == "__main__":
    count = main()
    sys.exit(0 if count > 0 else 1)