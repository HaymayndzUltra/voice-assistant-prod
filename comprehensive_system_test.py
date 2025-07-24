#!/usr/bin/env python3
"""
Comprehensive AI System Integration Test - Step 11
Tests all deployed container groups and agent functionality
"""
import subprocess
import requests
import json
import time
import sys
from typing import Dict, List, Tuple

def run_command(cmd: str) -> Tuple[int, str]:
    """Run shell command and return exit code and output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "Command timed out"
    except Exception as e:
        return -1, str(e)

def test_container_status() -> Dict[str, bool]:
    """Test if all containers are running"""
    print("🔍 Testing Container Status...")
    print("=" * 50)
    
    expected_containers = [
        "docker-core-services-1",
        "docker-memory-system-1", 
        "docker-learning-knowledge-1",
        "docker-reasoning-services-1",
        "docker-language-processing-1",
        "docker-gpu-infrastructure-1",
        "docker-vision-processing-1",
        "docker-speech-services-1",
        "docker-audio-interface-1",
        "docker-emotion-system-1",
        "docker-utility-services-1"
    ]
    
    results = {}
    for container in expected_containers:
        code, output = run_command(f"docker ps --filter name={container} --format '{{.Names}}'")
        is_running = container in output
        status = "✅ RUNNING" if is_running else "❌ NOT RUNNING"
        print(f"{container}: {status}")
        results[container] = is_running
        
    return results

def test_agent_logs() -> Dict[str, int]:
    """Test how many agents in each container have active logs"""
    print("\n🔍 Testing Agent Log Activity...")
    print("=" * 50)
    
    containers = [
        "docker-core-services-1",
        "docker-memory-system-1",
        "docker-learning-knowledge-1"
    ]
    
    results = {}
    for container in containers:
        code, output = run_command(f"docker exec {container} find /app/logs -name '*.log' 2>/dev/null | wc -l")
        try:
            log_count = int(output.strip()) if code == 0 else 0
        except:
            log_count = 0
            
        print(f"{container}: {log_count} log files")
        results[container] = log_count
        
    return results

def test_health_endpoints() -> Dict[str, bool]:
    """Test available health endpoints"""
    print("\n🔍 Testing Health Endpoints...")
    print("=" * 50)
    
    # Test ObservabilityHub (known to be working)
    health_tests = [
        ("ObservabilityHub", "http://localhost:9000/health"),
        ("ServiceRegistry HTTP", "http://localhost:8101/health"),
        ("SystemDigitalTwin HTTP", "http://localhost:8220/health"),
    ]
    
    results = {}
    for name, url in health_tests:
        try:
            response = requests.get(url, timeout=5)
            is_healthy = response.status_code == 200
            status = f"✅ {response.status_code}" if is_healthy else f"❌ {response.status_code}"
        except requests.RequestException as e:
            is_healthy = False
            status = f"❌ Connection failed: {str(e)[:50]}"
        except Exception as e:
            is_healthy = False
            status = f"❌ Error: {str(e)[:50]}"
            
        print(f"{name}: {status}")
        results[name] = is_healthy
        
    return results

def test_resource_usage() -> Dict[str, str]:
    """Test system resource usage"""
    print("\n🔍 Testing Resource Usage...")
    print("=" * 50)
    
    # Test Docker stats
    code, output = run_command("docker stats --no-stream --format 'table {{.Name}}\\t{{.CPUPerc}}\\t{{.MemUsage}}' | head -5")
    print("Top 5 Containers Resource Usage:")
    if code == 0:
        print(output)
    else:
        print("❌ Could not get Docker stats")
        
    # Test overall system
    results = {}
    
    # Memory usage
    code, output = run_command("free -h | grep Mem")
    if code == 0:
        results["memory"] = output.strip()
        print(f"System Memory: {output.strip()}")
    
    # Disk usage
    code, output = run_command("df -h / | tail -1")
    if code == 0:
        results["disk"] = output.strip()
        print(f"Disk Usage: {output.strip()}")
        
    return results

def generate_summary(container_results, log_results, health_results, resource_results) -> None:
    """Generate test summary"""
    print("\n" + "=" * 60)
    print("🎯 SYSTEM INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    # Container status
    running_containers = sum(1 for status in container_results.values() if status)
    total_containers = len(container_results)
    container_score = (running_containers / total_containers) * 100
    
    print(f"📦 CONTAINERS: {running_containers}/{total_containers} running ({container_score:.1f}%)")
    
    # Agent activity
    total_logs = sum(log_results.values())
    print(f"📝 AGENT LOGS: {total_logs} total log files created")
    
    # Health endpoints
    healthy_endpoints = sum(1 for status in health_results.values() if status)
    total_endpoints = len(health_results)
    health_score = (healthy_endpoints / total_endpoints) * 100 if total_endpoints > 0 else 0
    
    print(f"🏥 HEALTH ENDPOINTS: {healthy_endpoints}/{total_endpoints} responding ({health_score:.1f}%)")
    
    # Overall score
    overall_score = (container_score + health_score) / 2
    print(f"\n🏆 OVERALL SYSTEM HEALTH: {overall_score:.1f}%")
    
    if overall_score >= 90:
        print("✅ EXCELLENT - System ready for production!")
    elif overall_score >= 75:
        print("✅ GOOD - System functional with minor issues")
    elif overall_score >= 50:
        print("⚠️  MODERATE - System partially functional")
    else:
        print("❌ POOR - System needs significant work")

def main():
    """Run comprehensive system integration test"""
    print("🚀 AI SYSTEM COMPREHENSIVE INTEGRATION TEST")
    print("🎯 Step 11: Complete System Integration Test")
    print("=" * 60)
    
    start_time = time.time()
    
    # Run all tests
    container_results = test_container_status()
    log_results = test_agent_logs()
    health_results = test_health_endpoints()
    resource_results = test_resource_usage()
    
    # Generate summary
    generate_summary(container_results, log_results, health_results, resource_results)
    
    duration = time.time() - start_time
    print(f"\n⏱️  Test completed in {duration:.2f} seconds")
    print("\n🎯 Ready for Step 12: Load balancing & monitoring verification")

if __name__ == "__main__":
    main() 