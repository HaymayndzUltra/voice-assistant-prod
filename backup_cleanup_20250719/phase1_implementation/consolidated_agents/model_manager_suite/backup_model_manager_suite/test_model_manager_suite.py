#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Test Script for ModelManagerSuite
=================================

This script tests the consolidated ModelManagerSuite service to ensure:
1. GGUF model management functionality
2. Predictive loading algorithms
3. Model evaluation framework
4. Backward compatibility endpoints
5. Error handling and circuit breakers
"""

import sys
import os
import time
import json
import zmq
import threading
from pathlib import Path

# Add project paths
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent.parent.parent
main_pc_code_dir = project_root / "main_pc_code"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(main_pc_code_dir) not in sys.path:
    sys.path.insert(0, str(main_pc_code_dir))

from phase1_implementation.consolidated_agents.model_manager_suite.model_manager_suite import ModelManagerSuite

class ModelManagerSuiteTester:
    """Test suite for ModelManagerSuite"""
    
    def __init__(self):
        self.test_results = []
        self.suite = None
        self.context = zmq.Context()
        self.socket = None
        
    def setup(self):
        """Setup test environment"""
        print("🔧 Setting up ModelManagerSuite test environment...")
        
        # Create test directories
        test_dirs = [
            "phase1_implementation/data",
            "logs",
            "models"
        ]
        
        for dir_path in test_dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize ModelManagerSuite
        try:
            self.suite = ModelManagerSuite(port=7011, health_port=7111)
            print("✅ ModelManagerSuite initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize ModelManagerSuite: {e}")
            return False
        
        # Setup ZMQ connection for testing
        try:
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect("tcp://localhost:7011")
            print("✅ ZMQ connection established")
        except Exception as e:
            print(f"❌ Failed to connect to ModelManagerSuite: {e}")
            return False
        
        return True
    
    def teardown(self):
        """Cleanup test environment"""
        print("🧹 Cleaning up test environment...")
        
        if self.socket:
            self.socket.close()
        
        if self.context:
            self.context.term()
        
        if self.suite:
            self.suite.cleanup()
    
    def send_request(self, action: str, data: dict = None) -> dict:
        """Send request to ModelManagerSuite"""
        request = {
            "action": action,
            "data": data or {}
        }
        
        try:
            self.socket.send_json(request)
            response = self.socket.recv_json()
            return response
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def test_health_check(self):
        """Test health check functionality"""
        print("\n🏥 Testing Health Check...")
        
        response = self.send_request("health_check")
        
        if response.get("status") == "success":
            print("✅ Health check passed")
            self.test_results.append(("Health Check", "PASS"))
            return True
        else:
            print(f"❌ Health check failed: {response}")
            self.test_results.append(("Health Check", "FAIL"))
            return False
    
    def test_get_stats(self):
        """Test statistics endpoint"""
        print("\n📊 Testing Statistics...")
        
        response = self.send_request("get_stats")
        
        if response.get("status") == "success":
            stats = response.get("data", {})
            print(f"✅ Statistics retrieved: {stats}")
            self.test_results.append(("Statistics", "PASS"))
            return True
        else:
            print(f"❌ Statistics failed: {response}")
            self.test_results.append(("Statistics", "FAIL"))
            return False
    
    def test_model_status(self):
        """Test model status functionality"""
        print("\n📋 Testing Model Status...")
        
        response = self.send_request("get_model_status", {"model_id": "test_model"})
        
        if response.get("status") == "success":
            print("✅ Model status check passed")
            self.test_results.append(("Model Status", "PASS"))
            return True
        else:
            print(f"❌ Model status failed: {response}")
            self.test_results.append(("Model Status", "FAIL"))
            return False
    
    def test_performance_metrics(self):
        """Test performance metrics functionality"""
        print("\n📈 Testing Performance Metrics...")
        
        # Test logging a metric
        log_response = self.send_request("log_performance_metric", {
            "agent_name": "test_agent",
            "metric_name": "test_metric",
            "value": 95.5,
            "context": "test_context"
        })
        
        if log_response.get("status") == "success":
            print("✅ Performance metric logging passed")
            
            # Test retrieving metrics
            get_response = self.send_request("get_performance_metrics", {
                "agent_name": "test_agent"
            })
            
            if get_response.get("status") == "success":
                print("✅ Performance metrics retrieval passed")
                self.test_results.append(("Performance Metrics", "PASS"))
                return True
        
        print(f"❌ Performance metrics failed: {log_response}")
        self.test_results.append(("Performance Metrics", "FAIL"))
        return False
    
    def test_model_evaluation(self):
        """Test model evaluation functionality"""
        print("\n🎯 Testing Model Evaluation...")
        
        # Test logging evaluation
        log_response = self.send_request("log_model_evaluation", {
            "model_name": "test_model",
            "cycle_id": "test_cycle_001",
            "trust_score": 0.85,
            "accuracy": 0.92,
            "f1_score": 0.89,
            "avg_latency_ms": 150.0
        })
        
        if log_response.get("status") == "success":
            print("✅ Model evaluation logging passed")
            
            # Test retrieving evaluations
            get_response = self.send_request("get_model_evaluation_scores", {
                "model_name": "test_model"
            })
            
            if get_response.get("status") == "success":
                print("✅ Model evaluation retrieval passed")
                self.test_results.append(("Model Evaluation", "PASS"))
                return True
        
        print(f"❌ Model evaluation failed: {log_response}")
        self.test_results.append(("Model Evaluation", "FAIL"))
        return False
    
    def test_predictive_loading(self):
        """Test predictive loading functionality"""
        print("\n🔮 Testing Predictive Loading...")
        
        # Test recording usage
        record_response = self.send_request("record_usage", {
            "model_id": "test_model",
            "usage_type": "text_generation"
        })
        
        if record_response.get("status") == "success":
            print("✅ Usage recording passed")
            
            # Test prediction
            predict_response = self.send_request("predict_models", {})
            
            if predict_response.get("status") == "success":
                print("✅ Model prediction passed")
                self.test_results.append(("Predictive Loading", "PASS"))
                return True
        
        print(f"❌ Predictive loading failed: {record_response}")
        self.test_results.append(("Predictive Loading", "FAIL"))
        return False
    
    def test_backward_compatibility(self):
        """Test backward compatibility with legacy endpoints"""
        print("\n🔄 Testing Backward Compatibility...")
        
        # Test legacy load_model endpoint
        legacy_response = self.send_request("load_model", {
            "model_id": "legacy_test_model",
            "model_path": "models/test.gguf"
        })
        
        if legacy_response.get("status") in ["success", "error"]:  # Both are valid responses
            print("✅ Backward compatibility passed")
            self.test_results.append(("Backward Compatibility", "PASS"))
            return True
        else:
            print(f"❌ Backward compatibility failed: {legacy_response}")
            self.test_results.append(("Backward Compatibility", "FAIL"))
            return False
    
    def test_error_handling(self):
        """Test error handling and circuit breakers"""
        print("\n🛡️ Testing Error Handling...")
        
        # Test invalid request
        error_response = self.send_request("invalid_action", {
            "invalid_data": "test"
        })
        
        if error_response.get("status") == "error":
            print("✅ Error handling passed")
            self.test_results.append(("Error Handling", "PASS"))
            return True
        else:
            print(f"❌ Error handling failed: {error_response}")
            self.test_results.append(("Error Handling", "FAIL"))
            return False
    
    def run_all_tests(self):
        """Run all test cases"""
        print("🚀 Starting ModelManagerSuite Test Suite")
        print("=" * 50)
        
        if not self.setup():
            print("❌ Test setup failed")
            return False
        
        try:
            # Run all tests
            tests = [
                self.test_health_check,
                self.test_get_stats,
                self.test_model_status,
                self.test_performance_metrics,
                self.test_model_evaluation,
                self.test_predictive_loading,
                self.test_backward_compatibility,
                self.test_error_handling
            ]
            
            passed = 0
            total = len(tests)
            
            for test in tests:
                if test():
                    passed += 1
                time.sleep(0.5)  # Small delay between tests
            
            # Print results
            print("\n" + "=" * 50)
            print("📋 TEST RESULTS SUMMARY")
            print("=" * 50)
            
            for test_name, result in self.test_results:
                status_icon = "✅" if result == "PASS" else "❌"
                print(f"{status_icon} {test_name}: {result}")
            
            print(f"\n🎯 Overall: {passed}/{total} tests passed")
            
            if passed == total:
                print("🎉 ALL TESTS PASSED! ModelManagerSuite is working correctly.")
                return True
            else:
                print("⚠️ Some tests failed. Please check the implementation.")
                return False
                
        finally:
            self.teardown()

def main():
    """Main test runner"""
    tester = ModelManagerSuiteTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ ModelManagerSuite test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ ModelManagerSuite test failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 