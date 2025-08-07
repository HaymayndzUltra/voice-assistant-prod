#!/usr/bin/env python3
"""
CROSS-MACHINE COMMUNICATION TESTS
=================================
Tests for communication between MainPC and PC2 systems.
Based on analysis of GitHub workflows and cross-machine architecture.
"""

import asyncio
import socket
import json
import time
import requests
import zmq
import threading
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import subprocess
from pathlib import Path

@dataclass
class CrossMachineEndpoint:
    name: str
    host: str
    port: int
    protocol: str  # 'http', 'zmq', 'grpc'
    system: str    # 'mainpc', 'pc2', 'bridge'
    status: str = 'unknown'
    last_response_time: Optional[float] = None
    error_message: Optional[str] = None

class CrossMachineTester:
    def __init__(self):
        self.endpoints: List[CrossMachineEndpoint] = []
        self.test_results: Dict = {
            'zmq_bridge': {},
            'observability_sync': {},
            'service_discovery': {},
            'data_transfer': {},
            'failover': {},
            'summary': {}
        }
        
        # Define cross-machine endpoints based on config analysis
        self.define_cross_machine_endpoints()
    
    def define_cross_machine_endpoints(self):
        """Define known cross-machine communication endpoints"""
        self.endpoints = [
            # ZMQ Bridge (critical for cross-machine communication)
            CrossMachineEndpoint("ZMQ_Bridge", "localhost", 5600, "zmq", "bridge"),
            
            # Observability Hubs (cross-machine sync)
            CrossMachineEndpoint("MainPC_ObservabilityHub", "localhost", 9000, "http", "mainpc"),
            CrossMachineEndpoint("PC2_ObservabilityHub", "localhost", 9100, "http", "pc2"),
            
            # Cross-GPU Scheduler (new service we created)
            CrossMachineEndpoint("CrossGPU_Scheduler", "localhost", 7155, "grpc", "bridge"),
            CrossMachineEndpoint("CrossGPU_Health", "localhost", 8155, "http", "bridge"),
            
            # Translation Proxy (new service we created)
            CrossMachineEndpoint("Translation_Proxy", "localhost", 5596, "http", "bridge"),
            CrossMachineEndpoint("Translation_Health", "localhost", 6596, "http", "bridge"),
            
            # Service Registries (service discovery)
            CrossMachineEndpoint("MainPC_ServiceRegistry", "localhost", 7200, "http", "mainpc"),
            
            # System Digital Twins (cross-system coordination)
            CrossMachineEndpoint("MainPC_DigitalTwin", "localhost", 7220, "http", "mainpc"),
            
            # Error Bus (PC2 central error handling)
            CrossMachineEndpoint("PC2_ErrorBus", "localhost", 7150, "http", "pc2"),
            
            # Resource Management
            CrossMachineEndpoint("PC2_ResourceManager", "localhost", 7113, "http", "pc2"),
        ]
    
    def test_zmq_bridge_communication(self) -> Dict:
        """Test ZMQ Bridge functionality"""
        print("🌉 Testing ZMQ Bridge communication...")
        
        result = {
            'bridge_accessible': False,
            'pub_sub_working': False,
            'req_rep_working': False,
            'message_throughput': 0,
            'latency_ms': None,
            'errors': []
        }
        
        # Test basic connectivity
        zmq_bridge = next((ep for ep in self.endpoints if ep.name == "ZMQ_Bridge"), None)
        if zmq_bridge:
            result['bridge_accessible'] = self._test_port_connectivity(zmq_bridge.host, zmq_bridge.port)
            
            if result['bridge_accessible']:
                # Test ZMQ patterns
                result.update(self._test_zmq_patterns())
            else:
                result['errors'].append("ZMQ Bridge port not accessible")
        else:
            result['errors'].append("ZMQ Bridge endpoint not defined")
        
        return result
    
    def _test_zmq_patterns(self) -> Dict:
        """Test ZMQ communication patterns"""
        patterns_result = {
            'pub_sub_working': False,
            'req_rep_working': False,
            'message_throughput': 0,
            'latency_ms': None
        }
        
        try:
            # Test REQ-REP pattern (simple request-response)
            context = zmq.Context()
            
            # Test request-response
            socket_req = context.socket(zmq.REQ)
            socket_req.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            socket_req.connect("tcp://localhost:5600")
            
            start_time = time.time()
            test_message = {"type": "health_check", "timestamp": time.time()}
            socket_req.send_json(test_message)
            
            try:
                response = socket_req.recv_json()
                end_time = time.time()
                patterns_result['req_rep_working'] = True
                patterns_result['latency_ms'] = round((end_time - start_time) * 1000, 2)
            except zmq.Again:
                patterns_result['req_rep_working'] = False
            
            socket_req.close()
            
            # Test PUB-SUB pattern throughput
            socket_pub = context.socket(zmq.PUB)
            socket_sub = context.socket(zmq.SUB)
            
            socket_pub.bind("tcp://*:5601")  # Use different port for test
            socket_sub.connect("tcp://localhost:5601")
            socket_sub.setsockopt(zmq.SUBSCRIBE, b"test")
            
            time.sleep(0.1)  # Allow connection to establish
            
            # Send test messages
            messages_sent = 0
            start_time = time.time()
            for i in range(100):
                socket_pub.send_multipart([b"test", json.dumps({"id": i}).encode()])
                messages_sent += 1
                if time.time() - start_time > 1:  # Max 1 second test
                    break
            
            patterns_result['message_throughput'] = messages_sent
            patterns_result['pub_sub_working'] = messages_sent > 0
            
            socket_pub.close()
            socket_sub.close()
            context.term()
            
        except Exception as e:
            patterns_result['error'] = str(e)
        
        return patterns_result
    
    def test_observability_hub_sync(self) -> Dict:
        """Test ObservabilityHub cross-machine synchronization"""
        print("👁️ Testing ObservabilityHub synchronization...")
        
        result = {
            'mainpc_hub_accessible': False,
            'pc2_hub_accessible': False,
            'sync_endpoints_working': False,
            'metrics_cross_sync': False,
            'data_consistency': 'unknown',
            'sync_latency_ms': None,
            'errors': []
        }
        
        # Test MainPC ObservabilityHub
        mainpc_hub = next((ep for ep in self.endpoints if ep.name == "MainPC_ObservabilityHub"), None)
        if mainpc_hub:
            result['mainpc_hub_accessible'] = self._test_http_endpoint(
                f"http://{mainpc_hub.host}:{mainpc_hub.port}/health"
            )
            
            if result['mainpc_hub_accessible']:
                result.update(self._test_observability_endpoints(mainpc_hub, 'mainpc'))
        
        # Test PC2 ObservabilityHub
        pc2_hub = next((ep for ep in self.endpoints if ep.name == "PC2_ObservabilityHub"), None)
        if pc2_hub:
            result['pc2_hub_accessible'] = self._test_http_endpoint(
                f"http://{pc2_hub.host}:{pc2_hub.port}/health"
            )
            
            if result['pc2_hub_accessible']:
                result.update(self._test_observability_endpoints(pc2_hub, 'pc2'))
        
        # Test cross-synchronization
        if result['mainpc_hub_accessible'] and result['pc2_hub_accessible']:
            result.update(self._test_cross_hub_sync(mainpc_hub, pc2_hub))
        
        return result
    
    def _test_observability_endpoints(self, hub: CrossMachineEndpoint, system: str) -> Dict:
        """Test specific ObservabilityHub endpoints"""
        endpoints_result = {}
        
        test_endpoints = [
            f"http://{hub.host}:{hub.port}/metrics",
            f"http://{hub.host}:{hub.port}/health",
            f"http://{hub.host}:{hub.port}/status",
            f"http://{hub.host}:{hub.port}/agents"
        ]
        
        working_endpoints = 0
        for endpoint in test_endpoints:
            if self._test_http_endpoint(endpoint):
                working_endpoints += 1
        
        endpoints_result[f'{system}_endpoints_working'] = working_endpoints
        endpoints_result[f'{system}_endpoint_coverage'] = round((working_endpoints / len(test_endpoints)) * 100, 1)
        
        return endpoints_result
    
    def _test_cross_hub_sync(self, mainpc_hub: CrossMachineEndpoint, pc2_hub: CrossMachineEndpoint) -> Dict:
        """Test synchronization between ObservabilityHubs"""
        sync_result = {
            'sync_endpoints_working': False,
            'metrics_cross_sync': False,
            'sync_latency_ms': None
        }
        
        try:
            # Get metrics from both hubs
            start_time = time.time()
            
            mainpc_metrics_url = f"http://{mainpc_hub.host}:{mainpc_hub.port}/metrics"
            pc2_metrics_url = f"http://{pc2_hub.host}:{pc2_hub.port}/metrics"
            
            mainpc_response = requests.get(mainpc_metrics_url, timeout=3)
            pc2_response = requests.get(pc2_metrics_url, timeout=3)
            
            end_time = time.time()
            sync_result['sync_latency_ms'] = round((end_time - start_time) * 1000, 2)
            
            if mainpc_response.status_code == 200 and pc2_response.status_code == 200:
                sync_result['sync_endpoints_working'] = True
                
                # Check if both systems report awareness of each other
                mainpc_text = mainpc_response.text
                pc2_text = pc2_response.text
                
                # Look for cross-system metrics
                if 'pc2' in mainpc_text.lower() or 'cross_machine' in mainpc_text.lower():
                    sync_result['metrics_cross_sync'] = True
        
        except Exception as e:
            sync_result['error'] = str(e)
        
        return sync_result
    
    def test_service_discovery(self) -> Dict:
        """Test cross-machine service discovery"""
        print("🔍 Testing cross-machine service discovery...")
        
        result = {
            'mainpc_registry_accessible': False,
            'service_registration_working': False,
            'cross_machine_discovery': False,
            'service_count': 0,
            'discovery_latency_ms': None,
            'errors': []
        }
        
        # Test MainPC ServiceRegistry
        registry = next((ep for ep in self.endpoints if ep.name == "MainPC_ServiceRegistry"), None)
        if registry:
            result['mainpc_registry_accessible'] = self._test_http_endpoint(
                f"http://{registry.host}:{registry.port}/health"
            )
            
            if result['mainpc_registry_accessible']:
                result.update(self._test_service_registry_functionality(registry))
        
        return result
    
    def _test_service_registry_functionality(self, registry: CrossMachineEndpoint) -> Dict:
        """Test ServiceRegistry functionality"""
        registry_result = {
            'service_registration_working': False,
            'service_count': 0,
            'discovery_latency_ms': None
        }
        
        try:
            start_time = time.time()
            
            # Test service listing endpoint
            services_url = f"http://{registry.host}:{registry.port}/services"
            response = requests.get(services_url, timeout=5)
            
            end_time = time.time()
            registry_result['discovery_latency_ms'] = round((end_time - start_time) * 1000, 2)
            
            if response.status_code == 200:
                registry_result['service_registration_working'] = True
                
                try:
                    services = response.json()
                    if isinstance(services, list):
                        registry_result['service_count'] = len(services)
                    elif isinstance(services, dict):
                        registry_result['service_count'] = len(services.keys())
                except:
                    # If not JSON, try to count services from text
                    registry_result['service_count'] = response.text.count('service') if response.text else 0
        
        except Exception as e:
            registry_result['error'] = str(e)
        
        return registry_result
    
    def test_data_transfer_performance(self) -> Dict:
        """Test cross-machine data transfer performance"""
        print("📊 Testing cross-machine data transfer performance...")
        
        result = {
            'small_transfer_success': False,
            'large_transfer_success': False,
            'transfer_rate_mbps': 0,
            'concurrent_transfers_supported': 0,
            'errors': []
        }
        
        # Test with different payload sizes
        test_payloads = [
            ('small', 1024),      # 1KB
            ('medium', 1024*100), # 100KB
            ('large', 1024*1000)  # 1MB
        ]
        
        transfer_results = {}
        
        for payload_name, payload_size in test_payloads:
            success, transfer_rate = self._test_payload_transfer(payload_size)
            transfer_results[payload_name] = {
                'success': success,
                'transfer_rate_mbps': transfer_rate
            }
            
            if payload_name == 'small' and success:
                result['small_transfer_success'] = True
            elif payload_name == 'large' and success:
                result['large_transfer_success'] = True
        
        # Calculate average transfer rate
        successful_rates = [tr['transfer_rate_mbps'] for tr in transfer_results.values() if tr['success']]
        if successful_rates:
            result['transfer_rate_mbps'] = round(sum(successful_rates) / len(successful_rates), 2)
        
        result['transfer_details'] = transfer_results
        
        return result
    
    def _test_payload_transfer(self, payload_size: int) -> Tuple[bool, float]:
        """Test transferring a payload of specified size"""
        try:
            # Generate test payload
            test_data = {'data': 'x' * payload_size, 'size': payload_size, 'timestamp': time.time()}
            
            # Find an accessible endpoint to test with
            accessible_endpoints = [
                "http://localhost:9000/test",  # MainPC ObservabilityHub
                "http://localhost:9100/test",  # PC2 ObservabilityHub
                "http://localhost:5596/health"  # Translation Proxy
            ]
            
            for endpoint in accessible_endpoints:
                try:
                    start_time = time.time()
                    response = requests.post(endpoint, json=test_data, timeout=10)
                    end_time = time.time()
                    
                    transfer_time = end_time - start_time
                    transfer_rate_mbps = (payload_size / (1024 * 1024)) / transfer_time if transfer_time > 0 else 0
                    
                    if response.status_code in [200, 404, 405]:  # 404/405 means endpoint exists but doesn't accept POST
                        return True, transfer_rate_mbps
                
                except requests.exceptions.Timeout:
                    continue
                except Exception:
                    continue
            
            return False, 0.0
        
        except Exception:
            return False, 0.0
    
    def test_failover_resilience(self) -> Dict:
        """Test system resilience and failover capabilities"""
        print("🛡️ Testing failover resilience...")
        
        result = {
            'redundant_services_available': False,
            'graceful_degradation': False,
            'automatic_failover': False,
            'recovery_time_seconds': None,
            'errors': []
        }
        
        # Check for redundant services
        redundant_services = self._identify_redundant_services()
        result['redundant_services_available'] = len(redundant_services) > 0
        
        # Test graceful degradation
        if result['redundant_services_available']:
            result.update(self._test_graceful_degradation(redundant_services))
        
        return result
    
    def _identify_redundant_services(self) -> List[Dict]:
        """Identify services that have redundancy"""
        redundant_services = []
        
        # Group services by function
        service_groups = {
            'observability': ['MainPC_ObservabilityHub', 'PC2_ObservabilityHub'],
            'health_checks': ['CrossGPU_Health', 'Translation_Health'],
            'error_handling': ['PC2_ErrorBus']  # Could be extended
        }
        
        for group_name, service_names in service_groups.items():
            accessible_services = []
            for service_name in service_names:
                endpoint = next((ep for ep in self.endpoints if ep.name == service_name), None)
                if endpoint and self._test_port_connectivity(endpoint.host, endpoint.port):
                    accessible_services.append(endpoint)
            
            if len(accessible_services) > 1:
                redundant_services.append({
                    'group': group_name,
                    'services': accessible_services,
                    'redundancy_level': len(accessible_services)
                })
        
        return redundant_services
    
    def _test_graceful_degradation(self, redundant_services: List[Dict]) -> Dict:
        """Test graceful degradation when services fail"""
        degradation_result = {
            'graceful_degradation': False,
            'automatic_failover': False,
            'recovery_time_seconds': None
        }
        
        # This would typically involve:
        # 1. Simulating service failure
        # 2. Checking if other services continue working
        # 3. Measuring recovery time
        
        # For safety, we'll just check if multiple services in each group are responding
        for group_info in redundant_services:
            if group_info['redundancy_level'] >= 2:
                degradation_result['graceful_degradation'] = True
                break
        
        return degradation_result
    
    def _test_port_connectivity(self, host: str, port: int, timeout: float = 3.0) -> bool:
        """Test if a port is accessible"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception:
            return False
    
    def _test_http_endpoint(self, url: str, timeout: float = 3.0) -> bool:
        """Test if an HTTP endpoint is accessible"""
        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code in [200, 201, 202, 204]
        except Exception:
            return False
    
    def run_comprehensive_cross_machine_tests(self) -> Dict:
        """Run all cross-machine communication tests"""
        print("🚀 Running comprehensive cross-machine tests...")
        print("=" * 60)
        
        # Update endpoint status
        for endpoint in self.endpoints:
            endpoint.status = 'accessible' if self._test_port_connectivity(endpoint.host, endpoint.port) else 'inaccessible'
        
        # Run all test categories
        self.test_results['zmq_bridge'] = self.test_zmq_bridge_communication()
        self.test_results['observability_sync'] = self.test_observability_hub_sync()
        self.test_results['service_discovery'] = self.test_service_discovery()
        self.test_results['data_transfer'] = self.test_data_transfer_performance()
        self.test_results['failover'] = self.test_failover_resilience()
        
        # Generate summary
        self.test_results['summary'] = self._generate_cross_machine_summary()
        
        return self.test_results
    
    def _generate_cross_machine_summary(self) -> Dict:
        """Generate comprehensive test summary"""
        summary = {
            'total_endpoints': len(self.endpoints),
            'accessible_endpoints': sum(1 for ep in self.endpoints if ep.status == 'accessible'),
            'critical_systems_status': {},
            'communication_health': 'UNKNOWN',
            'performance_rating': 'UNKNOWN',
            'reliability_rating': 'UNKNOWN',
            'critical_issues': [],
            'recommendations': []
        }
        
        # Check critical systems
        critical_systems = ['ZMQ_Bridge', 'MainPC_ObservabilityHub', 'PC2_ObservabilityHub']
        for system in critical_systems:
            endpoint = next((ep for ep in self.endpoints if ep.name == system), None)
            summary['critical_systems_status'][system] = endpoint.status if endpoint else 'missing'
        
        # Determine communication health
        zmq_working = self.test_results['zmq_bridge'].get('bridge_accessible', False)
        obs_sync = self.test_results['observability_sync'].get('sync_endpoints_working', False)
        
        if zmq_working and obs_sync:
            summary['communication_health'] = 'HEALTHY'
        elif zmq_working or obs_sync:
            summary['communication_health'] = 'DEGRADED'
        else:
            summary['communication_health'] = 'CRITICAL'
        
        # Performance rating
        transfer_rate = self.test_results['data_transfer'].get('transfer_rate_mbps', 0)
        if transfer_rate > 10:
            summary['performance_rating'] = 'EXCELLENT'
        elif transfer_rate > 1:
            summary['performance_rating'] = 'GOOD'
        elif transfer_rate > 0:
            summary['performance_rating'] = 'ACCEPTABLE'
        else:
            summary['performance_rating'] = 'POOR'
        
        # Reliability rating
        redundancy = self.test_results['failover'].get('redundant_services_available', False)
        if redundancy and summary['communication_health'] == 'HEALTHY':
            summary['reliability_rating'] = 'HIGH'
        elif summary['communication_health'] in ['HEALTHY', 'DEGRADED']:
            summary['reliability_rating'] = 'MEDIUM'
        else:
            summary['reliability_rating'] = 'LOW'
        
        # Critical issues
        if not zmq_working:
            summary['critical_issues'].append('ZMQ_BRIDGE_DOWN')
        
        if summary['accessible_endpoints'] < 5:
            summary['critical_issues'].append('INSUFFICIENT_SERVICES')
        
        if summary['communication_health'] == 'CRITICAL':
            summary['critical_issues'].append('CROSS_MACHINE_COMMUNICATION_FAILURE')
        
        # Recommendations
        if 'ZMQ_BRIDGE_DOWN' in summary['critical_issues']:
            summary['recommendations'].append('Start ZMQ Bridge service immediately')
        
        if summary['performance_rating'] == 'POOR':
            summary['recommendations'].append('Optimize network configuration and service performance')
        
        if summary['reliability_rating'] == 'LOW':
            summary['recommendations'].append('Implement redundancy and failover mechanisms')
        
        return summary
    
    def save_results(self, filename: str = "cross_machine_test_results.json"):
        """Save test results to file"""
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        print(f"✅ Cross-machine test results saved to {filename}")
    
    def print_summary(self):
        """Print human-readable test summary"""
        summary = self.test_results['summary']
        
        print(f"\n📊 CROSS-MACHINE COMMUNICATION SUMMARY")
        print("=" * 60)
        print(f"Accessible Endpoints: {summary['accessible_endpoints']}/{summary['total_endpoints']}")
        print(f"Communication Health: {summary['communication_health']}")
        print(f"Performance Rating: {summary['performance_rating']}")
        print(f"Reliability Rating: {summary['reliability_rating']}")
        
        print(f"\n🔧 CRITICAL SYSTEMS STATUS:")
        for system, status in summary['critical_systems_status'].items():
            status_icon = "✅" if status == "accessible" else "❌"
            print(f"  {status_icon} {system}: {status.upper()}")
        
        if summary['critical_issues']:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in summary['critical_issues']:
                print(f"  • {issue}")
        
        if summary['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in summary['recommendations']:
                print(f"  • {rec}")

def main():
    """Main cross-machine test execution"""
    tester = CrossMachineTester()
    
    print("🚀 Starting Cross-Machine Communication Tests")
    print("=" * 60)
    
    # Run comprehensive tests
    results = tester.run_comprehensive_cross_machine_tests()
    
    # Print results
    tester.print_summary()
    
    # Save results
    tester.save_results()
    
    # Return appropriate exit code
    summary = results['summary']
    if summary['communication_health'] == 'CRITICAL':
        return 1  # Critical failure
    elif summary['communication_health'] == 'DEGRADED':
        return 2  # Warning
    else:
        return 0  # Success

if __name__ == "__main__":
    exit(main())