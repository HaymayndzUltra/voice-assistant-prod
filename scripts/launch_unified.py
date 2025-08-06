#!/usr/bin/env python3
"""
Unified System Launcher - Phase 1
Reads unified_startup.yaml and launches agents in dependency order
"""

import os
import sys
import yaml
import time
import subprocess
import logging
import signal
import requests
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict, deque
from pathlib import Path
from common.utils.log_setup import configure_logging

# Setup logging
logger = configure_logging(__name__)
logger = logging.getLogger('UnifiedLauncher')

class UnifiedSystemLauncher:
    def __init__(self, config_path: str = "config/unified_startup.yaml"):
        self.config_path = config_path
        self.config = None
        self.processes: Dict[str, subprocess.Popen] = {}
        self.agent_info: Dict[str, Dict] = {}
        self.shutdown_requested = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
        self.shutdown()
        sys.exit(0)
        
    def load_config(self):
        """Load and parse the YAML configuration"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {self.config_path}")
            
            # Set environment variables from global settings
            if 'global_settings' in self.config and 'environment' in self.config['global_settings']:
                for key, value in self.config['global_settings']['environment'].items():
                    os.environ[key] = str(value)
                    logger.debug(f"Set environment variable: {key}={value}")
                    
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
            
    def extract_agents(self) -> Dict[str, Dict]:
        """Extract all agents from the configuration"""
        agents = {}
        
        if 'agent_groups' not in self.config:
            logger.error("No agent_groups found in configuration")
            return agents
            
        for group_name, group_agents in self.config['agent_groups'].items():
            for agent_name, agent_config in group_agents.items():
                # Store agent with full info including group
                agents[agent_name] = {
                    **agent_config,
                    'group': group_name,
                    'name': agent_name
                }
                
        logger.info(f"Extracted {len(agents)} agents from configuration")
        return agents
        
    def topological_sort(self, agents: Dict[str, Dict]) -> List[str]:
        """Perform topological sort on agents based on dependencies"""
        # Build adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize all agents
        for agent_name in agents:
            in_degree[agent_name] = 0
            
        # Build dependency graph
        for agent_name, agent_config in agents.items():
            dependencies = agent_config.get('dependencies', [])
            for dep in dependencies:
                if dep in agents:  # Only include dependencies that exist
                    graph[dep].append(agent_name)
                    in_degree[agent_name] += 1
                else:
                    logger.warning(f"Agent {agent_name} has dependency {dep} which is not in the configuration")
                    
        # Kahn's algorithm for topological sort
        queue = deque([agent for agent in agents if in_degree[agent] == 0])
        sorted_agents = []
        
        while queue:
            agent = queue.popleft()
            sorted_agents.append(agent)
            
            for neighbor in graph[agent]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        if len(sorted_agents) != len(agents):
            logger.error("Circular dependency detected in agent configuration!")
            # Find agents involved in cycle
            remaining = set(agents) - set(sorted_agents)
            logger.error(f"Agents involved in circular dependency: {remaining}")
            raise ValueError("Cannot start system due to circular dependencies")
            
        return sorted_agents
        
    def substitute_env_vars(self, value: str) -> str:
        """Substitute environment variables in configuration values"""
        if isinstance(value, str) and '${' in value:
            # Handle PORT_OFFSET substitution
            if 'PORT_OFFSET' not in os.environ:
                os.environ['PORT_OFFSET'] = '0'
                
            # Simple substitution for ${VAR} patterns
            import re
            pattern = r'\$\{([^}]+)\}'
            
            def replacer(match):
                var_expr = match.group(1)
                
                # Handle arithmetic expressions like PORT_OFFSET+7200
                if '+' in var_expr:
                    parts = var_expr.split('+')
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        offset = parts[1].strip()
                        if var_name in os.environ and offset.isdigit():
                            return str(int(os.environ[var_name]) + int(offset))
                            
                # Handle simple variable substitution
                return os.environ.get(var_expr, match.group(0))
                
            return re.sub(pattern, replacer, value)
        return value
        
    def start_agent(self, agent_name: str, agent_config: Dict) -> bool:
        """Start a single agent"""
        try:
            script_path = agent_config['script_path']
            
            # Check if script exists
            if not os.path.exists(script_path):
                logger.error(f"Script not found for {agent_name}: {script_path}")
                return False
                
            # Prepare environment
            env = os.environ.copy()
            
            # Add agent-specific environment variables
            port = self.substitute_env_vars(str(agent_config.get('port', '')))
            health_port = self.substitute_env_vars(str(agent_config.get('health_check_port', '')))
            
            env['AGENT_NAME'] = agent_name
            env['AGENT_PORT'] = port
            env['HEALTH_CHECK_PORT'] = health_port
            
            # Add any agent-specific config as environment variables
            if 'config' in agent_config:
                for key, value in agent_config['config'].items():
                    env_key = f"AGENT_CONFIG_{key.upper()}"
                    env[env_key] = str(value)
                    
            # Start the process
            cmd = [sys.executable, script_path]
            logger.info(f"Starting {agent_name} on port {port} (health: {health_port})")
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[agent_name] = process
            self.agent_info[agent_name] = {
                'port': port,
                'health_port': health_port,
                'script': script_path,
                'group': agent_config.get('group', 'unknown')
            }
            
            # Give agent time to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"Agent {agent_name} failed to start:")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to start agent {agent_name}: {e}")
            return False
            
    def check_agent_health(self, agent_name: str, max_retries: int = 10) -> bool:
        """Check if an agent is healthy via its health endpoint"""
        agent_info = self.agent_info.get(agent_name)
        if not agent_info:
            return False
            
        health_port = agent_info['health_port']
        url = f"http://localhost:{health_port}/health"
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    logger.info(f"Agent {agent_name} is healthy")
                    return True
                else:
                    logger.warning(f"Agent {agent_name} health check returned {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.debug(f"Health check attempt {attempt + 1}/{max_retries} failed for {agent_name}: {e}")
                
            if attempt < max_retries - 1:
                time.sleep(3)
                
        logger.error(f"Agent {agent_name} failed health check after {max_retries} attempts")
        return False
        
    def launch_agents(self):
        """Launch all agents in dependency order"""
        # Extract and sort agents
        agents = self.extract_agents()
        sorted_agents = self.topological_sort(agents)
        
        logger.info(f"Starting {len(sorted_agents)} agents in dependency order...")
        logger.info(f"Launch order: {sorted_agents}")
        
        failed_agents = []
        
        for agent_name in sorted_agents:
            if self.shutdown_requested:
                break
                
            agent_config = agents[agent_name]
            
            # Check if agent is required
            if not agent_config.get('required', True):
                logger.info(f"Skipping optional agent: {agent_name}")
                continue
                
            # Start the agent
            if self.start_agent(agent_name, agent_config):
                # Wait for health check
                if self.check_agent_health(agent_name):
                    logger.info(f"Successfully started {agent_name}")
                else:
                    logger.error(f"Agent {agent_name} failed health check")
                    failed_agents.append(agent_name)
                    
                    # If it's a required agent, we should stop
                    if agent_config.get('required', True):
                        logger.error(f"Required agent {agent_name} failed, stopping launch")
                        break
            else:
                failed_agents.append(agent_name)
                if agent_config.get('required', True):
                    logger.error(f"Required agent {agent_name} failed to start, stopping launch")
                    break
                    
        if failed_agents:
            logger.error(f"Failed to start agents: {failed_agents}")
            return False
            
        logger.info("All agents started successfully!")
        return True
        
    def monitor_agents(self):
        """Monitor running agents and restart if necessary"""
        while not self.shutdown_requested:
            time.sleep(30)  # Check every 30 seconds
            
            for agent_name, process in list(self.processes.items()):
                if process.poll() is not None:
                    logger.warning(f"Agent {agent_name} has stopped (exit code: {process.returncode})")
                    
                    # Attempt to restart if it's a required agent
                    agent_config = self.agent_info.get(agent_name, {})
                    if agent_config.get('required', True):
                        logger.info(f"Attempting to restart {agent_name}...")
                        # TODO: Implement restart logic
                        
    def shutdown(self):
        """Gracefully shutdown all agents"""
        logger.info("Initiating system shutdown...")
        
        # Stop agents in reverse order
        agent_names = list(reversed(list(self.processes.keys())))
        
        for agent_name in agent_names:
            process = self.processes.get(agent_name)
            if process and process.poll() is None:
                logger.info(f"Stopping {agent_name}...")
                process.terminate()
                
                # Give it time to shutdown gracefully
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Agent {agent_name} did not stop gracefully, forcing...")
                    process.kill()
                    process.wait()
                    
        logger.info("All agents stopped")
        
    def generate_dependency_graph(self):
        """Generate a visual dependency graph"""
        try:
            import graphviz
            
            dot = graphviz.Digraph(comment='Unified System Dependencies')
            dot.attr(rankdir='TB')
            
            agents = self.extract_agents()
            
            # Add nodes with group colors
            group_colors = {
                'monitoring': 'lightblue',
                'core_services': 'lightgreen',
                'memory_system': 'lightyellow',
                'gpu_infrastructure': 'lightcoral',
                'processing_services': 'lightgray',
                'language_processing': 'lightpink',
                'speech_services': 'lightsalmon',
                'context_management': 'lightsteelblue',
                'reasoning_services': 'lightseagreen',
                'routing_services': 'lightgoldenrodyellow'
            }
            
            for agent_name, agent_config in agents.items():
                group = agent_config.get('group', 'unknown')
                color = group_colors.get(group, 'white')
                dot.node(agent_name, agent_name, style='filled', fillcolor=color)
                
            # Add edges for dependencies
            for agent_name, agent_config in agents.items():
                for dep in agent_config.get('dependencies', []):
                    if dep in agents:
                        dot.edge(dep, agent_name)
                        
            # Save the graph
            output_path = 'docs/unified_dependencies'
            dot.render(output_path, format='svg', cleanup=True)
            logger.info(f"Dependency graph saved to {output_path}.svg")
            
        except ImportError:
            logger.warning("graphviz not installed, skipping dependency graph generation")
            
    def run(self):
        """Main execution method"""
        try:
            # Load configuration
            self.load_config()
            
            # Generate dependency graph
            self.generate_dependency_graph()
            
            # Launch agents
            if self.launch_agents():
                logger.info("System startup complete!")
                
                # Write success marker
                with open('artifacts/phase1_smoke_ok.txt', 'w') as f:
                    f.write(f"Phase 1 smoke test passed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Successfully started {len(self.processes)} agents\n")
                    for agent_name in self.processes:
                        f.write(f"  - {agent_name}\n")
                        
                # Monitor agents
                self.monitor_agents()
            else:
                logger.error("System startup failed!")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            self.shutdown()
            sys.exit(1)
            
if __name__ == "__main__":
    launcher = UnifiedSystemLauncher()
    launcher.run()