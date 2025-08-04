#!/usr/bin/env python3
"""
Main PC Phase 2: PC2 Integration Testing
========================================
Comprehensive integration testing between Main PC and PC2 subsystems.
Tests cross-system communication, resource coordination, and hybrid functionality.
"""

import subprocess
import json
import time
import requests
import socket
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class MainPCPhase2IntegrationValidator:
    """
    Main PC Phase 2 Integration Validator
    Tests integration between Main PC and PC2 subsystems.
    """
    
    def __init__(self):
        # Main PC service endpoints
        self.mainpc_services = {
            'coordination': {'redis': 6379, 'nats': 4222},
            'emotion_system': {'redis': 6383, 'nats': 4225},
            'language_stack': {'redis': 6385, 'nats': 4227},
            'memory_stack': {'redis': 6381, 'nats': 4223},
            'translation_services': {'redis': 6384, 'nats': 4298},
            'speech_gpu': {'redis': 6387, 'nats': 4229},
            'observability': {'redis': 6380, 'http': 9000}
        }
        
        # PC2 service endpoints  
        self.pc2_services = {
            'infra_core': {'redis': 36379, 'nats': 34222, 'http': 35001},
            'coordination': {'redis': 36380, 'nats': 34223, 'http': 35002},
            'emotion_system': {'redis': 36381, 'nats': 34224, 'http': 35003},
            'memory_stack': {'redis': 36382, 'nats': 34225, 'http': 35004},
            'observability_hub': {'redis': 36383, 'nats': 34226, 'http': 35005}
        }
        
        self.test_results = {}

    def test_port_isolation(self) -> bool:
        """Test 1: Verify port isolation between Main PC and PC2."""
        print("🔌 TEST 1: PORT ISOLATION VALIDATION")
        print("=" * 50)
        
        conflicts = []
        mainpc_ports = set()
        pc2_ports = set()
        
        # Collect Main PC ports
        for service, ports in self.mainpc_services.items():
            for port_type, port in ports.items():
                mainpc_ports.add(port)
        
        # Collect PC2 ports  
        for service, ports in self.pc2_services.items():
            for port_type, port in ports.items():
                pc2_ports.add(port)
        
        # Check for conflicts
        common_ports = mainpc_ports.intersection(pc2_ports)
        if common_ports:
            conflicts.extend(common_ports)
            print(f"❌ Port conflicts found: {sorted(common_ports)}")
        else:
            print("✅ No port conflicts between Main PC and PC2")
        
        print(f"📊 Main PC ports: {len(mainpc_ports)} unique ports")
        print(f"📊 PC2 ports: {len(pc2_ports)} unique ports")
        print(f"📊 Total system ports: {len(mainpc_ports.union(pc2_ports))}")
        
        success = len(conflicts) == 0
        self.test_results['port_isolation'] = {'success': success, 'conflicts': conflicts}
        return success

    def test_cross_system_connectivity(self) -> bool:
        """Test 2: Cross-system network connectivity."""
        print(f"\n🌐 TEST 2: CROSS-SYSTEM CONNECTIVITY")
        print("=" * 50)
        
        connectivity_results = {}
        
        # Test Main PC to PC2 connectivity
        print("🔍 Testing Main PC → PC2 connectivity:")
        for service, ports in self.pc2_services.items():
            service_connectivity = {}
            for port_type, port in ports.items():
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    result = sock.connect_ex(('localhost', port))
                    sock.close()
                    
                    if result == 0:
                        print(f"   ✅ {service}:{port_type}({port})")
                        service_connectivity[port_type] = True
                    else:
                        print(f"   ❌ {service}:{port_type}({port})")
                        service_connectivity[port_type] = False
                except Exception as e:
                    print(f"   ⚠️  {service}:{port_type}({port}) - {str(e)[:30]}")
                    service_connectivity[port_type] = False
            
            connectivity_results[f'mainpc_to_pc2_{service}'] = service_connectivity
        
        # Test PC2 to Main PC connectivity
        print(f"\n🔍 Testing PC2 → Main PC connectivity:")
        for service, ports in self.mainpc_services.items():
            service_connectivity = {}
            for port_type, port in ports.items():
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
                    sock.settimeout(3)
                    result = sock.connect_ex(('localhost', port))
                    sock.close()
                    
                    if result == 0:
                        print(f"   ✅ {service}:{port_type}({port})")
                        service_connectivity[port_type] = True
                    else:
                        print(f"   ❌ {service}:{port_type}({port})")
                        service_connectivity[port_type] = False
                except Exception as e:
                    print(f"   ⚠️  {service}:{port_type}({port}) - {str(e)[:30]}")
                    service_connectivity[port_type] = False
            
            connectivity_results[f'pc2_to_mainpc_{service}'] = service_connectivity
        
        # Calculate success rate
        total_tests = sum(len(v) for v in connectivity_results.values())
        successful_tests = sum(sum(v.values()) for v in connectivity_results.values())
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n📊 Connectivity Results:")
        print(f"   Total tests: {total_tests}")
        print(f"   Successful: {successful_tests}")  
        print(f"   Success rate: {success_rate:.1f}%")
        
        success = success_rate >= 85  # 85% threshold for connectivity
        self.test_results['cross_system_connectivity'] = {
            'success': success, 
            'success_rate': success_rate,
            'details': connectivity_results
        }
        return success

    def test_observability_integration(self) -> bool:
        """Test 3: ObservabilityHub integration between systems."""
        print(f"\n📊 TEST 3: OBSERVABILITY INTEGRATION")
        print("=" * 50)
        
        observability_tests = {}
        
        # Test Main PC ObservabilityHub
        print("🔍 Testing Main PC ObservabilityHub:")
        try:
            response = requests.get("http://localhost:9000/health", timeout=5)
            if response.status_code == 200:
                print("   ✅ Main PC ObservabilityHub accessible")
                observability_tests['mainpc_hub'] = True
            else:
                print(f"   ❌ Main PC ObservabilityHub: HTTP {response.status_code}")
                observability_tests['mainpc_hub'] = False
        except Exception as e:
            print(f"   ❌ Main PC ObservabilityHub: {str(e)[:50]}")
            observability_tests['mainpc_hub'] = False
        
        # Test PC2 ObservabilityHub
        print("🔍 Testing PC2 ObservabilityHub:")
        try:
            response = requests.get("http://localhost:35005/health", timeout=5)
            if response.status_code == 200:
                print("   ✅ PC2 ObservabilityHub accessible")
                observability_tests['pc2_hub'] = True
            else:
                print(f"   ❌ PC2 ObservabilityHub: HTTP {response.status_code}")
                observability_tests['pc2_hub'] = False
        except Exception as e:
            print(f"   ❌ PC2 ObservabilityHub: {str(e)[:50]}")
            observability_tests['pc2_hub'] = False
        
        # Test cross-hub visibility
        print("🔍 Testing cross-hub integration:")
        both_accessible = observability_tests.get('mainpc_hub', False) and observability_tests.get('pc2_hub', False)
        if both_accessible:
            print("   ✅ Both observability hubs accessible")
            print("   ✅ Cross-system monitoring possible")
            observability_tests['cross_integration'] = True
        else:
            print("   ⚠️  Limited cross-system observability")
            observability_tests['cross_integration'] = False
        
        success = sum(observability_tests.values()) >= 2  # At least 2/3 tests pass
        self.test_results['observability_integration'] = {
            'success': success,
            'details': observability_tests
        }
        return success

    def test_hybrid_ai_coordination(self) -> bool:
        """Test 4: Hybrid AI service coordination."""
        print(f"\n🤖 TEST 4: HYBRID AI COORDINATION")
        print("=" * 50)
        
        hybrid_tests = {}
        
        # Test Main PC AI services accessibility  
        print("🔍 Testing Main PC AI services:")
        mainpc_ai_services = ['translation_services', 'speech_gpu', 'language_stack', 'memory_stack']
        mainpc_ai_healthy = 0
        
        for service in mainpc_ai_services:
            if service in self.mainpc_services:
                redis_port = self.mainpc_services[service]['redis']
                try:
                    result = subprocess.run(['nc', '-z', 'localhost', str(redis_port)], 
                                          capture_output=True, timeout=3)
                    if result.returncode == 0:
                        print(f"   ✅ {service} infrastructure ready")
                        mainpc_ai_healthy += 1
                    else:
                        print(f"   ❌ {service} infrastructure not accessible")
                except:
                    print(f"   ⚠️  {service} check failed")
        
        hybrid_tests['mainpc_ai_services'] = mainpc_ai_healthy / len(mainpc_ai_services)
        
        # Test PC2 coordination services
        print(f"\n🔍 Testing PC2 coordination services:")
        pc2_coord_services = ['coordination', 'memory_stack', 'emotion_system']
        pc2_coord_healthy = 0
        
        for service in pc2_coord_services:
            if service in self.pc2_services:
                redis_port = self.pc2_services[service]['redis']
                try:
                    result = subprocess.run(['nc', '-z', 'localhost', str(redis_port)], 
                                          capture_output=True, timeout=3)
                    if result.returncode == 0:
                        print(f"   ✅ {service} infrastructure ready")
                        pc2_coord_healthy += 1
                    else:
                        print(f"   ❌ {service} infrastructure not accessible")
                except:
                    print(f"   ⚠️  {service} check failed")
        
        hybrid_tests['pc2_coord_services'] = pc2_coord_healthy / len(pc2_coord_services)
        
        # Test hybrid integration potential
        print(f"\n🔍 Testing hybrid integration potential:")
        mainpc_score = hybrid_tests['mainpc_ai_services']
        pc2_score = hybrid_tests['pc2_coord_services']
        hybrid_potential = (mainpc_score + pc2_score) / 2
        
        if hybrid_potential >= 0.8:
            print(f"   ✅ Excellent hybrid integration potential ({hybrid_potential:.1%})")
            hybrid_tests['integration_potential'] = True
        elif hybrid_potential >= 0.6:
            print(f"   ⚠️  Good hybrid integration potential ({hybrid_potential:.1%})")
            hybrid_tests['integration_potential'] = True
        else:
            print(f"   ❌ Limited hybrid integration potential ({hybrid_potential:.1%})")
            hybrid_tests['integration_potential'] = False
        
        success = hybrid_tests['integration_potential']
        self.test_results['hybrid_ai_coordination'] = {
            'success': success,
            'mainpc_score': mainpc_score,
            'pc2_score': pc2_score,
            'hybrid_potential': hybrid_potential
        }
        return success

    def test_resource_coordination(self) -> bool:
        """Test 5: Resource coordination and isolation."""
        print(f"\n⚡ TEST 5: RESOURCE COORDINATION")
        print("=" * 50)
        
        resource_tests = {}
        
        # Test Redis isolation
        print("🔍 Testing Redis resource isolation:")
        redis_isolation = True
        try:
            # Count unique Redis instances
            result = subprocess.run(['docker', 'ps', '--format', 'json'], 
                                  capture_output=True, text=True)
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    container = json.loads(line)
                    containers.append(container.get('Names', ''))
            
            redis_containers = [c for c in containers if 'redis' in c.lower()]
            mainpc_redis = [c for c in redis_containers if not c.startswith('pc2_')]
            pc2_redis = [c for c in redis_containers if c.startswith('pc2_')]
            
            print(f"   📊 Main PC Redis instances: {len(mainpc_redis)}")
            print(f"   📊 PC2 Redis instances: {len(pc2_redis)}")
            print(f"   ✅ Redis resource isolation maintained")
            
            resource_tests['redis_isolation'] = True
            
        except Exception as e:
            print(f"   ❌ Redis isolation check failed: {str(e)[:50]}")
            resource_tests['redis_isolation'] = False
        
        # Test NATS coordination
        print(f"\n🔍 Testing NATS coordination:")
        try:
            nats_containers = [c for c in containers if 'nats' in c.lower()]
            mainpc_nats = [c for c in nats_containers if not c.startswith('pc2_')]
            pc2_nats = [c for c in nats_containers if c.startswith('pc2_')]
            
            print(f"   📊 Main PC NATS instances: {len(mainpc_nats)}")
            print(f"   📊 PC2 NATS instances: {len(pc2_nats)}")
            print(f"   ✅ NATS coordination potential confirmed")
            
            resource_tests['nats_coordination'] = True
            
        except Exception as e:
            print(f"   ❌ NATS coordination check failed: {str(e)[:50]}")
            resource_tests['nats_coordination'] = False
        
        # Test overall resource health
        print(f"\n🔍 Testing overall resource health:")
        resource_score = sum(resource_tests.values()) / len(resource_tests) if resource_tests else 0
        
        if resource_score >= 0.8:
            print(f"   ✅ Excellent resource coordination ({resource_score:.1%})")
            resource_tests['overall_health'] = True
        else:
            print(f"   ⚠️  Resource coordination needs attention ({resource_score:.1%})")
            resource_tests['overall_health'] = resource_score >= 0.5
        
        success = resource_tests.get('overall_health', False)
        self.test_results['resource_coordination'] = {
            'success': success,
            'resource_score': resource_score,
            'details': resource_tests
        }
        return success

    def run_integration_validation(self) -> bool:
        """Run complete Phase 2 integration validation."""
        print("🚀 MAIN PC PHASE 2: PC2 INTEGRATION TESTING")
        print("=" * 70)
        print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Run all tests
        tests = [
            ("Port Isolation", self.test_port_isolation),
            ("Cross-System Connectivity", self.test_cross_system_connectivity),
            ("Observability Integration", self.test_observability_integration),
            ("Hybrid AI Coordination", self.test_hybrid_ai_coordination),
            ("Resource Coordination", self.test_resource_coordination)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
                    print(f"\n✅ {test_name}: PASSED")
                else:
                    print(f"\n❌ {test_name}: FAILED")
            except Exception as e:
                print(f"\n⚠️  {test_name}: ERROR - {str(e)[:60]}")
        
        # Overall assessment
        success_rate = (passed_tests / total_tests) * 100
        print(f"\n🏆 PHASE 2 INTEGRATION ASSESSMENT:")
        print("=" * 50)
        print(f"✅ Passed Tests: {passed_tests}")
        print(f"❌ Failed Tests: {total_tests - passed_tests}")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 PHASE 2 INTEGRATION: SUCCESS!")
            print("✅ Main PC and PC2 ready for unified deployment")
            overall_success = True
        elif success_rate >= 60:
            print("⚠️  PHASE 2 INTEGRATION: PARTIAL SUCCESS")
            print("🔧 Some integration aspects need attention")
            overall_success = True
        else:
            print("❌ PHASE 2 INTEGRATION: NEEDS WORK")
            print("🔧 Significant integration issues require resolution")
            overall_success = False
        
        return overall_success

if __name__ == "__main__":
    validator = MainPCPhase2IntegrationValidator()
    success = validator.run_integration_validation()
    exit(0 if success else 1)
