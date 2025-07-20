#!/usr/bin/env python3
"""Test PC2 to MainPC communication."""

import zmq
import requests
import json
import time
from datetime import datetime

# Configuration
MAINPC_IP = "192.168.100.16"
PC2_IP = "192.168.100.17"

# Test endpoints
TEST_ENDPOINTS = {
    "MainPC ObservabilityHub": f"http://{MAINPC_IP}:9000/health",
    "PC2 ObservabilityHub": f"http://{PC2_IP}:9000/health",
    "PC2 AuthenticationAgent": f"tcp://{PC2_IP}:7116",
    "PC2 MemoryOrchestrator": f"tcp://{PC2_IP}:7140",
    "PC2 ResourceManager": f"tcp://{PC2_IP}:7113",
}

def test_http_endpoint(name, url):
    """Test HTTP endpoint."""
    print(f"\nTesting {name} at {url}...")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {name} is healthy")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ {name} returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ {name} failed: {e}")
        return False

def test_zmq_endpoint(name, endpoint):
    """Test ZMQ endpoint."""
    print(f"\nTesting {name} at {endpoint}...")
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
    
    try:
        socket.connect(endpoint)
        
        # Send health check request
        request = {
            "action": "health_check",
            "timestamp": datetime.now().isoformat()
        }
        socket.send_json(request)
        
        # Wait for response
        response = socket.recv_json()
        
        if response.get("status") in ["ok", "healthy"]:
            print(f"✅ {name} is healthy")
            print(f"   Response: {response}")
            return True
        else:
            print(f"❌ {name} returned unhealthy status")
            print(f"   Response: {response}")
            return False
            
    except zmq.error.Again:
        print(f"❌ {name} timeout - no response received")
        return False
    except Exception as e:
        print(f"❌ {name} failed: {e}")
        return False
    finally:
        socket.close()
        context.term()

def test_cross_machine_sync():
    """Test ObservabilityHub cross-machine sync."""
    print("\n" + "="*60)
    print("Testing ObservabilityHub Cross-Machine Sync")
    print("="*60)
    
    try:
        # Get metrics from PC2 ObservabilityHub
        pc2_metrics = requests.get(f"http://{PC2_IP}:9000/metrics", timeout=5)
        
        # Check if MainPC hub endpoint is configured
        if "mainpc_hub_endpoint" in pc2_metrics.text:
            print("✅ PC2 ObservabilityHub has MainPC sync configured")
        else:
            print("⚠️  PC2 ObservabilityHub may not have MainPC sync configured")
        
        # Try to get aggregated metrics from MainPC
        mainpc_metrics = requests.get(f"http://{MAINPC_IP}:9000/metrics", timeout=5)
        
        if "pc2_agents" in mainpc_metrics.text:
            print("✅ MainPC ObservabilityHub is receiving PC2 metrics")
        else:
            print("⚠️  MainPC ObservabilityHub may not be receiving PC2 metrics")
            
    except Exception as e:
        print(f"❌ Cross-machine sync test failed: {e}")

def main():
    """Run all communication tests."""
    print("="*60)
    print("PC2 ↔ MainPC Communication Test")
    print(f"MainPC IP: {MAINPC_IP}")
    print(f"PC2 IP: {PC2_IP}")
    print("="*60)
    
    results = {}
    
    # Test HTTP endpoints
    for name, url in TEST_ENDPOINTS.items():
        if url.startswith("http"):
            results[name] = test_http_endpoint(name, url)
    
    # Test ZMQ endpoints
    for name, endpoint in TEST_ENDPOINTS.items():
        if endpoint.startswith("tcp"):
            results[name] = test_zmq_endpoint(name, endpoint)
    
    # Test cross-machine sync
    test_cross_machine_sync()
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nTests passed: {passed}/{total}")
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    if passed == total:
        print("\n🎉 All communication tests passed!")
    else:
        print(f"\n⚠️  {total - passed} tests failed")

if __name__ == "__main__":
    main()