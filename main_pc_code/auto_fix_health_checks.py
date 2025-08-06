"""
Auto-fix script for agent health checks
Continuously monitors and fixes health check issues until all agents are healthy
"""

import time
import json
import socket
import logging
import subprocess
from typing import Dict, Set
import yaml
import os
import sys


# Import path manager for containerization-friendly paths
import sys
import os
from common.utils.log_setup import configure_logging
sys.path.insert(0, get_project_root())
from common.utils.path_manager import PathManager
# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(PathManager.get_logs_dir() / "health_check_fixes.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HealthCheckFixer:
    def __init__(self, config_path: str = PathManager.join_path("config", "startup_config.yaml")):
        self.config_path = config_path
        self.healthy_agents: Set[str] = set()
        self.unhealthy_agents: Dict[str, int] = {}  # agent_name -> retry_count
        self.max_retries = 3
        self.load_config()
        
    def load_config(self):
        """Load agent configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
            
    def check_agent_health(self, agent_name: str, host: str, port: int) -> bool:
        """Check health of a single agent."""
        try:
            # Use health check port (main port + 1)
            health_port = port + 1
            
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                result = s.connect_ex((host, health_port))
                if result == 0:
                    # Send health check request
                    s.sendall(json.dumps({"action": "health"}).encode())
                    response = s.recv(1024).decode()
                    try:
                        health_data = json.loads(response)
                        if health_data.get("status") == "ok":
                            logger.info(f"Health check passed for {agent_name}")
                            return True
                    except json.JSONDecodeError:
                        logger.error(f"Invalid health check response from {agent_name}: {response}")
        except Exception as e:
            logger.error(f"Health check error for {agent_name}: {e}")
        return False
        
    def restart_agent(self, agent_name: str, agent_config: dict) -> bool:
        """Restart an unhealthy agent."""
        try:
            # Kill existing process if any
            os.system(f"pkill -f {agent_name}")
            time.sleep(2)  # Wait for process to die
            
            # Start new process
            cmd = [
                sys.executable,
                agent_config['script_path'],
                '--port', str(agent_config['port']),
                '--host', agent_config['host']
            ]
            
            # Add dependencies if any
            for dep in agent_config.get('dependencies', []):
                dep_config = self.config.get(dep, {})
                if dep_config:
                    cmd.extend([
                        f'--{dep.lower()}_host', dep_config['host'],
                        f'--{dep.lower()}_port', str(dep_config['port'])
                    ])
            
            # Start process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            logger.info(f"Restarted {agent_name} with PID {process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restart {agent_name}: {e}")
            return False
            
    def fix_agent(self, agent_name: str, agent_config: dict):
        """Attempt to fix an unhealthy agent."""
        retry_count = self.unhealthy_agents.get(agent_name, 0)
        
        if retry_count >= self.max_retries:
            logger.error(f"Max retries reached for {agent_name}, skipping")
            return
            
        logger.info(f"Attempting to fix {agent_name} (attempt {retry_count + 1})")
        
        # Restart agent
        if self.restart_agent(agent_name, agent_config):
            # Wait for initialization
            time.sleep(10)
            
            # Check health again
            if self.check_agent_health(agent_name, agent_config['host'], agent_config['port']):
                self.healthy_agents.add(agent_name)
                if agent_name in self.unhealthy_agents:
                    del self.unhealthy_agents[agent_name]
            else:
                self.unhealthy_agents[agent_name] = retry_count + 1
                
    def monitor_and_fix(self):
        """Continuously monitor and fix unhealthy agents."""
        while True:
            try:
                # Check all agents
                for agent_name, agent_config in self.config.items():
                    if agent_name not in self.healthy_agents:
                        if not self.check_agent_health(agent_name, agent_config['host'], agent_config['port']):
                            self.fix_agent(agent_name, agent_config)
                        else:
                            self.healthy_agents.add(agent_name)
                            if agent_name in self.unhealthy_agents:
                                del self.unhealthy_agents[agent_name]
                
                # Log status
                logger.info(f"Health check status: {len(self.healthy_agents)}/{len(self.config)} agents healthy")
                if self.unhealthy_agents:
                    logger.warning(f"Unhealthy agents: {list(self.unhealthy_agents.keys())}")
                
                # Check if all agents are healthy
                if len(self.healthy_agents) == len(self.config):
                    logger.info("All agents are healthy!")
                    break
                    
                # Wait before next check
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in monitor_and_fix: {e}")
                time.sleep(5)
                
    def run(self):
        """Run the health check fixer."""
        logger.info("Starting health check fixer...")
        self.monitor_and_fix()
        
if __name__ == "__main__":
    fixer = HealthCheckFixer()
    fixer.run() 