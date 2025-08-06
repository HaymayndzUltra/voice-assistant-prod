import os
import sys
import subprocess
import time
import logging
from dotenv import load_dotenv
from pathlib import Path
from common.utils.log_setup import configure_logging

# Load environment variables
load_dotenv()
PC2_HOST = os.getenv('PC2_HOST', 'localhost')

# Configure logging
logger = configure_logging(__name__)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Define paths
MAIN_PC_CODE = os.path.abspath(os.path.dirname(__file__))

# Define services directly in code instead of loading from YAML
SERVICES = {
    'core_services': [
        {'name': 'TaskRouter', 'script_path': 'src/core/task_router.py', 'host': 'localhost', 'port': 8570, 'required': True},
        {'name': 'ModelManagerAgent', 'script_path': 'agents/model_manager_agent.py', 'host': 'localhost', 'port': 5570, 'required': True}
    ],
    'main_pc_gpu_services': [
        {'name': 'EnhancedModelRouter', 'script_path': 'FORMAINPC/EnhancedModelRouter.py', 'host': 'localhost', 'port': 5598, 'required': True},
        {'name': 'TinyLlamaService', 'script_path': 'FORMAINPC/TinyLlamaServiceEnhanced.py', 'host': 'localhost', 'port': 5615, 'required': True}
    ]
}

SERVICE_GROUPS = [
    'core_services',
    'main_pc_gpu_services'
]

def build_agent_lookup():
    """Build a lookup dictionary of all agents."""
    lookup = {}
    for group in SERVICE_GROUPS:
        for agent in SERVICES.get(group, []):
            lookup[agent['name']] = agent
    return lookup

def build_command(agent, agent_lookup):
    """Build command to launch an agent."""
    # Prefix script path with main_pc_code/ since we're launching from project root
    script_path = os.path.join(MAIN_PC_CODE, agent['script_path'])
    cmd = [sys.executable, script_path, '--port', str(agent['port'])]
    # Add dependencies as CLI args
    for dep in agent.get('dependencies', []):
        dep_cfg = agent_lookup.get(dep)
        if not dep_cfg:
            logger.warning(f"Dependency '{dep}' not found for agent '{agent['name']}'")
            continue
        cmd += [f'--{dep}_host', dep_cfg.get('host', 'localhost'), f'--{dep}_port', str(dep_cfg['port'])]
    return cmd

def main():
    """Main function to launch all agents."""
    agent_lookup = build_agent_lookup()
    processes = {}
    
    for group in SERVICE_GROUPS:
        for agent in SERVICES.get(group, []):
            cmd = build_command(agent, agent_lookup)
            logger.info(f"Launching {agent['name']}: {' '.join(cmd)}")
            # Launch from project root so agents can import from src and utils
            proc = subprocess.Popen(cmd, cwd=str(Path('.').resolve()))
            processes[agent['name']] = proc
            time.sleep(1)  # Stagger launches
            
    logger.info("All agents launched. Monitoring...")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Shutting down all agents...")
        for name, proc in processes.items():
            proc.terminate()
        logger.info("Shutdown complete.")

if __name__ == '__main__':
    main()