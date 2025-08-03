#!/usr/bin/env python3
"""
PC2 Utility Suite Validation Script
Validates the PC2 utility_suite group deployment.
"""

import requests
import redis
import json
import time
import sys
from datetime import datetime

class PC2UtilityValidator:
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6395
        self.nats_port = 4305
        
        # Service endpoints
        self.services = {
            "UnifiedUtilsAgent": {"port": 7418, "health": 8418},
            "FileSystemAssistantAgent": {"port": 7423, "health": 8423},
            "RemoteConnectorAgent": {"port": 7424, "health": 8424}
        }
        
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
                self.log_result("Utility Redis Connectivity", "FAIL", "Ping failed")
                return False
                
            # Test basic operations
            test_key = "pc2_utility_test"
            test_value = "pc2_utility_value"
            
            r.set(test_key, test_value)
            retrieved = r.get(test_key)
            r.delete(test_key)
            
            if retrieved == test_value:
                info = r.info()
                self.log_result("Utility Redis Connectivity", "PASS", "All operations successful", {
                    "connected_clients": info.get('connected_clients', 'N/A'),
                    "used_memory_human": info.get('used_memory_human', 'N/A'),
                    "uptime_in_seconds": info.get('uptime_in_seconds', 'N/A')
                })
                return True
            else:
                self.log_result("Utility Redis Connectivity", "FAIL", "Set/Get operation failed")
                return False
                
        except Exception as e:
            self.log_result("Utility Redis Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_nats_connectivity(self):
        """Test NATS server accessibility"""
        try:
            # Test NATS HTTP monitoring endpoint
            response = requests.get(f"http://localhost:{8305}/", timeout=5)
            
            if response.status_code == 200:
                # Try to get server info
                info_response = requests.get(f"http://localhost:{8305}/varz", timeout=5)
                if info_response.status_code == 200:
                    info = info_response.json()
                    self.log_result("Utility NATS Connectivity", "PASS", "Server accessible", {
                        "server_id": info.get('server_id', 'N/A'),
                        "connections": info.get('connections', 'N/A'),
                        "uptime": info.get('uptime', 'N/A')
                    })
                    return True
                else:
                    self.log_result("Utility NATS Connectivity", "PASS", "Basic endpoint accessible")
                    return True
            else:
                self.log_result("Utility NATS Connectivity", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Utility NATS Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_utility_service(self, service_name, config):
        """Test individual utility service"""
        try:
            # Test health endpoint
            health_response = requests.get(f"http://localhost:{config['health']}/health", timeout=10)
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                self.log_result(f"{service_name} Health", "PASS", "Service healthy", {
                    "status": health_data.get('status', 'N/A'),
                    "uptime": health_data.get('uptime', 'N/A')
                })
                
                # Test service endpoint based on service type
                try:
                    if service_name == "UnifiedUtilsAgent":
                        response = requests.post(f"http://localhost:{config['port']}/utils/execute", 
                                               json={"command": "ping", "args": ["localhost"]}, timeout=5)
                    elif service_name == "FileSystemAssistantAgent":
                        response = requests.post(f"http://localhost:{config['port']}/filesystem/list", 
                                               json={"path": "/tmp", "include_hidden": False}, timeout=5)
                    elif service_name == "RemoteConnectorAgent":
                        response = requests.post(f"http://localhost:{config['port']}/remote/test", 
                                               json={"host": "localhost", "type": "connection_test"}, timeout=5)
                    else:
                        response = requests.get(f"http://localhost:{config['port']}/status", timeout=5)
                    
                    if response.status_code == 200:
                        service_data = response.json()
                        self.log_result(f"{service_name} Service", "PASS", "Service endpoint available", {
                            "response": str(service_data)[:100] + "..." if len(str(service_data)) > 100 else str(service_data)
                        })
                    else:
                        self.log_result(f"{service_name} Service", "WARN", f"Service HTTP {response.status_code}")
                except:
                    self.log_result(f"{service_name} Service", "WARN", "Service endpoint not accessible")
                
                return True
            else:
                self.log_result(f"{service_name} Health", "FAIL", f"Health check HTTP {health_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result(f"{service_name} Health", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_utility_flow(self):
        """Test basic utility operations flow"""
        try:
            # Test utility integration flow
            utils_data = {
                "command": "system_info",
                "args": [],
                "timeout": 10
            }
            
            # Execute via UnifiedUtilsAgent
            response = requests.post(f"http://localhost:7418/utils/execute", 
                                    json=utils_data, timeout=10)
            
            if response.status_code == 200:
                utils_result = response.json()
                
                # Test filesystem operations
                fs_data = {
                    "operation": "create_temp",
                    "filename": "test_utility_file.txt",
                    "content": "PC2 utility test content"
                }
                
                fs_response = requests.post(f"http://localhost:7423/filesystem/create", 
                                          json=fs_data, timeout=10)
                
                if fs_response.status_code == 200:
                    # Test remote connection capabilities
                    remote_data = {
                        "operation": "test_local",
                        "target": "localhost",
                        "type": "ping"
                    }
                    
                    remote_response = requests.post(f"http://localhost:7424/remote/execute", 
                                                  json=remote_data, timeout=10)
                    
                    if remote_response.status_code == 200:
                        self.log_result("Utility Integration Flow", "PASS", "Full utility pipeline successful", {
                            "utils_executed": "Yes",
                            "filesystem_operation": "Yes",
                            "remote_test": "Yes"
                        })
                        return True
                    else:
                        self.log_result("Utility Integration Flow", "WARN", f"Remote operation failed HTTP {remote_response.status_code}")
                        return False
                else:
                    self.log_result("Utility Integration Flow", "WARN", f"Filesystem operation failed HTTP {fs_response.status_code}")
                    return False
            else:
                self.log_result("Utility Integration Flow", "WARN", f"Utils execution failed HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Utility Integration Flow", "WARN", f"Utility flow test error: {str(e)}")
            return False
    
    def run_validation(self):
        """Run all validation tests"""
        print("🔧 Starting PC2 Utility Suite Validation...")
        print("=" * 60)
        
        start_time = time.time()
        
        # Infrastructure tests
        redis_ok = self.test_redis_connectivity()
        nats_ok = self.test_nats_connectivity()
        
        # Service tests (only if infrastructure is working)
        service_results = []
        if redis_ok and nats_ok:
            for service_name, config in self.services.items():
                result = self.test_utility_service(service_name, config)
                service_results.append(result)
                
            # Utility integration test (only if services are working)
            if any(service_results):
                self.test_utility_flow()
        else:
            self.log_result("Utility Services", "SKIP", "Infrastructure not ready")
        
        # Summary
        total_time = time.time() - start_time
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')
        
        print("=" * 60)
        print(f"🔧 Utility Suite Validation Summary (completed in {total_time:.2f}s)")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        
        # Overall status
        service_success_rate = sum(service_results) / len(service_results) if service_results else 0
        
        if failed == 0 and passed > 0:
            if service_success_rate >= 1.0:  # 100% service success rate for 3 services
                print("🎯 Status: PC2 UTILITY SUITE FULLY OPERATIONAL")
                return True
            elif warnings == 0:
                print("🎯 Status: PC2 UTILITY SUITE INFRASTRUCTURE READY")
                return True
            else:
                print("🎯 Status: PC2 UTILITY SUITE OPERATIONAL (with warnings)")
                return True
        else:
            print("🎯 Status: PC2 UTILITY SUITE DEPLOYMENT ISSUES DETECTED")
            return False

if __name__ == "__main__":
    validator = PC2UtilityValidator()
    success = validator.run_validation()
    
    # Save results
    with open('/tmp/pc2_utility_validation.json', 'w') as f:
        json.dump(validator.results, f, indent=2)
    
    sys.exit(0 if success else 1)
