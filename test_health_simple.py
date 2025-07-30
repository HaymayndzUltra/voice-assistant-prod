#!/usr/bin/env python3
"""
Simple Health Check Script for Updated Services
Tests: SystemDigitalTwin, ModelManagerSuite, LearningOrchestrationService
"""

import zmq
import json
import requests
import sys
import time

def test_http_health(port, service_name):
    """Test HTTP health endpoint"""
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        print(f"✅ {service_name} HTTP ({port}): {response.status_code} - {response.text}")
        return True
    except Exception as e:
        print(f"❌ {service_name} HTTP ({port}): {e}")
        return False

def test_zmq_health(port, service_name, action="health_check"):
    """Test ZMQ health endpoint"""
    try:
        ctx = zmq.Context()
        socket = ctx.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
        socket.connect(f"tcp://localhost:{port}")

        socket.send_json({"action": action})
        response = socket.recv_json()

        status = response.get('status', 'unknown')
        print(f"✅ {service_name} ZMQ ({port}): {status}")
        print(f"   Response: {json.dumps(response, indent=2)}")

        socket.close()
        ctx.term()
        return True
    except Exception as e:
        print(f"❌ {service_name} ZMQ ({port}): {e}")
        return False

def main():
    """TODO: Add description for main."""
    print("🔍 Testing Updated Service Health Endpoints...")
    print("=" * 50)

    tests = [
        # SystemDigitalTwin
        ("SystemDigitalTwin HTTP", lambda: test_http_health(8220, "SystemDigitalTwin")),
        ("SystemDigitalTwin ZMQ", lambda: test_zmq_health(7220, "SystemDigitalTwin", "ping")),

        # ModelManagerSuite
        ("ModelManagerSuite ZMQ Main", lambda: test_zmq_health(7211, "ModelManagerSuite")),
        ("ModelManagerSuite ZMQ Health", lambda: test_zmq_health(8211, "ModelManagerSuite")),

        # LearningOrchestrationService
        ("LearningOrchestrationService ZMQ Main", lambda: test_zmq_health(7210, "LearningOrchestrationService")),
        ("LearningOrchestrationService ZMQ Health", lambda: test_zmq_health(8212, "LearningOrchestrationService")),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Testing {test_name}...")
        success = test_func()
        results.append((test_name, success))
        time.sleep(0.5)  # Small delay between tests

    print("\n" + "=" * 50)
    print("📊 SUMMARY:")
    passed = 0
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {test_name}")
        if success:
            passed += 1

    print(f"\n🎯 Result: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 ALL HEALTH CHECKS PASSED! Services are ready.")
        return 0
    else:
        print("⚠️  Some health checks failed. Check container status.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
