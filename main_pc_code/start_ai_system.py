import yaml
import psutil  # Added for duplicate-process detection
import subprocess
import time
import os
import sys
import signal
import logging
from typing import Dict, List
import socket
import threading
from pathlib import Path
import json
import zmq
from datetime import datetime
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# IP configuration (update as network changes)
# ---------------------------------------------------------------------------
MAIN_PC_IP = "192.168.100.16"
PC2_IP   = "192.168.100.17"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_system.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AgentManager:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.processes: Dict[str, subprocess.Popen] = {}
        self.health_check_threads: Dict[str, threading.Thread] = {}
        self.running = True
        self.load_config()
        # Build quick-lookup maps for agents on each machine for dependency resolution
        self.main_pc_agents = {a['name']: a for a in self.config.get('main_pc_agents', [])}
        self.pc2_agents     = {a['name']: a for a in self.config.get('pc2_agents', [])}
        # Combine for quick lookup
        self.agent_lookup: Dict[str, dict] = {**self.main_pc_agents, **self.pc2_agents}
        
        # Define service groups for dependency ordering
        self.service_groups = [
            ('main_pc_gpu_services', 'GPU Services'),
            ('emotion_system', 'Emotion System'),
            ('language_processing', 'Language Processing'),
            ('memory_system', 'Memory System'),
            ('learning_knowledge', 'Learning & Knowledge'),
            ('planning_execution', 'Planning & Execution'),
            ('tts_services', 'TTS Services'),
            ('code_generation', 'Code Generation'),
            ('audio_processing', 'Audio Processing'),
            ('vision', 'Vision'),
            ('monitoring_security', 'Monitoring & Security')
        ]

    def load_config(self):
        """Load the YAML configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
                if not self.config:
                    raise ValueError("Empty configuration file")
                
                # Validate required sections
                required_sections = ['core_services', 'main_pc_gpu_services', 'emotion_system', 
                                   'language_processing', 'memory_system', 'learning_knowledge']
                missing_sections = [section for section in required_sections if section not in self.config]
                if missing_sections:
                    raise ValueError(f"Missing required sections in config: {missing_sections}")
                    
                logger.info("Configuration loaded successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)

    def _build_command(self, agent_config: dict) -> List[str]:
        """Construct the subprocess command with dynamic CLI args (host / port + deps)."""
        cmd: List[str] = [
            sys.executable,
            agent_config['script_path'],
            '--port', str(agent_config['port']),
            '--host', MAIN_PC_IP  # all launches originate from main PC
        ]

        # Resolve dependencies if present
        for dep_name in agent_config.get('dependencies', []):
            dep_cfg = self.agent_lookup.get(dep_name)
            if not dep_cfg:
                logger.warning(f"Dependency '{dep_name}' not found in configuration – skipping arg pass.")
                continue
            # Decide host IP for the dependency based on which list it belonged to
            dep_host_ip = MAIN_PC_IP if dep_name in self.main_pc_agents else PC2_IP
            key_prefix = dep_name.lower()
            cmd.extend([
                f'--{key_prefix}_host', dep_host_ip,
                f'--{key_prefix}_port', str(dep_cfg['port'])
            ])
        return cmd

    def is_port_available(self, port: int, host: str = '127.0.0.1') -> bool:
        """Check if a port is available."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex((host, port))
                if result == 0:
                    logger.warning(f"Port {port} is already in use")
                    return False
                return True
        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
            return False

    def _is_agent_running(self, script_path: str) -> bool:
        """Return True if a process with given script is already running."""
        for proc in psutil.process_iter(attrs=["cmdline"]):
            try:
                cmd = proc.info["cmdline"] or []
                if any(script_path in part for part in cmd):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def start_agent(self, agent_config: dict, is_pc2: bool = False) -> bool:
        """Start a single agent process."""
        name = agent_config['name']
        script_path = agent_config['script_path']
        host = agent_config['host']
        port = agent_config['port']
        health_port = port + 1

        # Skip launch if process already running (prevents duplicates)
        if self._is_agent_running(script_path):
            logger.warning(f"{name} already running – skipping duplicate launch")
            return True

        # Check if both main port and health check port are available
        if not self.is_port_available(port) or not self.is_port_available(health_port):
            logger.error(f"Ports {port} or {health_port} are already in use for agent {name}")
            return False

        try:
            # Build command with dynamic CLI args
            cmd = self._build_command(agent_config)
            logger.debug(f"Launching {name}: {' '.join(cmd)}")
            
            # Prepare environment with updated PYTHONPATH
            process_env = os.environ.copy()
            project_root = os.path.dirname(os.path.abspath(__file__))
            orig_ppath = process_env.get('PYTHONPATH', '')
            process_env['PYTHONPATH'] = (
                f"{project_root}" if not orig_ppath else f"{project_root}{os.pathsep}{orig_ppath}"
            )
            
            # Start the agent process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=process_env,
                cwd=project_root
            )
            
            # Wait a bit to ensure process starts
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                logger.error(f"Agent {name} failed to start. Exit code: {process.returncode}")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False
            
            self.processes[name] = process
            logger.info(f"Started agent {name} with PID {process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start agent {name}: {e}")
            return False

    def health_check(self, agent_name: str, max_retries: int = 3) -> bool:
        """Perform health check for an agent with retry logic.
        
        Args:
            agent_name: Name of the agent to check
            max_retries: Maximum number of retry attempts
            
        Returns:
            bool: True if agent is healthy, False otherwise
        """
        if agent_name not in self.processes:
            logger.error(f"Agent {agent_name} process not found")
            return False
        
        process = self.processes[agent_name]
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # First check if process is still running
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    logger.error(f"Agent {agent_name} process died. Exit code: {process.returncode}")
                    logger.error(f"STDOUT: {stdout}")
                    logger.error(f"STDERR: {stderr}")
                    return False
                
                # Create ZMQ socket for health check
                context = zmq.Context()
                socket = context.socket(zmq.REQ)
                socket.setsockopt(zmq.LINGER, 0)
                socket.setsockopt(zmq.RCVTIMEO, 5000)  # 5 second timeout
                
                # Get agent port from config
                agent_config = next((s for s in self.config.get('core_services', []) 
                                   if s['name'] == agent_name), None)
                if not agent_config:
                    for group, _ in self.service_groups:
                        agent_config = next((s for s in self.config.get(group, []) 
                                           if s['name'] == agent_name), None)
                        if agent_config:
                            break
                
                if not agent_config:
                    logger.error(f"Could not find configuration for agent {agent_name}")
                    return False
                    
                port = agent_config['port']
                socket.connect(f"tcp://localhost:{port}")
                
                # Send health check request
                request = {
                    "action": "health_check",
                    "timestamp": datetime.now().isoformat()
                }
                socket.send_json(request)
                
                # Wait for response
                response = socket.recv_json()
                
                # Check response
                if response.get("status") == "ok":
                    logger.info(f"Health check passed for {agent_name}")
                    return True
                    
                logger.warning(f"Unhealthy response from {agent_name}: {response}")
                
            except zmq.error.ZMQError as e:
                logger.error(f"ZMQ error in health check for {agent_name} (attempt {retry_count + 1}/{max_retries}): {e}")
            except Exception as e:
                logger.error(f"Error in health check for {agent_name} (attempt {retry_count + 1}/{max_retries}): {e}")
            finally:
                try:
                    socket.close()
                    context.term()
                except:
                    pass
            
            retry_count += 1
            if retry_count < max_retries:
                delay = 2 ** retry_count  # Exponential backoff
                logger.info(f"Retrying health check for {agent_name} in {delay} seconds...")
                time.sleep(delay)
        
        logger.error(f"Health check failed for {agent_name} after {max_retries} retries")
        return False

    def start_health_check(self, agent_name: str, host: str, port: int):
        """Start a health check thread for an agent."""
        thread = threading.Thread(
            target=self.health_check,
            args=(agent_name,),
            daemon=True
        )
        thread.start()
        self.health_check_threads[agent_name] = thread

    def start_all_agents(self):
        """Start all agents defined in the configuration."""
        logger.info("Starting all agents...")
        
        # First start core services
        core_services = self.config.get('core_services', [])
        if not core_services:
            logger.error("No core services defined in configuration")
            sys.exit(1)
        
        # Start and verify core services first
        for service in core_services:
            name = service['name']
            logger.info(f"Starting core service: {name}")
            
            # Auto-heal on start failure: retry up to 3 times, with port-in-use detection and adaptive wait
            start_attempts = 0
            max_start_attempts = 3
            while start_attempts < max_start_attempts:
                started = self.start_agent(service)
                if started:
                    break
                start_attempts += 1
                # Check for port in use in logs
                last_log = ''
                try:
                    with open('ai_system.log', 'r') as logf:
                        last_log = logf.readlines()[-10:]
                        if any('Address already in use' in l for l in last_log):
                            logger.warning(f"Port in use for {name} (attempt {start_attempts}/{max_start_attempts}), waiting 5s for port release...")
                            time.sleep(5)
                        else:
                            logger.warning(f"Start failed for {name} (attempt {start_attempts}/{max_start_attempts}), retrying in 2s...")
                            time.sleep(2)
                except Exception:
                    logger.warning(f"Start failed for {name} (attempt {start_attempts}/{max_start_attempts}), retrying in 2s...")
                    time.sleep(2)
            if start_attempts >= max_start_attempts:
                logger.error(f"Failed to start core service {name} after {max_start_attempts} attempts")
                self.stop_all_agents()
                sys.exit(1)
            
            # Wait for service to initialize and verify health
            max_retries = 5
            retry_count = 0
            while retry_count < max_retries:
                if self.health_check(name):
                    logger.info(f"Core service {name} started and healthy")
                    break
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(f"Waiting {wait_time}s for {name} to initialize...")
                    time.sleep(wait_time)
            
            if retry_count >= max_retries:
                logger.error(f"Core service {name} failed health check")
                self.stop_all_agents()
                sys.exit(1)
        
        # Start remaining services in dependency order
        service_groups = [
            ('main_pc_gpu_services', 'GPU Services'),
            ('emotion_system', 'Emotion System'),
            ('language_processing', 'Language Processing'),
            ('memory_system', 'Memory System'),
            ('learning_knowledge', 'Learning & Knowledge'),
            ('planning_execution', 'Planning & Execution'),
            ('tts_services', 'TTS Services'),
            ('code_generation', 'Code Generation'),
            ('audio_processing', 'Audio Processing'),
            ('vision', 'Vision'),
            ('monitoring_security', 'Monitoring & Security')
        ]
        
        started_services = set()
        for config_key, group_name in service_groups:
            services = self.config.get(config_key, [])
            if not services:
                logger.warning(f"No services defined for {group_name}")
                continue
            
            logger.info(f"Starting {group_name}...")
            for service in services:
                name = service['name']
                if name in started_services:
                    continue
                
                # Check if dependencies are satisfied
                dependencies = service.get('dependencies', [])
                missing_deps = [dep for dep in dependencies if dep not in started_services]
                if missing_deps:
                    logger.error(f"Cannot start {name}, missing dependencies: {missing_deps}")
                    continue
                
                logger.info(f"Starting service: {name}")
                if not self.start_agent(service):
                    logger.error(f"Failed to start service {name}")
                    continue
                
                # Verify health with retries
                max_retries = 3
                retry_count = 0
                while retry_count < max_retries:
                    if self.health_check(name):
                        logger.info(f"Service {name} started and healthy")
                        started_services.add(name)
                        break
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 2 ** retry_count
                        logger.info(f"Waiting {wait_time}s for {name} to initialize...")
                        time.sleep(wait_time)
                
                if retry_count >= max_retries:
                    logger.error(f"Service {name} failed health check")
        
        # Start health check monitoring thread
        logger.info("Starting health check monitoring loop")
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
        
        if len(started_services) < len([s for group, _ in service_groups for s in self.config.get(group, [])]):
            logger.warning("Some services failed to start")
        else:
            logger.info("All services started successfully")

    def _health_check_loop(self):
        """Continuous health check loop for all agents."""
        logger.info("Starting health check monitoring loop")
        
        while self.running:
            try:
                for agent_name in self.processes:
                    if not self.health_check(agent_name, max_retries=1):
                        logger.error(f"Agent {agent_name} failed routine health check")
                        # TODO: Implement recovery logic here
                        
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                time.sleep(5)  # Wait before retrying

    def stop_all_agents(self):
        """Stop all running agent processes."""
        self.running = False
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Stopped agent {name}")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning(f"Force killed agent {name}")
            except Exception as e:
                logger.error(f"Error stopping agent {name}: {e}")

    def signal_handler(self, signum, frame):
        """Handle termination signals."""
        logger.info("Received termination signal")
        self.stop_all_agents()
        sys.exit(0)

