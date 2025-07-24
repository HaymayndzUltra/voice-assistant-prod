#!/usr/bin/env python3
"""
Intelligent Health Check Client v2.0
-------------------------------------
Enhanced with standardized health checking system
Checks actual agent readiness using Redis ready signals and comprehensive health data
Based on Background Agent findings - addresses the root cause of health check failures
"""

import sys
import os
import time
import socket
import redis
import requests
import json
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from common.health.standardized_health import check_agent_health, wait_for_agent_ready, get_system_health_summary

def check_redis_connectivity():
    """Check if Redis is accessible and responsive"""
    try:
        r = redis.Redis(host=os.getenv('${SECRET_PLACEHOLDER}0)
        r.ping()
        return True
    except Exception as e:
        print(f"Redis check failed: {e}")
        return False

def check_nats_connectivity():
    """Check if NATS is accessible"""
    try:
        nats_host = os.getenv('NATS_HOST', 'nats')
        response = requests.get(f"http://{nats_host}:8222/healthz", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"NATS check failed: {e}")
        return False

def check_agent_ready_signals(service_type):
    """Check if agents have set ready signals in Redis"""
    try:
        r = redis.Redis(host=os.getenv('${SECRET_PLACEHOLDER}0)
        
        # Define expected agents for each service type
        expected_agents = {
            'core': [
                'ServiceRegistry', 'SystemDigitalTwin', 'RequestCoordinator',
                'UnifiedSystemAgent', 'ObservabilityHub', 'ModelManagerSuite'
            ],
            'memory': [
                'MemoryClient', 'SessionMemoryAgent', 'KnowledgeBase'
            ],
            'utility': [
                'CodeGenerator', 'SelfTrainingOrchestrator', 'PredictiveHealthMonitor',
                'FixedStreamingTranslation', 'Executor', 'TinyLlamaServiceEnhanced',
                'LocalFineTunerAgent', 'NLLBAdapter'
            ]
        }
        
        agents = expected_agents.get(service_type, [])
        ready_count = 0
        
        for agent in agents:
            ready_key = f"agent:ready:{agent}"
            if r.get(ready_key) == b'1':
                ready_count += 1
        
        # Require at least 70% of agents to be ready
        required_ready = max(1, int(len(agents) * 0.7))
        is_ready = ready_count >= required_ready
        
        print(f"Service {service_type}: {ready_count}/{len(agents)} agents ready (need {required_ready})")
        return is_ready
        
    except Exception as e:
        print(f"Agent ready check failed: {e}")
        return False

def check_service_health(service_type):
    """Comprehensive health check for a service type"""
    print(f"Checking health for service: {service_type}")
    
    # Step 1: Check infrastructure dependencies
    if not check_redis_connectivity():
        print("❌ Redis not ready")
        return False
    
    if not check_nats_connectivity():
        print("❌ NATS not ready")
        return False
    
    # Step 2: Check if agents are reporting ready
    if not check_agent_ready_signals(service_type):
        print(f"❌ {service_type} agents not ready")
        return False
    
    # Step 3: Check service-specific endpoints
    service_ports = {
        'core': [7200, 7220],  # ServiceRegistry, SystemDigitalTwin
        'memory': [5713, 5574],  # MemoryClient, SessionMemoryAgent
        'utility': [5650, 5660]  # CodeGenerator, SelfTrainingOrchestrator
    }
    
    ports = service_ports.get(service_type, [])
    for port in ports:
        if not check_port_connectivity('localhost', port):
            print(f"❌ Port {port} not responding")
            return False
    
    print(f"✅ {service_type} service healthy")
    return True

def check_port_connectivity(host, port):
    """Check if a port is accessible"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_agent_health_standardized(agent_name, port):
    """Use standardized health checking for a specific agent"""
    try:
        health = check_agent_health(agent_name, port)
        print(f"📊 {agent_name} health: {health.status.value}")
        
        if health.checks:
            for check_name, result in health.checks.items():
                status_icon = "✅" if result else "❌"
                print(f"  {status_icon} {check_name}")
        
        return health.status.value in ['healthy', 'degraded']
    except Exception as e:
        print(f"❌ Health check failed for {agent_name}: {e}")
        return False

def wait_for_agents_ready(agents_with_ports, timeout=120):
    """Wait for multiple agents to become ready using standardized health checking"""
    print(f"🔍 Waiting for {len(agents_with_ports)} agents to become ready...")
    
    for agent_name, port in agents_with_ports:
        print(f"⏳ Waiting for {agent_name} (port {port})...")
        if wait_for_agent_ready(agent_name, port, timeout=timeout):
            print(f"✅ {agent_name} is ready")
        else:
            print(f"❌ {agent_name} failed to become ready within {timeout}s")
            return False
    
    return True

def get_system_status():
    """Get comprehensive system health status"""
    try:
        summary = get_system_health_summary()
        print(f"\n📊 SYSTEM HEALTH SUMMARY")
        print(f"Timestamp: {summary.get('timestamp', 'unknown')}")
        print(f"Total agents: {summary.get('total_agents', 0)}")
        print(f"Ready agents: {summary.get('ready_agents', 0)}")
        
        if 'agents' in summary:
            print(f"\n📋 AGENT STATUS:")
            for agent_name, health_data in summary['agents'].items():
                status = health_data.get('status', 'unknown')
                timestamp = health_data.get('timestamp', 'unknown')
                print(f"  {agent_name}: {status} (last check: {timestamp})")
        
        return summary
    except Exception as e:
        print(f"❌ Failed to get system status: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: health_check_client.py <command> [args...]")
        print("Commands:")
        print("  service <service_type>  - Check service health (legacy)")
        print("  agent <agent_name> <port>  - Check specific agent")
        print("  wait <agent_name> <port> [timeout]  - Wait for agent ready")
        print("  system  - Get system status")
        print("  summary - Get health summary")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "service":
        if len(sys.argv) != 3:
            print("Usage: health_check_client.py service <service_type>")
            print("Service types: core, memory, utility, gpu, reasoning, vision, learning, language, speech, audio, emotion")
            sys.exit(1)
        
        service_type = sys.argv[2]
        print(f"Waiting for {service_type} service to initialize...")
        time.sleep(10)
        
        if check_service_health(service_type):
            print(f"✅ {service_type} service is healthy")
            sys.exit(0)
        else:
            print(f"❌ {service_type} service is unhealthy")
            sys.exit(1)
    
    elif command == "agent":
        if len(sys.argv) != 4:
            print("Usage: health_check_client.py agent <agent_name> <port>")
            sys.exit(1)
        
        agent_name = sys.argv[2]
        port = int(sys.argv[3])
        
        if check_agent_health_standardized(agent_name, port):
            print(f"✅ {agent_name} is healthy")
            sys.exit(0)
        else:
            print(f"❌ {agent_name} is unhealthy")
            sys.exit(1)
    
    elif command == "wait":
        if len(sys.argv) < 4:
            print("Usage: health_check_client.py wait <agent_name> <port> [timeout]")
            sys.exit(1)
        
        agent_name = sys.argv[2]
        port = int(sys.argv[3])
        timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 60
        
        if wait_for_agent_ready(agent_name, port, timeout):
            print(f"✅ {agent_name} became ready")
            sys.exit(0)
        else:
            print(f"❌ {agent_name} failed to become ready")
            sys.exit(1)
    
    elif command in ["system", "summary"]:
        summary = get_system_status()
        if summary and summary.get('ready_agents', 0) > 0:
            print("✅ System has active agents")
            sys.exit(0)
        else:
            print("❌ System has no ready agents")
            sys.exit(1)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main() 