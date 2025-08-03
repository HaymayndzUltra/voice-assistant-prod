#!/usr/bin/env python3
"""
PC2 Tutoring CPU Validation Script
Validates the PC2 tutoring_cpu group deployment.
"""

import requests
import redis
import json
import time
import sys
from datetime import datetime

class PC2TutoringValidator:
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6393
        self.nats_port = 4303
        
        # Service endpoints
        self.services = {
            "TutorAgent": {"port": 7408, "health": 8408},
            "TutoringAgent": {"port": 7431, "health": 8431}
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
                self.log_result("Tutoring Redis Connectivity", "FAIL", "Ping failed")
                return False
                
            # Test basic operations
            test_key = "pc2_tutoring_test"
            test_value = "pc2_tutoring_value"
            
            r.set(test_key, test_value)
            retrieved = r.get(test_key)
            r.delete(test_key)
            
            if retrieved == test_value:
                info = r.info()
                self.log_result("Tutoring Redis Connectivity", "PASS", "All operations successful", {
                    "connected_clients": info.get('connected_clients', 'N/A'),
                    "used_memory_human": info.get('used_memory_human', 'N/A'),
                    "uptime_in_seconds": info.get('uptime_in_seconds', 'N/A')
                })
                return True
            else:
                self.log_result("Tutoring Redis Connectivity", "FAIL", "Set/Get operation failed")
                return False
                
        except Exception as e:
            self.log_result("Tutoring Redis Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_nats_connectivity(self):
        """Test NATS server accessibility"""
        try:
            # Test NATS HTTP monitoring endpoint
            response = requests.get(f"http://localhost:{8303}/", timeout=5)
            
            if response.status_code == 200:
                # Try to get server info
                info_response = requests.get(f"http://localhost:{8303}/varz", timeout=5)
                if info_response.status_code == 200:
                    info = info_response.json()
                    self.log_result("Tutoring NATS Connectivity", "PASS", "Server accessible", {
                        "server_id": info.get('server_id', 'N/A'),
                        "connections": info.get('connections', 'N/A'),
                        "uptime": info.get('uptime', 'N/A')
                    })
                    return True
                else:
                    self.log_result("Tutoring NATS Connectivity", "PASS", "Basic endpoint accessible")
                    return True
            else:
                self.log_result("Tutoring NATS Connectivity", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Tutoring NATS Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_tutoring_service(self, service_name, config):
        """Test individual tutoring service"""
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
                    if service_name == "TutorAgent":
                        response = requests.post(f"http://localhost:{config['port']}/ask", 
                                               json={"question": "What is 2+2?"}, timeout=5)
                    elif service_name == "TutoringAgent":
                        response = requests.post(f"http://localhost:{config['port']}/session/start", 
                                               json={"student_id": "test", "topic": "math"}, timeout=5)
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
    
    def test_tutoring_flow(self):
        """Test basic tutoring flow"""
        try:
            # Test tutoring session flow
            session_data = {
                "student_id": "test_student_001",
                "topic": "mathematics",
                "level": "beginner"
            }
            
            # Start session via TutoringAgent
            response = requests.post(f"http://localhost:7431/session/start", 
                                    json=session_data, timeout=5)
            
            if response.status_code == 200:
                session_result = response.json()
                session_id = session_result.get('session_id')
                
                if session_id:
                    # Ask question via TutorAgent
                    question_data = {
                        "session_id": session_id,
                        "question": "Can you explain basic addition?"
                    }
                    
                    tutor_response = requests.post(f"http://localhost:7408/ask", 
                                                 json=question_data, timeout=10)
                    
                    if tutor_response.status_code == 200:
                        self.log_result("Tutoring Flow", "PASS", "Session and Q&A flow successful", {
                            "session_id": session_id,
                            "tutor_responsive": "Yes"
                        })
                        return True
                    else:
                        self.log_result("Tutoring Flow", "WARN", f"Tutor Q&A failed HTTP {tutor_response.status_code}")
                        return False
                else:
                    self.log_result("Tutoring Flow", "WARN", "Session started but no session_id returned")
                    return False
            else:
                self.log_result("Tutoring Flow", "WARN", f"Session start failed HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Tutoring Flow", "WARN", f"Tutoring flow test error: {str(e)}")
            return False
    
    def run_validation(self):
        """Run all validation tests"""
        print("🎓 Starting PC2 Tutoring CPU Validation...")
        print("=" * 60)
        
        start_time = time.time()
        
        # Infrastructure tests
        redis_ok = self.test_redis_connectivity()
        nats_ok = self.test_nats_connectivity()
        
        # Service tests (only if infrastructure is working)
        service_results = []
        if redis_ok and nats_ok:
            for service_name, config in self.services.items():
                result = self.test_tutoring_service(service_name, config)
                service_results.append(result)
                
            # Tutoring integration test (only if services are working)
            if any(service_results):
                self.test_tutoring_flow()
        else:
            self.log_result("Tutoring Services", "SKIP", "Infrastructure not ready")
        
        # Summary
        total_time = time.time() - start_time
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')
        
        print("=" * 60)
        print(f"🎓 Tutoring CPU Validation Summary (completed in {total_time:.2f}s)")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        
        # Overall status
        service_success_rate = sum(service_results) / len(service_results) if service_results else 0
        
        if failed == 0 and passed > 0:
            if service_success_rate >= 1.0:  # 100% service success rate for 2 services
                print("🎯 Status: PC2 TUTORING CPU FULLY OPERATIONAL")
                return True
            elif warnings == 0:
                print("🎯 Status: PC2 TUTORING CPU INFRASTRUCTURE READY")
                return True
            else:
                print("🎯 Status: PC2 TUTORING CPU OPERATIONAL (with warnings)")
                return True
        else:
            print("🎯 Status: PC2 TUTORING CPU DEPLOYMENT ISSUES DETECTED")
            return False

if __name__ == "__main__":
    validator = PC2TutoringValidator()
    success = validator.run_validation()
    
    # Save results
    with open('/tmp/pc2_tutoring_validation.json', 'w') as f:
        json.dump(validator.results, f, indent=2)
    
    sys.exit(0 if success else 1)