def start_ultimate_tts_agent():
    """Start the Ultimate TTS Agent (streaming_tts_agent.py) in a subprocess."""
    try:
        # Use the script_path exactly as defined in startup_config.yaml
        script_path = 'agents/streaming_tts_agent.py'
        if not os.path.exists(script_path):
            print(f"Ultimate TTS Agent script not found: {script_path}")
            return
        # Prepare environment and launch the agent ensuring correct context
        process_env = os.environ.copy()
        project_root = os.path.dirname(os.path.abspath(__file__))
        orig_ppath = process_env.get('PYTHONPATH', '')
        process_env['PYTHONPATH'] = (
            f"{project_root}" if not orig_ppath else f"{project_root}{os.pathsep}{orig_ppath}"
        )
        subprocess.Popen([
            sys.executable,
            script_path
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=process_env,
        cwd=project_root)
        print("Ultimate TTS Agent started.")
    except Exception as e:
        print(f"Failed to start Ultimate TTS Agent: {e}")

def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    # Initialize and start the agent manager
    config_path = os.path.join('config', 'startup_config.yaml')
    manager = AgentManager(config_path)
    
    try:
        manager.start_all_agents()
        logger.info("All agents started successfully")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    finally:
        manager.stop_all_agents()

if __name__ == "__main__":
    start_ultimate_tts_agent()
    main()