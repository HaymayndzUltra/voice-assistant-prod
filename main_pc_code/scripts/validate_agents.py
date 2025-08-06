#!/usr/bin/env python3
"""
Agent Validation Script
Tests agent initialization and running capabilities
"""

import sys
import time
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
import json
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "agent_validation.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentValidator:
    def __init__(self):
        self.results: Dict[str, Dict[str, Any]] = {}
        
    def validate_agent(self, agent_path: str, timeout: int = 10) -> Dict[str, Any]:
        """Validate a single agent.
        
        Args:
            agent_path: Path to the agent script
            timeout: Maximum time to wait for agent to start (seconds)
            
        Returns:
            Dictionary containing validation results
        """
        logger.info(f"Validating agent: {agent_path}")
        
        try:
            # Start agent in a subprocess
            process = subprocess.Popen(
                [sys.executable, agent_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for agent to start
            start_time = time.time()
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    # Process ended before timeout
                    stdout, stderr = process.communicate()
                    return {
                        "success": False,
                        "error": f"Agent process ended unexpectedly. Exit code: {process.returncode}",
                        "stdout": stdout,
                        "stderr": stderr
                    }
                
                # Check if agent is running
                if self._check_agent_health(process.pid):
                    # Agent is running successfully
                    process.terminate()
                    return {
                        "success": True,
                        "pid": process.pid,
                        "uptime": time.time() - start_time
                    }
                
                time.sleep(0.1)
            
            # Timeout reached
            process.terminate()
            return {
                "success": False,
                "error": f"Timeout reached after {timeout} seconds",
                "stdout": process.stdout.read() if process.stdout else "",
                "stderr": process.stderr.read() if process.stderr else ""
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _check_agent_health(self, pid: int) -> bool:
        """Check if agent process is healthy.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if agent is healthy, False otherwise
        """
        try:
            import psutil

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
    except ImportError as e:
        print(f"Import error: {e}")
            process = psutil.Process(pid)
            return process.is_running() and process.status() == psutil.STATUS_RUNNING
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def validate_all(self, agent_paths: list[str]) -> Dict[str, Dict[str, Any]]:
        """Validate multiple agents.
        
        Args:
            agent_paths: List of paths to agent scripts
            
        Returns:
            Dictionary containing validation results for each agent
        """
        for agent_path in agent_paths:
            self.results[agent_path] = self.validate_agent(agent_path)
        
        return self.results
    
    def print_results(self):
        """Print validation results in a formatted way."""
        print("\nAgent Validation Results:")
        print("=" * 50)
        
        for agent_path, result in self.results.items():
            print(f"\nAgent: {Path(agent_path).name}")
            print("-" * 30)
            
            if result["success"]:
                print(f"Status: SUCCESS")
                print(f"PID: {result['pid']}")
                print(f"Uptime: {result['uptime']:.2f} seconds")
            else:
                print(f"Status: FAILED")
                print(f"Error: {result['error']}")
                if result.get("stdout"):
                    print("\nStdout:")
                    print(result["stdout"])
                if result.get("stderr"):
                    print("\nStderr:")
                    print(result["stderr"])
            
            print("-" * 30)

def main():
    # List of agents to validate
    agents = [
        "agents/MetaCognitionAgent.py",
        "agents/active_learning_monitor.py",
        "agents/unified_planning_agent.py"
    ]
    
    validator = AgentValidator()
    validator.validate_all(agents)
    validator.print_results()

if __name__ == "__main__":
    main() 