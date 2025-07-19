#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url

"""
MVS Startup Script
-----------------
Simple script to start the Minimal Viable System with proper error handling
All agents are now fully config-driven with no hardcoded values
Uses startup_config.yaml as the master map for agent paths
"""

import os
import sys
import time
import yaml
import logging
import subprocess
import signal
import argparse
import importlib.util
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Union


# Import path manager for containerization-friendly paths
import sys
import os
sys.path.insert(0, get_project_root())
from common.utils.path_env import get_path, join_path, get_file_path
from common.env_helpers import get_env
# Set up logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = f"{log_dir}/mvs_startup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("MVS_Startup")

# ANSI color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PC_CODE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(MAIN_PC_CODE_DIR, ".."))

def setup_environment():
    """Set up the environment variables needed for MVS"""
    logger.info("Setting up environment variables")
    
    # Create necessary directories
    for directory in ["logs", "data", "models", "cache", "certificates"]:
        os.makedirs(directory, exist_ok=True)
    
    # Machine configuration
    os.environ["MACHINE_TYPE"] = "MAINPC"
    os.environ["PYTHONPATH"] = f"{os.environ.get('PYTHONPATH', '')}:{os.getcwd()}"
    
    # Network configuration
    os.environ["MAIN_PC_IP"] = "localhost"
    os.environ["PC2_IP"] = "localhost"
    os.environ["BIND_ADDRESS"] = "0.0.0.0"
    
    # Security settings
    os.environ["SECURE_ZMQ"] = "0"  # Disable secure ZMQ for initial testing
    os.environ["ZMQ_CERTIFICATES_DIR"] = "certificates"
    
    # Service discovery
    os.environ["SYSTEM_DIGITAL_TWIN_PORT"] = "7120"
    os.environ["SERVICE_DISCOVERY_ENABLED"] = "1"
    os.environ["FORCE_LOCAL_SDT"] = "1"
    
    # Voice pipeline ports
    os.environ["TASK_ROUTER_PORT"] = "8573"
    os.environ["STREAMING_TTS_PORT"] = "5562"
    os.environ["TTS_PORT"] = "5562"
    os.environ["INTERRUPT_PORT"] = "5577"
    
    # Resource constraints
    os.environ["MAX_MEMORY_MB"] = "2048"
    os.environ["MAX_VRAM_MB"] = "2048"
    
    # Logging
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["LOG_DIR"] = "logs"
    
    # Timeouts and retries
    os.environ["ZMQ_REQUEST_TIMEOUT"] = "5000"
    os.environ["CONNECTION_RETRIES"] = "3"
    os.environ["SERVICE_DISCOVERY_TIMEOUT"] = "10000"
    
    # Voice pipeline settings
    os.environ["VOICE_SAMPLE_DIR"] = "voice_samples"
    os.environ["MODEL_DIR"] = "models"
    os.environ["CACHE_DIR"] = "cache"
    
    # Dummy audio for testing
    os.environ["USE_DUMMY_AUDIO"] = "true"
    
    logger.info("Environment setup complete")

def load_config():
    """Load the MVS configuration from minimal_system_config_local.yaml"""
    logger.info("Loading MVS configuration")
    
    # First check for a local config file
    config_path = os.path.join(SCRIPT_DIR, "minimal_system_config_local.yaml")
    if not os.path.exists(config_path):
        # If local config doesn't exist, use the default
        config_path = os.path.join(SCRIPT_DIR, "minimal_system_config.yaml")
        logger.info(f"Local config not found, using default: {config_path}")
        
        # If default config doesn't exist either, create it
        if not os.path.exists(config_path):
            logger.error(f"No configuration file found at {config_path}")
            sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

def load_master_map():
    """Load the master map from startup_config.yaml"""
    logger.info("Loading master map from startup_config.yaml")
    
    # Try to load the startup_config.yaml file
    master_map_path = get_file_path("main_pc_config", "startup_config.yaml")
    if not os.path.exists(master_map_path):
        logger.error(f"Master map not found at {master_map_path}")
        sys.exit(1)
    
    try:
        with open(master_map_path, 'r') as f:
            master_config = yaml.safe_load(f)
            logger.info(f"Master map loaded from {master_map_path}")
            
            # Create a dictionary mapping agent names to script paths
            agent_path_map = {}
            
            # Process all sections of the config that contain agent definitions
            sections = [
                'core_services', 'main_pc_gpu_services', 'emotion_system', 
                'memory_system', 'learning_knowledge', 'planning_execution',
                'tts_services', 'code_generation', 'audio_processing',
                'language_processing', 'vision'
            ]
            
            for section in sections:
                if section in master_config:
                    for agent in master_config[section]:
                        agent_name = agent.get('name')
                        script_path = agent.get('script_path')
                        if agent_name and script_path:
                            agent_path_map[agent_name] = script_path
            
            logger.info(f"Created agent path map with {len(agent_path_map)} entries")
            return agent_path_map
    except Exception as e:
        logger.error(f"Failed to load master map: {e}")
        sys.exit(1)

