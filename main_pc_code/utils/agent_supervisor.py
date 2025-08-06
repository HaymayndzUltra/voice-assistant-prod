#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
Agent Supervisor Process

This module provides a supervisor for agent processes that:
- Monitors agent processes and restarts them if they fail
- Provides a central point for health monitoring
- Implements proper dependency management for agent startup
- Handles graceful shutdown of the entire system
- Collects and aggregates logs from all agents
"""

import os
import sys
import time
import signal
import logging
import threading
import subprocess
import json
import yaml
import zmq
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set

# Import the PathManager for consistent path resolution
from utils.path_manager import PathManager
from common.env_helpers import get_env

# Configure logging
logger = configure_logging(__name__)
    ]
)
logger = logging.getLogger('agent_supervisor')

# Ensure the logs directory exists
logs_dir = PathManager.get_logs_dir()
file_handler = logging.FileHandler(logs_dir / str(PathManager.get_logs_dir() / "agent_supervisor.log"))
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

class AgentProcess:
    """Class representing a monitored agent process."""
    
    def __init__(self, name: str, path: str, port: int, health_port: int, 
                 dependencies: List[str] = None, params: Dict[str, Any] = None):
        self.name = name
        self.path = PathManager.resolve_path(path)
        self.port = port
        self.health_port = health_port
        self.dependencies = dependencies or []
        self.params = params or {}
        self.process = None
        self.stdout_file = None
        self.stderr_file = None
        self.is_running = False
        self.restart_count = 0
        self.last_restart = 0
        self.max_restarts = 5
        self.restart_window = 300  # 5 minutes
        self.startup_grace_period = 10  # seconds
        self.health_status = "unknown"
        self.health_check_thread = None
        self.health_check_interval = 5  # seconds
        self.stop_event = threading.Event()
        
    def start(self) -> bool:
        """Start the agent process.
        
        Returns:
            True if successful, False otherwise
        """
        if self.is_running:
            logger.info(f"Agent {self.name} is already running")
            return True
            
        # Check if we've exceeded the restart limit
        current_time = time.time()
        if (self.restart_count >= self.max_restarts and 
            current_time - self.last_restart < self.restart_window):
            logger.error(f"Agent {self.name} has exceeded restart limit "
                        f"({self.restart_count} restarts in {self.restart_window} seconds)")
            return False
            
        # Open log files
        logs_dir = PathManager.get_logs_dir()
        self.stdout_file = open(logs_dir / fstr(PathManager.get_logs_dir() / "{self.name.lower()}_stdout.log"), "a")
        self.stderr_file = open(logs_dir / fstr(PathManager.get_logs_dir() / "{self.name.lower()}_stderr.log"), "a")
        
        # Prepare command and environment
        cmd = [sys.executable, str(self.path)]
        
        # Add parameters
        for key, value in self.params.items():
            cmd.append(f"--{key}={value}")
            
        # Add port and health port
        cmd.append(f"--port={self.port}")
        cmd.append(f"--health_check_port={self.health_port}")
        
        # Add name if not already in params
        if 'name' not in self.params:
            cmd.append(f"--name={self.name}")
            
        # Set up environment
        env = os.environ.copy()
        project_root = str(PathManager.get_project_root())
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{project_root}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = project_root
            
        try:
            # Start the process
            self.process = subprocess.Popen(
                cmd,
                stdout=self.stdout_file,
                stderr=self.stderr_file,
                env=env,
                cwd=project_root
            )
            
            # Update state
            self.is_running = True
            self.restart_count += 1
            self.last_restart = time.time()
            
            logger.info(f"Started agent {self.name} with PID {self.process.pid}")
            
            # Start health check thread
            self.stop_event.clear()
            if self.health_check_thread is None or not self.health_check_thread.is_alive():
                self.health_check_thread = threading.Thread(
                    target=self._health_check_loop
                )
                self.health_check_thread.daemon = True
                self.health_check_thread.start()
                
            # Wait for startup grace period
            time.sleep(self.startup_grace_period)
            
            # Check if process is still running
            if self.process.poll() is not None:
                logger.error(f"Agent {self.name} exited immediately with code {self.process.returncode}")
                self.is_running = False
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error starting agent {self.name}: {e}")
            self.is_running = False
            return False
            
    def stop(self) -> bool:
        """Stop the agent process.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_running:
            logger.info(f"Agent {self.name} is not running")
            return True
            
        # Signal the health check thread to stop
        self.stop_event.set()
        
        try:
            # Try to terminate gracefully first
            if self.process and self.process.poll() is None:
                logger.info(f"Sending SIGTERM to agent {self.name} (PID {self.process.pid})")
                self.process.terminate()
                
                # Wait for the process to terminate
                for _ in range(10):  # Wait up to 10 seconds
                    if self.process.poll() is not None:
                        break
                    time.sleep(1)
                    
                # If still running, kill it
                if self.process.poll() is None:
                    logger.warning(f"Agent {self.name} did not terminate, sending SIGKILL")
                    self.process.kill()
                    self.process.wait()
            
            # Close log files
            if self.stdout_file:
                self.stdout_file.close()
                self.stdout_file = None
                
            if self.stderr_file:
                self.stderr_file.close()
                self.stderr_file = None
                
            # Update state
            self.is_running = False
            self.health_status = "unknown"
            
            logger.info(f"Stopped agent {self.name}")
            return True
        except Exception as e:
            logger.error(f"Error stopping agent {self.name}: {e}")
            return False
            
    def restart(self) -> bool:
        """Restart the agent process.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Restarting agent {self.name}")
        self.stop()
        time.sleep(2)  # Give it some time to fully stop
        return self.start()
        
    def check_health(self) -> Tuple[bool, str]:
        """Check the health of the agent.
        
        Returns:
            Tuple of (is_healthy, status_message)
        """
        try:
            # Check if process is running
            if self.process is None or self.process.poll() is not None:
                return False, f"Process not running (exit code: {self.process.returncode if self.process else None})"
                
            # Check health via ZMQ
            context = zmq.Context()
            socket = context.socket(zmq.REQ)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
            socket.connect(f"tcp://localhost:{self.health_port}")
            
            # Send health check request
            socket.send_json({"action": "health_check"})
            
            # Wait for response
            response = socket.recv_json()
            
            # Check if response indicates health
            if response.get("status") in ["ok", "ready", "HEALTHY"]:
                return True, json.dumps(response)
            else:
                return False, json.dumps(response)
        except zmq.error.Again:
            return False, "Timeout waiting for response"
        except Exception as e:
            return False, f"Error checking health: {e}"
        finally:
            if 'socket' in locals():
                socket.close()
            if 'context' in locals():
                context.term()
                
    def _health_check_loop(self):
        """Continuous health check loop."""
        while not self.stop_event.is_set():
            try:
                is_healthy, status = self.check_health()
                self.health_status = status
                
                if not is_healthy and self.is_running:
                    logger.warning(f"Agent {self.name} is unhealthy: {status}")
                    
                    # Check if process has died
                    if self.process and self.process.poll() is not None:
                        logger.error(f"Agent {self.name} process has died with code {self.process.returncode}")
                        self.is_running = False
                        self.restart()
            except Exception as e:
                logger.error(f"Error in health check loop for {self.name}: {e}")
                
            # Wait for next check
            self.stop_event.wait(self.health_check_interval)

class AgentSupervisor:
    """Agent supervisor class that manages multiple agent processes."""
    
    def __init__(self, config_path: str = None):
        """Initialize the agent supervisor.
        
        Args:
            config_path: Path to the configuration file
        """
        self.agents: Dict[str, AgentProcess] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.running = True
        self.stop_event = threading.Event()
        
        # Load configuration
        self.config_path = config_path or str(PathManager.get_config_dir() / "startup_config.yaml")
        self.load_config()
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def load_config(self):
        """Load agent configuration from file."""
        try:
            config_path = PathManager.resolve_path(self.config_path)
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            logger.info(f"Loaded configuration from {config_path}")
            
            # Handle different config formats
            all_agents = []
            
            # Check for minimal system config format (core_agents + dependencies)
            if 'core_agents' in config:
                all_agents.extend(config['core_agents'])
                logger.info(f"Added {len(config['core_agents'])} core agents")
                
            if 'dependencies' in config:
                all_agents.extend(config['dependencies'])
                logger.info(f"Added {len(config['dependencies'])} dependency agents")
                
            # Check for standard config format (agents)
            if 'agents' in config:
                all_agents.extend(config['agents'])
                logger.info(f"Added {len(config['agents'])} agents from standard format")
            
            # Process each agent
            for agent_config in all_agents:
                name = agent_config.get('name')
                file_path = agent_config.get('file_path')
                port = agent_config.get('port')
                
                # Handle health_check_port from params or direct config
                health_port = agent_config.get('health_check_port', port + 1)
                if isinstance(agent_config.get('params'), dict) and 'health_check_port' in agent_config['params']:
                    health_port = agent_config['params']['health_check_port']
                
                dependencies = agent_config.get('dependencies', []) or []
                params = agent_config.get('params', {}) or {}
                
                if not name or not file_path or not port:
                    logger.warning(f"Incomplete configuration for agent: {agent_config}")
                    continue
                    
                # Create agent process
                agent = AgentProcess(
                    name=name,
                    path=file_path,
                    port=port,
                    health_port=health_port,
                    dependencies=dependencies,
                    params=params
                )
                
                self.agents[name] = agent
                self.dependencies[name] = dependencies
                
                logger.info(f"Added agent {name} with dependencies: {dependencies}")
                
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            
    def start_all(self):
        """Start all agents in dependency order."""
        logger.info("Starting all agents")
        
        # Build dependency graph
        dependency_graph = {}
        for name, deps in self.dependencies.items():
            dependency_graph[name] = set(deps)
            
        # Find startup order using topological sort
        startup_order = self._topological_sort(dependency_graph)
        
        # Start agents in order
        for name in startup_order:
            if name in self.agents:
                agent = self.agents[name]
                
                # Check if dependencies are healthy
                deps_healthy = True
                for dep in agent.dependencies:
                    if dep not in self.agents or not self._is_agent_healthy(dep):
                        logger.warning(f"Dependency {dep} for agent {name} is not healthy")
                        deps_healthy = False
                        
                if not deps_healthy:
                    logger.error(f"Cannot start agent {name} because dependencies are not healthy")
                    continue
                    
                # Start the agent
                success = agent.start()
                if not success:
                    logger.error(f"Failed to start agent {name}")
                else:
                    logger.info(f"Successfully started agent {name}")
                    
                # Give it some time to initialize
                time.sleep(2)
                
    def stop_all(self):
        """Stop all agents in reverse dependency order."""
        logger.info("Stopping all agents")
        
        # Build dependency graph
        dependency_graph = {}
        for name, deps in self.dependencies.items():
            dependency_graph[name] = set(deps)
            
        # Find startup order using topological sort
        startup_order = self._topological_sort(dependency_graph)
        
        # Reverse to get shutdown order
        shutdown_order = list(reversed(startup_order))
        
        # Stop agents in order
        for name in shutdown_order:
            if name in self.agents:
                agent = self.agents[name]
                success = agent.stop()
                if not success:
                    logger.error(f"Failed to stop agent {name}")
                else:
                    logger.info(f"Successfully stopped agent {name}")
                    
                # Give it some time to shut down
                time.sleep(1)
                
    def restart_agent(self, name: str):
        """Restart a specific agent.
        
        Args:
            name: Name of the agent to restart
        
        Returns:
            True if successful, False otherwise
        """
        if name not in self.agents:
            logger.error(f"Agent {name} not found")
            return False
            
        agent = self.agents[name]
        return agent.restart()
        
    def check_health(self) -> Dict[str, bool]:
        """Check the health of all agents.
        
        Returns:
            Dictionary mapping agent names to health status
        """
        health_status = {}
        
        for name, agent in self.agents.items():
            is_healthy, _ = agent.check_health()
            health_status[name] = is_healthy
            
        return health_status
        
    def run(self):
        """Run the supervisor main loop."""
        logger.info("Starting agent supervisor")
        
        # Start all agents
        self.start_all()
        
        # Main loop
        try:
            while self.running and not self.stop_event.is_set():
                # Check health of all agents
                for name, agent in self.agents.items():
                    if agent.is_running:
                        is_healthy, status = agent.check_health()
                        
                        if not is_healthy:
                            logger.warning(f"Agent {name} is unhealthy: {status}")
                            
                            # Check if process has died
                            if agent.process and agent.process.poll() is not None:
                                logger.error(f"Agent {name} process has died with code {agent.process.returncode}")
                                agent.is_running = False
                                agent.restart()
                                
                # Wait before next check
                time.sleep(10)
        except Exception as e:
            logger.error(f"Error in supervisor main loop: {e}")
        finally:
            # Stop all agents
            self.stop_all()
            
    def _signal_handler(self, sig, frame):
        """Handle signals for graceful shutdown."""
        logger.info(f"Received signal {sig}, shutting down")
        self.running = False
        self.stop_event.set()
        
    def _topological_sort(self, graph: Dict[str, Set[str]]) -> List[str]:
        """Perform topological sort on dependency graph.
        
        Args:
            graph: Dependency graph as dictionary of node -> dependencies
            
        Returns:
            List of nodes in topological order
        """
        # Find all nodes
        nodes = set(graph.keys())
        for deps in graph.values():
            nodes.update(deps)
            
        # Create a new graph with all nodes
        result_graph = {node: set(graph.get(node, set())) for node in nodes}
        
        # Find nodes with no dependencies
        result = []
        no_deps = [n for n, deps in result_graph.items() if not deps]
        
        # Remove nodes with no dependencies
        while no_deps:
            node = no_deps.pop(0)
            result.append(node)
            
            # Remove this node from dependencies of other nodes
            for deps in result_graph.values():
                deps.discard(node)
                
            # Find new nodes with no dependencies
            new_no_deps = [n for n, deps in result_graph.items() 
                          if n not in result and not deps]
            no_deps.extend(new_no_deps)
            
        # Check for cycles
        if any(deps for deps in result_graph.values()):
            cycles = [n for n, deps in result_graph.items() if deps]
            logger.warning(f"Cyclic dependencies detected: {cycles}")
            
            # Add remaining nodes to result
            for node in nodes:
                if node not in result:
                    result.append(node)
                    
        return result
        
    def _is_agent_healthy(self, name: str) -> bool:
        """Check if an agent is healthy.
        
        Args:
            name: Name of the agent
            
        Returns:
            True if agent is healthy, False otherwise
        """
        if name not in self.agents:
            return False
            
        agent = self.agents[name]
        is_healthy, _ = agent.check_health()
        return is_healthy

def main():
    """Main entry point."""
    import argparse

# Containerization-friendly paths (Blueprint.md Step 5)
from common.utils.path_manager import PathManager
    
    parser = argparse.ArgumentParser(description="Agent Supervisor")
    parser.add_argument("--config", help="Path to configuration file")
    args = parser.parse_args()
    
    # Initialize supervisor
    supervisor = AgentSupervisor(config_path=args.config)
    
    # Run supervisor
    supervisor.run()

if __name__ == "__main__":
    main() 