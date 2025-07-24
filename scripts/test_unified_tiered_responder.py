#!/usr/bin/env python3
"""
Test Unified Tiered Responder
Validates that the unified agent works correctly across MainPC and PC2 configurations.
"""
import sys
import time
import json
import zmq
import threading
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from main_pc_code.agents.tiered_responder_unified import TieredResponder

def test_machine_type_detection():
    """Test automatic machine type detection"""
    print("🔍 Testing machine type detection...")
    
    # Test explicit machine type
    responder_mainpc = TieredResponder(machine_type="MainPC")
    assert responder_mainpc.machine_type == "MainPC"
    print("  ✅ MainPC machine type set correctly")
    
    responder_pc2 = TieredResponder(machine_type="PC2")
    assert responder_pc2.machine_type == "PC2"
    print("  ✅ PC2 machine type set correctly")
    
    # Test port configuration
    mainpc_port = responder_mainpc.port
    pc2_port = responder_pc2.port
    assert mainpc_port != pc2_port, f"Ports should be different: MainPC={mainpc_port}, PC2={pc2_port}"
    print(f"  ✅ Port configuration: MainPC={mainpc_port}, PC2={pc2_port}")
    
    return True

def test_resource_thresholds():
    """Test machine-specific resource thresholds"""
    print("🎛️ Testing resource thresholds...")
    
    mainpc_responder = TieredResponder(machine_type="MainPC")
    pc2_responder = TieredResponder(machine_type="PC2")
    
    # Check resource manager thresholds
    mainpc_cpu = mainpc_responder.resource_manager.cpu_threshold
    pc2_cpu = pc2_responder.resource_manager.cpu_threshold
    
    assert mainpc_cpu < pc2_cpu, f"MainPC should have lower CPU threshold: MainPC={mainpc_cpu}, PC2={pc2_cpu}"
    print(f"  ✅ CPU thresholds: MainPC={mainpc_cpu}%, PC2={pc2_cpu}%")
    
    return True

def test_response_processing():
    """Test response processing for different tiers"""
    print("⚡ Testing response processing...")
    
    responder = TieredResponder(machine_type="Generic", port=9001)
    
    # Test instant response
    instant_query = {"text": "ping", "id": "test_1"}
    instant_response = responder._handle_instant_response(instant_query)
    assert instant_response["tier"] == "instant"
    assert "response_time" in instant_response
    print("  ✅ Instant response processing")
    
    # Test fast response
    fast_query = {"text": "what is the weather", "id": "test_2"}
    fast_response = responder._handle_fast_response(fast_query)
    assert fast_response["tier"] == "fast"
    assert "machine_type" in fast_response
    print("  ✅ Fast response processing")
    
    # Test deep response
    deep_query = {"text": "create a detailed plan", "id": "test_3"}
    deep_response = responder._handle_deep_response(deep_query)
    assert deep_response["tier"] == "deep"
    assert "analysis" in deep_response
    print("  ✅ Deep response processing")
    
    return True

def test_tier_determination():
    """Test query tier determination logic"""
    print("🧠 Testing tier determination...")
    
    responder = TieredResponder(machine_type="Generic", port=9002)
    
    test_cases = [
        ({"text": "hello"}, "instant"),
        ({"text": "ping"}, "instant"),
        ({"text": "what is Python"}, "fast"),
        ({"text": "how do I learn programming"}, "fast"),
        ({"text": "create a detailed business plan"}, "deep"),
        ({"text": "analyze this complex data"}, "deep"),
        ({"text": "random query"}, "fast"),  # default
    ]
    
    for query, expected_tier in test_cases:
        determined_tier = responder._determine_tier(query)
        assert determined_tier == expected_tier, f"Query '{query['text']}' should be {expected_tier}, got {determined_tier}"
    
    print(f"  ✅ Tested {len(test_cases)} tier determination cases")
    return True

def test_error_handling():
    """Test error handling patterns"""
    print("🛡️ Testing error handling...")
    
    mainpc_responder = TieredResponder(machine_type="MainPC", port=9003)
    pc2_responder = TieredResponder(machine_type="PC2", port=9004)
    
    # Check error publisher availability
    assert mainpc_responder.error_publisher is not None, "MainPC should have error publisher"
    assert pc2_responder.error_publisher is None, "PC2 should not have error publisher"
    print("  ✅ Error publisher configuration")
    
    # Test resource manager error handling
    stats = mainpc_responder.resource_manager.get_stats()
    assert isinstance(stats, dict), "Resource stats should be a dictionary"
    assert "cpu_percent" in stats, "CPU stats should be present"
    print("  ✅ Resource monitoring error handling")
    
    return True

def test_configuration_loading():
    """Test machine configuration loading"""
    print("⚙️ Testing configuration loading...")
    
    # Test different machine configurations
    machines = ["MainPC", "PC2", "Generic"]
    
    for machine in machines:
        responder = TieredResponder(machine_type=machine, port=9005 + hash(machine) % 1000)
        
        # Check basic configuration
        assert responder.machine_type == machine
        assert hasattr(responder, 'resource_manager')
        assert hasattr(responder, 'response_stats')
        
        # Check machine-specific stats
        assert responder.response_stats['machine_type'] == machine
        
    print(f"  ✅ Configuration loading for {len(machines)} machine types")
    return True

def test_status_reporting():
    """Test comprehensive status reporting"""
    print("📊 Testing status reporting...")
    
    responder = TieredResponder(machine_type="Generic", port=9006)
    
    # Let it run briefly to generate some stats
    time.sleep(0.1)
    
    status = responder.get_status()
    
    required_fields = [
        'status', 'machine_type', 'uptime_seconds', 
        'response_stats', 'resource_stats', 'queue_size', 
        'health', 'timestamp'
    ]
    
    for field in required_fields:
        assert field in status, f"Status should contain {field}"
    
    assert status['machine_type'] == "Generic"
    assert status['status'] == "running"
    print("  ✅ Status reporting includes all required fields")
    
    return True

def run_performance_test():
    """Run a brief performance test"""
    print("🚀 Running performance test...")
    
    responder = TieredResponder(machine_type="Generic", port=9007)
    
    # Process multiple queries to test performance
    test_queries = [
        {"text": "ping", "id": f"perf_{i}"} for i in range(10)
    ]
    
    start_time = time.time()
    
    for query in test_queries:
        response = responder._handle_instant_response(query)
        assert response["tier"] == "instant"
    
    end_time = time.time()
    total_time = end_time - start_time
    avg_time = total_time / len(test_queries)
    
    print(f"  ✅ Processed {len(test_queries)} queries in {total_time:.3f}s (avg: {avg_time:.3f}s)")
    
    # Check if we're meeting instant response requirements
    assert avg_time < 0.01, f"Average response time {avg_time:.3f}s should be < 0.01s for instant queries"
    
    return True

def main():
    """Run all tests"""
    print("🧪 Testing Unified Tiered Responder")
    print("=" * 50)
    
    tests = [
        test_machine_type_detection,
        test_resource_thresholds,
        test_response_processing,
        test_tier_determination,
        test_error_handling,
        test_configuration_loading,
        test_status_reporting,
        run_performance_test,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"  ✅ {test.__name__} PASSED")
            else:
                failed += 1
                print(f"  ❌ {test.__name__} FAILED")
        except Exception as e:
            failed += 1
            print(f"  ❌ {test.__name__} FAILED: {e}")
        print()
    
    print("=" * 50)
    print(f"📈 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Unified Tiered Responder is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 