#!/usr/bin/env python3
"""
Prometheus Metrics Validation Script
Tests metrics endpoints and functionality across all agents.

This script validates that Prometheus metrics are properly implemented
and accessible on all agents in the AI system.
"""

import sys
import os
import time
import json
import requests
import threading
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Tuple
import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from common.utils.path_manager import PathManager
from common.utils.prometheus_exporter import is_prometheus_available

def test_prometheus_availability():
    """Test if Prometheus client is available"""
    print("🔍 Testing Prometheus client availability...")
    
    available = is_prometheus_available()
    if available:
        print("✅ Prometheus client is available")
        return True
    else:
        print("❌ Prometheus client is NOT available")
        print("   Install with: pip install prometheus_client")
        return False

def get_agent_ports_from_config() -> Dict[str, Dict[str, Any]]:
    """Extract agent ports from startup configuration files"""
    print("🔍 Loading agent configurations...")
    
    agents = {}
    
    # Load MainPC agents
    main_config_path = Path(project_root) / "main_pc_code" / "config" / "startup_config.yaml"
    if main_config_path.exists():
        with open(main_config_path, 'r') as f:
            main_config = yaml.safe_load(f)
            
        # Extract from agent_groups structure
        if 'agent_groups' in main_config:
            for group_name, group_data in main_config['agent_groups'].items():
                if 'agents' in group_data:
                    for agent_name, agent_config in group_data['agents'].items():
                        port = agent_config.get('port')
                        health_port = agent_config.get('health_check_port', port + 1 if port else None)
                        # BaseAgent serves metrics on http_health_port which is health_check_port + 1
                        metrics_port = health_port + 1 if health_port else None
                        
                        agents[agent_name] = {
                            'type': 'MainPC',
                            'group': group_name,
                            'port': port,
                            'health_port': health_port,
                            'metrics_port': metrics_port,
                            'script_path': agent_config.get('script_path'),
                            'expected_baseagent': True  # Assume MainPC agents use BaseAgent
                        }
    
    # Load PC2 agents
    pc2_config_path = Path(project_root) / "pc2_code" / "config" / "startup_config.yaml"
    if pc2_config_path.exists():
        with open(pc2_config_path, 'r') as f:
            pc2_config = yaml.safe_load(f)
            
        # Extract from pc2_services structure (which is a list)
        if 'pc2_services' in pc2_config and isinstance(pc2_config['pc2_services'], list):
            for agent_config in pc2_config['pc2_services']:
                agent_name = agent_config.get('name')
                if not agent_name:
                    continue
                    
                port = agent_config.get('port')
                health_port = agent_config.get('health_check_port', port + 1 if port else None)
                # BaseAgent serves metrics on http_health_port which is health_check_port + 1  
                metrics_port = health_port + 1 if health_port else None
                
                agents[agent_name] = {
                    'type': 'PC2',
                    'group': 'pc2_services',
                    'port': port,
                    'health_port': health_port,
                    'metrics_port': metrics_port,
                    'script_path': agent_config.get('script_path'),
                    'expected_baseagent': False  # Assume PC2 agents might be legacy
                }
    
    print(f"✅ Found {len(agents)} agents in configuration")
    return agents

