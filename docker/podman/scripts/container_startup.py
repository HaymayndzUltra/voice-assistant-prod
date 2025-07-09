#!/usr/bin/env python3
import os
import sys
import time
import logging
import subprocess
import yaml
import socket
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("container_startup")

# Global variables
CONTAINER_GROUP = os.environ.get('CONTAINER_GROUP', 'unknown').replace('-', '_')
BASE_DIR = "/app"
PC2_MODE = os.environ.get('PC2_MODE', 'false').lower() == 'true'

# Set the appropriate config paths based on PC2_MODE
if PC2_MODE:
    logger.info("Running in PC2 mode")
    STARTUP_CONFIG = os.path.join(BASE_DIR, "pc2_code/config/startup_config.yaml")
    CONTAINER_GROUPS_CONFIG = os.path.join(BASE_DIR, "pc2_code/config/container_grouping.yaml")
else:
    logger.info("Running in MainPC mode")
    STARTUP_CONFIG = os.path.join(BASE_DIR, "main_pc_code/config/startup_config.yaml")
    CONTAINER_GROUPS_CONFIG = os.path.join(BASE_DIR, "main_pc_code/config/container_groups.yaml")

def setup_environment():
    """Set up environment variables from global settings"""
    try:
        if os.path.exists(STARTUP_CONFIG):
            with open(STARTUP_CONFIG, 'r') as f:
                config = yaml.safe_load(f)
                
            if 'global_settings' in config and 'environment' in config['global_settings']:
                for key, value in config['global_settings']['environment'].items():
                    os.environ[key] = str(value)
                    logger.info(f"Set environment variable {key}={value}")
                    
        # Set additional environment variables
        os.environ["LOG_DIR"] = os.path.join(BASE_DIR, "logs")
        os.environ["DATA_DIR"] = os.path.join(BASE_DIR, "data")
        os.environ["MODELS_DIR"] = os.path.join(BASE_DIR, "models")
        
        return True
    except Exception as e:
        logger.error(f"Failed to set up environment: {e}")
        return False

