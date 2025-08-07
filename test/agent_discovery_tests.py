#!/usr/bin/env python3
"""
AGENT DISCOVERY & HEALTH CHECK TESTS
====================================
Specialized tests for discovering active agents and checking their health status.
"""

import asyncio
import socket
import json
import time
import requests
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

@dataclass
class AgentDiscovery:
    name: str
    port: int
    health_port: int
    status: str  # 'active', 'inactive', 'unknown'
    health_response: Optional[Dict] = None
    response_time_ms: Optional[float] = None
    last_checked: Optional[str] = None

class AgentDiscoveryTester:
    def __init__(self):
        self.discovered_agents: List[AgentDiscovery] = []
        self.port_ranges = {
            'mainpc_services': (7200, 7299),
            'mainpc_health': (8200, 8299),
            'pc2_services': (7100, 7199),
            'pc2_health': (8100, 8199),
            'observability': (9000, 9199),
            'special_services': (5570, 5799)
        }
    
    def discover_active_agents(self) -> List[AgentDiscovery]:
        """Discover all active agents by scanning port ranges"""
        print("🔍 Discovering active agents...")
        
        discovered = []
        
        # Scan all port ranges
        for range_name, (start_port, end_port) in self.port_ranges.items():
            print(f"   Scanning {range_name} ports {start_port}-{end_port}...")
            
            for port in range(start_port, end_port + 1):
                if self._is_port_open(port):
                    agent_name = self._identify_agent_by_port(port)
                    health_port = self._determine_health_port(port, range_name)
                    
                    discovery = AgentDiscovery(
                        name=agent_name,
                        port=port,
                        health_port=health_port,
                        status='active'
                    )
                    
                    # Test health endpoint
                    health_result = self._test_health_endpoint(health_port or port)
                    if health_result:
                        discovery.health_response = health_result['response']
                        discovery.response_time_ms = health_result['response_time']
                        discovery.status = 'active'
                    else:
                        discovery.status = 'inactive'
                    
                    discovery.last_checked = time.strftime('%Y-%m-%d %H:%M:%S')
                    discovered.append(discovery)
        
        self.discovered_agents = discovered
        print(f"✅ Discovered {len(discovered)} active agents")
        return discovered
    
    def _is_port_open(self, port: int, timeout: float = 1.0) -> bool:
        """Check if a port is open"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    def _identify_agent_by_port(self, port: int) -> str:
        """Try to identify agent by port number"""
        # Known port mappings based on configs
        known_ports = {
            # MainPC services
            7200: "ServiceRegistry",
            7201: "UnifiedSystemAgent", 
            7202: "LearningOpportunityDetector",
            7205: "GoalManager",
            7210: "LearningOrchestrationService",
            7211: "ModelManagerSuite",
            7213: "ModelOrchestrator",
            7220: "SystemDigitalTwin",
            9000: "MainPC_ObservabilityHub",
            
            # PC2 services
            7100: "TieredResponder",
            7101: "AsyncProcessor",
            7102: "CacheManager",
            7104: "DreamWorldAgent",
            7105: "UnifiedMemoryReasoningAgent",
            7108: "TutoringServiceAgent",
            7111: "ContextManager",
            7112: "ExperienceTracker",
            7113: "ResourceManager",
            7115: "TaskScheduler",
            7116: "AuthenticationAgent",
            7118: "UnifiedUtilsAgent",
            7119: "ProactiveContextMonitor",
            7140: "MemoryOrchestratorService",
            7150: "CentralErrorBus",
            9100: "PC2_ObservabilityHub",
            
            # Cross-machine services
            5600: "ZMQ_Bridge",
            5596: "StreamingTranslationProxy",
            7155: "CrossMachineGPUScheduler"
        }
        
        return known_ports.get(port, f"Unknown_Agent_{port}")
    
    def _determine_health_port(self, service_port: int, range_name: str) -> Optional[int]:
        """Determine the health check port for a service port"""
        if range_name == 'mainpc_services':
            return service_port + 1000  # 7200 -> 8200
        elif range_name == 'pc2_services':
            return service_port + 1000  # 7100 -> 8100
        elif range_name == 'observability':
            return service_port  # ObservabilityHub uses same port
        elif range_name == 'special_services':
            return service_port + 1000  # 5570 -> 6570
        else:
            return None
    
    def _test_health_endpoint(self, port: int) -> Optional[Dict]:
        """Test health endpoint and measure response time"""
        health_endpoints = [
            f"http://localhost:{port}/health",
            f"http://localhost:{port}/status", 
            f"http://localhost:{port}/ping",
            f"http://localhost:{port}/metrics"
        ]
        
        for endpoint in health_endpoints:
            try:
                start_time = time.time()
                response = requests.get(endpoint, timeout=3)
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                    except:
                        response_data = {"status": "ok", "text": response.text[:100]}
                    
                    return {
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'response': response_data,
                        'response_time': round(response_time, 2)
                    }
            except Exception:
                continue
        
        return None
    
    def perform_health_checks(self) -> Dict:
        """Perform comprehensive health checks on discovered agents"""
        print("🩺 Performing health checks...")
        
        results = {
            'healthy_agents': [],
            'unhealthy_agents': [],
            'unresponsive_agents': [],
            'performance_metrics': {},
            'summary': {}
        }
        
        for agent in self.discovered_agents:
            print(f"   Checking {agent.name}...")
            
            # Basic connectivity check
            if not self._is_port_open(agent.port):
                results['unresponsive_agents'].append({
                    'name': agent.name,
                    'port': agent.port,
                    'issue': 'Port not accessible'
                })
                continue
            
            # Health endpoint check
            health_result = self._test_health_endpoint(agent.health_port or agent.port)
            
            if health_result:
                # Detailed health analysis
                health_status = self._analyze_health_response(health_result)
                
                if health_status['status'] == 'healthy':
                    results['healthy_agents'].append({
                        'name': agent.name,
                        'port': agent.port,
                        'response_time': health_result['response_time'],
                        'health_data': health_status
                    })
                else:
                    results['unhealthy_agents'].append({
                        'name': agent.name,
                        'port': agent.port,
                        'issues': health_status['issues'],
                        'health_data': health_status
                    })
                
                # Performance metrics
                results['performance_metrics'][agent.name] = {
                    'response_time_ms': health_result['response_time'],
                    'endpoint': health_result['endpoint']
                }
            else:
                results['unresponsive_agents'].append({
                    'name': agent.name,
                    'port': agent.port,
                    'issue': 'No health endpoint responding'
                })
        
        # Generate summary
        total_agents = len(self.discovered_agents)
        results['summary'] = {
            'total_discovered': total_agents,
            'healthy': len(results['healthy_agents']),
            'unhealthy': len(results['unhealthy_agents']),
            'unresponsive': len(results['unresponsive_agents']),
            'health_percentage': round((len(results['healthy_agents']) / total_agents * 100), 1) if total_agents > 0 else 0,
            'avg_response_time': self._calculate_avg_response_time(results['performance_metrics'])
        }
        
        return results
    
    def _analyze_health_response(self, health_result: Dict) -> Dict:
        """Analyze health response for detailed status"""
        response = health_result.get('response', {})
        issues = []
        
        # Check response time
        response_time = health_result.get('response_time', 0)
        if response_time > 1000:  # > 1 second
            issues.append(f"Slow response time: {response_time}ms")
        
        # Check response content
        if isinstance(response, dict):
            # Look for error indicators
            if response.get('status') == 'error':
                issues.append(f"Service reports error: {response.get('message', 'Unknown')}")
            
            # Check memory usage if available
            if 'memory' in response:
                memory_usage = response['memory'].get('percent', 0)
                if memory_usage > 90:
                    issues.append(f"High memory usage: {memory_usage}%")
            
            # Check CPU usage if available
            if 'cpu' in response:
                cpu_usage = response['cpu'].get('percent', 0)
                if cpu_usage > 80:
                    issues.append(f"High CPU usage: {cpu_usage}%")
        
        return {
            'status': 'healthy' if not issues else 'unhealthy',
            'issues': issues,
            'response_data': response,
            'response_time_ms': response_time
        }
    
    def _calculate_avg_response_time(self, performance_metrics: Dict) -> float:
        """Calculate average response time across all agents"""
        if not performance_metrics:
            return 0.0
        
        total_time = sum(metrics['response_time_ms'] for metrics in performance_metrics.values())
        return round(total_time / len(performance_metrics), 2)
    
    def test_service_dependencies(self) -> Dict:
        """Test dependencies between discovered services"""
        print("🔗 Testing service dependencies...")
        
        dependency_map = {
            # MainPC dependencies (from config analysis)
            "ModelManagerSuite": [],
            "SystemDigitalTwin": ["ModelManagerSuite"],
            "ObservabilityHub": ["SystemDigitalTwin"],
            "UnifiedSystemAgent": ["SystemDigitalTwin"],
            "RequestCoordinator": ["SystemDigitalTwin"],
            
            # PC2 dependencies
            "MemoryOrchestratorService": [],
            "ResourceManager": ["PC2_ObservabilityHub"],
            "TieredResponder": ["ResourceManager"],
            "AsyncProcessor": ["ResourceManager"],
            "CacheManager": ["MemoryOrchestratorService"],
            "UnifiedMemoryReasoningAgent": ["MemoryOrchestratorService"],
        }
        
        results = {
            'satisfied_dependencies': [],
            'unsatisfied_dependencies': [],
            'dependency_chains': {},
            'critical_missing': []
        }
        
        discovered_names = {agent.name for agent in self.discovered_agents}
        
        for agent_name, dependencies in dependency_map.items():
            if agent_name in discovered_names:
                satisfied = []
                missing = []
                
                for dep in dependencies:
                    if dep in discovered_names:
                        satisfied.append(dep)
                    else:
                        missing.append(dep)
                
                if missing:
                    results['unsatisfied_dependencies'].append({
                        'agent': agent_name,
                        'missing': missing,
                        'satisfied': satisfied
                    })
                    
                    # Check if missing dependency is critical
                    if agent_name in ["SystemDigitalTwin", "ObservabilityHub", "MemoryOrchestratorService"]:
                        results['critical_missing'].extend(missing)
                else:
                    results['satisfied_dependencies'].append(agent_name)
                
                results['dependency_chains'][agent_name] = {
                    'required': dependencies,
                    'satisfied': satisfied,
                    'missing': missing
                }
        
        return results
    
    def generate_discovery_report(self) -> Dict:
        """Generate comprehensive discovery report"""
        print("📊 Generating discovery report...")
        
        # Run all tests
        discovery_results = self.discover_active_agents()
        health_results = self.perform_health_checks()
        dependency_results = self.test_service_dependencies()
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'discovery_summary': {
                'total_agents_discovered': len(discovery_results),
                'port_ranges_scanned': list(self.port_ranges.keys()),
                'discovery_duration': 'N/A'  # Could add timing
            },
            'health_summary': health_results['summary'],
            'dependency_summary': {
                'total_dependencies_checked': len(dependency_results['dependency_chains']),
                'satisfied_count': len(dependency_results['satisfied_dependencies']),
                'unsatisfied_count': len(dependency_results['unsatisfied_dependencies']),
                'critical_missing_count': len(set(dependency_results['critical_missing']))
            },
            'detailed_results': {
                'discovered_agents': [
                    {
                        'name': agent.name,
                        'port': agent.port,
                        'health_port': agent.health_port,
                        'status': agent.status,
                        'response_time_ms': agent.response_time_ms
                    } for agent in discovery_results
                ],
                'health_checks': health_results,
                'dependencies': dependency_results
            },
            'recommendations': self._generate_recommendations(health_results, dependency_results)
        }
        
        return report
    
    def _generate_recommendations(self, health_results: Dict, dependency_results: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Health-based recommendations
        if health_results['summary']['unresponsive'] > 0:
            recommendations.append(f"Investigate {health_results['summary']['unresponsive']} unresponsive agents")
        
        if health_results['summary']['health_percentage'] < 80:
            recommendations.append(f"System health at {health_results['summary']['health_percentage']}% - consider service restart")
        
        if health_results['summary']['avg_response_time'] > 500:
            recommendations.append(f"Average response time {health_results['summary']['avg_response_time']}ms is high - check resource usage")
        
        # Dependency-based recommendations
        if dependency_results['critical_missing']:
            critical = list(set(dependency_results['critical_missing']))
            recommendations.append(f"Critical services missing: {', '.join(critical)} - start immediately")
        
        if dependency_results['unsatisfied_dependencies']:
            recommendations.append(f"Fix {len(dependency_results['unsatisfied_dependencies'])} dependency chains")
        
        # Discovery-based recommendations
        discovered_count = len(self.discovered_agents)
        if discovered_count < 10:
            recommendations.append(f"Only {discovered_count} agents discovered - consider starting more services")
        
        return recommendations
    
    def save_report(self, report: Dict, filename: str = "agent_discovery_report.json"):
        """Save discovery report to file"""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"✅ Discovery report saved to {filename}")

def main():
    """Main discovery test execution"""
    tester = AgentDiscoveryTester()
    
    print("🚀 Starting Agent Discovery & Health Check Tests")
    print("=" * 60)
    
    # Generate comprehensive report
    report = tester.generate_discovery_report()
    
    # Print summary
    print(f"\n📊 DISCOVERY SUMMARY")
    print("-" * 30)
    print(f"Agents Discovered: {report['discovery_summary']['total_agents_discovered']}")
    print(f"Health Percentage: {report['health_summary']['health_percentage']}%")
    print(f"Healthy Agents: {report['health_summary']['healthy']}")
    print(f"Unhealthy Agents: {report['health_summary']['unhealthy']}")
    print(f"Unresponsive Agents: {report['health_summary']['unresponsive']}")
    print(f"Dependencies Satisfied: {report['dependency_summary']['satisfied_count']}")
    print(f"Dependencies Unsatisfied: {report['dependency_summary']['unsatisfied_count']}")
    print(f"Average Response Time: {report['health_summary']['avg_response_time']}ms")
    
    if report['recommendations']:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
    
    # Save results
    tester.save_report(report)
    
    # Return appropriate exit code
    if report['health_summary']['healthy'] == 0:
        return 1  # Critical - no healthy agents
    elif report['health_summary']['health_percentage'] < 50:
        return 2  # Warning - less than 50% healthy
    else:
        return 0  # Success

if __name__ == "__main__":
    exit(main())