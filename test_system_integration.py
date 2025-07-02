#!/usr/bin/env python3
"""
System Integration Test Script
----------------------------
This script performs a comprehensive integration test of both MainPC and PC2 agents.
It checks:
1. If all agents are running and responding to health checks
2. If agents can communicate with each other across machines
3. If the system as a whole is functioning correctly

Usage:
    python test_system_integration.py [--skip-mainpc] [--skip-pc2] [--timeout SECONDS]
"""

import os
import sys
import yaml
import json
import time
import argparse
import socket
import zmq
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tabulate import tabulate

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent
MAIN_PC_CONFIG_PATH = PROJECT_ROOT / 'main_pc_code' / 'config' / 'startup_config.yaml'
PC2_CONFIG_PATH = PROJECT_ROOT / 'pc2_code' / 'config' / 'startup_config.yaml'

# Default timeout for health check requests
DEFAULT_TIMEOUT = 5

# Test results
test_results = {
    'mainpc_agents': {'total': 0, 'healthy': 0, 'unhealthy': 0},
    'pc2_agents': {'total': 0, 'healthy': 0, 'unhealthy': 0},
    'cross_communication': {'total': 0, 'successful': 0, 'failed': 0},
    'functional_tests': {'total': 0, 'passed': 0, 'failed': 0}
}

def load_config(config_path):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading configuration from {config_path}: {e}")
        return None

def extract_agents(config, is_pc2=False):
    """Extract all agents from the configuration"""
    agents = []
    
    if is_pc2:
        # PC2 config has a simple structure
        for agent in config.get('pc2_services', []):
            if isinstance(agent, dict) and 'name' in agent and 'script_path' in agent:
                agents.append(agent)
    else:
        # MainPC config has a more complex structure
        for section in config:
            if isinstance(config[section], list):
                for item in config[section]:
                    if isinstance(item, dict) and 'name' in item and 'script_path' in item:
                        agents.append(item)
    
    return agents

def check_port_open(host, port, timeout=1):
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def check_agent_health(agent, is_pc2=False):
    """Check if an agent is healthy by connecting to its health port"""
    name = agent.get('name', 'Unknown')
    host = agent.get('host', 'localhost')
    if host == '0.0.0.0':
        host = 'localhost'
    
    port = agent.get('port', 0)
    health_port = agent.get('health_check_port', port + 1)
    
    result = {
        'name': name,
        'host': host,
        'port': port,
        'health_port': health_port,
        'status': 'unknown',
        'message': '',
        'is_pc2': is_pc2
    }
    
    # First check if the port is open
    if not check_port_open(host, port):
        result['status'] = 'unreachable'
        result['message'] = f"Port {port} is closed"
        return result
    
    # Then check if health port is open
    if not check_port_open(host, health_port):
        result['status'] = 'unhealthy'
        result['message'] = f"Health port {health_port} is closed"
        return result
    
    # Try to connect to the health endpoint
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, DEFAULT_TIMEOUT * 1000)
        socket.connect(f"tcp://{host}:{health_port}")
        
        socket.send_json({"action": "health_check"})
        response = socket.recv_json()
        
        result['status'] = 'healthy'
        result['message'] = str(response)
        return result
    except Exception as e:
        result['status'] = 'error'
        result['message'] = str(e)
        return result
    finally:
        socket.close()
        context.term()

def test_cross_communication(mainpc_agents, pc2_agents):
    """Test communication between MainPC and PC2 agents"""
    results = []
    
    # Test communication from PC2 to MainPC
    # We'll use the RemoteConnectorAgent on PC2 to communicate with SystemDigitalTwin on MainPC
    remote_connector = None
    system_digital_twin = None
    
    for agent in pc2_agents:
        if isinstance(agent, dict) and agent.get('name') == 'RemoteConnectorAgent':
            remote_connector = agent
            break
    
    for agent in mainpc_agents:
        if isinstance(agent, dict) and agent.get('name') == 'SystemDigitalTwin':
            system_digital_twin = agent
            break
    
    if remote_connector and system_digital_twin:
        result = {
            'test_name': 'PC2 → MainPC Communication',
            'status': 'pending',
            'message': ''
        }
        
        try:
            # Connect to RemoteConnectorAgent
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, DEFAULT_TIMEOUT * 1000)
            remote_port = remote_connector.get('port', 0)
            socket.connect(f"tcp://localhost:{remote_port}")
            
            # Send request to connect to SystemDigitalTwin
            request = {
                "action": "connect_to_mainpc",
                "target_agent": "SystemDigitalTwin",
                "request": {"action": "ping"}
            }
            
            socket.send_json(request)
            response = socket.recv_json()
            
            if isinstance(response, dict) and response.get('status') == 'success':
                result['status'] = 'passed'
                result['message'] = f"Successfully communicated with SystemDigitalTwin: {response}"
            else:
                result['status'] = 'failed'
                result['message'] = f"Failed to communicate with SystemDigitalTwin: {response}"
                
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f"Error testing PC2 → MainPC communication: {e}"
        finally:
            socket.close()
            context.term()
            
        results.append(result)
        
        # Update test results
        test_results['cross_communication']['total'] += 1
        if result['status'] == 'passed':
            test_results['cross_communication']['successful'] += 1
        else:
            test_results['cross_communication']['failed'] += 1
    
    return results

