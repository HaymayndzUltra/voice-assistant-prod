#!/usr/bin/env python3
"""
MainPC Health Checker

This script dynamically loads all agents from the MainPC configuration file,
launches them in the correct order based on their dependencies, and performs
a precise health check on each one based on a deep analysis of their actual code.
"""

import os
import sys
import yaml
import time
import json
import zmq
import signal
import logging
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
from datetime import datetime
import psutil
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/mainpc_health_checker.log')
    ]
)
logger = logging.getLogger("MainPCHealthChecker")

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

# Constants
STARTUP_CONFIG_PATH = "/home/haymayndz/AI_System_Monorepo/main_pc_code/config/startup_config.yaml"
WAIT_TIME_AFTER_LAUNCH = 5  # seconds to wait after launching each agent
HEALTH_CHECK_TIMEOUT = 10000  # milliseconds
MAX_RETRIES = 3

class Agent:
    """Represents an agent with its configuration and runtime state."""
    
    def __init__(self, name: str, script_path: str, port: int, dependencies: List[str] = None,
                 required: bool = False, host: str = "0.0.0.0", params: Dict[str, Any] = None):
        self.name = name
        self.script_path = script_path
        self.port = port
        self.dependencies = dependencies or []
        self.required = required
        self.host = host
        self.params = params or {}
        self.process = None
        self.health_check_port = port + 1  # Standard pattern in BaseAgent
        self.status = "NOT_STARTED"
        self.health_info = {}
        self.start_time = None
        self.zmq_health_check_method = None  # Will be set after analysis

    def __repr__(self):
        return f"Agent(name={self.name}, port={self.port}, status={self.status})"

