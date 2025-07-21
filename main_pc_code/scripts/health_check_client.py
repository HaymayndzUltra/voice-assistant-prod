#!/usr/bin/env python3
"""
Intelligent Health Check Client
------------------------------
Checks actual agent readiness instead of just port connectivity
Based on Background Agent findings - addresses the root cause of health check failures
"""

import sys
import os
import time
import socket
import redis
import requests
from pathlib import Path

def check_redis_connectivity():
    """Check if Redis is accessible and responsive"""
    try:
        r = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379, db=0)
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
        r = redis.Redis(host=os.getenv('REDIS_HOST', 'redis'), port=6379, db=0)
        
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

def main():
    if len(sys.argv) != 2:
        print("Usage: health_check_client.py <service_type>")
        print("Service types: core, memory, utility, gpu, reasoning, vision, learning, language, speech, audio, emotion")
        sys.exit(1)
    
    service_type = sys.argv[1]
    
    # Give services time to initialize
    print(f"Waiting for {service_type} service to initialize...")
    time.sleep(10)
    
    # Perform health check
    if check_service_health(service_type):
        print(f"✅ {service_type} service is healthy")
        sys.exit(0)
    else:
        print(f"❌ {service_type} service is unhealthy")
        sys.exit(1)

if __name__ == "__main__":
    main() 