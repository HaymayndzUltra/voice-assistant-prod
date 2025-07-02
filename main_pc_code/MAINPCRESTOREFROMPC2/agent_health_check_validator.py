#!/usr/bin/env python3
"""
Agent Health Check Validator
Performs comprehensive health check validation on target agents
"""

import subprocess
import zmq
import json
import time
import signal
import sys
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

class AgentHealthValidator:
    def __init__(self):
        self.target_agents = [
            {
                "name": "MoodTrackerAgent",
                "script_path": "agents/mood_tracker_agent.py",
                "host": "localhost",
                "port": 5704,
                "health_port": 5705,
                "health_action": "health"  # Base agent format
            },
            {
                "name": "HumanAwarenessAgent", 
                "script_path": "agents/human_awareness_agent.py",
                "host": "localhost",
                "port": 5705,
                "health_port": 5706,
                "health_action": "health_check"  # Agent-specific format
            }
        ]
        self.processes = {}
        self.results = {}
        
    def launch_agent(self, agent_config: Dict[str, Any]) -> Optional[subprocess.Popen]:
        """Launch an agent in isolation as a separate subprocess."""
        try:
            print(f"🚀 Launching {agent_config['name']}...")
            print(f"   Script: {agent_config['script_path']}")
            print(f"   Port: {agent_config['port']}")
            
            # Launch the agent process without command line arguments
            # Agents will use their default port configuration
            process = subprocess.Popen([
                sys.executable,
                agent_config['script_path']
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.processes[agent_config['name']] = process
            print(f"   ✅ Process started with PID: {process.pid}")
            return process
            
        except Exception as e:
            print(f"   ❌ Failed to launch {agent_config['name']}: {e}")
            return None
    
    def perform_health_check(self, agent_config: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Perform health check on agent's health port."""
        try:
            print(f"🔍 Performing health check on {agent_config['name']}...")
            print(f"   Health port: {agent_config['health_port']}")
            
            # Wait 5 seconds for initialization
            print("   ⏳ Waiting 5 seconds for agent initialization...")
            time.sleep(5)
            
            # Create ZMQ client
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 10000)  # 10 second timeout
            socket.setsockopt(zmq.SNDTIMEO, 5000)   # 5 second timeout
            
            # Connect to health port
            socket.connect(f"tcp://{agent_config['host']}:{agent_config['health_port']}")
            
            # Send health check request using agent-specific action
            request = {'action': agent_config['health_action']}
            print(f"   📤 Sending request: {request}")
            socket.send_json(request)
            
            # Receive response
            print("   📥 Waiting for response...")
            response_bytes = socket.recv()
            response = json.loads(response_bytes.decode('utf-8'))
            
            print(f"   📋 Response received: {json.dumps(response, indent=2)}")
            
            # Validate response
            is_valid = self._validate_health_response(response)
            
            socket.close()
            context.term()
            
            return is_valid, response
            
        except zmq.error.Again:
            print("   ❌ Timeout: No response within 10 seconds")
            return False, {"error": "Timeout - no response received"}
        except json.JSONDecodeError as e:
            print(f"   ❌ Invalid JSON response: {e}")
            return False, {"error": f"Invalid JSON response: {e}"}
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            return False, {"error": str(e)}
    
    def _validate_health_response(self, response: Dict[str, Any]) -> bool:
        """Validate the health check response."""
        try:
            # Check if response is a valid JSON object
            if not isinstance(response, dict):
                print("   ❌ Response is not a JSON object")
                return False
            
            # Check for required 'status' field
            if 'status' not in response:
                print("   ❌ Response missing 'status' field")
                return False
            
            # Check if status is 'ok' or 'success'
            status = response['status']
            if status not in ['ok', 'success']:
                print(f"   ❌ Status is not 'ok' or 'success': {status}")
                return False
            
            # Check for initialization_status (optional but preferred)
            if 'initialization_status' in response:
                print("   ✅ Found initialization_status field")
            
            print("   ✅ Health check response validation passed")
            return True
            
        except Exception as e:
            print(f"   ❌ Response validation error: {e}")
            return False
    
    def terminate_agent(self, agent_name: str):
        """Terminate an agent process."""
        if agent_name in self.processes:
            process = self.processes[agent_name]
            try:
                print(f"🛑 Terminating {agent_name} (PID: {process.pid})...")
                process.terminate()
                process.wait(timeout=5)
                print(f"   ✅ {agent_name} terminated successfully")
            except subprocess.TimeoutExpired:
                print(f"   ⚠️  Force killing {agent_name}...")
                process.kill()
                process.wait()
                print(f"   ✅ {agent_name} force killed")
            except Exception as e:
                print(f"   ❌ Error terminating {agent_name}: {e}")
    
    def run_validation(self):
        """Run the complete health check validation process."""
        print("=" * 80)
        print("🔬 AGENT HEALTH CHECK VALIDATION")
        print("=" * 80)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Target agents: {len(self.target_agents)}")
        print()
        
        for agent_config in self.target_agents:
            print(f"🎯 Testing: {agent_config['name']}")
            print("-" * 60)
            
            # Step 1: Launch agent
            process = self.launch_agent(agent_config)
            if not process:
                self.results[agent_config['name']] = {
                    "status": "FAILED",
                    "error": "Failed to launch agent",
                    "response": None
                }
                continue
            
            # Step 2: Perform health check
            is_valid, response = self.perform_health_check(agent_config)
            
            # Step 3: Determine final status
            if is_valid:
                final_status = "✅ HEALTH CHECK VALIDATED"
            else:
                final_status = "❌ HEALTH CHECK FAILED"
            
            # Store results
            self.results[agent_config['name']] = {
                "status": final_status,
                "response": response,
                "is_valid": is_valid
            }
            
            # Step 4: Terminate agent
            self.terminate_agent(agent_config['name'])
            print()
        
        # Generate final report
        self._generate_report()
    
    def _generate_report(self):
        """Generate the final validation report."""
        print("=" * 80)
        print("📊 VALIDATION REPORT")
        print("=" * 80)
        print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        for agent_name, result in self.results.items():
            print(f"🎯 {agent_name}")
            print("-" * 40)
            print(f"Status: {result['status']}")
            
            if result['response']:
                print("Response:")
                print(json.dumps(result['response'], indent=2))
            else:
                print("Response: None")
            
            print()
        
        # Summary
        print("=" * 80)
        print("📈 SUMMARY")
        print("=" * 80)
        
        total_agents = len(self.results)
        successful_agents = sum(1 for r in self.results.values() if r['is_valid'])
        failed_agents = total_agents - successful_agents
        
        print(f"Total agents tested: {total_agents}")
        print(f"✅ Successful: {successful_agents}")
        print(f"❌ Failed: {failed_agents}")
        
        if successful_agents == total_agents:
            print("🎉 ALL AGENTS PASSED HEALTH CHECK VALIDATION!")
        else:
            print("⚠️  SOME AGENTS FAILED HEALTH CHECK VALIDATION")
        
        print("=" * 80)

def main():
    """Main entry point."""
    validator = AgentHealthValidator()
    
    try:
        validator.run_validation()
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        # Clean up any running processes
        for agent_name in validator.processes:
            validator.terminate_agent(agent_name)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        # Clean up any running processes
        for agent_name in validator.processes:
            validator.terminate_agent(agent_name)
        sys.exit(1)

if __name__ == "__main__":
    main() 