def load_container_groups():
    """Load container group definitions"""
    try:
        if os.path.exists(CONTAINER_GROUPS_CONFIG):
            with open(CONTAINER_GROUPS_CONFIG, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Container groups config not found: {CONTAINER_GROUPS_CONFIG}")
            return {}
    except Exception as e:
        logger.error(f"Error loading container groups: {e}")
        return {}

def load_agents_for_group():
    """Load agents for this container group"""
    try:
        # First try to load from container_grouping.yaml (PC2) or container_groups.yaml (MainPC)
        container_groups = load_container_groups()
        
        if PC2_MODE:
            # PC2 mode - use container_groups["container_groups"][group_name]
            if "container_groups" in container_groups and CONTAINER_GROUP in container_groups["container_groups"]:
                group_config = container_groups["container_groups"][CONTAINER_GROUP]
                agents_list = group_config.get("agents", [])
                
                # Convert to dictionary format expected by the rest of the code
                agents = {}
                for agent in agents_list:
                    agent_name = agent["name"]
                    agents[agent_name] = {
                        "script_path": agent["script_path"],
                        "port": agent["port"],
                        "required": agent.get("required", True),
                        "priority": agent.get("priority", "medium")
                    }
                
                logger.info(f"Found {len(agents)} agents for group {CONTAINER_GROUP} in container_grouping.yaml")
                return agents
            
            # If not found in container_grouping.yaml, try mapping from container_mapping
            if "container_mapping" in container_groups:
                container_name = CONTAINER_GROUP.replace('_', '-')  # Convert back to hyphenated format
                if container_name in container_groups["container_mapping"]:
                    group_name = container_groups["container_mapping"][container_name]
                    if group_name in container_groups:
                        agent_names = container_groups[group_name]
                        
                        # Now we need to look up these agents in startup_config.yaml
                        if os.path.exists(STARTUP_CONFIG):
                            with open(STARTUP_CONFIG, 'r') as f:
                                startup_config = yaml.safe_load(f)
                                
                            agents = {}
                            if 'pc2_services' in startup_config:
                                for agent_config in startup_config['pc2_services']:
                                    if isinstance(agent_config, dict) and 'name' in agent_config:
                                        if agent_config['name'] in agent_names:
                                            agents[agent_config['name']] = agent_config
                            
                            logger.info(f"Found {len(agents)} agents for group {CONTAINER_GROUP} via container_mapping")
                            return agents
        else:
            # MainPC mode - direct lookup in container_groups.yaml
            if CONTAINER_GROUP in container_groups:
                agent_names = container_groups[CONTAINER_GROUP]
                
                # Now we need to look up these agents in startup_config.yaml
                if os.path.exists(STARTUP_CONFIG):
                    with open(STARTUP_CONFIG, 'r') as f:
                        startup_config = yaml.safe_load(f)
                        
                    agents = {}
                    if 'agent_groups' in startup_config and CONTAINER_GROUP in startup_config['agent_groups']:
                        agents = startup_config['agent_groups'][CONTAINER_GROUP]
                        logger.info(f"Found {len(agents)} agents for group {CONTAINER_GROUP} in startup_config.yaml")
                        return agents
        
        # Fallback to direct lookup in startup_config.yaml
        if os.path.exists(STARTUP_CONFIG):
            with open(STARTUP_CONFIG, 'r') as f:
                config = yaml.safe_load(f)
                
            if PC2_MODE:
                # PC2 mode - look for pc2_services
                if 'pc2_services' in config:
                    # Filter agents by container group (using naming convention)
                    group_prefix = CONTAINER_GROUP.replace('pc2_', '')
                    agents = {}
                    for agent_config in config['pc2_services']:
                        if isinstance(agent_config, dict) and 'name' in agent_config:
                            # Simple heuristic - add agent if its name contains the group prefix
                            # This is a fallback and not ideal
                            if group_prefix.lower() in agent_config['name'].lower():
                                agents[agent_config['name']] = agent_config
                    
                    if agents:
                        logger.info(f"Found {len(agents)} agents for group {CONTAINER_GROUP} using name matching")
                        return agents
            else:
                # MainPC mode - look for agent_groups
                if 'agent_groups' in config and CONTAINER_GROUP in config['agent_groups']:
                    agents = config['agent_groups'][CONTAINER_GROUP]
                    logger.info(f"Found {len(agents)} agents for group {CONTAINER_GROUP}")
                    return agents
            
        logger.warning(f"No configuration for group '{CONTAINER_GROUP}' found")
        return {}
    except Exception as e:
        logger.error(f"Error loading agent configuration: {e}")
        return {}

def start_agent(agent_name, agent_config):
    """Start an individual agent"""
    script_path = agent_config.get('script_path')
    if not script_path:
        logger.error(f"No script path for agent {agent_name}")
        return None
        
    # Make path absolute if it's not
    if not script_path.startswith('/'):
        script_path = os.path.join(BASE_DIR, script_path)
        
    # Check if script exists
    if not os.path.exists(script_path):
        logger.warning(f"Agent script not found: {script_path}")
        # Create a placeholder agent script
        try:
            os.makedirs(os.path.dirname(script_path), exist_ok=True)
            with open(script_path, 'w') as f:
                f.write(f"""#!/usr/bin/env python3
import time
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("{agent_name}")

logger.info("Starting {agent_name} placeholder agent")
logger.info("Container group: {CONTAINER_GROUP}")
logger.info("This is a placeholder agent until the actual agent implementation is provided")

# Keep the container running
while True:
    logger.info("{agent_name} is running...")
    time.sleep(60)
""")
            os.chmod(script_path, 0o755)  # Make it executable
            logger.info(f"Created placeholder script for {agent_name} at {script_path}")
        except Exception as e:
            logger.error(f"Failed to create placeholder script: {e}")
            return None
        
    # Set agent-specific environment variables
    env = os.environ.copy()
    env['AGENT_NAME'] = agent_name
    env['AGENT_PORT'] = str(agent_config.get('port', 0))
    env['HEALTH_CHECK_PORT'] = str(agent_config.get('health_check_port', 0))
    
    logger.info(f"Starting agent: {agent_name} from {script_path}")
    try:
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=env
        )
        logger.info(f"Started {agent_name} with PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Failed to start agent {agent_name}: {e}")
        return None

