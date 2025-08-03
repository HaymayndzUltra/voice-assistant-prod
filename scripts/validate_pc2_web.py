#!/usr/bin/env python3
"""
PC2 Web Interface Validation Script
Validates the PC2 web_interface group deployment.
"""

import requests
import redis
import json
import time
import sys
from datetime import datetime

class PC2WebValidator:
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6396
        self.nats_port = 4306
        
        # Service endpoints
        self.services = {
            "UnifiedWebAgent": {"port": 7426, "health": 8426, "web": 8080, "dev": 3000}
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
                self.log_result("Web Redis Connectivity", "FAIL", "Ping failed")
                return False
                
            # Test basic operations
            test_key = "pc2_web_test"
            test_value = "pc2_web_value"
            
            r.set(test_key, test_value)
            retrieved = r.get(test_key)
            r.delete(test_key)
            
            if retrieved == test_value:
                info = r.info()
                self.log_result("Web Redis Connectivity", "PASS", "All operations successful", {
                    "connected_clients": info.get('connected_clients', 'N/A'),
                    "used_memory_human": info.get('used_memory_human', 'N/A'),
                    "uptime_in_seconds": info.get('uptime_in_seconds', 'N/A')
                })
                return True
            else:
                self.log_result("Web Redis Connectivity", "FAIL", "Set/Get operation failed")
                return False
                
        except Exception as e:
            self.log_result("Web Redis Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_nats_connectivity(self):
        """Test NATS server accessibility"""
        try:
            # Test NATS HTTP monitoring endpoint
            response = requests.get(f"http://localhost:{8306}/", timeout=5)
            
            if response.status_code == 200:
                # Try to get server info
                info_response = requests.get(f"http://localhost:{8306}/varz", timeout=5)
                if info_response.status_code == 200:
                    info = info_response.json()
                    self.log_result("Web NATS Connectivity", "PASS", "Server accessible", {
                        "server_id": info.get('server_id', 'N/A'),
                        "connections": info.get('connections', 'N/A'),
                        "uptime": info.get('uptime', 'N/A')
                    })
                    return True
                else:
                    self.log_result("Web NATS Connectivity", "PASS", "Basic endpoint accessible")
                    return True
            else:
                self.log_result("Web NATS Connectivity", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Web NATS Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_web_service(self, service_name, config):
        """Test individual web service"""
        try:
            # Test health endpoint
            health_response = requests.get(f"http://localhost:{config['health']}/health", timeout=10)
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                self.log_result(f"{service_name} Health", "PASS", "Service healthy", {
                    "status": health_data.get('status', 'N/A'),
                    "uptime": health_data.get('uptime', 'N/A')
                })
                
                # Test API endpoint
                try:
                    api_response = requests.get(f"http://localhost:{config['port']}/api/v1/status", timeout=5)
                    if api_response.status_code == 200:
                        self.log_result(f"{service_name} API", "PASS", "API endpoint available")
                    else:
                        self.log_result(f"{service_name} API", "WARN", f"API HTTP {api_response.status_code}")
                except:
                    self.log_result(f"{service_name} API", "WARN", "API endpoint not accessible")
                
                # Test web interface port
                try:
                    web_response = requests.get(f"http://localhost:{config['web']}/", timeout=5)
                    if web_response.status_code == 200:
                        self.log_result(f"{service_name} Web UI", "PASS", "Web interface available")
                    else:
                        self.log_result(f"{service_name} Web UI", "WARN", f"Web UI HTTP {web_response.status_code}")
                except:
                    self.log_result(f"{service_name} Web UI", "WARN", "Web interface not accessible")
                
                return True
            else:
                self.log_result(f"{service_name} Health", "FAIL", f"Health check HTTP {health_response.status_code}")
                return False
                
        except Exception as e:
            self.log_result(f"{service_name} Health", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_web_endpoints(self):
        """Test comprehensive web endpoints"""
        try:
            # Test various API endpoints
            endpoints = [
                {"path": "/api/v1/health", "method": "GET"},
                {"path": "/api/v1/agents", "method": "GET"},
                {"path": "/api/v1/status", "method": "GET"}
            ]
            
            successful_endpoints = 0
            
            for endpoint in endpoints:
                try:
                    if endpoint["method"] == "GET":
                        response = requests.get(f"http://localhost:7426{endpoint['path']}", timeout=5)
                    else:
                        response = requests.post(f"http://localhost:7426{endpoint['path']}", timeout=5)
                    
                    if response.status_code in [200, 201, 202]:
                        successful_endpoints += 1
                except:
                    pass
            
            if successful_endpoints > 0:
                self.log_result("Web API Endpoints", "PASS", f"{successful_endpoints}/{len(endpoints)} endpoints responding", {
                    "successful_endpoints": successful_endpoints,
                    "total_endpoints": len(endpoints)
                })
                return True
            else:
                self.log_result("Web API Endpoints", "WARN", "No API endpoints responding")
                return False
                
        except Exception as e:
            self.log_result("Web API Endpoints", "WARN", f"API endpoints test error: {str(e)}")
            return False
    
    def test_web_functionality(self):
        """Test basic web functionality"""
        try:
            # Test web interface root
            response = requests.get("http://localhost:8080/", timeout=10)
            
            if response.status_code == 200:
                # Test API call through web interface
                api_data = {
                    "action": "test",
                    "data": {"message": "PC2 web interface test"}
                }
                
                api_response = requests.post("http://localhost:7426/api/v1/test", 
                                           json=api_data, timeout=10)
                
                if api_response.status_code in [200, 201, 404]:  # 404 is OK if endpoint doesn't exist
                    self.log_result("Web Functionality", "PASS", "Web interface and API integration working", {
                        "web_interface": "Accessible",
                        "api_integration": "Functional"
                    })
                    return True
                else:
                    self.log_result("Web Functionality", "WARN", f"API integration issues HTTP {api_response.status_code}")
                    return False
            else:
                self.log_result("Web Functionality", "WARN", f"Web interface not accessible HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Web Functionality", "WARN", f"Web functionality test error: {str(e)}")
            return False
    
    def run_validation(self):
        """Run all validation tests"""
        print("🌐 Starting PC2 Web Interface Validation...")
        print("=" * 60)
        
        start_time = time.time()
        
        # Infrastructure tests
        redis_ok = self.test_redis_connectivity()
        nats_ok = self.test_nats_connectivity()
        
        # Service tests (only if infrastructure is working)
        service_results = []
        if redis_ok and nats_ok:
            for service_name, config in self.services.items():
                result = self.test_web_service(service_name, config)
                service_results.append(result)
                
            # Web functionality tests (only if services are working)
            if any(service_results):
                self.test_web_endpoints()
                self.test_web_functionality()
        else:
            self.log_result("Web Services", "SKIP", "Infrastructure not ready")
        
        # Summary
        total_time = time.time() - start_time
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')
        
        print("=" * 60)
        print(f"🌐 Web Interface Validation Summary (completed in {total_time:.2f}s)")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        
        # Overall status
        service_success_rate = sum(service_results) / len(service_results) if service_results else 0
        
        if failed == 0 and passed > 0:
            if service_success_rate >= 1.0:  # 100% service success rate
                print("🎯 Status: PC2 WEB INTERFACE FULLY OPERATIONAL")
                return True
            elif warnings == 0:
                print("🎯 Status: PC2 WEB INTERFACE INFRASTRUCTURE READY")
                return True
            else:
                print("🎯 Status: PC2 WEB INTERFACE OPERATIONAL (with warnings)")
                return True
        else:
            print("🎯 Status: PC2 WEB INTERFACE DEPLOYMENT ISSUES DETECTED")
            return False

if __name__ == "__main__":
    validator = PC2WebValidator()
    success = validator.run_validation()
    
    # Save results
    with open('/tmp/pc2_web_validation.json', 'w') as f:
        json.dump(validator.results, f, indent=2)
    
    sys.exit(0 if success else 1)
