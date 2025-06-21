#!/usr/bin/env python3
import os
import sys
import yaml
import subprocess
import time
import logging
import signal
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("system_log.txt"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Define paths
CURRENT_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = CURRENT_DIR / "config" / "startup_config.yaml"
PROJECT_ROOT = CURRENT_DIR.parent

# Set environment variables
os.environ["PYTHONPATH"] = f"{PROJECT_ROOT}:{CURRENT_DIR}:{os.environ.get('PYTHONPATH', '')}"

def load_config():
    """Load configuration from YAML file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}

def kill_existing_processes():
    """Kill any existing Python processes that might be using our ports."""
    try:
        logger.info("Checking for existing processes...")
        # Check for processes using our ports
        ports_to_check = []
        config = load_config()
        for section in config.values():
            if isinstance(section, list):
                for agent in section:
                    if 'port' in agent:
                        ports_to_check.append(str(agent['port']))
        
        # Use lsof to find processes using these ports
        if ports_to_check:
            port_list = ",".join(ports_to_check)
            os.system(f"lsof -i :{port_list} | grep LISTEN | awk '{{print $2}}' | xargs -r kill -9")
            logger.info("Cleaned up any existing processes")
    except Exception as e:
        logger.error(f"Error cleaning up processes: {e}")

def build_command(agent, agent_lookup):
    """Build command to launch an agent."""
    script_path = os.path.join(CURRENT_DIR, agent['script_path'])
    cmd = [sys.executable, script_path, '--port', str(agent['port'])]
    
    # Add dependencies as CLI args
    for dep in agent.get('dependencies', []):
        dep_cfg = agent_lookup.get(dep)
        if not dep_cfg:
            logger.warning(f"Dependency '{dep}' not found for agent '{agent['name']}'")
            continue
        cmd += [f'--{dep}_host', dep_cfg.get('host', 'localhost'), 
                f'--{dep}_port', str(dep_cfg['port'])]
    return cmd

def build_agent_lookup(config):
    """Build a lookup dictionary of all agents."""
    lookup = {}
    for section in config.values():
        if isinstance(section, list):
            for agent in section:
                if 'name' in agent:
                    lookup[agent['name']] = agent
    return lookup

def launch_agents_in_order(config):
    """Launch agents in the correct order based on dependencies."""
    agent_lookup = build_agent_lookup(config)
    processes = {}
    
    # Define the order of sections to launch
    section_order = [
        'core_services',
        'main_pc_gpu_services',
        'emotion_system',
        'memory_system',
        'learning_knowledge',
        'language_processing',
        'planning_execution',
        'tts_services',
        'code_generation',
        'audio_processing',
        'vision',
        'monitoring_security'
    ]
    
    # Launch agents in order
    for section in section_order:
        if section in config:
            logger.info(f"Starting {section}...")
            for agent in config[section]:
                if not os.path.exists(os.path.join(CURRENT_DIR, agent['script_path'])):
                    logger.warning(f"Script not found: {agent['script_path']} for agent {agent['name']}")
                    continue
                
                cmd = build_command(agent, agent_lookup)
                logger.info(f"Launching {agent['name']}: {' '.join(cmd)}")
                
                try:
                    proc = subprocess.Popen(
                        cmd,
                        env=dict(os.environ),
                        cwd=str(PROJECT_ROOT)
                    )
                    processes[agent['name']] = proc
                    # Wait a bit between agent startups to avoid race conditions
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Failed to start {agent['name']}: {e}")
    
    return processes

def signal_handler(sig, frame, processes):
    """Handle shutdown signals."""
    logger.info("Shutting down all agents...")
    for name, proc in processes.items():
        try:
            proc.terminate()
        except:
            pass
    logger.info("Shutdown complete.")
    sys.exit(0)

def main():
    """Main function to launch the AI system."""
    # Kill any existing processes
    kill_existing_processes()
    
    # Create necessary directories
    os.makedirs("logs", exist_ok=True)
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        return
    
    # Launch agents
    processes = launch_agents_in_order(config)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, lambda sig, frame: signal_handler(sig, frame, processes))
    signal.signal(signal.SIGTERM, lambda sig, frame: signal_handler(sig, frame, processes))
    
    # Keep the main process running
    logger.info("All agents launched. Monitoring...")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None, processes)

if __name__ == "__main__":
    main() 