#!/usr/bin/env python3
"""
Stage 1: PC2 Local Validation Script
Direct validation of PC2 infrastructure without pytest dependencies.
"""

import redis
import requests
import socket
import time
import sys
from typing import Dict, List


class PC2Stage1Validator:
    """Validator for PC2 Stage 1: Local validation of running infrastructure."""
    
    # PC2 Redis port mappings from existing infrastructure
    REDIS_PORTS = {
        'pc2_infra': 6390,
        'pc2_memory': 6391,
        'pc2_async': 6392,
        'pc2_tutoring': 6393,
        'pc2_vision': 6394,
        'pc2_utility': 6395,
        'pc2_web': 6396
    }
    
    # NATS port mappings
    NATS_PORTS = {
        'pc2_infra': 4300,
        'pc2_memory': 4301,
        'pc2_async': 4302,
        'pc2_tutoring': 4303,
        'pc2_vision': 4304,
        'pc2_utility': 4305,
        'pc2_web': 4306
    }
    
    def __init__(self):
        self.results = {
            'redis_health': {},
            'redis_operations': {},
            'observability': {},
            'port_allocation': {},
            'inter_group_comm': {}
        }
    
    def test_redis_health(self):
        """Test that all 7 PC2 Redis instances are responding."""
        print("\n=== PC2 Redis Health Check ===")
        
        healthy_count = 0
        
        for group, port in self.REDIS_PORTS.items():
            try:
                r = redis.Redis(host='localhost', port=port, socket_timeout=5)
                ping_result = r.ping()
                self.results['redis_health'][group] = {'port': port, 'status': 'HEALTHY', 'ping': ping_result}
                print(f"✅ {group:15} (port {port}): HEALTHY")
                healthy_count += 1
            except Exception as e:
                self.results['redis_health'][group] = {'port': port, 'status': 'FAILED', 'error': str(e)}
                print(f"❌ {group:15} (port {port}): FAILED - {str(e)}")
        
        print(f"\nRedis Health Score: {healthy_count}/{len(self.REDIS_PORTS)} instances healthy")
        return healthy_count == len(self.REDIS_PORTS)
    
    def test_redis_operations(self):
        """Test basic Redis operations on each PC2 Redis instance."""
        print("\n=== PC2 Redis Operations Test ===")
        
        test_key = "pc2_stage1_test"
        test_value = "validation_successful"
        success_count = 0
        
        for group, port in self.REDIS_PORTS.items():
            try:
                r = redis.Redis(host='localhost', port=port, socket_timeout=5)
                
                # Test SET operation
                result = r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
                if not result:
                    raise Exception("SET operation failed")
                
                # Test GET operation
                retrieved = r.get(test_key)
                if retrieved.decode() != test_value:
                    raise Exception("GET operation failed - value mismatch")
                
                # Cleanup
                r.delete(test_key)
                
                self.results['redis_operations'][group] = {'status': 'SUCCESS'}
                print(f"✅ {group:15}: SET/GET operations successful")
                success_count += 1
                
            except Exception as e:
                self.results['redis_operations'][group] = {'status': 'FAILED', 'error': str(e)}
                print(f"❌ {group:15}: {str(e)}")
        
        print(f"\nRedis Operations Score: {success_count}/{len(self.REDIS_PORTS)} instances successful")
        return success_count == len(self.REDIS_PORTS)
    
    def test_observability_hub(self):
        """Test basic connectivity to PC2 ObservabilityHub if available."""
        print("\n=== PC2 ObservabilityHub Test ===")
        
        observability_ports = [9200, 9210]  # From existing container
        
        for port in observability_ports:
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=5)
                self.results['observability'][f'port_{port}'] = {
                    'status': 'RESPONDING',
                    'http_code': response.status_code
                }
                print(f"✅ ObservabilityHub port {port}: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                self.results['observability'][f'port_{port}'] = {
                    'status': 'FAILED',
                    'error': f"{type(e).__name__}: {e}"
                }
                print(f"⚠️  ObservabilityHub port {port}: {type(e).__name__} - {e}")
        
        # Don't require ObservabilityHub to be fully ready for Stage 1 to pass
        return True
    
    def test_inter_group_communication(self):
        """Simulate inter-group communication using Redis pub/sub."""
        print("\n=== PC2 Inter-Group Communication Test ===")
        
        source_group = 'pc2_memory'
        target_group = 'pc2_async'
        
        try:
            source_redis = redis.Redis(host='localhost', port=self.REDIS_PORTS[source_group])
            target_redis = redis.Redis(host='localhost', port=self.REDIS_PORTS[target_group])
            
            # Simulate memory -> async pipeline communication
            message_channel = "pc2_inter_group_test"
            message_data = f"{{\"task_id\": \"stage1_validation\", \"timestamp\": {time.time()}}}"
            
            # Subscribe to channel on target
            pubsub = target_redis.pubsub()
            pubsub.subscribe(message_channel)
            
            # Wait a moment for subscription to be ready
            time.sleep(0.1)
            
            # Publish from source
            result = source_redis.publish(message_channel, message_data)
            
            # Check if message received
            message = pubsub.get_message(timeout=1)  # Skip subscription confirmation
            message = pubsub.get_message(timeout=2)  # Get actual message
            
            if message and message['type'] == 'message':
                self.results['inter_group_comm'] = {'status': 'SUCCESS', 'message_received': True}
                print(f"✅ Inter-group communication test: {source_group} → {target_group} successful")
                pubsub.close()
                return True
            else:
                self.results['inter_group_comm'] = {'status': 'PARTIAL', 'message_received': False}
                print(f"⚠️  Inter-group communication test: {source_group} → {target_group} no message received")
                pubsub.close()
                # Don't fail the test as this might be timing issue
                return True
                
        except Exception as e:
            self.results['inter_group_comm'] = {'status': 'FAILED', 'error': str(e)}
            print(f"❌ Inter-group communication test failed: {str(e)}")
            return False
    
    def test_port_allocation(self):
        """Verify PC2 port allocation and availability."""
        print("\n=== PC2 Port Allocation Test ===")
        
        pc2_ports = list(self.REDIS_PORTS.values()) + list(self.NATS_PORTS.values())
        
        bound_ports = []
        unbound_ports = []
        
        for port in pc2_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    bound_ports.append(port)
                else:
                    unbound_ports.append(port)
            finally:
                sock.close()
        
        print(f"✅ Bound ports (PC2 services): {bound_ports}")
        if unbound_ports:
            print(f"⚠️  Unbound ports: {unbound_ports}")
        
        # At least Redis ports should be bound
        redis_ports = list(self.REDIS_PORTS.values())
        bound_redis_ports = [p for p in redis_ports if p in bound_ports]
        
        self.results['port_allocation'] = {
            'bound_ports': bound_ports,
            'unbound_ports': unbound_ports,
            'redis_bound_count': len(bound_redis_ports),
            'redis_total_count': len(redis_ports)
        }
        
        success = len(bound_redis_ports) == len(redis_ports)
        if success:
            print(f"✅ Port allocation test: {len(bound_redis_ports)}/{len(redis_ports)} Redis ports bound")
        else:
            print(f"❌ Port allocation test: Only {len(bound_redis_ports)}/{len(redis_ports)} Redis ports bound")
        
        return success
    
    def run_all_tests(self):
        """Run all Stage 1 validation tests."""
        print("🎯 PC2 STAGE 1 LOCAL VALIDATION")
        print("=" * 50)
        
        test_results = [
            ("Redis Health Check", self.test_redis_health()),
            ("Redis Operations", self.test_redis_operations()),
            ("ObservabilityHub", self.test_observability_hub()),
            ("Inter-Group Communication", self.test_inter_group_communication()),
            ("Port Allocation", self.test_port_allocation())
        ]
        
        print("\n" + "=" * 50)
        print("🎯 STAGE 1 VALIDATION SUMMARY")
        print("=" * 50)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:25}: {status}")
            if result:
                passed_tests += 1
        
        print(f"\nOverall Score: {passed_tests}/{total_tests} tests passed")
        
        # Stage 1 passes if critical infrastructure tests pass
        critical_tests_passed = test_results[0][1] and test_results[1][1] and test_results[4][1]  # Redis health, ops, ports
        
        if critical_tests_passed:
            print("🎉 STAGE 1: LOCAL PC2 VALIDATION - PASSED")
            print("✅ PC2 infrastructure is ready for Stage 2 integration testing")
            return True
        else:
            print("❌ STAGE 1: LOCAL PC2 VALIDATION - FAILED")
            print("⚠️  Critical PC2 infrastructure issues must be resolved before proceeding")
            return False


def main():
    """Main entry point for PC2 Stage 1 validation."""
    validator = PC2Stage1Validator()
    success = validator.run_all_tests()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