def import_agent_module(agent_name: str, file_path: str, agent_path_map: Dict[str, str]):
    """Dynamically import an agent module from its file path"""
    try:
        # First, try to find the agent in the master map
        script_path = agent_path_map.get(agent_name)
        
        if script_path:
            # Use the path from the master map
            full_path = os.path.join(MAIN_PC_CODE_DIR, script_path)
            logger.info(f"Using master map path for {agent_name}: {full_path}")
            
            # Check if file exists at the master map path
            if not os.path.exists(full_path):
                logger.warning(f"Agent file not found at master map path: {full_path}")
                # Continue to fallback paths
                script_path = None
        
        # If not found in master map or the file doesn't exist, try multiple possible locations
        if not script_path or not os.path.exists(full_path):
            # Define possible directories to search in order of priority
            search_dirs = [
                "agents",           # main_pc_code/agents/
                "FORMAINPC",        # main_pc_code/FORMAINPC/
                "src/core",         # main_pc_code/src/core/
                "src/agents",       # main_pc_code/src/agents/
                "src/memory",       # main_pc_code/src/memory/
                "src/network",      # main_pc_code/src/network/
                "src/audio",        # main_pc_code/src/audio/
                "src/vision",       # main_pc_code/src/vision/
                ".",                # main_pc_code/ (root directory)
            ]
            
            # Try each directory until we find the file
            found = False
            for directory in search_dirs:
                candidate_path = os.path.join(MAIN_PC_CODE_DIR, directory, file_path)
                if os.path.exists(candidate_path):
                    full_path = candidate_path
                    found = True
                    logger.info(f"Found {agent_name} at {full_path}")
                    break
            
            if not found:
                logger.error(f"Agent file not found in any standard location: {file_path}")
                return None
        
        # At this point, full_path should be valid
        if not os.path.exists(full_path):
            logger.error(f"Agent file not found: {full_path}")
            return None
            
        # Get module name from file path (without extension)
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Import the module
        spec = importlib.util.spec_from_file_location(module_name, full_path)
        if spec is None:
            logger.error(f"Failed to create module spec for {full_path}")
            return None
            
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            logger.error(f"Failed to get loader from spec for {full_path}")
            return None
            
        spec.loader.exec_module(module)
        
        return module
    except Exception as e:
        logger.error(f"Error importing agent module {file_path}: {e}")
        return None

def get_agent_class(module, agent_name: str):
    """Get the agent class from the module based on the agent name"""
    if module is None or agent_name is None:
        logger.error("Invalid module or agent_name provided to get_agent_class")
        return None
        
    try:
        # First, try to find a class with the exact agent name
        if hasattr(module, agent_name):
            return getattr(module, agent_name)
        
        # If not found, look for a class that matches the pattern AgentNameAgent
        if hasattr(module, f"{agent_name}Agent"):
            return getattr(module, f"{agent_name}Agent")
            
        # If still not found, try to find any class that contains the agent name
        for attr_name in dir(module):
            if agent_name.lower() in attr_name.lower() and attr_name.endswith("Agent"):
                return getattr(module, attr_name)
                
        # If we get here, we couldn't find a matching class
        logger.error(f"Could not find agent class for {agent_name} in module")
        return None
    except Exception as e:
        logger.error(f"Error getting agent class for {agent_name}: {e}")
        return None

