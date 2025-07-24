#!/usr/bin/env python3
"""
Health Check Script for AI System Containers
"""

import os
import sys
import json
import time
import requests
import subprocess
from typing import Dict, Any

def check_process_health(service_name: str) -> Dict[str, Any]:
    """Check if a service process is running"""
    pidfile = f"/app/logs/{service_name}.pid"
    
    if not os.path.exists(pidfile):
        return {"status": "not_started", "pid": None}
    
    try:
        with open(pidfile, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process exists
        os.kill(pid, 0)  # Signal 0 just checks if process exists
        return {"status": "running", "pid": pid}
        
    except (OSError, ValueError):
        return {"status": "stopped", "pid": None}

def check_port_health(port: int) -> Dict[str, Any]:
    """Check if a port is responding"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "status_code": response.status_code,
            "response_time": response.elapsed.total_seconds()
        }
    except requests.exceptions.RequestException as e:
        return {"status": "unreachable", "error": str(e)}

def check_gpu_health() -> Dict[str, Any]:
    """Check GPU status if available"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total,utilization.gpu', 
                               '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            gpu_stats = []
            
            for i, line in enumerate(lines):
                if line.strip():
                    parts = line.split(', ')
                    if len(parts) >= 3:
                        gpu_stats.append({
                            "gpu_id": i,
                            "memory_used_mb": int(parts[0]),
                            "memory_total_mb": int(parts[1]), 
                            "utilization_percent": int(parts[2])
                        })
            
            return {"status": "available", "gpus": gpu_stats}
        else:
            return {"status": "error", "message": result.stderr}
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"status": "not_available"}

def get_container_role() -> str:
    """Get container role from environment"""
    return os.environ.get('CONTAINER_ROLE', 'unknown')

def main():
    """Main health check logic"""
    container_role = get_container_role()
    
    health_status = {
        "timestamp": time.time(),
        "container_role": container_role,
        "overall_status": "healthy",
        "services": {},
        "system": {}
    }
    
    # Define service configurations by container role
    service_configs = {
        "core_platform": {
            "services": ["ServiceRegistry", "SystemDigitalTwin", "RequestCoordinator", "ObservabilityHub"],
            "ports": [7200, 7220, 26002, 9000]
        },
        "model_manager_gpu": {
            "services": ["ModelManagerSuite", "UnifiedSystemAgent"],
            "ports": [7211, 7225],
            "gpu_required": True
        },
        "memory_stack": {
            "services": ["MemoryClient", "SessionMemoryAgent", "KnowledgeBase"],
            "ports": [5713, 5574, 5715]
        },
        "vision_dream_gpu": {
            "services": ["VisionProcessingAgent", "DreamWorldAgent", "DreamingModeAgent"],
            "ports": [7150, 7104, 7127],
            "gpu_required": True
        }
    }
    
    config = service_configs.get(container_role, {"services": [], "ports": []})
    
    # Check service processes
    for service in config.get("services", []):
        health_status["services"][service] = check_process_health(service)
        if health_status["services"][service]["status"] != "running":
            health_status["overall_status"] = "unhealthy"
    
    # Check ports
    port_status = {}
    for port in config.get("ports", []):
        port_status[f"port_{port}"] = check_port_health(port)
        if port_status[f"port_{port}"]["status"] != "healthy":
            health_status["overall_status"] = "degraded"
    
    health_status["system"]["ports"] = port_status
    
    # Check GPU if required
    if config.get("gpu_required", False):
        health_status["system"]["gpu"] = check_gpu_health()
        if health_status["system"]["gpu"]["status"] != "available":
            health_status["overall_status"] = "degraded"
    
    # Check disk space
    try:
        disk_usage = subprocess.run(['df', '/app'], capture_output=True, text=True)
        if disk_usage.returncode == 0:
            lines = disk_usage.stdout.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 5:
                    health_status["system"]["disk"] = {
                        "total_kb": int(parts[1]),
                        "used_kb": int(parts[2]),
                        "available_kb": int(parts[3]),
                        "usage_percent": int(parts[4].rstrip('%'))
                    }
                    
                    # Alert if disk usage > 90%
                    if health_status["system"]["disk"]["usage_percent"] > 90:
                        health_status["overall_status"] = "degraded"
    except:
        pass
    
    # Memory usage
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        mem_total = None
        mem_available = None
        
        for line in meminfo.split('\n'):
            if line.startswith('MemTotal:'):
                mem_total = int(line.split()[1])  # in KB
            elif line.startswith('MemAvailable:'):
                mem_available = int(line.split()[1])  # in KB
                
        if mem_total and mem_available:
            mem_used = mem_total - mem_available
            usage_percent = (mem_used / mem_total) * 100
            
            health_status["system"]["memory"] = {
                "total_kb": mem_total,
                "used_kb": mem_used,
                "available_kb": mem_available,
                "usage_percent": round(usage_percent, 2)
            }
            
            # Alert if memory usage > 95%
            if usage_percent > 95:
                health_status["overall_status"] = "degraded"
                
    except:
        pass
    
    # Output results
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        print(json.dumps(health_status, indent=2))
    else:
        # Human readable output
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌"
        }
        
        print(f"{status_emoji.get(health_status['overall_status'], '❓')} Container: {container_role}")
        print(f"Overall Status: {health_status['overall_status'].upper()}")
        print(f"Timestamp: {time.ctime(health_status['timestamp'])}")
        print()
        
        if health_status["services"]:
            print("Services:")
            for service, status in health_status["services"].items():
                emoji = "✅" if status["status"] == "running" else "❌"
                print(f"  {emoji} {service}: {status['status']}")
            print()
        
        if "ports" in health_status["system"]:
            print("Ports:")
            for port, status in health_status["system"]["ports"].items():
                emoji = "✅" if status["status"] == "healthy" else "❌"
                print(f"  {emoji} {port}: {status['status']}")
            print()
        
        if "gpu" in health_status["system"]:
            gpu_status = health_status["system"]["gpu"]
            emoji = "✅" if gpu_status["status"] == "available" else "❌"
            print(f"GPU: {emoji} {gpu_status['status']}")
            if gpu_status["status"] == "available":
                for gpu in gpu_status.get("gpus", []):
                    print(f"  GPU {gpu['gpu_id']}: {gpu['memory_used_mb']}MB/{gpu['memory_total_mb']}MB ({gpu['utilization_percent']}% util)")
            print()
    
    # Exit with appropriate code
    if health_status["overall_status"] == "healthy":
        sys.exit(0)
    elif health_status["overall_status"] == "degraded":
        sys.exit(1)
    else:  # unhealthy
        sys.exit(2)

if __name__ == "__main__":
    main() 