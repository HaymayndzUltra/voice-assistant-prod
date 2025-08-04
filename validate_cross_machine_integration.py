#!/usr/bin/env python3

"""
Cross-Machine Integration Validator
Validates Main PC ↔ PC2 integration across different machines
"""

import requests
import socket
import time
import json
from datetime import datetime

class CrossMachineValidator:
    def __init__(self):
        # Main PC services (localhost)
        self.mainpc_services = {
            'coordination': 'http://localhost:6379',
            'translation': 'http://localhost:5584',
            'speech_gpu': 'http://localhost:6387', 
            'language_stack': 'http://localhost:6385',
            'memory_stack': 'http://localhost:6381',
            'observability': 'http://localhost:9000'
        }
        
        # PC2 services (remote machine)
        self.pc2_host = "192.168.100.17"  # PC2 machine IP
        self.mainpc_host = "192.168.100.16"  # Main PC IP
        self.pc2_services = {
            'infra_core': f'http://{self.pc2_host}:9210',
            'memory_stack': f'http://{self.pc2_host}:6391', 
            'async_pipeline': f'http://{self.pc2_host}:6392',
            'tutoring_cpu': f'http://{self.pc2_host}:6393',
            'vision_dream_gpu': f'http://{self.pc2_host}:6394',
            'utility_suite': f'http://{self.pc2_host}:6395',
            'web_interface': f'http://{self.pc2_host}:6396'
        }

    def test_network_connectivity(self):
        """Test basic network connectivity to PC2 machine"""
        print("🌐 TESTING NETWORK CONNECTIVITY")
        print("=" * 50)
        
        results = {}
        for service, url in self.pc2_services.items():
            try:
                # Extract host and port
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                host, port = parsed.hostname, parsed.port or 80
                
                # Test socket connectivity
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                sock.close()
                
                if result == 0:
                    print(f"   ✅ {service}: {host}:{port} - REACHABLE")
                    results[service] = True
                else:
                    print(f"   ❌ {service}: {host}:{port} - UNREACHABLE")
                    results[service] = False
                    
            except Exception as e:
                print(f"   ❌ {service}: ERROR - {str(e)}")
                results[service] = False
        
        success_rate = (sum(results.values()) / len(results)) * 100
        print(f"\n📊 Network Connectivity: {success_rate:.1f}% ({sum(results.values())}/{len(results)})")
        return results

    def test_main_pc_health(self):
        """Verify Main PC services are still healthy"""
        print("\n🏠 TESTING MAIN PC HEALTH")
        print("=" * 50)
        
        healthy_count = 0
        total_count = len(self.mainpc_services)
        
        for service, url in self.mainpc_services.items():
            try:
                # Try Redis ping for Redis services
                if 'redis' in url or ':6379' in url or ':6381' in url or ':6384' in url or ':6385' in url or ':6387' in url:
                    import redis
                    port = int(url.split(':')[-1])
                    r = redis.Redis(host='localhost', port=port, socket_timeout=2)
                    r.ping()
                    print(f"   ✅ {service}: Redis HEALTHY")
                    healthy_count += 1
                # Try HTTP health check for HTTP services
                else:
                    resp = requests.get(f"{url}/health", timeout=3)
                    if resp.status_code == 200:
                        print(f"   ✅ {service}: HTTP HEALTHY")
                        healthy_count += 1
                    else:
                        print(f"   ⚠️ {service}: HTTP {resp.status_code}")
                        
            except Exception as e:
                print(f"   ❌ {service}: UNHEALTHY - {str(e)}")
        
        success_rate = (healthy_count / total_count) * 100
        print(f"\n📊 Main PC Health: {success_rate:.1f}% ({healthy_count}/{total_count})")
        return success_rate

    def test_cross_machine_communication(self):
        """Test actual communication between Main PC and PC2"""
        print("\n🔄 TESTING CROSS-MACHINE COMMUNICATION")
        print("=" * 50)
        
        # Test 1: Main PC → PC2 Redis connectivity
        try:
            import redis
            pc2_redis = redis.Redis(host=self.pc2_host, port=6390, socket_timeout=3)  # PC2 infra redis
            pc2_redis.set("mainpc_test", "hello_from_mainpc")
            result = pc2_redis.get("mainpc_test")
            if result == b"hello_from_mainpc":
                print("   ✅ Main PC → PC2 Redis: SUCCESS")
                communication_success = True
            else:
                print("   ❌ Main PC → PC2 Redis: FAILED")
                communication_success = False
        except Exception as e:
            print(f"   ❌ Main PC → PC2 Redis: ERROR - {str(e)}")
            communication_success = False

        # Test 2: Cross-machine observability
        try:
            # Send test metric to PC2 ObservabilityHub
            pc2_obs_url = f"http://{self.pc2_host}:9210/metrics"
            test_data = {
                "source": "mainpc",
                "timestamp": datetime.now().isoformat(),
                "test_metric": "cross_machine_validation"
            }
            resp = requests.post(pc2_obs_url, json=test_data, timeout=5)
            if resp.status_code in [200, 201, 202]:
                print("   ✅ Main PC → PC2 ObservabilityHub: SUCCESS")
                obs_success = True
            else:
                print(f"   ❌ Main PC → PC2 ObservabilityHub: HTTP {resp.status_code}")
                obs_success = False
        except Exception as e:
            print(f"   ❌ Main PC → PC2 ObservabilityHub: ERROR - {str(e)}")
            obs_success = False

        overall_success = communication_success and obs_success
        success_rate = ((communication_success + obs_success) / 2) * 100
        print(f"\n📊 Cross-Machine Communication: {success_rate:.1f}% (2/2 tests)")
        return overall_success

    def run_integration_test(self):
        """Run complete cross-machine integration test"""
        print("🚀 CROSS-MACHINE INTEGRATION TESTING")
        print("=" * 60)
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🖥️ Main PC: localhost")
        print(f"🖥️ PC2: {self.pc2_host}")
        
        # Test sequence
        mainpc_health = self.test_main_pc_health()
        network_results = self.test_network_connectivity()
        communication_success = self.test_cross_machine_communication()
        
        # Overall assessment
        print("\n🏆 INTEGRATION ASSESSMENT")
        print("=" * 50)
        
        network_success_rate = (sum(network_results.values()) / len(network_results)) * 100
        
        print(f"📊 Main PC Health: {mainpc_health:.1f}%")
        print(f"📊 Network Connectivity: {network_success_rate:.1f}%")
        print(f"📊 Cross-Machine Communication: {'✅ SUCCESS' if communication_success else '❌ FAILED'}")
        
        overall_success = mainpc_health >= 80 and network_success_rate >= 70 and communication_success
        
        if overall_success:
            print("\n🎉 CROSS-MACHINE INTEGRATION: SUCCESS!")
            print("✅ Ready for Production Cross-Machine Deployment")
        else:
            print("\n❌ CROSS-MACHINE INTEGRATION: NEEDS WORK")
            print("🔧 Issues need resolution before production deployment")
        
        return overall_success

if __name__ == "__main__":
    validator = CrossMachineValidator()
    success = validator.run_integration_test()
    exit(0 if success else 1)
