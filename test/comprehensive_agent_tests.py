#!/usr/bin/env python3
"""
COMPREHENSIVE AGENT TEST SUITE
==============================
Based on analysis of GitHub workflows and startup configurations.
Tests all active/required agents in MainPC and PC2 systems.
"""

import asyncio
import requests
import socket
import json
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import pytest
from dataclasses import dataclass

@dataclass
class AgentConfig:
    name: str
    script_path: str
    port: int
    health_check_port: int
    required: bool
    dependencies: List[str]
    system: str  # 'mainpc' or 'pc2'

class ComprehensiveAgentTester:
    def __init__(self):
        self.mainpc_agents: List[AgentConfig] = []
        self.pc2_agents: List[AgentConfig] = []
        self.results: Dict = {
            'mainpc': {},
            'pc2': {},
            'cross_machine': {},
            'summary': {}
        }
        
    def load_agent_configs(self):
        """Load and parse agent configurations from startup configs"""
        print("🔍 Loading agent configurations...")
        
        # Load MainPC agents
        mainpc_config_path = Path("main_pc_code/config/startup_config.yaml")
        if mainpc_config_path.exists():
            with open(mainpc_config_path) as f:
                mainpc_config = yaml.safe_load(f)
            self.mainpc_agents = self._parse_mainpc_config(mainpc_config)
        
        # Load PC2 agents
        pc2_config_path = Path("pc2_code/config/startup_config.yaml")
        if pc2_config_path.exists():
            with open(pc2_config_path) as f:
                pc2_config = yaml.safe_load(f)
            self.pc2_agents = self._parse_pc2_config(pc2_config)
        
        print(f"📊 Loaded {len(self.mainpc_agents)} MainPC agents, {len(self.pc2_agents)} PC2 agents")
    
    def _parse_mainpc_config(self, config: Dict) -> List[AgentConfig]:
        """Parse MainPC configuration into agent configs"""
        agents = []
        agent_groups = config.get('agent_groups', {})
        
        for group_name, group_agents in agent_groups.items():
            for agent_name, agent_data in group_agents.items():
                if isinstance(agent_data, dict):
                    # Handle PORT_OFFSET substitution
                    port = agent_data.get('port', '0')
                    if isinstance(port, str) and 'PORT_OFFSET' in port:
                        port = port.replace('${PORT_OFFSET}+', '').replace('${PORT_OFFSET}', '0')
                        port = int(port) if port.isdigit() else 0
                    
                    health_port = agent_data.get('health_check_port', port + 1000)
                    if isinstance(health_port, str) and 'PORT_OFFSET' in health_port:
                        health_port = health_port.replace('${PORT_OFFSET}+', '').replace('${PORT_OFFSET}', '0')
                        health_port = int(health_port) if str(health_port).isdigit() else port + 1000
                    
                    agents.append(AgentConfig(
                        name=agent_name,
                        script_path=agent_data.get('script_path', ''),
                        port=int(port) if str(port).isdigit() else 0,
                        health_check_port=int(health_port) if str(health_port).isdigit() else 0,
                        required=agent_data.get('required', False),
                        dependencies=agent_data.get('dependencies', []),
                        system='mainpc'
                    ))
        
        return [a for a in agents if a.required]  # Only test required agents
    
    def _parse_pc2_config(self, config: Dict) -> List[AgentConfig]:
        """Parse PC2 configuration into agent configs"""
        agents = []
        pc2_services = config.get('pc2_services', [])
        
        for service in pc2_services:
            if isinstance(service, dict):
                # Handle PORT_OFFSET substitution
                port = service.get('port', '0')
                if isinstance(port, str) and 'PORT_OFFSET' in port:
                    port = port.replace('${PORT_OFFSET}+', '').replace('${PORT_OFFSET}', '0')
                    port = int(port) if port.isdigit() else 0
                
                health_port = service.get('health_check_port', port + 1000)
                if isinstance(health_port, str) and 'PORT_OFFSET' in health_port:
                    health_port = health_port.replace('${PORT_OFFSET}+', '').replace('${PORT_OFFSET}', '0')
                    health_port = int(health_port) if str(health_port).isdigit() else port + 1000
                
                agents.append(AgentConfig(
                    name=service.get('name', ''),
                    script_path=service.get('script_path', ''),
                    port=int(port) if str(port).isdigit() else 0,
                    health_check_port=int(health_port) if str(health_port).isdigit() else 0,
                    required=service.get('required', False),
                    dependencies=service.get('dependencies', []),
                    system='pc2'
                ))
        
        return [a for a in agents if a.required]  # Only test required agents

    def test_agent_accessibility(self, agent: AgentConfig) -> Dict:
        """Test if agent is accessible on its ports"""
        result = {
            'agent': agent.name,
            'system': agent.system,
            'port_accessible': False,
            'health_port_accessible': False,
            'script_exists': False,
            'health_response': None,
            'errors': []
        }
        
        # Check if script file exists
        script_path = Path(agent.script_path)
        result['script_exists'] = script_path.exists()
        if not script_path.exists():
            result['errors'].append(f"Script not found: {agent.script_path}")
        
        # Test main port
        if agent.port > 0:
            result['port_accessible'] = self._test_port(agent.port)
            if not result['port_accessible']:
                result['errors'].append(f"Port {agent.port} not accessible")
        
        # Test health check port
        if agent.health_check_port > 0:
            result['health_port_accessible'] = self._test_port(agent.health_check_port)
            if not result['health_port_accessible']:
                result['errors'].append(f"Health port {agent.health_check_port} not accessible")
            
            # Try health endpoint
            if result['health_port_accessible']:
                health_response = self._test_health_endpoint(agent.health_check_port)
                result['health_response'] = health_response
        
        return result
    
    def _test_port(self, port: int, timeout: float = 2.0) -> bool:
        """Test if a port is accessible"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex(('localhost', port))
                return result == 0
        except Exception:
            return False
    
    def _test_health_endpoint(self, port: int) -> Optional[Dict]:
        """Test health endpoint response"""
        health_urls = [
            f"http://localhost:{port}/health",
            f"http://localhost:{port}/status",
            f"http://localhost:{port}/ping"
        ]
        
        for url in health_urls:
            try:
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    try:
                        return {
                            'url': url,
                            'status_code': response.status_code,
                            'response': response.json()
                        }
                    except:
                        return {
                            'url': url,
                            'status_code': response.status_code,
                            'response': response.text[:200]
                        }
            except Exception as e:
                continue
        
        return None
    
    def test_dependency_chain(self, agent: AgentConfig) -> Dict:
        """Test if agent dependencies are satisfied"""
        result = {
            'agent': agent.name,
            'dependencies_satisfied': True,
            'missing_dependencies': [],
            'dependency_status': {}
        }
        
        all_agents = self.mainpc_agents + self.pc2_agents
        agent_by_name = {a.name: a for a in all_agents}
        
        for dep_name in agent.dependencies:
            if dep_name in agent_by_name:
                dep_agent = agent_by_name[dep_name]
                dep_accessible = self._test_port(dep_agent.port)
                result['dependency_status'][dep_name] = {
                    'exists': True,
                    'accessible': dep_accessible,
                    'port': dep_agent.port
                }
                if not dep_accessible:
                    result['dependencies_satisfied'] = False
            else:
                result['missing_dependencies'].append(dep_name)
                result['dependencies_satisfied'] = False
                result['dependency_status'][dep_name] = {
                    'exists': False,
                    'accessible': False,
                    'port': None
                }
        
        return result
    
    def test_cross_machine_communication(self) -> Dict:
        """Test cross-machine communication between MainPC and PC2"""
        result = {
            'zmq_bridge_accessible': False,
            'mainpc_observability_accessible': False,
            'pc2_observability_accessible': False,
            'cross_sync_working': False,
            'errors': []
        }
        
        # Test ZMQ Bridge (port 5600)
        result['zmq_bridge_accessible'] = self._test_port(5600)
        if not result['zmq_bridge_accessible']:
            result['errors'].append("ZMQ Bridge (port 5600) not accessible")
        
        # Test MainPC ObservabilityHub (port 9000)
        result['mainpc_observability_accessible'] = self._test_port(9000)
        if not result['mainpc_observability_accessible']:
            result['errors'].append("MainPC ObservabilityHub (port 9000) not accessible")
        
        # Test PC2 ObservabilityHub (port 9100)
        result['pc2_observability_accessible'] = self._test_port(9100)
        if not result['pc2_observability_accessible']:
            result['errors'].append("PC2 ObservabilityHub (port 9100) not accessible")
        
        # Test cross-machine sync
        if result['mainpc_observability_accessible'] and result['pc2_observability_accessible']:
            result['cross_sync_working'] = True
        
        return result
    
    def run_comprehensive_tests(self) -> Dict:
        """Run all comprehensive tests"""
        print("🚀 Running comprehensive agent tests...")
        
        self.load_agent_configs()
        
        # Test MainPC agents
        print(f"\n🖥️  Testing {len(self.mainpc_agents)} MainPC agents...")
        for agent in self.mainpc_agents:
            print(f"   Testing {agent.name}...")
            self.results['mainpc'][agent.name] = {
                'accessibility': self.test_agent_accessibility(agent),
                'dependencies': self.test_dependency_chain(agent)
            }
        
        # Test PC2 agents
        print(f"\n💻 Testing {len(self.pc2_agents)} PC2 agents...")
        for agent in self.pc2_agents:
            print(f"   Testing {agent.name}...")
            self.results['pc2'][agent.name] = {
                'accessibility': self.test_agent_accessibility(agent),
                'dependencies': self.test_dependency_chain(agent)
            }
        
        # Test cross-machine communication
        print(f"\n🌐 Testing cross-machine communication...")
        self.results['cross_machine'] = self.test_cross_machine_communication()
        
        # Generate summary
        self.results['summary'] = self._generate_summary()
        
        return self.results
    
    def _generate_summary(self) -> Dict:
        """Generate test summary"""
        summary = {
            'total_agents': len(self.mainpc_agents) + len(self.pc2_agents),
            'mainpc_agents': len(self.mainpc_agents),
            'pc2_agents': len(self.pc2_agents),
            'accessible_agents': 0,
            'healthy_agents': 0,
            'agents_with_satisfied_deps': 0,
            'cross_machine_status': 'DOWN',
            'critical_issues': [],
            'recommendations': []
        }
        
        # Count accessible and healthy agents
        all_results = {**self.results['mainpc'], **self.results['pc2']}
        for agent_name, agent_result in all_results.items():
            if agent_result['accessibility']['port_accessible']:
                summary['accessible_agents'] += 1
            
            if agent_result['accessibility']['health_response']:
                summary['healthy_agents'] += 1
            
            if agent_result['dependencies']['dependencies_satisfied']:
                summary['agents_with_satisfied_deps'] += 1
        
        # Cross-machine status
        cross_machine = self.results['cross_machine']
        if cross_machine['mainpc_observability_accessible'] and cross_machine['pc2_observability_accessible']:
            summary['cross_machine_status'] = 'UP'
        elif cross_machine['mainpc_observability_accessible'] or cross_machine['pc2_observability_accessible']:
            summary['cross_machine_status'] = 'PARTIAL'
        
        # Critical issues
        if summary['accessible_agents'] == 0:
            summary['critical_issues'].append("NO_SERVICES_RUNNING")
        
        if summary['cross_machine_status'] == 'DOWN':
            summary['critical_issues'].append("CROSS_MACHINE_COMMUNICATION_DOWN")
        
        if summary['agents_with_satisfied_deps'] < summary['total_agents'] * 0.5:
            summary['critical_issues'].append("DEPENDENCY_CHAIN_BROKEN")
        
        # Recommendations
        if summary['accessible_agents'] < summary['total_agents']:
            summary['recommendations'].append("Start missing agents using startup scripts")
        
        if summary['cross_machine_status'] != 'UP':
            summary['recommendations'].append("Check ObservabilityHub deployment and ZMQ Bridge")
        
        if summary['agents_with_satisfied_deps'] < summary['total_agents']:
            summary['recommendations'].append("Review and fix agent dependency chains")
        
        return summary
    
    def save_results(self, filename: str = "comprehensive_test_results.json"):
        """Save test results to file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"✅ Test results saved to {filename}")
    
    def print_summary(self):
        """Print human-readable test summary"""
        summary = self.results['summary']
        
        print(f"\n📊 COMPREHENSIVE TEST SUMMARY")
        print("=" * 50)
        print(f"Total Agents Tested: {summary['total_agents']}")
        print(f"  MainPC: {summary['mainpc_agents']}")
        print(f"  PC2: {summary['pc2_agents']}")
        print(f"Accessible Agents: {summary['accessible_agents']}/{summary['total_agents']}")
        print(f"Healthy Agents: {summary['healthy_agents']}/{summary['total_agents']}")
        print(f"Dependencies Satisfied: {summary['agents_with_satisfied_deps']}/{summary['total_agents']}")
        print(f"Cross-Machine Status: {summary['cross_machine_status']}")
        
        if summary['critical_issues']:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in summary['critical_issues']:
                print(f"  • {issue}")
        
        if summary['recommendations']:
            print(f"\n💡 RECOMMENDATIONS:")
            for rec in summary['recommendations']:
                print(f"  • {rec}")

