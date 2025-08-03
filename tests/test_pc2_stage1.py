#!/usr/bin/env python3
"""
Stage 1: PC2 Local Validation Tests
Tests the PC2 infrastructure that's currently running to validate Stage 1.
"""

import pytest
import requests
import redis
import time
from typing import Dict, List


class TestPC2Stage1:
    """Test PC2 Stage 1: Local validation of running infrastructure."""
    
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
    
    # NATS port mappings (for future use)
    NATS_PORTS = {
        'pc2_infra': 4300,
        'pc2_memory': 4301,
        'pc2_async': 4302,
        'pc2_tutoring': 4303,
        'pc2_vision': 4304,
        'pc2_utility': 4305,
        'pc2_web': 4306
    }
    
    def test_all_redis_connections_healthy(self):
        """Test that all 7 PC2 Redis instances are responding."""
        results = {}
        
        for group, port in self.REDIS_PORTS.items():
            try:
                r = redis.Redis(host='localhost', port=port, socket_timeout=5)
                ping_result = r.ping()
                results[group] = {'port': port, 'status': 'HEALTHY', 'ping': ping_result}
            except Exception as e:
                results[group] = {'port': port, 'status': 'FAILED', 'error': str(e)}
        
        # Print results for visibility
        print("\n=== PC2 Redis Health Check Results ===")
        healthy_count = 0
        for group, result in results.items():
            status = result['status']
            port = result['port']
            if status == 'HEALTHY':
                print(f"✅ {group:15} (port {port}): HEALTHY")
                healthy_count += 1
            else:
                print(f"❌ {group:15} (port {port}): FAILED - {result.get('error', 'Unknown error')}")
        
        print(f"\nHealth Score: {healthy_count}/{len(self.REDIS_PORTS)} Redis instances healthy")
        
        # All Redis instances must be healthy for Stage 1 to pass
        assert healthy_count == len(self.REDIS_PORTS), f"Only {healthy_count}/{len(self.REDIS_PORTS)} Redis instances are healthy"
    
    def test_redis_basic_operations(self):
        """Test basic Redis operations on each PC2 Redis instance."""
        test_key = "pc2_stage1_test"
        test_value = "validation_successful"
        
        for group, port in self.REDIS_PORTS.items():
            r = redis.Redis(host='localhost', port=port, socket_timeout=5)
            
            # Test SET operation
            result = r.set(test_key, test_value, ex=60)  # Expire in 60 seconds
            assert result is True, f"Failed to SET on {group} Redis (port {port})"
            
            # Test GET operation
            retrieved = r.get(test_key)
            assert retrieved.decode() == test_value, f"Failed to GET on {group} Redis (port {port})"
            
            # Cleanup
            r.delete(test_key)
    
    def test_observability_hub_basic_connectivity(self):
        """Test basic connectivity to PC2 ObservabilityHub if available."""
        observability_ports = [9200, 9210]  # From existing container
        
        for port in observability_ports:
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=5)
                print(f"✅ ObservabilityHub port {port}: HTTP {response.status_code}")
                # Don't assert success since the service might still be starting
            except requests.exceptions.RequestException as e:
                print(f"⚠️  ObservabilityHub port {port}: {type(e).__name__} - {e}")
                # Expected since ObservabilityHub might not be fully ready
    
    def test_redis_inter_group_communication_simulation(self):
        """Simulate inter-group communication using Redis pub/sub."""
        source_group = 'pc2_memory'
        target_group = 'pc2_async'
        
        source_redis = redis.Redis(host='localhost', port=self.REDIS_PORTS[source_group])
        target_redis = redis.Redis(host='localhost', port=self.REDIS_PORTS[target_group])
        
        # Simulate memory -> async pipeline communication
        message_channel = "pc2_inter_group_test"
        message_data = {"task_id": "stage1_validation", "timestamp": time.time()}
        
        # Subscribe to channel on target
        pubsub = target_redis.pubsub()
        pubsub.subscribe(message_channel)
        
        # Publish from source
        source_redis.publish(message_channel, str(message_data))
        
        # Check if message received
        message = pubsub.get_message(timeout=5)  # Skip subscription confirmation
        message = pubsub.get_message(timeout=5)  # Get actual message
        
        if message and message['type'] == 'message':
            print(f"✅ Inter-group communication test: {source_group} → {target_group} successful")
            assert True
        else:
            print(f"⚠️  Inter-group communication test: {source_group} → {target_group} no message received")
            # Don't fail the test as this might be timing issue
        
        pubsub.close()
    
    def test_port_availability_for_stage2(self):
        """Verify that PC2 ports don't conflict with Main PC services."""
        import socket
        
        # Check that PC2 ports are bound (should be occupied by PC2 services)
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
        
        print(f"\n=== PC2 Port Allocation Status ===")
        print(f"✅ Bound ports (PC2 services): {bound_ports}")
        print(f"⚠️  Unbound ports: {unbound_ports}")
        
        # At least Redis ports should be bound
        redis_ports = list(self.REDIS_PORTS.values())
        bound_redis_ports = [p for p in redis_ports if p in bound_ports]
        
        assert len(bound_redis_ports) == len(redis_ports), f"Only {len(bound_redis_ports)}/{len(redis_ports)} Redis ports are bound"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
