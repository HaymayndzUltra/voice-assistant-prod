#!/usr/bin/env python3
"""
Comprehensive Health Check for Voice Assistant Agents
Tests EmotionSynthesisAgent, ToneDetector, and VoiceProfiler agents
"""

import subprocess
import time
import zmq
import json
import logging
import sys
import signal
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgentHealthChecker:
    def __init__(self):
        self.processes = {}
        self.results = {}
        
    def launch_agent(self, name: str, script_path: str, port: int) -> bool:
        """Launch an agent as a subprocess."""
        try:
            logger.info(f"Launching {name} on port {port}...")
            cmd = [sys.executable, script_path, "--port", str(port)]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes[name] = process
            logger.info(f"✅ {name} launched successfully (PID: {process.pid})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to launch {name}: {e}")
            return False
    
    def wait_for_initialization(self, name: str, wait_time: int = 8) -> bool:
        """Wait for agent initialization."""
        logger.info(f"Waiting {wait_time} seconds for {name} to initialize...")
        time.sleep(wait_time)
        
        if name in self.processes:
            process = self.processes[name]
            if process.poll() is None:  # Process is still running
                logger.info(f"✅ {name} appears to be running")
                return True
            else:
                logger.error(f"❌ {name} process terminated during initialization")
                return False
        return False
    
    def send_health_check(self, name: str, port: int, action: str = "health_check") -> Optional[Dict]:
        """Send health check request to agent."""
        try:
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            socket.setsockopt(zmq.SNDTIMEO, 5000)  # 5 second timeout
            
            health_port = port + 1
            socket.connect(f"tcp://localhost:{health_port}")
            
            # Send health check request
            request = {"action": action}
            logger.info(f"Sending health check to {name} on port {health_port}: {request}")
            socket.send_json(request)
            
            # Receive response
            response = socket.recv_json()
            logger.info(f"Received response from {name}: {response}")
            
            socket.close()
            context.term()
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Health check failed for {name}: {e}")
            return None
    
    def validate_response(self, name: str, response: Dict) -> bool:
        """Validate the health check response."""
        try:
            # Check if response is valid JSON
            if not isinstance(response, dict):
                logger.error(f"❌ {name}: Response is not a dictionary")
                return False
            
            # Check for status field
            if 'status' not in response:
                logger.error(f"❌ {name}: No 'status' field in response")
                return False
            
            # Check if status is 'ok'
            if response['status'] != 'ok':
                logger.error(f"❌ {name}: Status is not 'ok' (got: {response['status']})")
                return False
            
            # Check for initialization_status (optional but preferred)
            if 'initialization_status' in response:
                logger.info(f"✅ {name}: Has initialization_status field")
            
            logger.info(f"✅ {name}: Health check response validated successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ {name}: Error validating response: {e}")
            return False
    
    def terminate_agent(self, name: str) -> bool:
        """Terminate an agent process."""
        try:
            if name in self.processes:
                process = self.processes[name]
                logger.info(f"Terminating {name} (PID: {process.pid})...")
                
                # Try graceful termination first
                process.terminate()
                time.sleep(2)
                
                # Force kill if still running
                if process.poll() is None:
                    logger.warning(f"Force killing {name}...")
                    process.kill()
                    time.sleep(1)
                
                # Check if terminated
                if process.poll() is not None:
                    logger.info(f"✅ {name} terminated successfully")
                    return True
                else:
                    logger.error(f"❌ Failed to terminate {name}")
                    return False
            else:
                logger.warning(f"No process found for {name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error terminating {name}: {e}")
            return False
    
    def test_agent(self, name: str, script_path: str, port: int, action: str = "health_check") -> Dict:
        """Test a single agent."""
        logger.info(f"\n{'='*60}")
        logger.info(f"TESTING {name.upper()}")
        logger.info(f"{'='*60}")
        
        result = {
            "name": name,
            "script_path": script_path,
            "port": port,
            "health_port": port + 1,
            "launch_success": False,
            "initialization_success": False,
            "health_check_success": False,
            "response_valid": False,
            "response_data": None,
            "termination_success": False,
            "overall_success": False
        }
        
        try:
            # Step 1: Launch agent
            result["launch_success"] = self.launch_agent(name, script_path, port)
            if not result["launch_success"]:
                return result
            
            # Step 2: Wait for initialization
            result["initialization_success"] = self.wait_for_initialization(name)
            if not result["initialization_success"]:
                return result
            
            # Step 3: Send health check
            response = self.send_health_check(name, port, action)
            result["health_check_success"] = response is not None
            result["response_data"] = response
            
            if result["health_check_success"]:
                # Step 4: Validate response
                result["response_valid"] = self.validate_response(name, response)
            
            # Step 5: Terminate agent
            result["termination_success"] = self.terminate_agent(name)
            
            # Overall success
            result["overall_success"] = (
                result["launch_success"] and
                result["initialization_success"] and
                result["health_check_success"] and
                result["response_valid"] and
                result["termination_success"]
            )
            
        except Exception as e:
            logger.error(f"❌ Unexpected error testing {name}: {e}")
            result["overall_success"] = False
        
        return result
    
    def run_all_tests(self) -> Dict:
        """Run health checks for all agents."""
        agents = [
            {
                "name": "EmotionSynthesisAgent",
                "script_path": "agents/emotion_synthesis_agent.py",
                "port": 5706,
                "action": "health_check"
            },
            {
                "name": "ToneDetector",
                "script_path": "agents/tone_detector.py",
                "port": 5625,
                "action": "health_check"
            },
            {
                "name": "VoiceProfiler",
                "script_path": "agents/voice_profiling_agent.py",
                "port": 5708,
                "action": "health_check"
            }
        ]
        
        logger.info("Starting comprehensive health check for all agents...")
        
        for agent_config in agents:
            result = self.test_agent(**agent_config)
            self.results[agent_config["name"]] = result
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a comprehensive report."""
        report = []
        report.append("=" * 80)
        report.append("COMPREHENSIVE HEALTH CHECK REPORT")
        report.append("=" * 80)
        report.append("")
        
        total_agents = len(self.results)
        successful_agents = sum(1 for result in self.results.values() if result["overall_success"])
        
        report.append(f"SUMMARY:")
        report.append(f"  Total Agents Tested: {total_agents}")
        report.append(f"  Successful: {successful_agents}")
        report.append(f"  Failed: {total_agents - successful_agents}")
        report.append(f"  Success Rate: {(successful_agents/total_agents)*100:.1f}%")
        report.append("")
        
        for name, result in self.results.items():
            status = "✅ PASSED" if result["overall_success"] else "❌ FAILED"
            report.append(f"{name}: {status}")
            report.append(f"  Port: {result['port']} (Health: {result['health_port']})")
            report.append(f"  Launch: {'✅' if result['launch_success'] else '❌'}")
            report.append(f"  Initialization: {'✅' if result['initialization_success'] else '❌'}")
            report.append(f"  Health Check: {'✅' if result['health_check_success'] else '❌'}")
            report.append(f"  Response Valid: {'✅' if result['response_valid'] else '❌'}")
            report.append(f"  Termination: {'✅' if result['termination_success'] else '❌'}")
            
            if result["response_data"]:
                report.append(f"  Response: {json.dumps(result['response_data'], indent=2)}")
            
            report.append("")
        
        report.append("=" * 80)
        report.append("END OF REPORT")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def cleanup(self):
        """Cleanup all processes."""
        logger.info("Cleaning up all processes...")
        for name in list(self.processes.keys()):
            self.terminate_agent(name)

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    logger.info("Received interrupt signal, cleaning up...")
    if hasattr(signal_handler, 'checker'):
        signal_handler.checker.cleanup()
    sys.exit(0)

def main():
    """Main function."""
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    checker = AgentHealthChecker()
    signal_handler.checker = checker  # Store reference for signal handler
    
    try:
        # Run all tests
        results = checker.run_all_tests()
        
        # Generate and print report
        report = checker.generate_report()
        print(report)
        
        # Save report to file
        with open("health_check_report.txt", "w") as f:
            f.write(report)
        
        logger.info("Report saved to health_check_report.txt")
        
        # Return appropriate exit code
        successful_agents = sum(1 for result in results.values() if result["overall_success"])
        total_agents = len(results)
        
        if successful_agents == total_agents:
            logger.info("🎉 ALL AGENTS PASSED HEALTH CHECK!")
            return 0
        else:
            logger.error(f"❌ {total_agents - successful_agents} AGENT(S) FAILED HEALTH CHECK!")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Unexpected error during health check: {e}")
        return 1
    finally:
        checker.cleanup()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 