def run_functional_tests():
    """Run functional tests on the system"""
    results = []
    
    # Test 1: Check if TieredResponder can handle a request
    result = {
        'test_name': 'TieredResponder Request Handling',
        'status': 'pending',
        'message': ''
    }
    
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, DEFAULT_TIMEOUT * 1000)
        socket.connect("tcp://localhost:7100")  # TieredResponder port
        
        request = {
            "action": "process_request",
            "data": "Hello, system!"
        }
        
        socket.send_json(request)
        response = socket.recv_json()
        
        if isinstance(response, dict) and response.get('status') == 'success':
            result['status'] = 'passed'
            result['message'] = f"TieredResponder successfully processed request: {response}"
        else:
            result['status'] = 'failed'
            result['message'] = f"TieredResponder failed to process request: {response}"
            
    except Exception as e:
        result['status'] = 'error'
        result['message'] = f"Error testing TieredResponder: {e}"
    finally:
        socket.close()
        context.term()
        
    results.append(result)
    
    # Update test results
    test_results['functional_tests']['total'] += 1
    if result['status'] == 'passed':
        test_results['functional_tests']['passed'] += 1
    else:
        test_results['functional_tests']['failed'] += 1
    
    # Test 2: Check if UnifiedMemoryReasoningAgent can handle a memory query
    result = {
        'test_name': 'Memory Query Handling',
        'status': 'pending',
        'message': ''
    }
    
    try:
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, DEFAULT_TIMEOUT * 1000)
        socket.connect("tcp://localhost:7105")  # UnifiedMemoryReasoningAgent port
        
        request = {
            "action": "query_memory",
            "query": "test"
        }
        
        socket.send_json(request)
        response = socket.recv_json()
        
        if isinstance(response, dict) and response.get('status') in ['success', 'no_results']:
            result['status'] = 'passed'
            result['message'] = f"Memory query successful: {response}"
        else:
            result['status'] = 'failed'
            result['message'] = f"Memory query failed: {response}"
            
    except Exception as e:
        result['status'] = 'error'
        result['message'] = f"Error testing memory query: {e}"
    finally:
        socket.close()
        context.term()
        
    results.append(result)
    
    # Update test results
    test_results['functional_tests']['total'] += 1
    if result['status'] == 'passed':
        test_results['functional_tests']['passed'] += 1
    else:
        test_results['functional_tests']['failed'] += 1
    
    return results