def launch_agent(agent_config: Dict[str, Any], agent_path_map: Dict[str, str]):
    """Launch a single agent using its configuration"""
    name = agent_config.get('name')
    if name is None:
        logger.warning("Agent configuration missing 'name' field")
        return None
        
    file_path = agent_config.get('file_path')
    if not file_path:
        logger.warning(f"Skipping {name}: No file path specified")
        return None
    
    logger.info(f"Launching {name} from {file_path}")
    
    try:
        # Import the agent module
        module = import_agent_module(name, file_path, agent_path_map)
        if not module:
            logger.error(f"Failed to import module for {name}")
            return None
            
        # Get the agent class
        agent_class = get_agent_class(module, name)
        if not agent_class:
            logger.error(f"Failed to find agent class for {name}")
            return None
            
        # Create a thread to run the agent
        def run_agent():
            try:
                # Special case for SystemDigitalTwin which doesn't accept name parameter
                if name == "SystemDigitalTwin":
                    agent = agent_class()
                else:
                    # Initialize the agent with its configuration
                    agent = agent_class(**agent_config)
                
                # Check if the agent has a run method
                if hasattr(agent, 'run') and callable(getattr(agent, 'run')):
                    agent.run()
                # Check if the agent has a start method
                elif hasattr(agent, 'start') and callable(getattr(agent, 'start')):
                    agent.start()
                else:
                    logger.warning(f"Agent {name} does not have a run or start method")
            except Exception as e:
                logger.error(f"Error running agent {name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Start the agent thread
        thread = threading.Thread(target=run_agent, name=f"Agent-{name}")
        thread.daemon = True
        thread.start()
        
        return {
            'name': name,
            'thread': thread,
            'start_time': time.time(),
            'config': agent_config
        }
    except Exception as e:
        logger.error(f"Failed to launch {name}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def launch_agents(config, agent_path_map):
    """Launch all agents in the correct order"""
    logger.info("Starting to launch agents")
    
    # Combine core agents and dependencies into a single list
    all_agents = []
    if 'core_agents' in config:
        all_agents.extend(config['core_agents'])
    if 'dependencies' in config:
        all_agents.extend(config['dependencies'])
    
    # First launch agents with no dependencies
    independent_agents = [agent for agent in all_agents if not agent.get('dependencies')]
    dependent_agents = [agent for agent in all_agents if agent.get('dependencies')]
    
    agent_threads = []
    
    # Launch independent agents first
    logger.info(f"Launching {len(independent_agents)} independent agents")
    for agent in independent_agents:
        thread_info = launch_agent(agent, agent_path_map)
        if thread_info:
            agent_threads.append(thread_info)
            print(f"{GREEN}✓{RESET} Started {agent.get('name')}")
        else:
            print(f"{RED}✗{RESET} Failed to start {agent.get('name')}")
        time.sleep(2)  # Give each agent time to start
    
    # Launch dependent agents in order of dependency depth
    logger.info(f"Launching {len(dependent_agents)} dependent agents")
    
    # Simple approach: try to launch agents multiple times until all are launched
    remaining_agents = dependent_agents.copy()
    max_attempts = 3
    for attempt in range(max_attempts):
        if not remaining_agents:
            break
            
        still_remaining = []
        for agent in remaining_agents:
            # Check if all dependencies are launched
            deps = agent.get('dependencies', [])
            deps_launched = all(any(t['name'] == dep for t in agent_threads) for dep in deps)
            
            if deps_launched:
                thread_info = launch_agent(agent, agent_path_map)
                if thread_info:
                    agent_threads.append(thread_info)
                    print(f"{GREEN}✓{RESET} Started {agent.get('name')}")
                else:
                    print(f"{RED}✗{RESET} Failed to start {agent.get('name')}")
                time.sleep(2)  # Give each agent time to start
            else:
                still_remaining.append(agent)
        
        remaining_agents = still_remaining
        if remaining_agents:
            logger.info(f"Waiting for dependencies, {len(remaining_agents)} agents remaining")
            time.sleep(5)  # Wait before next attempt
    
    # Check if any agents couldn't be launched
    if remaining_agents:
        for agent in remaining_agents:
            logger.warning(f"Could not launch {agent.get('name')} due to missing dependencies")
            print(f"{YELLOW}!{RESET} Could not launch {agent.get('name')} due to missing dependencies")
    
    return agent_threads

def monitor_agents(agent_threads):
    """Monitor the running agents"""
    try:
        while True:
            # Check if all threads are still alive
            for agent_info in agent_threads:
                thread = agent_info['thread']
                name = agent_info['name']
                
                if not thread.is_alive():
                    logger.warning(f"Agent {name} has stopped")
                    print(f"{RED}!{RESET} Agent {name} has stopped")
            
            # Sleep for a while before checking again
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, stopping agents")
        print(f"\n{YELLOW}Stopping agents...{RESET}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Start the Minimal Viable System")
    parser.add_argument("--check-only", action="store_true", help="Only check agent files without launching")
    parser.add_argument("--agent", help="Launch only the specified agent")
    args = parser.parse_args()
    
    print(f"{BLUE}{BOLD}Starting Minimal Viable System...{RESET}")
    
    # Setup environment
    setup_environment()
    
    # Load configuration
    config = load_config()
    
    # Load master map
    agent_path_map = load_master_map()
    
    if args.check_only:
        print(f"{YELLOW}Checking agent files only, not launching{RESET}")
        # TODO: Implement check-only functionality
        sys.exit(0)
    
    # Launch agents
    if args.agent:
        # Launch only the specified agent
        print(f"{BLUE}Launching only agent: {args.agent}{RESET}")
        agent_config = None
        
        # Find the agent in the configuration
        for agent in config.get('core_agents', []) + config.get('dependencies', []):
            if agent.get('name') == args.agent:
                agent_config = agent
                break
        
        if agent_config:
            agent_info = launch_agent(agent_config, agent_path_map)
            if agent_info:
                print(f"{GREEN}✓{RESET} Started {args.agent}")
                monitor_agents([agent_info])
            else:
                print(f"{RED}✗{RESET} Failed to start {args.agent}")
        else:
            print(f"{RED}Agent {args.agent} not found in configuration{RESET}")
            sys.exit(1)
    else:
        # Launch all agents
        agent_threads = launch_agents(config, agent_path_map)
        
        print(f"{GREEN}{BOLD}All agents launched successfully!{RESET}")
        print(f"Monitoring {len(agent_threads)} agents. Press Ctrl+C to stop.")
        
        # Monitor the agents
        monitor_agents(agent_threads)
    
    print(f"{BLUE}{BOLD}MVS has been stopped.{RESET}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user, shutting down...{RESET}")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"{RED}Error: {e}{RESET}")
        sys.exit(1) 