def check_dependencies_status(dependencies):
    """Check if dependencies are running or need to be mocked"""
    if not dependencies:
        return True  # No dependencies
    
    # In a real implementation, we would check if these services are available
    # For now, just return True if we're in MainPC mode, and False if we're in PC2 mode
    # and have dependencies that are likely on MainPC
    if PC2_MODE:
        mainpc_dependencies = [name for name in dependencies if name in ['SystemDigitalTwin', 'MemoryOrchestratorService']]
        if mainpc_dependencies:
            logger.warning(f"PC2 agent has MainPC dependencies: {mainpc_dependencies}")
            return False
    
    return True

def main():
    """Main function to start all agents for this container group"""
    logger.info(f"Starting container for group: {CONTAINER_GROUP}")
    logger.info(f"PC2 mode: {PC2_MODE}")
    
    # Setup environment
    if not setup_environment():
        logger.error("Failed to set up environment")
        sys.exit(1)
    
    # Load agents for this group
    agents = load_agents_for_group()
    if not agents:
        logger.warning(f"No agents found for group {CONTAINER_GROUP}")
        logger.info("Creating placeholder agent to keep container running")
        
        # Create a placeholder agent to keep the container running
        placeholder_process = subprocess.Popen(
            [sys.executable, "-c", f"""
import time
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("placeholder")
logger.info("Starting placeholder process for {CONTAINER_GROUP}")
while True:
    logger.info("{CONTAINER_GROUP} placeholder is running...")
    time.sleep(60)
"""],
            env=os.environ.copy()
        )
        
        try:
            placeholder_process.wait()
        except KeyboardInterrupt:
            placeholder_process.terminate()
        sys.exit(0)
        
    # Start all agents
    processes = []
    for agent_name, agent_config in agents.items():
        # Check if agent has dependencies
        dependencies = agent_config.get('dependencies', [])
        
        # If agent has dependencies that are not available, log a warning
        if dependencies and not check_dependencies_status(dependencies):
            logger.warning(f"Agent {agent_name} has dependencies that may not be available: {dependencies}")
            logger.warning(f"Starting agent anyway, it may not function correctly")
            
        process = start_agent(agent_name, agent_config)
        if process:
            processes.append((process, agent_name))
    
    if not processes:
        logger.error("Failed to start any agents")
        sys.exit(1)
        
    logger.info(f"Started {len(processes)} agents for group {CONTAINER_GROUP}")
    
    # Monitor and restart processes if they die
    try:
        while True:
            for i, (process, name) in enumerate(processes[:]):
                if process.poll() is not None:
                    exit_code = process.poll()
                    logger.warning(f"Agent {name} terminated with code {exit_code}")
                    
                    # Get output from the process
                    output, _ = process.communicate()
                    logger.info(f"Agent output: {output}")
                    
                    # Check if we should restart the agent
                    # Don't restart if process exited with code 0 (clean exit)
                    if exit_code != 0:
                        logger.info(f"Restarting agent {name}")
                        new_process = start_agent(name, agents[name])
                        if new_process:
                            processes[i] = (new_process, name)
                        else:
                            logger.error(f"Failed to restart agent {name}")
                    else:
                        logger.info(f"Agent {name} will not be automatically restarted")
                        
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutting down all agents")
        for process, _ in processes:
            process.terminate()

if __name__ == "__main__":
    main() 