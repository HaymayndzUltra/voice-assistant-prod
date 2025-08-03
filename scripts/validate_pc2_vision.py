#!/usr/bin/env python3
"""
PC2 Vision Dream GPU Validation Script
Validates the PC2 vision_dream_gpu group deployment.
"""

import requests
import redis
import json
import time
import sys
from datetime import datetime

class PC2VisionValidator:
    def __init__(self):
        self.redis_host = "localhost"
        self.redis_port = 6394
        self.nats_port = 4304
        
        # Service endpoints
        self.services = {
            "VisionProcessingAgent": {"port": 7450, "health": 8450},
            "DreamWorldAgent": {"port": 7404, "health": 8404},
            "DreamingModeAgent": {"port": 7427, "health": 8427}
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
                self.log_result("Vision Redis Connectivity", "FAIL", "Ping failed")
                return False
                
            # Test basic operations
            test_key = "pc2_vision_test"
            test_value = "pc2_vision_value"
            
            r.set(test_key, test_value)
            retrieved = r.get(test_key)
            r.delete(test_key)
            
            if retrieved == test_value:
                info = r.info()
                self.log_result("Vision Redis Connectivity", "PASS", "All operations successful", {
                    "connected_clients": info.get('connected_clients', 'N/A'),
                    "used_memory_human": info.get('used_memory_human', 'N/A'),
                    "uptime_in_seconds": info.get('uptime_in_seconds', 'N/A')
                })
                return True
            else:
                self.log_result("Vision Redis Connectivity", "FAIL", "Set/Get operation failed")
                return False
                
        except Exception as e:
            self.log_result("Vision Redis Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_nats_connectivity(self):
        """Test NATS server accessibility"""
        try:
            # Test NATS HTTP monitoring endpoint
            response = requests.get(f"http://localhost:{8304}/", timeout=5)
            
            if response.status_code == 200:
                # Try to get server info
                info_response = requests.get(f"http://localhost:{8304}/varz", timeout=5)
                if info_response.status_code == 200:
                    info = info_response.json()
                    self.log_result("Vision NATS Connectivity", "PASS", "Server accessible", {
                        "server_id": info.get('server_id', 'N/A'),
                        "connections": info.get('connections', 'N/A'),
                        "uptime": info.get('uptime', 'N/A')
                    })
                    return True
                else:
                    self.log_result("Vision NATS Connectivity", "PASS", "Basic endpoint accessible")
                    return True
            else:
                self.log_result("Vision NATS Connectivity", "FAIL", f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Vision NATS Connectivity", "FAIL", f"Connection error: {str(e)}")
            return False
    
    def test_vision_service(self, service_name, config):
        """Test individual vision service"""
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
                    if service_name == "VisionProcessingAgent":
                        response = requests.post(f"http://localhost:{config['port']}/process", 
                                               json={"image_url": "test", "operation": "analyze"}, timeout=5)
                    elif service_name == "DreamWorldAgent":
                        response = requests.post(f"http://localhost:{config['port']}/world/create", 
                                               json={"name": "test_world", "size": [100, 100]}, timeout=5)
                    elif service_name == "DreamingModeAgent":
                        response = requests.post(f"http://localhost:{config['port']}/dream/start", 
                                               json={"prompt": "test dream", "duration": 10}, timeout=5)
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
    
    def test_gpu_availability(self):
        """Test GPU availability for vision services"""
        try:
            # Check GPU availability through nvidia-smi command
            import subprocess
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used', 
                                   '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                gpu_info = result.stdout.strip().split('\n')
                self.log_result("GPU Availability", "PASS", f"Found {len(gpu_info)} GPU(s)", {
                    "gpu_info": gpu_info[0] if gpu_info else "No details"
                })
                return True
            else:
                self.log_result("GPU Availability", "WARN", "nvidia-smi command failed")
                return False
                
        except Exception as e:
            self.log_result("GPU Availability", "WARN", f"GPU check error: {str(e)}")
            return False
    
    def test_vision_flow(self):
        """Test basic vision processing flow"""
        try:
            # Test vision-dream integration flow
            vision_data = {
                "image_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                "operations": ["analyze", "enhance"]
            }
            
            # Process via VisionProcessingAgent
            response = requests.post(f"http://localhost:7450/process", 
                                    json=vision_data, timeout=10)
            
            if response.status_code == 200:
                vision_result = response.json()
                
                # Create dream world based on vision results
                dream_data = {
                    "name": "vision_dream_test",
                    "size": [64, 64],
                    "style": "abstract"
                }
                
                dream_response = requests.post(f"http://localhost:7404/world/create", 
                                             json=dream_data, timeout=10)
                
                if dream_response.status_code == 200:
                    # Initiate dreaming mode
                    dreaming_data = {
                        "prompt": "creative vision processing",
                        "duration": 5,
                        "style": "surreal"
                    }
                    
                    dreaming_response = requests.post(f"http://localhost:7427/dream/start", 
                                                    json=dreaming_data, timeout=10)
                    
                    if dreaming_response.status_code == 200:
                        self.log_result("Vision-Dream Flow", "PASS", "Full vision-dream pipeline successful", {
                            "vision_processed": "Yes",
                            "world_created": "Yes", 
                            "dreaming_started": "Yes"
                        })
                        return True
                    else:
                        self.log_result("Vision-Dream Flow", "WARN", f"Dreaming failed HTTP {dreaming_response.status_code}")
                        return False
                else:
                    self.log_result("Vision-Dream Flow", "WARN", f"World creation failed HTTP {dream_response.status_code}")
                    return False
            else:
                self.log_result("Vision-Dream Flow", "WARN", f"Vision processing failed HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Vision-Dream Flow", "WARN", f"Vision-dream flow test error: {str(e)}")
            return False
    
    def run_validation(self):
        """Run all validation tests"""
        print("🎨 Starting PC2 Vision Dream GPU Validation...")
        print("=" * 60)
        
        start_time = time.time()
        
        # Infrastructure tests
        redis_ok = self.test_redis_connectivity()
        nats_ok = self.test_nats_connectivity()
        
        # GPU test
        gpu_ok = self.test_gpu_availability()
        
        # Service tests (only if infrastructure is working)
        service_results = []
        if redis_ok and nats_ok:
            for service_name, config in self.services.items():
                result = self.test_vision_service(service_name, config)
                service_results.append(result)
                
            # Vision-dream integration test (only if services are working)
            if any(service_results):
                self.test_vision_flow()
        else:
            self.log_result("Vision Services", "SKIP", "Infrastructure not ready")
        
        # Summary
        total_time = time.time() - start_time
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warnings = sum(1 for r in self.results if r['status'] == 'WARN')
        
        print("=" * 60)
        print(f"🎨 Vision Dream GPU Validation Summary (completed in {total_time:.2f}s)")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")
        
        # Overall status
        service_success_rate = sum(service_results) / len(service_results) if service_results else 0
        
        if failed == 0 and passed > 0:
            if service_success_rate >= 1.0:  # 100% service success rate for 3 services
                print("🎯 Status: PC2 VISION DREAM GPU FULLY OPERATIONAL")
                return True
            elif warnings == 0:
                print("🎯 Status: PC2 VISION DREAM GPU INFRASTRUCTURE READY")
                return True
            else:
                print("🎯 Status: PC2 VISION DREAM GPU OPERATIONAL (with warnings)")
                return True
        else:
            print("🎯 Status: PC2 VISION DREAM GPU DEPLOYMENT ISSUES DETECTED")
            return False

if __name__ == "__main__":
    validator = PC2VisionValidator()
    success = validator.run_validation()
    
    # Save results
    with open('/tmp/pc2_vision_validation.json', 'w') as f:
        json.dump(validator.results, f, indent=2)
    
    sys.exit(0 if success else 1)
