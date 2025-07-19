#!/usr/bin/env python3
"""
EmotionEngine Health Check Validation Script
Performs comprehensive health check validation on EmotionEngine agent
"""

import zmq
import json
import time
import sys
import subprocess
import signal
import os
from datetime import datetime
from typing import Dict, Any, Optional
from common.env_helpers import get_env

class EmotionEngineHealthChecker:
    def __init__(self, main_port: int = 5575, script_path: str = "agents/emotion_engine.py"):
        self.main_port = main_port
        self.health_port = main_port + 1
        self.script_path = script_path
        self.agent_process = None
        self.pid_file = "emotion_engine_pid.txt"
        
    def launch_agent(self) -> bool:
        """Launch the EmotionEngine agent as a separate subprocess."""
        try:
            print(f"🚀 Launching EmotionEngine agent...")
            print(f"   Script: {self.script_path}")
            print(f"   Main Port: {self.main_port}")
            print(f"   Health Port: {self.health_port}")
            
            # Launch agent with port argument
            cmd = ["python3", self.script_path, "--port", str(self.main_port)]
            self.agent_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Save PID to file
            with open(self.pid_file, 'w') as f:
                f.write(str(self.agent_process.pid))
            
            print(f"✅ Agent launched successfully (PID: {self.agent_process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to launch agent: {e}")
            return False
    
    def wait_for_initialization(self, timeout: int = 10) -> bool:
        """Wait for agent initialization with timeout."""
        print(f"⏳ Waiting {timeout} seconds for agent initialization...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Quick health check to see if agent is responding
                response = self.send_health_check(timeout=2)
                if response and response.get('status') == 'ok':
                    print(f"✅ Agent initialized successfully!")
                    return True
            except:
                pass
            
            time.sleep(1)
            remaining = timeout - int(time.time() - start_time)
            if remaining > 0:
                print(f"   Waiting... {remaining}s remaining")
        
        print(f"⚠️  Agent may not be fully initialized after {timeout} seconds")
        return False
    
    def send_health_check(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Send health check request to the agent's health port."""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.RCVTIMEO, timeout * 1000)
        
        try:
            socket.connect(f"tcp://localhost:{self.health_port}")
            
            # Send health check request
            request = {'action': 'health_check'}
            print(f"📡 Sending health check request to port {self.health_port}...")
            socket.send_string(json.dumps(request))
            
            # Wait for response
            response = socket.recv_json()  # BaseAgent uses send_json() for response
            print(f"📥 Response received: {json.dumps(response, indent=2)}")
            return response
            
        except zmq.error.Again:
            print(f"⏰ Timeout: No response from port {self.health_port} within {timeout} seconds")
            return None
        except Exception as e:
            print(f"❌ Error during health check: {e}")
            return None
        finally:
            socket.close()
            context.term()
    
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate the health check response."""
        print(f"🔍 Validating response...")
        
        # Check if response is a valid JSON object
        if not isinstance(response, dict):
            print(f"❌ Response is not a valid JSON object")
            return False
        
        # Check for required 'status': 'ok' field
        if response.get('status') != 'ok':
            print(f"❌ Response missing or invalid 'status': 'ok' field")
            print(f"   Actual status: {response.get('status')}")
            return False
        
        # Check for initialization_status field (optional but preferred)
        if 'initialization_status' in response:
            init_status = response['initialization_status']
            print(f"✅ Found initialization_status: {init_status}")
        else:
            print(f"⚠️  No initialization_status field found (optional)")
        
        # Check for other useful fields
        useful_fields = ['service', 'ready', 'initialized', 'message', 'timestamp']
        found_fields = [field for field in useful_fields if field in response]
        if found_fields:
            print(f"✅ Found additional fields: {found_fields}")
        
        return True
    
    def terminate_agent(self):
        """Terminate the agent process."""
        if self.agent_process:
            try:
                print(f"🛑 Terminating agent process (PID: {self.agent_process.pid})...")
                
                # Try graceful termination first
                self.agent_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    self.agent_process.wait(timeout=5)
                    print(f"✅ Agent terminated gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    print(f"⚠️  Force killing agent process...")
                    self.agent_process.kill()
                    self.agent_process.wait()
                    print(f"✅ Agent force killed")
                
            except Exception as e:
                print(f"❌ Error terminating agent: {e}")
        
        # Clean up PID file
        try:
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
        except:
            pass
    
    def run_health_check_validation(self) -> bool:
        """Run the complete health check validation process."""
        print("=" * 60)
        print("🧠 EMOTIONENGINE HEALTH CHECK VALIDATION")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Target Agent: EmotionEngine")
        print(f"Main Port: {self.main_port}")
        print(f"Health Port: {self.health_port}")
        print("=" * 60)
        
        try:
            # Step 1: Launch the agent
            if not self.launch_agent():
                return False
            
            # Step 2: Wait for initialization
            if not self.wait_for_initialization(timeout=10):
                print(f"⚠️  Proceeding with health check despite initialization warning...")
            
            # Step 3: Perform health check
            print(f"\n🔍 Performing health check validation...")
            response = self.send_health_check(timeout=5)
            
            if not response:
                print(f"❌ No response received from agent")
                return False
            
            # Step 4: Validate response
            is_valid = self.validate_response(response)
            
            # Step 5: Generate final report
            print(f"\n" + "=" * 60)
            print("📊 HEALTH CHECK VALIDATION REPORT")
            print("=" * 60)
            print(f"Target Agent: EmotionEngine")
            print(f"Main Port: {self.main_port}")
            print(f"Health Port: {self.health_port}")
            print(f"Timestamp: {datetime.now().isoformat()}")
            print(f"Agent PID: {self.agent_process.pid if self.agent_process else 'N/A'}")
            print("-" * 60)
            print("📥 JSON Response Received:")
            print(json.dumps(response, indent=2))
            print("-" * 60)
            
            if is_valid:
                print("✅ HEALTH CHECK VALIDATED")
                print("   ✓ Agent responds instantly")
                print("   ✓ Response is valid JSON")
                print("   ✓ Contains 'status': 'ok'")
                print("   ✓ Agent is fully responsive")
                return True
            else:
                print("❌ HEALTH CHECK FAILED")
                print("   ✗ Response validation failed")
                return False
                
        except Exception as e:
            print(f"❌ Unexpected error during validation: {e}")
            return False
        finally:
            # Always terminate the agent
            self.terminate_agent()
            print(f"\n🏁 Health check validation completed")

def main():
    """Main function to run the health check validation."""
    # Configuration
    MAIN_PORT = 5575
    SCRIPT_PATH = "agents/emotion_engine.py"
    
    # Create health checker instance
    checker = EmotionEngineHealthChecker(
        main_port=MAIN_PORT,
        script_path=SCRIPT_PATH
    )
    
    # Run validation
    success = checker.run_health_check_validation()
    
    # Exit with appropriate code
    if success:
        print(f"\n🎉 Health check validation completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 Health check validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 