def print_health_check_table(results):
    """Print health check results as a table"""
    table_data = []
    for result in results:
        status_symbol = "✅" if result['status'] == 'healthy' else "❌"
        location = "PC2" if result['is_pc2'] else "MainPC"
        table_data.append([
            status_symbol,
            result['name'],
            location,
            f"{result['host']}:{result['port']}",
            result['status'],
            result['message'][:50] + ('...' if len(result['message']) > 50 else '')
        ])
    
    headers = ["Status", "Agent Name", "Location", "Address", "Status", "Message"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def print_cross_communication_table(results):
    """Print cross-communication test results as a table"""
    table_data = []
    for result in results:
        status_symbol = "✅" if result['status'] == 'passed' else "❌"
        table_data.append([
            status_symbol,
            result['test_name'],
            result['status'],
            result['message'][:50] + ('...' if len(result['message']) > 50 else '')
        ])
    
    headers = ["Status", "Test Name", "Status", "Message"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def print_functional_test_table(results):
    """Print functional test results as a table"""
    table_data = []
    for result in results:
        status_symbol = "✅" if result['status'] == 'passed' else "❌"
        table_data.append([
            status_symbol,
            result['test_name'],
            result['status'],
            result['message'][:50] + ('...' if len(result['message']) > 50 else '')
        ])
    
    headers = ["Status", "Test Name", "Status", "Message"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

def print_summary():
    """Print a summary of all test results"""
    print("\n=== Test Summary ===")
    
    # MainPC agents
    mainpc_health = test_results['mainpc_agents']
    mainpc_health_rate = (mainpc_health['healthy'] / mainpc_health['total']) * 100 if mainpc_health['total'] > 0 else 0
    print(f"MainPC Agents: {mainpc_health['healthy']}/{mainpc_health['total']} healthy ({mainpc_health_rate:.1f}%)")
    
    # PC2 agents
    pc2_health = test_results['pc2_agents']
    pc2_health_rate = (pc2_health['healthy'] / pc2_health['total']) * 100 if pc2_health['total'] > 0 else 0
    print(f"PC2 Agents: {pc2_health['healthy']}/{pc2_health['total']} healthy ({pc2_health_rate:.1f}%)")
    
    # Cross-communication
    cross_comm = test_results['cross_communication']
    cross_comm_rate = (cross_comm['successful'] / cross_comm['total']) * 100 if cross_comm['total'] > 0 else 0
    print(f"Cross-Communication Tests: {cross_comm['successful']}/{cross_comm['total']} passed ({cross_comm_rate:.1f}%)")
    
    # Functional tests
    func_tests = test_results['functional_tests']
    func_tests_rate = (func_tests['passed'] / func_tests['total']) * 100 if func_tests['total'] > 0 else 0
    print(f"Functional Tests: {func_tests['passed']}/{func_tests['total']} passed ({func_tests_rate:.1f}%)")
    
    # Overall status
    total_tests = mainpc_health['total'] + pc2_health['total'] + cross_comm['total'] + func_tests['total']
    total_passed = mainpc_health['healthy'] + pc2_health['healthy'] + cross_comm['successful'] + func_tests['passed']
    overall_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\nOverall Status: {total_passed}/{total_tests} tests passed ({overall_rate:.1f}%)")
    
    if overall_rate == 100:
        print("\n✅ ALL TESTS PASSED! The system is fully operational.")
    elif overall_rate >= 80:
        print("\n🟡 MOST TESTS PASSED. The system is operational but some components may have issues.")
    else:
        print("\n❌ MULTIPLE FAILURES. The system is not fully operational.")

def main():
    """Main function"""
    global DEFAULT_TIMEOUT
    
    parser = argparse.ArgumentParser(description="System Integration Test")
    parser.add_argument("--skip-mainpc", action="store_true", help="Skip MainPC agent tests")
    parser.add_argument("--skip-pc2", action="store_true", help="Skip PC2 agent tests")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout for health checks in seconds")
    args = parser.parse_args()
    
    DEFAULT_TIMEOUT = args.timeout
    
    print("=== System Integration Test ===\n")
    
    health_check_results = []
    
    # Test MainPC agents
    if not args.skip_mainpc:
        print("Testing MainPC agents...")
        mainpc_config = load_config(MAIN_PC_CONFIG_PATH)
        if mainpc_config:
            mainpc_agents = extract_agents(mainpc_config)
            test_results['mainpc_agents']['total'] = len(mainpc_agents)
            
            print(f"Found {len(mainpc_agents)} MainPC agents")
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(check_agent_health, agent, False): agent for agent in mainpc_agents}
                
                for future in as_completed(futures):
                    result = future.result()
                    health_check_results.append(result)
                    
                    if result['status'] == 'healthy':
                        test_results['mainpc_agents']['healthy'] += 1
                    else:
                        test_results['mainpc_agents']['unhealthy'] += 1
        else:
            print("Failed to load MainPC configuration")
    
    # Test PC2 agents
    if not args.skip_pc2:
        print("\nTesting PC2 agents...")
        pc2_config = load_config(PC2_CONFIG_PATH)
        if pc2_config:
            pc2_agents = extract_agents(pc2_config, True)
            test_results['pc2_agents']['total'] = len(pc2_agents)
            
            print(f"Found {len(pc2_agents)} PC2 agents")
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(check_agent_health, agent, True): agent for agent in pc2_agents}
                
                for future in as_completed(futures):
                    result = future.result()
                    health_check_results.append(result)
                    
                    if result['status'] == 'healthy':
                        test_results['pc2_agents']['healthy'] += 1
                    else:
                        test_results['pc2_agents']['unhealthy'] += 1
        else:
            print("Failed to load PC2 configuration")
    
    # Print health check results
    print("\n=== Health Check Results ===")
    print_health_check_table(health_check_results)
    
    # Test cross-communication between MainPC and PC2
    if not args.skip_mainpc and not args.skip_pc2:
        print("\n=== Cross-Communication Tests ===")
        mainpc_config = load_config(MAIN_PC_CONFIG_PATH)
        pc2_config = load_config(PC2_CONFIG_PATH)
        if mainpc_config and pc2_config:
            cross_comm_results = test_cross_communication(
                extract_agents(mainpc_config),
                extract_agents(pc2_config, True)
            )
            print_cross_communication_table(cross_comm_results)
        else:
            print("Skipping cross-communication tests due to missing configuration")
    
    # Run functional tests
    print("\n=== Functional Tests ===")
    functional_test_results = run_functional_tests()
    print_functional_test_table(functional_test_results)
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    main() 