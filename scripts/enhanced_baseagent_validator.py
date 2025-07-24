#!/usr/bin/env python3
"""
Enhanced BaseAgent Validation Framework
Phase 1 Week 2 Day 2 - Automated testing and performance validation
"""

import os
import sys
import time
import json
import subprocess
import threading
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
import unittest
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from common.core.enhanced_base_agent import EnhancedBaseAgent, PerformanceMetrics, EnhancedErrorHandler
from common.core.unified_config_manager import UnifiedConfigManager, Config, load_unified_config


class BaseAgentPerformanceTest(unittest.TestCase):
    """Performance testing for enhanced BaseAgent"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_start_time = time.time()
        
    def tearDown(self):
        """Clean up test environment"""
        pass
    
    def test_initialization_performance(self):
        """Test BaseAgent initialization performance"""
        print("\n🔧 Testing initialization performance...")
        
        # Test basic initialization time
        start_time = time.time()
        agent = EnhancedBaseAgent(name="TestAgent", port=15000)
        init_time = time.time() - start_time
        
        print(f"  📊 Initialization time: {init_time:.4f}s")
        print(f"  📊 Config load time: {agent.performance_metrics.config_load_time:.4f}s")
        print(f"  📊 ZMQ setup time: {agent.performance_metrics.zmq_setup_time:.4f}s")
        
        # Performance assertions
        self.assertLess(init_time, 2.0, "Initialization should be under 2 seconds")
        self.assertLess(agent.performance_metrics.config_load_time, 0.5, 
                       "Config loading should be under 0.5 seconds")
        
        # Cleanup
        agent.graceful_shutdown_enhanced()
        
    def test_configuration_performance(self):
        """Test unified configuration loading performance"""
        print("\n⚙️ Testing configuration performance...")
        
        # Test configuration manager
        manager = UnifiedConfigManager()
        
        # Test cache performance
        start_time = time.time()
        config1 = manager.get_agent_config("TestAgent")
        first_load_time = time.time() - start_time
        
        start_time = time.time()
        config2 = manager.get_agent_config("TestAgent")  # Should be cached
        cached_load_time = time.time() - start_time
        
        print(f"  📊 First load time: {first_load_time:.4f}s")
        print(f"  📊 Cached load time: {cached_load_time:.4f}s")
        print(f"  📊 Cache speedup: {first_load_time/cached_load_time:.1f}x")
        
        # Performance assertions
        self.assertLess(first_load_time, 0.5, "First config load should be under 0.5 seconds")
        self.assertLess(cached_load_time, 0.1, "Cached config load should be under 0.1 seconds")
        self.assertLess(cached_load_time, first_load_time, "Cache should be faster than first load")
        
    def test_error_handling_performance(self):
        """Test enhanced error handling performance"""
        print("\n❌ Testing error handling performance...")
        
        error_handler = EnhancedErrorHandler("TestAgent")
        
        # Test error reporting performance
        test_errors = [Exception(f"Test error {i}") for i in range(100)]
        
        start_time = time.time()
        for error in test_errors:
            error_handler.report_error(error, category="TEST", severity="ERROR")
        error_handling_time = time.time() - start_time
        
        avg_error_time = error_handling_time / len(test_errors)
        
        print(f"  📊 100 errors processed in: {error_handling_time:.4f}s")
        print(f"  📊 Average error processing time: {avg_error_time*1000:.2f}ms")
        print(f"  📊 Error statistics: {error_handler.get_statistics()}")
        
        # Performance assertions
        self.assertLess(avg_error_time, 0.01, "Error processing should be under 10ms per error")
        self.assertEqual(error_handler.get_statistics()['total_errors'], 100)
        
    def test_metrics_collection_performance(self):
        """Test performance metrics collection"""
        print("\n📊 Testing metrics collection performance...")
        
        metrics = PerformanceMetrics()
        
        # Test response time collection
        start_time = time.time()
        for i in range(1000):
            metrics.add_response_time(0.1 + (i % 10) * 0.01)
        metrics_time = time.time() - start_time
        
        print(f"  📊 1000 metrics collected in: {metrics_time:.4f}s")
        print(f"  📊 Average response time: {metrics.get_avg_response_time():.4f}s")
        print(f"  📊 Memory usage: {metrics.memory_usage_mb:.2f}MB")
        
        # Performance assertions
        self.assertLess(metrics_time, 0.1, "Metrics collection should be very fast")
        self.assertGreater(metrics.get_avg_response_time(), 0, "Should calculate average correctly")


class BaseAgentFunctionalityTest(unittest.TestCase):
    """Functionality testing for enhanced BaseAgent"""
    
    def test_unified_config_compatibility(self):
        """Test backward compatibility with both config patterns"""
        print("\n🔄 Testing config pattern compatibility...")
        
        # Test MainPC pattern
        mainpc_config = load_unified_config(agent_name="TestMainPC")
        self.assertIsInstance(mainpc_config, dict)
        print(f"  ✅ MainPC pattern: {len(mainpc_config)} config keys loaded")
        
        # Test PC2 pattern
        pc2_config_loader = Config()
        pc2_config = pc2_config_loader.get_config("TestPC2")
        self.assertIsInstance(pc2_config, dict)
        print(f"  ✅ PC2 pattern: {len(pc2_config)} config keys loaded")
        
        # Test configuration consistency
        manager = UnifiedConfigManager()
        direct_config = manager.get_agent_config("TestDirect")
        self.assertIsInstance(direct_config, dict)
        print(f"  ✅ Direct pattern: {len(direct_config)} config keys loaded")
        
    def test_service_discovery_integration(self):
        """Test service discovery functionality"""
        print("\n🌐 Testing service discovery...")
        
        agent = EnhancedBaseAgent(name="TestServiceAgent", port=15001)
        
        # Test capability registration
        capabilities = ['test_capability', 'enhanced_testing']
        dependencies = ['TestDependency']
        agent.service_registry.register_service(capabilities, dependencies)
        
        self.assertEqual(agent.service_registry.capabilities, capabilities)
        self.assertEqual(agent.service_registry.dependencies, dependencies)
        self.assertTrue(agent.service_registry.is_registered("TestServiceAgent"))
        
        print(f"  ✅ Capabilities registered: {capabilities}")
        print(f"  ✅ Dependencies tracked: {dependencies}")
        
        agent.graceful_shutdown_enhanced()
        
    def test_enhanced_health_status(self):
        """Test enhanced health status reporting"""
        print("\n🏥 Testing enhanced health status...")
        
        agent = EnhancedBaseAgent(name="TestHealthAgent", port=15002)
        
        # Generate some test activity
        agent.performance_metrics.request_count = 10
        agent.performance_metrics.add_response_time(0.1)
        agent.performance_metrics.add_response_time(0.2)
        
        health_status = agent.get_health_status_enhanced()
        
        # Verify health status structure
        required_fields = ['agent_name', 'status', 'uptime', 'performance', 
                          'error_stats', 'service_info', 'config_info']
        for field in required_fields:
            self.assertIn(field, health_status)
        
        # Verify performance metrics
        self.assertIn('request_count', health_status['performance'])
        self.assertIn('avg_response_time', health_status['performance'])
        self.assertEqual(health_status['performance']['request_count'], 10)
        
        print(f"  ✅ Health status fields: {list(health_status.keys())}")
        print(f"  ✅ Performance metrics: {health_status['performance']['request_count']} requests")
        print(f"  ✅ Average response time: {health_status['performance']['avg_response_time']:.4f}s")
        
        agent.graceful_shutdown_enhanced()


class BaseAgentStressTest(unittest.TestCase):
    """Stress testing for enhanced BaseAgent"""
    
    def test_concurrent_agent_creation(self):
        """Test concurrent agent creation and performance"""
        print("\n🔥 Testing concurrent agent creation...")
        
        def create_test_agent(agent_id):
            """Create and test an agent"""
            try:
                agent = EnhancedBaseAgent(name=f"StressTestAgent{agent_id}", port=15100 + agent_id)
                time.sleep(0.1)  # Simulate some work
                agent.graceful_shutdown_enhanced()
                return True
            except Exception as e:
                return False
        
        # Create multiple agents concurrently
        threads = []
        results = []
        
        start_time = time.time()
        for i in range(10):
            thread = threading.Thread(target=lambda i=i: results.append(create_test_agent(i)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        success_count = sum(results)
        
        print(f"  📊 Created {success_count}/10 agents in {total_time:.4f}s")
        print(f"  📊 Average creation time: {total_time/10:.4f}s per agent")
        
        # Performance assertions
        self.assertEqual(success_count, 10, "All agents should be created successfully")
        self.assertLess(total_time, 5.0, "Should create 10 agents in under 5 seconds")
    
    def test_memory_usage_under_load(self):
        """Test memory usage under sustained load"""
        print("\n🧠 Testing memory usage under load...")
        
        agent = EnhancedBaseAgent(name="MemoryTestAgent", port=15200)
        
        initial_memory = agent.performance_metrics.memory_usage_mb
        
        # Simulate load by processing many requests
        for i in range(100):
            agent.performance_metrics.add_response_time(0.05)
            agent.performance_metrics.request_count += 1
            
            # Periodically update system metrics
            if i % 20 == 0:
                agent.performance_metrics.update_system_metrics()
        
        final_memory = agent.performance_metrics.memory_usage_mb
        memory_growth = final_memory - initial_memory
        
        print(f"  📊 Initial memory: {initial_memory:.2f}MB")
        print(f"  📊 Final memory: {final_memory:.2f}MB")
        print(f"  📊 Memory growth: {memory_growth:.2f}MB")
        print(f"  📊 Total requests processed: {agent.performance_metrics.request_count}")
        
        # Memory assertions (allow some growth but prevent leaks)
        self.assertLess(memory_growth, 10.0, "Memory growth should be under 10MB")
        
        agent.graceful_shutdown_enhanced()


def run_performance_validation():
    """Run comprehensive performance validation"""
    print("=" * 80)
    print("ENHANCED BASEAGENT VALIDATION FRAMEWORK")
    print("Phase 1 Week 2 Day 2 - Performance and Functionality Testing")
    print("=" * 80)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add performance tests
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(BaseAgentPerformanceTest))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(BaseAgentFunctionalityTest))
    test_suite.addTests(unittest.TestLoader().loadTestsFromTestCase(BaseAgentStressTest))
    
    # Run tests with custom runner
    class CustomTestRunner:
        def run(self, suite):
            """Custom test runner with detailed output"""
            results = {
                'tests_run': 0,
                'failures': [],
                'errors': [],
                'success_count': 0
            }
            
            start_time = time.time()
            
            for test in suite:
                test_start = time.time()
                try:
                    test.debug()  # Run the test
                    results['success_count'] += 1
                    test_time = time.time() - test_start
                    print(f"  ✅ {test._testMethodName}: PASSED ({test_time:.4f}s)")
                except Exception as e:
                    test_time = time.time() - test_start
                    print(f"  ❌ {test._testMethodName}: FAILED ({test_time:.4f}s) - {e}")
                    results['failures'].append((test._testMethodName, str(e)))
                
                results['tests_run'] += 1
            
            total_time = time.time() - start_time
            
            # Print summary
            print("\n" + "=" * 80)
            print("VALIDATION RESULTS SUMMARY")
            print("=" * 80)
            print(f"📊 Tests Run: {results['tests_run']}")
            print(f"✅ Passed: {results['success_count']}")
            print(f"❌ Failed: {len(results['failures'])}")
            print(f"⏱️  Total Time: {total_time:.4f}s")
            print(f"📈 Success Rate: {results['success_count']/results['tests_run']*100:.1f}%")
            
            if results['failures']:
                print(f"\n❌ FAILED TESTS:")
                for test_name, error in results['failures']:
                    print(f"  - {test_name}: {error}")
            
            # Save results
            results_data = {
                'timestamp': datetime.now().isoformat(),
                'validation_type': 'enhanced_baseagent',
                'summary': {
                    'tests_run': results['tests_run'],
                    'success_count': results['success_count'],
                    'failure_count': len(results['failures']),
                    'success_rate': results['success_count']/results['tests_run']*100,
                    'total_time': total_time
                },
                'failures': results['failures']
            }
            
            results_file = "phase1_week2_day2_validation_results.json"
            with open(results_file, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            print(f"\n📄 Detailed results saved to: {results_file}")
            print("\n✅ Enhanced BaseAgent Validation Complete")
            
            return results
    
    # Run the validation
    runner = CustomTestRunner()
    return runner.run(test_suite)


if __name__ == "__main__":
    run_performance_validation() 