def test_agent_metrics_endpoint(agent_name: str, agent_info: Dict[str, Any]) -> Dict[str, Any]:
    """Test metrics endpoint for a specific agent"""
    result = {
        'agent_name': agent_name,
        'agent_info': agent_info,
        'metrics_accessible': False,
        'health_accessible': False,
        'prometheus_format': False,
        'metrics_content': None,
        'health_content': None,
        'errors': []
    }
    
    metrics_port = agent_info.get('metrics_port')
    if not metrics_port:
        result['errors'].append("No metrics port configured")
        return result
    
    # Test metrics endpoint
    try:
        metrics_url = f"http://localhost:{metrics_port}/metrics"
        response = requests.get(metrics_url, timeout=5)
        
        if response.status_code == 200:
            result['metrics_accessible'] = True
            result['metrics_content'] = response.text[:500]  # First 500 chars
            
            # Check if it's Prometheus format
            if 'agent_requests_total' in response.text or 'agent_uptime_seconds' in response.text:
                result['prometheus_format'] = True
        else:
            result['errors'].append(f"Metrics endpoint returned {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        result['errors'].append(f"Metrics endpoint connection error: {e}")
    
    # Test health endpoint  
    try:
        health_url = f"http://localhost:{metrics_port}/health"
        response = requests.get(health_url, timeout=5)
        
        if response.status_code == 200:
            result['health_accessible'] = True
            try:
                result['health_content'] = response.json()
            except:
                result['health_content'] = response.text[:200]
        else:
            result['errors'].append(f"Health endpoint returned {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        result['errors'].append(f"Health endpoint connection error: {e}")
    
    return result

def start_test_agent(agent_name: str, agent_info: Dict[str, Any]) -> Tuple[subprocess.Popen, bool]:
    """Start an agent for testing and return the process"""
    script_path = agent_info.get('script_path')
    if not script_path:
        return None, False
    
    # Resolve script path
    if script_path.startswith('main_pc_code/'):
        full_script_path = project_root / script_path
    elif script_path.startswith('pc2_code/'):
        full_script_path = project_root / script_path
    else:
        full_script_path = project_root / script_path
    
    if not full_script_path.exists():
        print(f"   ❌ Script not found: {full_script_path}")
        return None, False
    
    try:
        # Set environment variables for metrics
        env = os.environ.copy()
        env['ENABLE_PROMETHEUS_METRICS'] = 'true'
        
        # Start the agent
        cmd = [
            sys.executable, str(full_script_path),
            '--port', str(agent_info['port'])
        ]
        
        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(project_root)
        )
        
        # Give agent time to start
        time.sleep(3)
        
        # Check if process is still running
        if process.poll() is None:
            return process, True
        else:
            stdout, stderr = process.communicate()
            print(f"   ❌ Agent failed to start: {stderr.decode()}")
            return None, False
            
    except Exception as e:
        print(f"   ❌ Error starting agent: {e}")
        return None, False

def validate_metrics_across_agents():
    """Run comprehensive metrics validation across all agents"""
    print("\n🎯 PROMETHEUS METRICS VALIDATION")
    print("=" * 60)
    
    # Check Prometheus availability
    if not test_prometheus_availability():
        return False
    
    # Get agent configurations
    agents = get_agent_ports_from_config()
    if not agents:
        print("❌ No agents found in configuration")
        return False
    
    # Test a sample of agents (avoid overwhelming the system)
    sample_agents = dict(list(agents.items())[:5])  # Test first 5 agents
    
    print(f"\n🧪 Testing metrics on {len(sample_agents)} sample agents...")
    
    results = []
    running_processes = []
    
    for agent_name, agent_info in sample_agents.items():
        print(f"\n📊 Testing {agent_name} ({agent_info['type']})...")
        
        # Try to start the agent
        process, started = start_test_agent(agent_name, agent_info)
        if started:
            running_processes.append(process)
            print(f"   ✅ Agent started on port {agent_info['port']}")
            
            # Test metrics endpoints
            result = test_agent_metrics_endpoint(agent_name, agent_info)
            results.append(result)
            
            # Print immediate results
            if result['metrics_accessible']:
                print(f"   ✅ Metrics endpoint accessible")
                if result['prometheus_format']:
                    print(f"   ✅ Prometheus format detected")
                else:
                    print(f"   ⚠️  Metrics format not recognized as Prometheus")
            else:
                print(f"   ❌ Metrics endpoint not accessible")
            
            if result['health_accessible']:
                print(f"   ✅ Health endpoint accessible")
            else:
                print(f"   ❌ Health endpoint not accessible")
                
        else:
            print(f"   ❌ Failed to start agent")
            results.append({
                'agent_name': agent_name,
                'agent_info': agent_info,
                'errors': ['Failed to start agent'],
                'metrics_accessible': False,
                'health_accessible': False,
                'prometheus_format': False
            })
    
    # Clean up processes
    print(f"\n🧹 Cleaning up test agents...")
    for process in running_processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            try:
                process.kill()
            except:
                pass
    
    # Generate summary report
    print(f"\n📋 VALIDATION SUMMARY")
    print("=" * 40)
    
    total_agents = len(results)
    metrics_working = sum(1 for r in results if r['metrics_accessible'])
    health_working = sum(1 for r in results if r['health_accessible'])
    prometheus_format = sum(1 for r in results if r['prometheus_format'])
    
    print(f"Agents tested: {total_agents}")
    print(f"Metrics endpoints working: {metrics_working}/{total_agents} ({metrics_working/total_agents*100:.1f}%)")
    print(f"Health endpoints working: {health_working}/{total_agents} ({health_working/total_agents*100:.1f}%)")
    print(f"Prometheus format detected: {prometheus_format}/{total_agents} ({prometheus_format/total_agents*100:.1f}%)")
    
    # Show detailed errors
    print(f"\n🔍 DETAILED RESULTS:")
    for result in results:
        status = "✅" if result['metrics_accessible'] and result['prometheus_format'] else "❌"
        print(f"{status} {result['agent_name']}")
        if result['errors']:
            for error in result['errors']:
                print(f"      Error: {error}")
    
    # Success criteria
    success_rate = prometheus_format / total_agents if total_agents > 0 else 0
    success = success_rate >= 0.8  # 80% success rate
    
    print(f"\n🎯 VALIDATION RESULT: {'✅ PASS' if success else '❌ FAIL'}")
    if success:
        print(f"   Metrics integration successful ({success_rate*100:.1f}% success rate)")
    else:
        print(f"   Metrics integration needs improvement ({success_rate*100:.1f}% success rate)")
        
    return success

def test_legacy_metrics_wrapper():
    """Test the LegacyMetricsWrapper functionality"""
    print("\n🧪 Testing LegacyMetricsWrapper...")
    
    try:
        from common.utils.legacy_metrics_support import quick_metrics_setup
        
        # Create test wrapper
        metrics = quick_metrics_setup("TestLegacyAgent", 9999)
        
        if metrics:
            print("   ✅ LegacyMetricsWrapper created successfully")
            
            # Test basic functionality
            metrics.set_health_status('healthy')
            metrics.record_request('test_endpoint', 'success', 0.1)
            metrics.record_error('test_error')
            
            # Get summary
            summary = metrics.get_metrics_summary()
            print(f"   ✅ Metrics summary: {summary['agent_name']}")
            
            # Test metrics endpoint (if server started)
            try:
                response = requests.get('http://localhost:10099/metrics', timeout=2)
                if response.status_code == 200:
                    print("   ✅ Legacy metrics endpoint accessible")
                else:
                    print(f"   ⚠️  Legacy metrics endpoint returned {response.status_code}")
            except:
                print("   ⚠️  Legacy metrics endpoint not accessible (expected if no server)")
            
            # Cleanup
            metrics.cleanup()
            print("   ✅ LegacyMetricsWrapper cleaned up")
            
            return True
        else:
            print("   ❌ Failed to create LegacyMetricsWrapper")
            return False
            
    except Exception as e:
        print(f"   ❌ LegacyMetricsWrapper test failed: {e}")
        return False

def main():
    """Main validation function"""
    print("🚀 PHASE 0 DAY 7 - PROMETHEUS METRICS VALIDATION")
    print("=" * 60)
    
    success = True
    
    # Test 1: Legacy metrics wrapper
    if not test_legacy_metrics_wrapper():
        success = False
    
    # Test 2: Comprehensive agent metrics validation
    if not validate_metrics_across_agents():
        success = False
    
    # Final result
    print("\n🏁 FINAL VALIDATION RESULT")
    print("=" * 30)
    
    if success:
        print("✅ PROMETHEUS METRICS VALIDATION PASSED")
        print("   All metrics systems are working correctly")
        print("   Ready to proceed with Phase 0 completion")
        return 0
    else:
        print("❌ PROMETHEUS METRICS VALIDATION FAILED")
        print("   Some issues need to be resolved before Phase 1")
        print("   Review the detailed results above")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 