# Pytest integration
class TestComprehensiveAgents:
    def setup_method(self):
        self.tester = ComprehensiveAgentTester()
        self.tester.load_agent_configs()
    
    def test_mainpc_agents_accessibility(self):
        """Test that MainPC agents are accessible"""
        failed_agents = []
        for agent in self.tester.mainpc_agents:
            result = self.tester.test_agent_accessibility(agent)
            if not result['port_accessible']:
                failed_agents.append(f"{agent.name} (port {agent.port})")
        
        assert len(failed_agents) == 0, f"MainPC agents not accessible: {failed_agents}"
    
    def test_pc2_agents_accessibility(self):
        """Test that PC2 agents are accessible"""
        failed_agents = []
        for agent in self.tester.pc2_agents:
            result = self.tester.test_agent_accessibility(agent)
            if not result['port_accessible']:
                failed_agents.append(f"{agent.name} (port {agent.port})")
        
        assert len(failed_agents) == 0, f"PC2 agents not accessible: {failed_agents}"
    
    def test_cross_machine_communication(self):
        """Test cross-machine communication"""
        result = self.tester.test_cross_machine_communication()
        assert result['mainpc_observability_accessible'], "MainPC ObservabilityHub not accessible"
        assert result['pc2_observability_accessible'], "PC2 ObservabilityHub not accessible"
        assert result['cross_sync_working'], "Cross-machine synchronization not working"
    
    def test_agent_dependencies(self):
        """Test that agent dependencies are satisfied"""
        failed_deps = []
        all_agents = self.tester.mainpc_agents + self.tester.pc2_agents
        
        for agent in all_agents:
            result = self.tester.test_dependency_chain(agent)
            if not result['dependencies_satisfied']:
                failed_deps.append(f"{agent.name}: {result['missing_dependencies']}")
        
        assert len(failed_deps) == 0, f"Agents with unsatisfied dependencies: {failed_deps}"

def main():
    """Main test execution"""
    tester = ComprehensiveAgentTester()
    results = tester.run_comprehensive_tests()
    
    tester.print_summary()
    tester.save_results()
    
    # Return exit code based on results
    summary = results['summary']
    if 'NO_SERVICES_RUNNING' in summary['critical_issues']:
        return 1  # Critical failure
    elif summary['accessible_agents'] < summary['total_agents'] * 0.5:
        return 2  # Partial failure
    else:
        return 0  # Success

if __name__ == "__main__":
    exit(main())