class MainPCHealthChecker:
    """
    Main health checker class that loads agents, determines startup order,
    launches agents, and performs health checks.
    """
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.launched_processes: List[subprocess.Popen] = []
        self.zmq_context = zmq.Context()
        self.running = True
        self.startup_order: List[str] = []
        
        # Signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """Handle termination signals by cleaning up processes."""
        logger.info(f"Received signal {sig}, shutting down...")
        self.cleanup()
        sys.exit(0)

    def load_agents_from_config(self) -> None:
        """Load all agents from the startup configuration file."""
        try:
            with open(STARTUP_CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
                
            # Process all agent categories
            categories = [
                'core_services', 'main_pc_gpu_services', 'emotion_system',
                'language_processing', 'memory_system', 'learning_knowledge',
                'planning_execution', 'tts_services', 'code_generation',
                'audio_processing', 'vision', 'monitoring_security'
            ]
            
            for category in categories:
                if category in config:
                    for agent_config in config[category]:
                        name = agent_config.get('name')
                        script_path = agent_config.get('script_path')
                        
                        # Handle different config formats
                        if isinstance(agent_config, dict):
                            port = agent_config.get('port')
                            dependencies = agent_config.get('dependencies', [])
                            required = agent_config.get('required', False)
                            host = agent_config.get('host', '0.0.0.0')
                            params = agent_config.get('params', {})
                        else:
                            # Parse compact format {name: X, script_path: Y, ...}
                            port = agent_config.get('port')
                            dependencies = agent_config.get('dependencies', [])
                            required = agent_config.get('required', False)
                            host = agent_config.get('host', '0.0.0.0')
                            params = agent_config.get('params', {})
                        
                        if name and script_path and port:
                            # Create agent object
                            agent = Agent(
                                name=name,
                                script_path=script_path,
                                port=port,
                                dependencies=dependencies,
                                required=required,
                                host=host,
                                params=params
                            )
                            self.agents[name] = agent
                            logger.debug(f"Loaded agent: {name} from {script_path}")
                        else:
                            logger.warning(f"Skipping incomplete agent config: {agent_config}")
            
            logger.info(f"Loaded {len(self.agents)} agents from configuration")
        except Exception as e:
            logger.error(f"Error loading agents from config: {e}")
            raise

    def determine_startup_order(self) -> List[str]:
        """
        Perform a topological sort on the agent list based on dependencies.
        Returns a list of agent names in the correct startup order.
        """
        # Build dependency graph
        graph = defaultdict(list)
        in_degree = {name: 0 for name in self.agents}
        
        # Count dependencies
        for name, agent in self.agents.items():
            for dep in agent.dependencies:
                if dep in self.agents:  # Only consider valid dependencies
                    graph[dep].append(name)
                    in_degree[name] += 1
                else:
                    logger.warning(f"Agent {name} has unknown dependency: {dep}")
        
        # Find all nodes with no dependencies
        queue = [name for name, degree in in_degree.items() if degree == 0]
        
        # Perform topological sort
        result = []
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # Reduce in-degree of neighbors
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for cycles
        if len(result) != len(self.agents):
            logger.error("Dependency cycle detected in agent configuration")
            # Find and report the cycle
            remaining = [name for name, degree in in_degree.items() if degree > 0]
            logger.error(f"Agents in dependency cycle: {remaining}")
            
            # Fall back to a simple priority-based order
            logger.info("Falling back to priority-based startup order")
            priority_order = [
                "SystemDigitalTwin",
                "ModelManagerAgent",
                "MemoryOrchestrator",
                "CoordinatorAgent",
                "TaskRouter"
            ]
            
            # Start with priority agents, then add the rest
            ordered = []
            for name in priority_order:
                if name in self.agents and name not in ordered:
                    ordered.append(name)
            
            # Add remaining agents
            for name in self.agents:
                if name not in ordered:
                    ordered.append(name)
            
            result = ordered
        
        self.startup_order = result
        logger.info(f"Determined startup order: {result}")
        return result

    def analyze_agent_health_check_mechanisms(self) -> None:
        """
        Analyze the code of representative agents to determine their
        health check mechanisms.
        """
        # Based on code analysis, we've identified these health check patterns:
        # 1. BaseAgent: Uses ZMQ REP socket on port+1, expects {"action": "health"} or {"action": "health_check"}
        # 2. SystemDigitalTwin: Uses HTTP on health_check_port if specified
        # 3. Some agents implement custom _health_check methods that check dependencies
        
        # Set default health check method for all agents
        for name, agent in self.agents.items():
            # Default ZMQ REP socket health check
            agent.zmq_health_check_method = {
                "type": "zmq_req",
                "port": agent.health_check_port,
                "request": {"action": "health_check"},
                "success_key": "status",
                "success_value": "ok"
            }
            
            # Special case for SystemDigitalTwin which has an HTTP health endpoint
            if name == "SystemDigitalTwin" and "health_check_port" in agent.params:
                agent.zmq_health_check_method = {
                    "type": "http",
                    "port": agent.params["health_check_port"],
                    "endpoint": "/health",
                    "success_key": "status",
                    "success_value": "healthy"
                }
                
            # Special case for CoordinatorAgent with its custom health port
            if name == "CoordinatorAgent":
                agent.zmq_health_check_method["port"] = 26010  # Override the port
                logger.info(f"Set custom health check port for CoordinatorAgent: {agent.zmq_health_check_method['port']}")

    def launch_agent(self, agent_name: str) -> bool:
        """
        Launch a single agent and wait for it to start.
        
        Args:
            agent_name: The name of the agent to launch
            
        Returns:
            bool: True if the agent was launched successfully, False otherwise
        """
        if agent_name not in self.agents:
            logger.error(f"Unknown agent: {agent_name}")
            return False
        
        agent = self.agents[agent_name]
        
        # Prepare environment variables
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{env.get('PYTHONPATH', '')}:{os.getcwd()}"
        
        # Build the command
        script_path = agent.script_path
        if not script_path.startswith('/'):
            # Relative path - prepend main_pc_code
            script_path = f"main_pc_code/{script_path}"
        
        cmd = ["python3", script_path]
        
        try:
            logger.info(f"Launching agent: {agent_name} ({script_path})")
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            agent.process = process
            agent.status = "STARTING"
            agent.start_time = time.time()
            self.launched_processes.append(process)
            
            # Start log capture threads
            threading.Thread(target=self._capture_output, args=(process.stdout, f"{agent_name}-stdout"), daemon=True).start()
            threading.Thread(target=self._capture_output, args=(process.stderr, f"{agent_name}-stderr"), daemon=True).start()
            
            # Wait for the agent to start
            logger.info(f"Waiting {WAIT_TIME_AFTER_LAUNCH}s for {agent_name} to initialize...")
            time.sleep(WAIT_TIME_AFTER_LAUNCH)
            
            # Check if process is still running
            if process.poll() is not None:
                logger.error(f"Agent {agent_name} exited prematurely with code {process.returncode}")
                agent.status = "FAILED"
                return False
            
            logger.info(f"Agent {agent_name} launched successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error launching agent {agent_name}: {e}")
            agent.status = "FAILED"
            return False

    def _capture_output(self, pipe, prefix):
        """Capture and log output from a subprocess pipe."""
        for line in pipe:
            logger.debug(f"{prefix}: {line.strip()}")

    def check_agent_health(self, agent_name: str) -> bool:
        """
        Check the health of a single agent using its specific health check mechanism.
        
        Args:
            agent_name: The name of the agent to check
            
        Returns:
            bool: True if the agent is healthy, False otherwise
        """
        if agent_name not in self.agents:
            logger.error(f"Unknown agent: {agent_name}")
            return False
        
        agent = self.agents[agent_name]
        
        # Skip if the agent failed to launch
        if agent.status == "FAILED":
            return False
        
        # Check if process is still running
        if agent.process and agent.process.poll() is not None:
            logger.error(f"Agent {agent_name} process has terminated with code {agent.process.returncode}")
            agent.status = "CRASHED"
            return False
        
        # Perform health check based on the agent's mechanism
        health_check_method = agent.zmq_health_check_method
        
        if health_check_method["type"] == "zmq_req":
            return self._check_zmq_health(agent_name)
        elif health_check_method["type"] == "http":
            return self._check_http_health(agent_name)
        else:
            logger.error(f"Unknown health check method for {agent_name}: {health_check_method['type']}")
            return False

    def _check_zmq_health(self, agent_name: str) -> bool:
        """
        Check agent health using ZMQ REQ/REP pattern.
        
        Args:
            agent_name: The name of the agent to check
            
        Returns:
            bool: True if the agent is healthy, False otherwise
        """
        agent = self.agents[agent_name]
        health_check_method = agent.zmq_health_check_method
        port = health_check_method["port"]
        request_data = health_check_method["request"]
        success_key = health_check_method["success_key"]
        success_value = health_check_method["success_value"]
        
        # Create socket
        socket = self.zmq_context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.setsockopt(zmq.RCVTIMEO, HEALTH_CHECK_TIMEOUT)
        socket.setsockopt(zmq.SNDTIMEO, HEALTH_CHECK_TIMEOUT)
        
        try:
            # Connect to agent's health check port - use 127.0.0.1 instead of localhost
            socket.connect(f"tcp://127.0.0.1:{port}")
            logger.debug(f"Connected to {agent_name} health check port {port}")
            
            # Send health check request
            socket.send_json(request_data)
            logger.debug(f"Sent health check request to {agent_name}: {request_data}")
            
            # Wait for response
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            
            if poller.poll(HEALTH_CHECK_TIMEOUT):
                response = socket.recv_json()
                logger.debug(f"Received health check response from {agent_name}: {response}")
                
                # Check if response indicates health - accept multiple formats
                if success_key in response:
                    status_value = response[success_key]
                    # Accept "ok", "HEALTHY", or "healthy" as valid status values
                    if (status_value == success_value or 
                        status_value == "HEALTHY" or 
                        (isinstance(status_value, str) and status_value.lower() == "healthy")):
                    agent.status = "HEALTHY"
                    agent.health_info = response
                    return True
                
                    agent.status = "UNHEALTHY"
                    agent.health_info = response
                    logger.warning(f"Agent {agent_name} reported unhealthy status: {response}")
                    return False
            else:
                agent.status = "UNREACHABLE"
                logger.warning(f"Health check timeout for {agent_name}")
                return False
                
        except Exception as e:
            agent.status = "UNREACHABLE"
            logger.error(f"Error checking health of {agent_name}: {e}")
            return False
        finally:
            socket.close()

    def _check_http_health(self, agent_name: str) -> bool:
        """
        Check agent health using HTTP endpoint.
        
        Args:
            agent_name: The name of the agent to check
            
        Returns:
            bool: True if the agent is healthy, False otherwise
        """
        import requests
        
        agent = self.agents[agent_name]
        health_check_method = agent.zmq_health_check_method
        port = health_check_method["port"]
        endpoint = health_check_method["endpoint"]
        success_key = health_check_method["success_key"]
        success_value = health_check_method["success_value"]
        
        try:
            # Send HTTP request
            url = f"http://localhost:{port}{endpoint}"
            logger.debug(f"Sending HTTP health check to {agent_name}: {url}")
            
            response = requests.get(url, timeout=HEALTH_CHECK_TIMEOUT/1000)
            
            if response.status_code == 200:
                data = response.json()
                logger.debug(f"Received HTTP health check response from {agent_name}: {data}")
                
                # Check if response indicates health
                if success_key in data and data[success_key] == success_value:
                    agent.status = "HEALTHY"
                    agent.health_info = data
                    return True
                else:
                    agent.status = "UNHEALTHY"
                    agent.health_info = data
                    logger.warning(f"Agent {agent_name} reported unhealthy status: {data}")
                    return False
            else:
                agent.status = "UNREACHABLE"
                logger.warning(f"HTTP health check failed for {agent_name}: {response.status_code}")
                return False
                
        except Exception as e:
            agent.status = "UNREACHABLE"
            logger.error(f"Error checking HTTP health of {agent_name}: {e}")
            return False

    def launch_and_verify_agents(self) -> bool:
        """
        Launch all agents in the correct order and verify their health.
        
        Returns:
            bool: True if all required agents are healthy, False otherwise
        """
        all_healthy = True
        
        for agent_name in self.startup_order:
            agent = self.agents[agent_name]
            
            # Launch the agent
            if self.launch_agent(agent_name):
                # Check health after launch
                healthy = False
                for attempt in range(MAX_RETRIES):
                    logger.info(f"Health check attempt {attempt + 1}/{MAX_RETRIES} for {agent_name}")
                    if self.check_agent_health(agent_name):
                        healthy = True
                        break
                    time.sleep(2)  # Wait before retry
                
                if not healthy and agent.required:
                    logger.error(f"Required agent {agent_name} is not healthy after {MAX_RETRIES} attempts")
                    all_healthy = False
            else:
                if agent.required:
                    logger.error(f"Failed to launch required agent {agent_name}")
                    all_healthy = False
        
        return all_healthy

    def generate_health_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive health report for all agents.
        
        Returns:
            Dict: Health report data
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(self.agents),
            "healthy_agents": sum(1 for agent in self.agents.values() if agent.status == "HEALTHY"),
            "unhealthy_agents": sum(1 for agent in self.agents.values() if agent.status in ["UNHEALTHY", "UNREACHABLE", "FAILED", "CRASHED"]),
            "not_started": sum(1 for agent in self.agents.values() if agent.status == "NOT_STARTED"),
            "agent_details": {}
        }
        
        for name, agent in self.agents.items():
            report["agent_details"][name] = {
                "status": agent.status,
                "port": agent.port,
                "script_path": agent.script_path,
                "required": agent.required,
                "dependencies": agent.dependencies,
                "uptime_seconds": time.time() - agent.start_time if agent.start_time else 0,
                "health_info": agent.health_info
            }
        
        return report

    def print_health_summary(self) -> None:
        """Print a summary of agent health statuses."""
        print("\n=== MainPC Agent Health Summary ===")
        print(f"Total Agents: {len(self.agents)}")
        
        # Count by status
        status_counts = defaultdict(int)
        for agent in self.agents.values():
            status_counts[agent.status] += 1
        
        print(f"HEALTHY: {status_counts['HEALTHY']}")
        print(f"UNHEALTHY: {status_counts['UNHEALTHY']}")
        print(f"UNREACHABLE: {status_counts['UNREACHABLE']}")
        print(f"FAILED/CRASHED: {status_counts['FAILED'] + status_counts['CRASHED']}")
        
        # Print detailed status
        print("\nDetailed Agent Status:")
        print("-" * 80)
        print(f"{'Agent Name':<30} {'Status':<15} {'Port':<8} {'Dependencies'}")
        print("-" * 80)
        
        for name in self.startup_order:
            agent = self.agents[name]
            status_marker = "✅" if agent.status == "HEALTHY" else "❌"
            deps = ", ".join(agent.dependencies) if agent.dependencies else "None"
            print(f"{name:<30} [{status_marker}] {agent.status:<10} {agent.port:<8} {deps}")
        
        print("-" * 80)
        
        # Print required but unhealthy agents
        unhealthy_required = [name for name, agent in self.agents.items() 
                             if agent.required and agent.status != "HEALTHY"]
        
        if unhealthy_required:
            print("\n⚠️  WARNING: The following required agents are not healthy:")
            for name in unhealthy_required:
                print(f"  - {name} ({self.agents[name].status})")
        
        print("\n" + "=" * 80)

    def cleanup(self) -> None:
        """Terminate all launched processes and clean up resources."""
        logger.info("Cleaning up resources...")
        
        # Terminate all processes
        for process in self.launched_processes:
            try:
                if process.poll() is None:  # If still running
                    process.terminate()
                    logger.debug(f"Terminated process PID {process.pid}")
            except Exception as e:
                logger.error(f"Error terminating process: {e}")
        
        # Wait for processes to terminate
        for process in self.launched_processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if not terminated
                try:
                    process.kill()
                    logger.warning(f"Force killed process PID {process.pid}")
                except Exception as e:
                    logger.error(f"Error killing process: {e}")
        
        # Clean up ZMQ context
        self.zmq_context.term()
        logger.info("Cleanup complete")

    def run(self) -> int:
        """
        Run the health checker.
        
        Returns:
            int: Exit code (0 for success, 1 for failure)
        """
        try:
            # Load agents from config
            self.load_agents_from_config()
            
            # Determine startup order
            self.determine_startup_order()
            
            # Analyze health check mechanisms
            self.analyze_agent_health_check_mechanisms()
            
            # Launch and verify agents
            success = self.launch_and_verify_agents()
            
            # Generate and print health report
            self.print_health_summary()
            
            # Save report to file
            report = self.generate_health_report()
            report_path = f"logs/health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Health report saved to {report_path}")
            
            return 0 if success else 1
            
        except Exception as e:
            logger.error(f"Error in health checker: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 1
        finally:
            self.cleanup()

if __name__ == "__main__":
    checker = MainPCHealthChecker()
    exit_code = checker.run()
    sys.exit(exit_code)
