"""
PC2 Agent Launcher
------------------
Script to launch, manage, and monitor agents running on PC2.
Run this script on PC2 to start all offloaded agents.

Features:
- Launch specified or all PC2 agents
- Monitor agent health status
- Auto-restart crashed agents
- Centralized logging for all PC2 agents
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import subprocess
import threading
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pc2_launcher.log')
    ]
)
logger = logging.getLogger('PC2Launcher')

# Default path for agent scripts (relative to this script)
DEFAULT_AGENTS_PATH = Path("agents")

# Default agent configs - update as needed
AGENT_CONFIGS = {
    # Model Management & Routing
    "context_bridge": {
        "script": "context_bridge_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    
    # Code Generation
    "code_generator": {
        "script": "code_generator_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 3,
        "dependencies": []  # Removed model_manager dependency since it's now on Main PC
    },
    "chain_of_thought": {
        "script": "chain_of_thought_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "progressive_code_generator": {
        "script": "progressive_code_generator.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []  # Removed model_manager dependency since it's now on Main PC
    },
    "auto_fixer": {
        "script": "auto_fixer_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "test_generator": {
        "script": "test_generator_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "executor": {
        "script": "executor_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    
    # Language
    "translator": {
        "script": "translator_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "web_scraper": {
        "script": "web_scraper_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    
    # Memory
    "contextual_memory": {
        "script": "contextual_memory_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "context_summarizer": {
        "script": "context_summarizer_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "error_pattern_memory": {
        "script": "error_pattern_memory.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "jarvis_memory": {
        "script": "jarvis_memory_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "digital_twin": {
        "script": "digital_twin_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "filesystem_assistant": {
        "script": "filesystem_assistant.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    },
    "learning_mode": {
        "script": "learning_mode_agent.py",
        "directory": "agents",
        "enabled": True,
        "auto_restart": True,
        "start_delay": 2,
        "dependencies": []
    }
}

class AgentProcess:
    """Class to manage an agent process"""
    
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.process = None
        self.last_started = None
        self.restart_count = 0
        self.status = "STOPPED"
        self.log_file = None
        self.monitor_thread = None
        self.stopping = False
        self.logger = logging.getLogger(f'Agent.{name}')
    
    def start(self):
        """Start the agent process"""
        if self.process and self.process.poll() is None:
            self.logger.warning(f"Agent {self.name} is already running")
            return
        
        script_path = Path(self.config.get("directory", DEFAULT_AGENTS_PATH)) / self.config["script"]
        
        if not script_path.exists():
            self.logger.error(f"Script {script_path} does not exist")
            self.status = "ERROR"
            return
        
        # Create log directory if needed
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = log_dir / f"{self.name}_{timestamp}.log"
        
        with open(self.log_file, 'w') as log:
            self.logger.info(f"Starting agent {self.name} from {script_path}")
            
            try:
                # Start the process with redirected output
                self.process = subprocess.Popen(
                    [sys.executable, str(script_path)],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=script_path.parent
                )
                
                self.last_started = time.time()
                self.status = "STARTING"
                
                # Start monitor thread
                if not self.monitor_thread or not self.monitor_thread.is_alive():
                    self.monitor_thread = threading.Thread(target=self.monitor, daemon=True)
                    self.monitor_thread.start()
                
                self.logger.info(f"Agent {self.name} started with PID {self.process.pid}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to start agent {self.name}: {e}")
                self.status = "ERROR"
                return False
    
    def stop(self):
        """Stop the agent process"""
        if not self.process or self.process.poll() is not None:
            self.logger.warning(f"Agent {self.name} is not running")
            self.status = "STOPPED"
            return
        
        self.stopping = True
        self.logger.info(f"Stopping agent {self.name} (PID {self.process.pid})")
        
        try:
            # Try graceful termination first
            self.process.terminate()
            
            # Wait up to 5 seconds for termination
            for _ in range(10):
                if self.process.poll() is not None:
                    break
                time.sleep(0.5)
            
            # Force kill if still running
            if self.process.poll() is None:
                self.logger.warning(f"Agent {self.name} did not terminate gracefully, killing process")
                self.process.kill()
            
            self.status = "STOPPED"
            self.logger.info(f"Agent {self.name} stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping agent {self.name}: {e}")
            self.status = "ERROR"
        
        finally:
            self.stopping = False
    
    def restart(self):
        """Restart the agent process"""
        self.logger.info(f"Restarting agent {self.name}")
        self.stop()
        # Give it a moment to fully stop
        time.sleep(1)
        success = self.start()
        if success:
            self.restart_count += 1
        return success
    
    def monitor(self):
        """Monitor the agent process and restart if needed"""
        while not self.stopping and self.process:
            returncode = self.process.poll()
            
            # Process is still running
            if returncode is None:
                # Update status if enough time has passed
                if self.status == "STARTING" and (time.time() - self.last_started) > 5:
                    self.status = "RUNNING"
                
                time.sleep(1)
                continue
            
            # Process has exited
            if returncode != 0 and not self.stopping:
                self.logger.warning(f"Agent {self.name} exited with code {returncode}")
                self.status = "CRASHED"
                
                # Auto-restart if enabled
                if self.config.get("auto_restart", True):
                    self.logger.info(f"Auto-restarting agent {self.name}")
                    time.sleep(1)  # Brief delay before restart
                    self.restart()
            else:
                self.status = "STOPPED"
                break

class PC2Launcher:
    """Main launcher for PC2 agents"""
    
    def __init__(self, args):
        self.args = args
        self.agents = {}
        self.status_thread = None
        self.running = True
        self.logger = logging.getLogger('PC2Launcher')
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle signals for clean shutdown"""
        self.logger.info("Shutdown signal received, stopping all agents...")
        self.running = False
        self.stop_all_agents()
        sys.exit(0)
    
    def load_agents(self):
        """Load agents from configuration"""
        # Filter agents based on command line arguments
        if self.args.agents:
            requested_agents = self.args.agents.split(',')
            filtered_configs = {k: v for k, v in AGENT_CONFIGS.items() if k in requested_agents}
            
            # Check for unknown agents
            unknown_agents = [a for a in requested_agents if a not in AGENT_CONFIGS]
            if unknown_agents:
                self.logger.warning(f"Unknown agent(s): {', '.join(unknown_agents)}")
        else:
            # Use all agents
            filtered_configs = AGENT_CONFIGS
        
        # Create agent objects
        for name, config in filtered_configs.items():
            if config.get("enabled", True):
                self.agents[name] = AgentProcess(name, config)
    
    def start_agents(self):
        """Start all loaded agents in the correct order"""
        # Group agents by dependency level
        dependency_levels = {}
        max_level = 0
        
        # Assign dependency levels
        for name, agent in self.agents.items():
            dependencies = agent.config.get("dependencies", [])
            level = 0
            
            for dep in dependencies:
                if dep in self.agents:
                    # Find the level of this dependency
                    dep_level = 0
                    for l, agents in dependency_levels.items():
                        if dep in agents:
                            dep_level = l
                            break
                    
                    # Our level must be higher than the dependency's level
                    level = max(level, dep_level + 1)
            
            # Add to the appropriate level
            if level not in dependency_levels:
                dependency_levels[level] = []
            dependency_levels[level].append(name)
            max_level = max(max_level, level)
        
        # Start agents level by level
        self.logger.info("Starting agents...")
        for level in range(max_level + 1):
            if level in dependency_levels:
                agent_names = dependency_levels[level]
                self.logger.info(f"Starting level {level} agents: {', '.join(agent_names)}")
                
                for name in agent_names:
                    start_delay = self.agents[name].config.get("start_delay", 2)
                    time.sleep(start_delay)
                    self.agents[name].start()
        
        self.logger.info("All agents started")
    
    def stop_all_agents(self):
        """Stop all running agents"""
        self.logger.info("Stopping all agents...")
        
        # Reverse the agent order (stop in reverse of startup order)
        for name in reversed(list(self.agents.keys())):
            self.agents[name].stop()
        
        self.logger.info("All agents stopped")
    
    def print_status(self):
        """Print current status of all agents"""
        print("\n" + "=" * 80)
        print(f"PC2 AGENT STATUS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Group by category
        categories = {
            "Model Management": ["model_manager", "context_bridge"],
            "Code Generation": ["code_generator", "chain_of_thought", "progressive_code_generator", 
                               "auto_fixer", "test_generator", "executor"],
            "Language": ["translator", "web_scraper"],
            "Memory": ["contextual_memory", "context_summarizer", "error_pattern_memory", 
                      "jarvis_memory", "digital_twin", "filesystem_assistant", "learning_mode"]
        }
        
        for category, agent_names in categories.items():
            print(f"\n{category}:")
            print("-" * 40)
            
            for name in agent_names:
                if name in self.agents:
                    agent = self.agents[name]
                    pid = agent.process.pid if agent.process else "N/A"
                    status_color = {
                        "RUNNING": "\033[92m",  # Green
                        "STARTING": "\033[93m", # Yellow
                        "STOPPED": "\033[91m",  # Red
                        "CRASHED": "\033[91m",  # Red
                        "ERROR": "\033[91m"     # Red
                    }.get(agent.status, "")
                    reset_color = "\033[0m"
                    
                    print(f"  {name:25} [{pid:>5}] Status: {status_color}{agent.status:8}{reset_color} " +
                          f"Restarts: {agent.restart_count}")
        
        print("\n" + "=" * 80)
        print("Press Ctrl+C to stop all agents and exit")
        print("=" * 80 + "\n")
    
    def status_monitor(self):
        """Thread to monitor and display agent status"""
        while self.running:
            self.print_status()
            time.sleep(5)  # Update every 5 seconds
    
    def start_status_monitor(self):
        """Start the status monitor thread"""
        self.status_thread = threading.Thread(target=self.status_monitor, daemon=True)
        self.status_thread.start()
    
    def run(self):
        """Main launcher function"""
        self.logger.info("PC2 Agent Launcher starting...")
        
        try:
            # Load agent configurations
            self.load_agents()
            
            # Start status monitor if not in quiet mode
            if not self.args.quiet:
                self.start_status_monitor()
            
            # Start the agents
            self.start_agents()
            
            # Keep main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
            self.running = False
            self.stop_all_agents()
        except Exception as e:
            self.logger.error(f"Error in launcher: {e}", exc_info=True)
            self.running = False
            self.stop_all_agents()
        finally:
            self.logger.info("PC2 Agent Launcher exiting")

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="PC2 Agent Launcher")
    parser.add_argument("--agents", help="Comma-separated list of agents to launch (default: all)")
    parser.add_argument("--quiet", action="store_true", help="Don't display interactive status")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    launcher = PC2Launcher(args)
    launcher.run()
