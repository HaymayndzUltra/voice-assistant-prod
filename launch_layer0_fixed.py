from common.config_manager import get_service_ip, get_service_url, get_redis_url
'\nLayer 0 Agent Launcher with Improved Error Handling\n'
import os
import sys
import time
import yaml
import subprocess
import signal
import logging
from pathlib import Path
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler(), logging.FileHandler('layer0_launcher.log')])
logger = logging.getLogger('Layer0Launcher')
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
processes = []

def load_config():
    """Load the MVS configuration"""
    config_path = os.path.join(SCRIPT_DIR, 'main_pc_code', 'NEWMUSTFOLLOW', 'minimal_system_config_local.yaml')
    if not os.path.exists(config_path):
        logger.error(f'Config file not found: {config_path}')
        return None
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f'Error loading config: {e}')
        return None

def setup_environment():
    """Set up the environment variables needed for the agents"""
    for directory in ['logs', 'data', 'models', 'cache', 'certificates']:
        os.makedirs(directory, exist_ok=True)
    os.environ['MACHINE_TYPE'] = 'MAINPC'
    os.environ['PYTHONPATH'] = f"{os.environ.get('PYTHONPATH', '')}:{SCRIPT_DIR}"
    os.environ['MAIN_PC_IP'] = 'localhost'
    os.environ['PC2_IP'] = 'localhost'
    os.environ['BIND_ADDRESS'] = '0.0.0.0'
    os.environ['SECURE_ZMQ'] = '0'
    os.environ['USE_DUMMY_AUDIO'] = 'true'
    os.environ['ZMQ_REQUEST_TIMEOUT'] = '10000'
    os.environ['CONNECTION_RETRIES'] = '5'
    os.environ['SERVICE_DISCOVERY_TIMEOUT'] = '15000'

def launch_agent(agent_config):
    """Launch a single agent"""
    name = agent_config.get('name')
    file_path = agent_config.get('file_path')
    if not file_path:
        logger.error(f'No file path specified for {name}')
        return None
    if os.path.isabs(file_path):
        full_path = file_path
    else:
        search_dirs = [os.path.join(SCRIPT_DIR, 'main_pc_code', 'agents'), os.path.join(SCRIPT_DIR, 'main_pc_code', 'FORMAINPC'), os.path.join(SCRIPT_DIR, 'main_pc_code', 'src', 'core'), os.path.join(SCRIPT_DIR, 'main_pc_code', 'src', 'memory'), os.path.join(SCRIPT_DIR, 'main_pc_code', 'src', 'audio'), os.path.join(SCRIPT_DIR, 'main_pc_code'), SCRIPT_DIR]
        for directory in search_dirs:
            candidate_path = os.path.join(directory, file_path)
            if os.path.exists(candidate_path):
                full_path = candidate_path
                break
        else:
            logger.error(f'Could not find {file_path} for {name}')
            return None
    try:
        cmd = [sys.executable, full_path]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)
        logger.info(f'Launched {name} (PID: {process.pid})')
        return process
    except Exception as e:
        logger.error(f'Failed to launch {name}: {e}')
        return None

def main():
    """Main function"""
    setup_environment()
    config = load_config()
    if not config:
        logger.error('Failed to load configuration')
        return
    all_agents = []
    if 'core_agents' in config:
        all_agents.extend(config['core_agents'])
    if 'dependencies' in config:
        all_agents.extend(config['dependencies'])
    for agent_config in all_agents:
        name = agent_config.get('name')
        process = launch_agent(agent_config)
        if process:
            processes.append((name, process))
            logger.info(f'Started {name}')
            time.sleep(2)
        else:
            logger.info(f'Failed to start {name}')
    logger.info(f'Launched {len(processes)} agents')
    try:
        logger.info('Press Ctrl+C to stop all agents')
        while True:
            time.sleep(1)
            for name, process in list(processes):
                if process.poll() is not None:
                    logger.info(f'Agent {name} has terminated with code {process.returncode}')
                    processes.remove((name, process))
            if not processes:
                logger.info('All agents have terminated')
                break
    except KeyboardInterrupt:
        logger.info('Stopping all agents...')
        for name, process in processes:
            logger.info(f'Stopping {name}...')
            try:
                process.terminate()
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
    logger.info('All agents stopped')
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Interrupted by user')
    except Exception as e:
        logger.error(f'Error: {e}')