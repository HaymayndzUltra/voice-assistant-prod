#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
Agent Health Check Validation Script

This script performs health check validation on target agents to ensure they are
fully responsive and report their status correctly.

Target Agents:
- TieredResponder (main port 7110, health port 7112)
- AsyncProcessor (main port 7101, health port 7103) 
- CacheManager (main port 7102, health port 7102 via CacheManagerHealth)
- PerformanceMonitor (main port 7103, health port 7103 via PerformanceMonitorHealth)
"""

import subprocess
import zmq
import json
import time
import signal
import sys
import os
from typing import Dict, Any, Optional
from pathlib import Path
from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip
from common.env_helpers import get_env

class AgentHealthValidator:
    def __init__(self):
        self.context = zmq.Context()
        self.processes = {}
        
        # Agent configurations with correct ports
        self.agents = {
            'TieredResponder': {
                'script_path': 'agents/tiered_responder.py',
                'main_port': 7110,
                'health_port': 7112,
                'health_check_type': 'direct',  # Direct health check via ZMQ
                'required': True
            },
            'AsyncProcessor': {
                'script_path': 'agents/async_processor.py', 
                'main_port': 7101,
                'health_port': 7103,
                'health_check_type': 'direct',  # Direct health check via ZMQ
                'required': True
            },
            'CacheManager': {
                'script_path': 'agents/cache_manager.py',
                'main_port': 7102, 
                'health_port': 7102,
                'health_check_type': 'health_class',  # Uses CacheManagerHealth class
                'required': True
            },
            'PerformanceMonitor': {
                'script_path': 'agents/performance_monitor.py',
                'main_port': 7103,
                'health_port': 7103,
                'health_check_type': 'health_class',  # Uses PerformanceMonitorHealth class
                'required': True
            }
        }
        
    def launch_agent(self, agent_name: str) -> bool:
        """Launch an agent in isolation as a separate subprocess"""
        agent_config = self.agents[agent_name]
        script_path = agent_config['script_path']
        
        print(f"🚀 Launching {agent_name}...")
        
        try:
            # Launch the agent process (no port arguments needed as they use hardcoded ports)
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[agent_name] = process
            print(f"✅ {agent_name} process started (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to launch {agent_name}: {str(e)}")
            return False
    
    def perform_health_check(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Perform health check on agent's health port"""
        agent_config = self.agents[agent_name]
        health_port = agent_config['health_port']
        health_check_type = agent_config['health_check_type']
        
        print(f"🔍 Performing health check on {agent_name} (health port: {health_port}, type: {health_check_type})...")
        
        try:
            # Create ZMQ client socket
            socket = self.context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout
            
            # Connect to health port
            socket.connect(get_zmq_connection_string({health_port}, "localhost")))
            
            # Send health check request
            request = {'action': 'health_check'}
            socket.send_json(request)
            
            # Receive response
            response = socket.recv_json()
            
            socket.close()
            return response
            
        except zmq.error.Again:
            print(f"⏰ Timeout waiting for {agent_name} health check response")
            return None
        except Exception as e:
            print(f"❌ Health check failed for {agent_name}: {str(e)}")
            return None
    
    def validate_response(self, agent_name: str, response: Dict[str, Any]) -> bool:
        """Validate the health check response"""
        print(f"📊 Validating {agent_name} response...")
        
        # Check if response is valid JSON object
        if not isinstance(response, dict):
            print(f"❌ {agent_name}: Response is not a valid JSON object")
            return False
        
        # Check for required 'status' field
        if 'status' not in response:
            print(f"❌ {agent_name}: Missing 'status' field in response")
            return False
        
        # Check if status is 'ok'
        if response['status'] != 'ok':
            print(f"❌ {agent_name}: Status is '{response['status']}', expected 'ok'")
            return False
        
        # Check for service field (present in some agents)
        if 'service' in response:
            print(f"✅ {agent_name}: Service field present: {response['service']}")
        
        # Check for initialization_status (optional but preferred)
        if 'initialization_status' in response:
            print(f"✅ {agent_name}: Has initialization_status field")
        
        print(f"✅ {agent_name}: Response validation passed")
        return True
    
    def terminate_agent(self, agent_name: str):
        """Terminate an agent process"""
        if agent_name in self.processes:
            process = self.processes[agent_name]
            print(f"🛑 Terminating {agent_name} (PID: {process.pid})...")
            
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {agent_name} terminated successfully")
            except subprocess.TimeoutExpired:
                print(f"⚠️ {agent_name} didn't terminate gracefully, forcing...")
                process.kill()
                process.wait()
            except Exception as e:
                print(f"❌ Error terminating {agent_name}: {str(e)}")
            
            del self.processes[agent_name]
    
    def test_agent(self, agent_name: str) -> Dict[str, Any]:
        """Test a single agent end-to-end"""
        print(f"\n{'='*60}")
        print(f"🧪 TESTING {agent_name}")
        print(f"{'='*60}")
        
        result = {
            'agent_name': agent_name,
            'launch_success': False,
            'health_check_success': False,
            'response_validation': False,
            'response_data': None,
            'final_status': 'FAILED'
        }
        
        # Step 1: Launch the agent
        if not self.launch_agent(agent_name):
            result['final_status'] = 'LAUNCH_FAILED'
            return result
        
        result['launch_success'] = True
        
        # Step 2: Wait for initialization
        print(f"⏳ Waiting 5 seconds for {agent_name} initialization...")
        time.sleep(5)
        
        # Step 3: Perform health check
        response = self.perform_health_check(agent_name)
        if response is None:
            result['final_status'] = 'HEALTH_CHECK_FAILED'
            self.terminate_agent(agent_name)
            return result
        
        result['health_check_success'] = True
        result['response_data'] = response
        
        # Step 4: Validate response
        if self.validate_response(agent_name, response):
            result['response_validation'] = True
            result['final_status'] = 'SUCCESS'
        else:
            result['final_status'] = 'VALIDATION_FAILED'
        
        # Step 5: Terminate agent
        self.terminate_agent(agent_name)
        
        return result
    
    def run_validation(self):
        """Run health check validation on all agents"""
        print("🎯 AGENT HEALTH CHECK VALIDATION")
        print("=" * 60)
        
        results = {}
        
        for agent_name in self.agents.keys():
            try:
                result = self.test_agent(agent_name)
                results[agent_name] = result
            except Exception as e:
                print(f"❌ Unexpected error testing {agent_name}: {str(e)}")
                results[agent_name] = {
                    'agent_name': agent_name,
                    'launch_success': False,
                    'health_check_success': False,
                    'response_validation': False,
                    'response_data': None,
                    'final_status': 'ERROR',
                    'error': str(e)
                }
        
        # Generate final report
        self.generate_report(results)
    
    def generate_report(self, results: Dict[str, Dict[str, Any]]):
        """Generate final validation report"""
        print(f"\n{'='*60}")
        print("📋 VALIDATION REPORT")
        print(f"{'='*60}")
        
        success_count = 0
        total_count = len(results)
        
        for agent_name, result in results.items():
            status_icon = "✅" if result['final_status'] == 'SUCCESS' else "❌"
            print(f"\n{status_icon} {agent_name}: {result['final_status']}")
            
            if result['final_status'] == 'SUCCESS':
                success_count += 1
                print(f"   📊 Response: {json.dumps(result['response_data'], indent=2)}")
            else:
                if result['response_data']:
                    print(f"   📊 Response: {json.dumps(result['response_data'], indent=2)}")
                if 'error' in result:
                    print(f"   ❌ Error: {result['error']}")
        
        print(f"\n{'='*60}")
        print(f"📈 SUMMARY: {success_count}/{total_count} agents passed validation")
        
        if success_count == total_count:
            print("🎉 ALL AGENTS HEALTH CHECK VALIDATED")
        else:
            print("⚠️ SOME AGENTS FAILED HEALTH CHECK")
        
        print(f"{'='*60}")
    
    def cleanup(self):
        """Cleanup all running processes"""
        print("\n🧹 Cleaning up...")
        for agent_name in list(self.processes.keys()):
            self.terminate_agent(agent_name)

def main():
    validator = AgentHealthValidator()
    
    try:
        validator.run_validation()
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
    finally:
        validator.cleanup()

if __name__ == "__main__":
    main() 