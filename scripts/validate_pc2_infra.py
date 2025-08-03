#!/usr/bin/env python3
"""
PC2 Infrastructure Validation Script
Validates the PC2 infra_core group deployment.
"""

import requests
import redis
import json
import time
import sys
from datetime import datetime

class PC2InfraValidator:
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6390
        self.nats_port = 4300
        self.obs_hub_port = 9200
        self.resource_mgr_port = 7213
        self.results = []
        
    def log_result(self, test_name, status, message="", details=None):
        """Log test result"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "status": status,
            "message": message,
            "details": details or {}
        }
        self.results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {message}")
        
        if details:
            for key, value in details.items():
                print(f"   └─ {key}: {value}")
    
    def test_redis_connectivity(self):
        """Test Redis connection and basic operations"""
        try:
            r = redis.Redis(host=self.redis_host, port=self.redis_port, decode_responses=True)
            
            # Test connection
            ping_result = r.ping()
            if not ping_result:
                self.log_result("Redis Connectivity", "FAIL", "Ping failed")
                return False
                
            # Test basic operations
            test_key = "pc2_test_key"
            test_value = "pc2_test_value"
            
            r.set(test_key, test_value)
            retrieved = r.get(test_key)
            r.delete(test_key)
            
            if retrieved == test_value:
                info = r.info()
                self.log_result("Redis Connectivity", "PASS", "All operations successful", {
                    "connected_clients": info.get('connected_clients', 'N/A'),
                    "used_memory_human": info.get('used_memory_human', 'N/A'),
                    "uptime_in_seconds": info.get('uptime_in_seconds', 'N/A')
                })
                return True
            else:
                self.log_result("Redis Connectivity", "FAIL", "Set/Get operation failed")
                return False
                
        except Exception as e:
            self.log_result("Redis Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_nats_connectivity(self):
        """Test NATS server accessibility"""
        try:
            # Test NATS HTTP monitoring endpoint
            response = requests.get(f"http://localhost:{8300}/", timeout=5)
            
            if response.status_code == 200:
                # Try to get server info
                info_response = requests.get(f"http://localhost:{8300}/varz", timeout=5)
                if info_response.status_code == 200:
                    info = info_response.json()
                    self.log_result("NATS Connectivity", "PASS", "Server accessible", {
                        "server_id": info.get('server_id', 'N/A'),
                        "connections": info.get('connections', 'N/A'),
                        "uptime": info.get('uptime', 'N/A')
                    })
                    return True
                else:
                    self.log_result("NATS Connectivity", "PASS", "Basic endpoint accessible")
                    return True
            else:
                self.log_result("NATS Connectivity", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("NATS Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_observability_hub(self):
        """Test ObservabilityHub service"""
        try:
            # Test health endpoint
            health_response = requests.get(f"http://localhost:{9210}/health", timeout=10)
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                self.log_result("ObservabilityHub Health", "PASS", "Service healthy", {
                    "status": health_data.get('status', 'N/A'),
                    "uptime": health_data.get('uptime', 'N/A')
                })
                
                # Test metrics endpoint
                try:
                    metrics_response = requests.get(f"http://localhost:{9200}/metrics", timeout=5)
                    if metrics_response.status_code == 200:
                        metrics_count = len(metrics_response.text.strip().split('\n'))
                        self.log_result("ObservabilityHub Metrics", "PASS", f"Metrics available", {
                            "metrics_lines": metrics_count
                        })
                    else:
                        self.log_result("ObservabilityHub Metrics", "WARN", f"Metrics HTTP {metrics_response.status_code}")
                except:
                    self.log_result("ObservabilityHub Metrics", "WARN", "Metrics endpoint not accessible")
                
                return True
            else:
                self.log_result("ObservabilityHub Health", "FAIL", f"Health check HTTP {health_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("ObservabilityHub Health", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_resource_manager(self):
        """Test ResourceManager service"""
        try:
            # Test health endpoint
            health_response = requests.get(f"http://localhost:{8213}/health", timeout=10)
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                self.log_result("ResourceManager Health", "PASS", "Service healthy", {
                    "status": health_data.get('status', 'N/A'),
                    "uptime": health_data.get('uptime', 'N/A')
                })
                
                # Test resources endpoint
                try:
                    resources_response = requests.get(f"http://localhost:{7213}/resources", timeout=5)
                    if resources_response.status_code == 200:
                        resources_data = resources_response.json()
                        self.log_result("ResourceManager Resources", "PASS", "Resources endpoint available", {
                            "status": resources_data.get('status', 'N/A')
                        })
                    else:
                        self.log_result("ResourceManager Resources", "WARN", f"Resources HTTP {resources_response.status_code}")
                except:
                    self.log_result("ResourceManager Resources", "WARN", "Resources endpoint not accessible")
                
                return True
            else:
                self.log_result("ResourceManager Health", "FAIL", f"Health check HTTP {health_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("ResourceManager Health", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def run_validation(self):
        """Run all validation tests"""
        print("🚀 Starting PC2 Infrastructure Validation...")
        print("=" * 50)
        
        start_time = time.time()
        
        # Infrastructure tests
        redis_ok = self.test_redis_connectivity()
        nats_ok = self.test_nats_connectivity()
        
        # Application tests (only if infrastructure is working)
        obs_ok = False
        rm_ok = False
        
        if redis_ok and nats_ok:
            obs_ok = self.test_observability_hub()
            rm_ok = self.test_resource_manager()
        else:
            self.log_result("Application Tests", "SKIP", "Infrastructure not ready")
        
        # Summary
        total_time = time.time() - start_time
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')
        
        print("=" * 50)
        print(f"📊 Validation Summary (completed in {total_time:.2f}s)")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        
        # Overall status
        if failed == 0 and passed > 0:
            if warnings == 0:
                print("🎯 Status: PC2 INFRA CORE FULLY OPERATIONAL")
                return True
            else:
                print("🎯 Status: PC2 INFRA CORE OPERATIONAL (with warnings)")
                return True
        else:
            print("🎯 Status: PC2 INFRA CORE DEPLOYMENT ISSUES DETECTED")
            return False

if __name__ == "__main__":
    validator = PC2InfraValidator()
    success = validator.run_validation()
    
    # Save results
    with open('/tmp/pc2_infra_validation.json', 'w') as f:
        json.dump(validator.results, f, indent=2)
    
    sys.exit(0 if success else 1)
